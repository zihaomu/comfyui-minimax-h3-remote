from __future__ import annotations

import json
import time
import urllib.error
import urllib.parse
import urllib.request
import uuid
from collections.abc import Callable, Iterable
from pathlib import Path
from typing import Any


class H3ApiError(RuntimeError):
    pass


FilePart = tuple[str, str, str, bytes]


class H3Client:
    def __init__(self, server_url: str, api_key: str, request_timeout_s: float = 120) -> None:
        server_url = server_url.strip().rstrip("/")
        parsed = urllib.parse.urlparse(server_url)
        if parsed.scheme not in {"http", "https"} or not parsed.netloc:
            raise ValueError("server_url must be an http:// or https:// URL")
        if not api_key:
            raise ValueError("api_key is required; set the node input or H3_API_KEY")
        self.server_url = server_url
        self.api_key = api_key
        self.request_timeout_s = request_timeout_s

    def health(self) -> dict[str, Any]:
        return self._json_request("/healthz")

    def submit(self, request: dict[str, Any], files: Iterable[FilePart] = ()) -> dict[str, Any]:
        file_parts = list(files)
        if not file_parts:
            return self._json_request("/v1/generate", method="POST", json_body=request)
        body, content_type = encode_multipart(request, file_parts)
        return self._json_request(
            "/v1/generate",
            method="POST",
            body=body,
            content_type=content_type,
        )

    def get_job(self, job_id: str) -> dict[str, Any]:
        return self._json_request(f"/v1/jobs/{job_id}")

    def cancel(self, job_id: str) -> None:
        try:
            self._json_request(f"/v1/jobs/{job_id}/cancel", method="POST", body=b"")
        except H3ApiError:
            pass

    def wait(
        self,
        job_id: str,
        timeout_s: float,
        poll_interval_s: float,
        on_poll: Callable[[dict[str, Any]], None] | None = None,
    ) -> dict[str, Any]:
        deadline = time.monotonic() + timeout_s
        while True:
            job = self.get_job(job_id)
            if on_poll:
                on_poll(job)
            if job["status"] == "done":
                return job
            if job["status"] in {"error", "canceled"}:
                raise H3ApiError(job.get("error") or f"job {job['status']}")
            if time.monotonic() >= deadline:
                raise H3ApiError(f"job did not finish within {timeout_s:.0f} seconds")
            time.sleep(poll_interval_s)

    def download(self, job_id: str, target: Path) -> None:
        target.parent.mkdir(parents=True, exist_ok=True)
        temporary = target.with_suffix(target.suffix + ".part")
        request = self._request(f"/v1/jobs/{job_id}/result")
        try:
            with urllib.request.urlopen(request, timeout=self.request_timeout_s) as response, temporary.open("wb") as handle:
                while chunk := response.read(1024 * 1024):
                    handle.write(chunk)
            temporary.replace(target)
        except (urllib.error.HTTPError, urllib.error.URLError, TimeoutError, OSError) as exc:
            temporary.unlink(missing_ok=True)
            raise self._api_error(exc) from exc

    def _json_request(
        self,
        path: str,
        method: str = "GET",
        json_body: dict[str, Any] | None = None,
        body: bytes | None = None,
        content_type: str = "application/json",
    ) -> dict[str, Any]:
        if json_body is not None:
            body = json.dumps(json_body).encode("utf-8")
        request = self._request(path, method=method, body=body, content_type=content_type)
        try:
            with urllib.request.urlopen(request, timeout=self.request_timeout_s) as response:
                return json.load(response)
        except (urllib.error.HTTPError, urllib.error.URLError, TimeoutError, OSError, json.JSONDecodeError) as exc:
            raise self._api_error(exc) from exc

    def _request(
        self,
        path: str,
        method: str = "GET",
        body: bytes | None = None,
        content_type: str | None = None,
    ) -> urllib.request.Request:
        headers = {"Authorization": f"Bearer {self.api_key}"}
        if content_type:
            headers["Content-Type"] = content_type
        return urllib.request.Request(
            f"{self.server_url}{path}",
            data=body,
            method=method,
            headers=headers,
        )

    @staticmethod
    def _api_error(exc: BaseException) -> H3ApiError:
        if isinstance(exc, urllib.error.HTTPError):
            detail = exc.read().decode("utf-8", errors="replace")
            try:
                detail = json.loads(detail).get("detail", detail)
            except json.JSONDecodeError:
                pass
            return H3ApiError(f"H3 API returned HTTP {exc.code}: {detail}")
        return H3ApiError(f"H3 API request failed: {exc}")


def encode_multipart(request: dict[str, Any], files: Iterable[FilePart]) -> tuple[bytes, str]:
    boundary = f"----minimax-h3-{uuid.uuid4().hex}"
    chunks = [
        f"--{boundary}\r\n".encode(),
        b'Content-Disposition: form-data; name="request"\r\n',
        b"Content-Type: application/json\r\n\r\n",
        json.dumps(request).encode("utf-8"),
        b"\r\n",
    ]
    for field_name, filename, content_type, payload in files:
        chunks.extend(
            (
                f"--{boundary}\r\n".encode(),
                f'Content-Disposition: form-data; name="{field_name}"; filename="{filename}"\r\n'.encode(),
                f"Content-Type: {content_type}\r\n\r\n".encode(),
                payload,
                b"\r\n",
            )
        )
    chunks.append(f"--{boundary}--\r\n".encode())
    return b"".join(chunks), f"multipart/form-data; boundary={boundary}"
