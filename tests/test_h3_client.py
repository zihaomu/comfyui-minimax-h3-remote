from __future__ import annotations

import io
import json
from pathlib import Path
from tempfile import TemporaryDirectory
import unittest
from unittest.mock import Mock, patch
import urllib.error

from h3_client import H3ApiError, H3Client, encode_multipart


class FakeResponse:
    def __init__(self, payload: bytes) -> None:
        self._stream = io.BytesIO(payload)

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc, traceback) -> None:
        return None

    def read(self, size: int = -1) -> bytes:
        return self._stream.read(size)


class H3ClientTests(unittest.TestCase):
    def test_constructor_normalizes_url_and_requires_credentials(self) -> None:
        client = H3Client("https://h3.example.com///", "secret")
        self.assertEqual(client.server_url, "https://h3.example.com")
        with self.assertRaisesRegex(ValueError, "http"):
            H3Client("file:///tmp/h3", "secret")
        with self.assertRaisesRegex(ValueError, "api_key"):
            H3Client("https://h3.example.com", "")

    @patch("h3_client.urllib.request.urlopen")
    def test_json_submit_uses_bearer_auth_and_expected_payload(self, urlopen) -> None:
        urlopen.return_value = FakeResponse(b'{"job_id":"job-1","status":"queued"}')
        client = H3Client("https://h3.example.com", "test-token")

        response = client.submit({"mode": "t2v", "prompt": "scene"})

        self.assertEqual(response["job_id"], "job-1")
        request = urlopen.call_args.args[0]
        self.assertEqual(request.full_url, "https://h3.example.com/v1/generate")
        self.assertEqual(request.method, "POST")
        self.assertEqual(request.get_header("Authorization"), "Bearer test-token")
        self.assertEqual(json.loads(request.data), {"mode": "t2v", "prompt": "scene"})

    def test_multipart_supports_repeated_reference_fields(self) -> None:
        request = {"mode": "r2v", "prompt": "<Picture 1>"}
        body, content_type = encode_multipart(
            request,
            [
                ("ref_images", "one.png", "image/png", b"one"),
                ("ref_images", "two.png", "image/png", b"two"),
            ],
        )

        boundary = content_type.split("boundary=", 1)[1]
        self.assertEqual(body.count(b'name="ref_images"'), 2)
        self.assertIn(json.dumps(request).encode(), body)
        self.assertTrue(body.endswith(f"--{boundary}--\r\n".encode()))

    def test_wait_reports_progress_and_returns_done_job(self) -> None:
        client = H3Client("https://h3.example.com", "secret")
        client.get_job = Mock(
            side_effect=[
                {"status": "queued", "step": 0},
                {"status": "running", "step": 2},
                {"status": "done", "step": 4},
            ]
        )
        observed = []

        with patch("h3_client.time.sleep"):
            result = client.wait("job-1", 60, 1, observed.append)

        self.assertEqual(result["status"], "done")
        self.assertEqual([job["status"] for job in observed], ["queued", "running", "done"])

    def test_wait_surfaces_remote_error(self) -> None:
        client = H3Client("https://h3.example.com", "secret")
        client.get_job = Mock(return_value={"status": "error", "error": "generation failed"})
        with self.assertRaisesRegex(H3ApiError, "generation failed"):
            client.wait("job-1", 60, 1)

    @patch("h3_client.urllib.request.urlopen")
    def test_download_is_atomic(self, urlopen) -> None:
        urlopen.return_value = FakeResponse(b"webm-data")
        client = H3Client("https://h3.example.com", "secret")
        with TemporaryDirectory() as temporary:
            target = Path(temporary) / "nested" / "result.webm"
            client.download("job-1", target)
            self.assertEqual(target.read_bytes(), b"webm-data")
            self.assertFalse(target.with_suffix(".webm.part").exists())

    @patch("h3_client.urllib.request.urlopen")
    def test_http_error_exposes_server_detail(self, urlopen) -> None:
        urlopen.side_effect = urllib.error.HTTPError(
            "https://h3.example.com/healthz",
            401,
            "Unauthorized",
            hdrs=None,
            fp=io.BytesIO(b'{"detail":"invalid API key"}'),
        )
        with self.assertRaisesRegex(H3ApiError, "invalid API key"):
            H3Client("https://h3.example.com", "secret").health()


if __name__ == "__main__":
    unittest.main()
