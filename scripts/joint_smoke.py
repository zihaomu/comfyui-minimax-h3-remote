#!/usr/bin/env python3
from __future__ import annotations

import argparse
import hashlib
import json
import os
import sys
from pathlib import Path

ROOT = Path(__file__).parents[1]
sys.path.insert(0, str(ROOT))

from h3_client import CLIENT_VERSION, H3Client


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Verify the released ComfyUI client against a MiniMax H3 server"
    )
    parser.add_argument("--url", default=os.environ.get("H3_API_URL"))
    parser.add_argument("--api-key", default=os.environ.get("H3_API_KEY"))
    parser.add_argument("--generate", action="store_true")
    parser.add_argument("--output", type=Path, default=Path("h3-joint-smoke.webm"))
    parser.add_argument("--timeout-s", type=float, default=900)
    args = parser.parse_args()
    if not args.url or not args.api_key:
        parser.error("set H3_API_URL and H3_API_KEY or pass --url and --api-key")

    client = H3Client(args.url, args.api_key)
    health = client.health()
    capabilities = client.require_compatible_server()
    summary: dict[str, object] = {
        "health": {
            "status": health.get("status"),
            "ready": health.get("ready"),
            "busy": health.get("busy"),
            "queue_depth": health.get("queue_depth"),
        },
        "compatibility": {
            "client_version": CLIENT_VERSION,
            "api_version": capabilities["api_version"],
            "server_version": capabilities["server_version"],
        },
    }
    if not health.get("ready"):
        raise RuntimeError("server is not ready")
    if not args.generate:
        print(json.dumps(summary, indent=2, sort_keys=True))
        return 0

    submitted = client.submit(
        {
            "mode": "t2v",
            "prompt": "A small sailboat crosses a calm bay at sunrise, natural ambience.",
            "width": 640,
            "height": 384,
            "frames": 22,
            "fps": 24,
            "steps": 4,
            "seed": 20260913,
            "cfg_scale": 1.0,
            "turbo": False,
        }
    )
    job = client.wait(
        submitted["job_id"],
        timeout_s=args.timeout_s,
        poll_interval_s=1,
    )
    client.download(job["job_id"], args.output)
    digest = hashlib.sha256(args.output.read_bytes()).hexdigest()
    metrics = job.get("metrics") or {}
    if metrics.get("output_bytes") != args.output.stat().st_size:
        raise RuntimeError("download size does not match server metrics")
    if metrics.get("sha256") != digest:
        raise RuntimeError("download SHA-256 does not match server metrics")
    summary["generation"] = {
        "job_id": job["job_id"],
        "status": job["status"],
        "output": str(args.output),
        "output_bytes": args.output.stat().st_size,
        "sha256": digest,
        "video_frames": metrics.get("video_frames"),
        "unique_video_frames": metrics.get("unique_video_frames"),
        "audio_sample_rate": metrics.get("audio_sample_rate"),
        "audio_channels": metrics.get("audio_channels"),
    }
    print(json.dumps(summary, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
