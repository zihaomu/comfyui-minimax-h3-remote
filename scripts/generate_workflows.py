#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys
import uuid


ROOT = Path(__file__).parents[1]
OUTPUT_DIR = ROOT / "example_workflows"
VERSION = "0.1.0"

MODE_CONFIG = {
    "t2v": {
        "name": "MiniMax H3 Remote - Text to Video",
        "description": "Generate a video with audio from a text prompt using a remote MiniMax H3 server.",
        "prompt": "A red panda walks along a mossy log in a misty forest. Natural forest ambience and soft footsteps.",
        "images": [],
    },
    "i2v": {
        "name": "MiniMax H3 Remote - Image to Video",
        "description": "Animate a first frame with a remote MiniMax H3 server.",
        "prompt": "The subject starts moving naturally while the camera follows. Matching ambient sound.",
        "images": [("first_frame", "first_frame.png")],
    },
    "fl2v": {
        "name": "MiniMax H3 Remote - First and Last Frame to Video",
        "description": "Generate a smooth transition between first and last frames with a remote MiniMax H3 server.",
        "prompt": "Create a smooth cinematic transition from the first frame to the last frame. Matching ambient sound.",
        "images": [("first_frame", "first_frame.png"), ("last_frame", "last_frame.png")],
    },
    "r2v": {
        "name": "MiniMax H3 Remote - Reference Image to Video",
        "description": "Generate a video from a reference image with a remote MiniMax H3 server.",
        "prompt": "The subject shown in <Picture 1> walks toward the camera. Gentle wind and natural ambience.",
        "images": [("ref_images", "reference.png")],
    },
}

REQUIRED_INPUTS = (
    ("server_url", "STRING"),
    ("api_key", "STRING"),
    ("mode", "COMBO"),
    ("prompt", "STRING"),
    ("width", "INT"),
    ("height", "INT"),
    ("frames", "INT"),
    ("steps", "INT"),
    ("seed", "INT"),
    ("poll_interval_s", "FLOAT"),
    ("timeout_minutes", "INT"),
)
OPTIONAL_INPUTS = (
    ("first_frame", "IMAGE"),
    ("last_frame", "IMAGE"),
    ("ref_images", "IMAGE"),
    ("ref_video", "VIDEO"),
    ("ref_audio", "AUDIO"),
)


def load_image_node(node_id: int, filename: str, link_id: int, y: int) -> dict:
    return {
        "id": node_id,
        "type": "LoadImage",
        "pos": [80, y],
        "size": [320, 360],
        "flags": {},
        "order": node_id - 1,
        "mode": 0,
        "inputs": [
            {"name": "image", "type": "COMBO", "widget": {"name": "image"}, "link": None},
            {"name": "upload", "type": "IMAGEUPLOAD", "widget": {"name": "upload"}, "link": None},
        ],
        "outputs": [
            {"name": "IMAGE", "type": "IMAGE", "slot_index": 0, "links": [link_id]},
            {"name": "MASK", "type": "MASK", "slot_index": 1, "links": None},
        ],
        "properties": {"cnr_id": "comfy-core", "Node name for S&R": "LoadImage"},
        "widgets_values": [filename, "image"],
    }


def remote_node(node_id: int, mode: str, prompt: str, links_by_input: dict[str, int]) -> dict:
    inputs = [
        {"name": name, "type": input_type, "widget": {"name": name}, "link": None}
        for name, input_type in REQUIRED_INPUTS
    ]
    for slot_index, (name, input_type) in enumerate(OPTIONAL_INPUTS, start=len(REQUIRED_INPUTS)):
        inputs.append({"name": name, "type": input_type, "link": links_by_input.get(name), "slot_index": slot_index})
    return {
        "id": node_id,
        "type": "MiniMaxH3Remote",
        "pos": [540, 180],
        "size": [460, 540],
        "flags": {},
        "order": node_id - 1,
        "mode": 0,
        "inputs": inputs,
        "outputs": [
            {"name": "video", "type": "VIDEO", "slot_index": 0, "links": None},
            {"name": "frames", "type": "IMAGE", "slot_index": 1, "links": None},
            {"name": "audio", "type": "AUDIO", "slot_index": 2, "links": None},
            {"name": "fps", "type": "FLOAT", "slot_index": 3, "links": None},
            {"name": "job_id", "type": "STRING", "slot_index": 4, "links": None},
        ],
        "properties": {"cnr_id": "minimax-h3-remote", "ver": VERSION, "Node name for S&R": "MiniMaxH3Remote"},
        "widgets_values": ["", "", mode, prompt, 640, 384, 22, 4, 11, "fixed", 4.0, 240],
    }


def build_workflow(mode: str) -> dict:
    config = MODE_CONFIG[mode]
    image_nodes = []
    links = []
    links_by_input = {}
    for index, (input_name, filename) in enumerate(config["images"], start=1):
        image_nodes.append(load_image_node(index, filename, index, 80 + (index - 1) * 410))
        links_by_input[input_name] = index

    remote_id = len(image_nodes) + 1
    remote = remote_node(remote_id, mode, config["prompt"], links_by_input)
    input_slots = {item["name"]: index for index, item in enumerate(remote["inputs"])}
    for index, (input_name, _) in enumerate(config["images"], start=1):
        links.append({
            "id": index,
            "origin_id": index,
            "origin_slot": 0,
            "target_id": remote_id,
            "target_slot": input_slots[input_name],
            "type": "IMAGE",
        })

    workflow_id = str(uuid.uuid5(uuid.NAMESPACE_URL, f"https://github.com/zihaomu/comfyui-minimax-h3-remote/{mode}"))
    return {
        "id": workflow_id,
        "revision": 0,
        "version": 1,
        "state": {"lastGroupId": 0, "lastNodeId": remote_id, "lastLinkId": len(links), "lastRerouteId": 0},
        "nodes": [*image_nodes, remote],
        "links": links,
        "groups": [],
        "reroutes": [],
        "config": {},
        "extra": {
            "ds": {"scale": 1.0, "offset": [0, 0]},
            "info": {
                "name": config["name"],
                "author": "zihaomu",
                "description": config["description"],
                "version": VERSION,
                "created": "2026-09-08",
                "modified": "2026-09-08",
                "software": "ComfyUI",
            },
        },
        "models": [],
    }


def render(workflow: dict) -> str:
    return json.dumps(workflow, ensure_ascii=False, indent=2) + "\n"


def main() -> int:
    parser = argparse.ArgumentParser(description="Generate MiniMax H3 remote example workflows")
    parser.add_argument("--check", action="store_true", help="fail when checked-in workflows differ")
    args = parser.parse_args()
    failures = []
    for mode in MODE_CONFIG:
        path = OUTPUT_DIR / f"minimax_h3_remote_{mode}.json"
        expected = render(build_workflow(mode))
        if args.check:
            if not path.is_file() or path.read_text(encoding="utf-8") != expected:
                failures.append(str(path.relative_to(ROOT)))
        else:
            OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
            path.write_text(expected, encoding="utf-8")
    if failures:
        print("Out-of-date workflows: " + ", ".join(failures), file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
