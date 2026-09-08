from __future__ import annotations

import importlib.util
from pathlib import Path
import sys
from tempfile import TemporaryDirectory
import types
import unittest
from unittest.mock import patch


ROOT = Path(__file__).parents[1]
PACKAGE = "comfyui_minimax_h3_remote_test"


def load_node_module():
    for name in tuple(sys.modules):
        if name == PACKAGE or name.startswith(f"{PACKAGE}."):
            sys.modules.pop(name)

    numpy = types.ModuleType("numpy")
    numpy.int16 = object()
    pil = types.ModuleType("PIL")
    pil.Image = object()
    torch = types.ModuleType("torch")
    torch.uint8 = object()

    comfy = types.ModuleType("comfy")
    comfy.__path__ = []
    model_management = types.ModuleType("comfy.model_management")
    model_management.throw_exception_if_processing_interrupted = lambda: None
    utils = types.ModuleType("comfy.utils")
    utils.ProgressBar = lambda total: types.SimpleNamespace(update_absolute=lambda *args: None)
    comfy.model_management = model_management
    comfy.utils = utils

    folder_paths = types.ModuleType("folder_paths")
    folder_paths.get_temp_directory = lambda: "/tmp"
    comfy_api = types.ModuleType("comfy_api")
    comfy_api.__path__ = []
    latest = types.ModuleType("comfy_api.latest")
    latest.InputImpl = types.SimpleNamespace(VideoFromFile=object)
    comfy_api.latest = latest

    sys.modules.update({
        "numpy": numpy,
        "PIL": pil,
        "torch": torch,
        "comfy": comfy,
        "comfy.model_management": model_management,
        "comfy.utils": utils,
        "folder_paths": folder_paths,
        "comfy_api": comfy_api,
        "comfy_api.latest": latest,
    })

    package = types.ModuleType(PACKAGE)
    package.__path__ = [str(ROOT)]
    sys.modules[PACKAGE] = package

    for module_name in ("h3_client", "node"):
        qualified = f"{PACKAGE}.{module_name}"
        spec = importlib.util.spec_from_file_location(qualified, ROOT / f"{module_name}.py")
        assert spec is not None and spec.loader is not None
        module = importlib.util.module_from_spec(spec)
        sys.modules[qualified] = module
        spec.loader.exec_module(module)
    return sys.modules[f"{PACKAGE}.node"]


class NodeContractTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.node_module = load_node_module()

    def test_node_declares_native_comfyui_outputs_and_no_default_secret(self) -> None:
        node = self.node_module.MiniMaxH3Remote
        self.assertEqual(node.RETURN_TYPES, ("VIDEO", "IMAGE", "AUDIO", "FLOAT", "STRING"))
        self.assertEqual(node.RETURN_NAMES, ("video", "frames", "audio", "fps", "job_id"))
        self.assertTrue(node.OUTPUT_NODE)
        self.assertEqual(node.INPUT_TYPES()["required"]["server_url"][1]["default"], "")
        self.assertEqual(node.INPUT_TYPES()["required"]["api_key"][1]["default"], "")

    def test_frame_count_snaps_to_h3_sequence(self) -> None:
        snap = self.node_module._snap_frames
        self.assertEqual([snap(value) for value in (0, 5, 13, 14, 22, 123, 124, 999)], [5, 5, 5, 22, 22, 124, 124, 362])

    def test_mode_specific_inputs_are_enforced(self) -> None:
        validate = self.node_module._validate_inputs
        image = object()
        validate("t2v", None, None, None, None, None)
        validate("i2v", image, None, None, None, None)
        validate("fl2v", image, image, None, None, None)
        validate("r2v", None, None, image, None, None)
        with self.assertRaisesRegex(ValueError, "first_frame only"):
            validate("i2v", None, None, None, None, None)
        with self.assertRaisesRegex(ValueError, "requires ref"):
            validate("r2v", None, None, None, None, None)

    def test_t2v_execution_builds_v1_request_and_native_outputs(self) -> None:
        module = self.node_module

        class FakeClient:
            instances = []

            def __init__(self, server_url, api_key):
                self.server_url = server_url
                self.api_key = api_key
                self.request = None
                self.files = None
                self.__class__.instances.append(self)

            def require_compatible_server(self):
                return {"api_version": "v1", "server_version": "0.1.0"}

            def submit(self, request, files):
                self.request = request
                self.files = files
                return {"job_id": "20260908T000000Z_123456789abc"}

            def wait(self, job_id, timeout_s, poll_interval_s, on_poll):
                on_poll({"step": 4})
                return {"status": "done"}

            def cancel(self, job_id):
                raise AssertionError("cancel should not be called")

            def download(self, job_id, target):
                target.parent.mkdir(parents=True, exist_ok=True)
                target.write_bytes(b"webm")

        components = types.SimpleNamespace(
            images="frames",
            audio={"waveform": "audio", "sample_rate": 32000},
            frame_rate=24,
        )
        video = types.SimpleNamespace(get_components=lambda: components)
        module.H3Client = FakeClient
        module.InputImpl.VideoFromFile = lambda path: video

        with TemporaryDirectory() as temporary:
            module.folder_paths.get_temp_directory = lambda: temporary
            result = module.MiniMaxH3Remote().generate(
                "https://h3.example.com",
                "secret",
                "t2v",
                "A quiet forest",
                640,
                384,
                22,
                4,
                11,
                1.0,
                10,
            )

        client = FakeClient.instances[-1]
        self.assertEqual(client.files, [])
        self.assertEqual(client.request["mode"], "t2v")
        self.assertEqual(client.request["fps"], 24)
        self.assertEqual(client.request["cfg_scale"], 1.0)
        self.assertFalse(client.request["turbo"])
        self.assertEqual(result, (video, "frames", components.audio, 24.0, "20260908T000000Z_123456789abc"))

    def test_server_url_and_key_fall_back_to_environment(self) -> None:
        module = self.node_module

        class StopAfterConstruction:
            values = None

            def __init__(self, server_url, api_key):
                self.__class__.values = (server_url, api_key)

            def require_compatible_server(self):
                raise RuntimeError("stop")

        module.H3Client = StopAfterConstruction
        with patch.dict(
            module.os.environ,
            {"H3_API_URL": "https://env.example.com", "H3_API_KEY": "env-key"},
        ):
            with self.assertRaisesRegex(RuntimeError, "stop"):
                module.MiniMaxH3Remote().generate(
                    "", "", "t2v", "prompt", 640, 384, 22, 4, 11, 1.0, 10
                )
        self.assertEqual(StopAfterConstruction.values, ("https://env.example.com", "env-key"))


if __name__ == "__main__":
    unittest.main()
