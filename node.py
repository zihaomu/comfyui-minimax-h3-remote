from __future__ import annotations

import io
import os
import re
import wave
from pathlib import Path

import numpy as np
from PIL import Image
import torch

import comfy.model_management
import comfy.utils
import folder_paths
from comfy_api.latest import InputImpl

from .h3_client import FilePart, H3Client


class MiniMaxH3Remote:
    @classmethod
    def INPUT_TYPES(cls):
        return {
            "required": {
                "server_url": (
                    "STRING",
                    {"default": os.environ.get("H3_API_URL", "")},
                ),
                "api_key": ("STRING", {"default": "", "multiline": False}),
                "mode": (["t2v", "i2v", "fl2v", "r2v"],),
                "prompt": ("STRING", {"default": "", "multiline": True}),
                "width": ("INT", {"default": 1344, "min": 256, "max": 1344, "step": 32}),
                "height": ("INT", {"default": 768, "min": 256, "max": 1344, "step": 32}),
                "frames": ("INT", {"default": 124, "min": 5, "max": 362, "step": 17}),
                "steps": ("INT", {"default": 20, "min": 1, "max": 50}),
                "seed": (
                    "INT",
                    {"default": 11, "min": -1, "max": 2_147_483_647, "control_after_generate": True},
                ),
                "poll_interval_s": ("FLOAT", {"default": 4.0, "min": 1.0, "max": 30.0, "step": 0.5}),
                "timeout_minutes": ("INT", {"default": 240, "min": 10, "max": 720}),
            },
            "optional": {
                "first_frame": ("IMAGE",),
                "last_frame": ("IMAGE",),
                "ref_images": ("IMAGE",),
                "ref_video": ("VIDEO",),
                "ref_audio": ("AUDIO",),
            },
        }

    RETURN_TYPES = ("VIDEO", "IMAGE", "AUDIO", "FLOAT", "STRING")
    RETURN_NAMES = ("video", "frames", "audio", "fps", "job_id")
    FUNCTION = "generate"
    CATEGORY = "MiniMax H3/remote"
    OUTPUT_NODE = True

    def generate(
        self,
        server_url,
        api_key,
        mode,
        prompt,
        width,
        height,
        frames,
        steps,
        seed,
        poll_interval_s,
        timeout_minutes,
        first_frame=None,
        last_frame=None,
        ref_images=None,
        ref_video=None,
        ref_audio=None,
    ):
        server_url = server_url.strip() or os.environ.get("H3_API_URL", "")
        api_key = api_key.strip() or os.environ.get("H3_API_KEY", "")
        frames = _snap_frames(frames)
        _validate_inputs(mode, first_frame, last_frame, ref_images, ref_video, ref_audio)
        client = H3Client(server_url, api_key)
        client.require_compatible_server()
        request = {
            "mode": mode,
            "prompt": prompt,
            "width": width,
            "height": height,
            "frames": frames,
            "fps": 24,
            "steps": steps,
            "seed": seed,
            "cfg_scale": 1.0,
            "turbo": False,
        }
        files = _build_files(first_frame, last_frame, ref_images, ref_video, ref_audio)
        submitted = client.submit(request, files)
        job_id = submitted["job_id"]
        if not re.fullmatch(r"[0-9]{8}T[0-9]{6}Z_[a-f0-9]{12}", job_id):
            raise RuntimeError("H3 API returned an invalid job_id")

        progress = comfy.utils.ProgressBar(steps)

        def on_poll(job):
            comfy.model_management.throw_exception_if_processing_interrupted()
            progress.update_absolute(min(int(job.get("step", 0)), steps), steps)

        try:
            client.wait(
                job_id,
                timeout_s=timeout_minutes * 60,
                poll_interval_s=poll_interval_s,
                on_poll=on_poll,
            )
        except BaseException:
            client.cancel(job_id)
            raise

        result_dir = Path(folder_paths.get_temp_directory()) / "minimax_h3_remote" / job_id
        result_path = result_dir / "result.webm"
        client.download(job_id, result_path)
        video = InputImpl.VideoFromFile(str(result_path))
        components = video.get_components()
        if components.audio is None:
            raise RuntimeError("H3 result does not contain an audio stream")
        return (
            video,
            components.images,
            components.audio,
            float(components.frame_rate),
            job_id,
        )


def _snap_frames(frames: int) -> int:
    return min(362, max(5, round((frames - 5) / 17) * 17 + 5))


def _validate_inputs(mode, first_frame, last_frame, ref_images, ref_video, ref_audio) -> None:
    references = ref_images is not None or ref_video is not None or ref_audio is not None
    if mode == "t2v" and (first_frame is not None or last_frame is not None or references):
        raise ValueError("t2v does not accept conditioning inputs")
    if mode == "i2v" and (first_frame is None or last_frame is not None or references):
        raise ValueError("i2v requires first_frame only")
    if mode == "fl2v" and (first_frame is None or last_frame is None or references):
        raise ValueError("fl2v requires first_frame and last_frame only")
    if mode == "r2v" and (first_frame is not None or last_frame is not None or not references):
        raise ValueError("r2v requires ref_images, ref_video, or ref_audio")


def _build_files(first_frame, last_frame, ref_images, ref_video, ref_audio) -> list[FilePart]:
    files: list[FilePart] = []
    if first_frame is not None:
        files.append(("first_frame", "first.png", "image/png", _image_to_png(first_frame[0])))
    if last_frame is not None:
        files.append(("last_frame", "last.png", "image/png", _image_to_png(last_frame[0])))
    if ref_images is not None:
        if ref_images.shape[0] > 8:
            raise ValueError("at most 8 reference images are supported")
        for index, image in enumerate(ref_images):
            files.append(("ref_images", f"ref_{index + 1:02d}.png", "image/png", _image_to_png(image)))
    if ref_video is not None:
        buffer = io.BytesIO()
        ref_video.save_to(buffer, format="mp4", codec="h264", preset="ultrafast")
        files.append(("ref_videos", "reference.mp4", "video/mp4", buffer.getvalue()))
    if ref_audio is not None:
        files.append(("ref_audio", "reference.wav", "audio/wav", _audio_to_wav(ref_audio)))
    return files


def _image_to_png(image) -> bytes:
    pixels = image.detach().float().cpu().clamp(0, 1)
    pixels = (pixels[..., :3] * 255.0).round().to(dtype=torch.uint8).numpy()
    buffer = io.BytesIO()
    Image.fromarray(pixels, mode="RGB").save(buffer, format="PNG")
    return buffer.getvalue()


def _audio_to_wav(audio) -> bytes:
    waveform = audio["waveform"].detach().float().cpu()
    if waveform.ndim == 3:
        waveform = waveform[0]
    if waveform.ndim == 1:
        waveform = waveform.unsqueeze(0)
    if waveform.ndim != 2 or waveform.shape[0] not in {1, 2}:
        raise ValueError("reference audio must be mono or stereo")
    samples = (waveform.clamp(-1, 1).transpose(0, 1).numpy() * 32767.0).round().astype(np.int16)
    buffer = io.BytesIO()
    with wave.open(buffer, "wb") as output:
        output.setnchannels(waveform.shape[0])
        output.setsampwidth(2)
        output.setframerate(int(audio["sample_rate"]))
        output.writeframes(samples.astype("<i2", copy=False).tobytes())
    return buffer.getvalue()
