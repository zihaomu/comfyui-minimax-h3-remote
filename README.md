# MiniMax H3 Remote for ComfyUI

[![CI](https://github.com/zihaomu/comfyui-minimax-h3-remote/actions/workflows/ci.yml/badge.svg)](https://github.com/zihaomu/comfyui-minimax-h3-remote/actions/workflows/ci.yml)

`comfyui-minimax-h3-remote` connects a local ComfyUI workflow to a self-hosted MiniMax H3 inference server. The server owns the model weights and GPU runtime; the local node uploads conditioning media, follows the asynchronous job, downloads the validated result, and converts it to native ComfyUI types.

## Features

- T2V, I2V, FL2V, and reference-image/video/audio R2V.
- Asynchronous submission, queue polling, progress reporting, cancellation, and result download.
- Native `VIDEO`, `IMAGE`, and `AUDIO` outputs, plus FPS and the reusable server `job_id`.
- Endpoint and API key configuration through environment variables, keeping credentials out of workflow JSON.
- No model weights or GPU inference runtime in this repository.

## Requirements

- A current ComfyUI release with native `VIDEO` support.
- A MiniMax H3 server exposing API `v1`; client 0.1.x supports server 0.1.x.
- Network access from the local ComfyUI Python process to that server.

The node uses dependencies already shipped with current ComfyUI: PyTorch, Pillow, NumPy, PyAV, and the Python standard library.

## Installation

Clone this repository into the local ComfyUI `custom_nodes` directory:

```bash
cd /path/to/ComfyUI/custom_nodes
git clone https://github.com/zihaomu/comfyui-minimax-h3-remote.git
```

Configure the process that starts ComfyUI, then restart it:

```bash
export H3_API_URL=https://h3.example.com
export H3_API_KEY='<server API key>'
python main.py
```

PowerShell:

```powershell
$env:H3_API_URL = "https://h3.example.com"
$env:H3_API_KEY = "<server API key>"
python main.py
```

The node appears under `MiniMax H3/remote` as **MiniMax H3 (remote)**. Keep its `server_url` and `api_key` widgets empty to use the environment variables. See the [installation and connection guide](doc/installation.md) for HTTPS and SSH tunnel examples.

## Example Workflows

ComfyUI discovers the four templates in [`example_workflows/`](example_workflows):

- `minimax_h3_remote_t2v.json`
- `minimax_h3_remote_i2v.json`
- `minimax_h3_remote_fl2v.json`
- `minimax_h3_remote_r2v.json`

The templates use the 640x384, 22-frame, 4-step smoke profile and leave endpoint and key values empty. Replace the placeholder images in conditioned workflows before running them.

The remote node is an output node and can run by itself. Connect its `VIDEO` output to ComfyUI's native **Save Video** node when a persistent local copy is required.

## Node Outputs

- `VIDEO`: lazy ComfyUI video suitable for Preview Video or Save Video.
- `IMAGE`: decoded frame batch in `[N,H,W,C]` layout.
- `AUDIO`: waveform dictionary with shape `[1,C,L]`; H3 output is 32 kHz stereo.
- `fps`: output frame rate, currently 24.
- `job_id`: server-side identifier for diagnostics and result recovery.

## Development

The tests run without ComfyUI, PyTorch, a GPU, or a live server:

```bash
python -m unittest discover -s tests -v
python scripts/generate_workflows.py --check
```

See [Troubleshooting](doc/troubleshooting.md), the [compatibility matrix](doc/compatibility.md), and the [client/server evolution plan](doc/项目目的与服务端客户端演进规划.md).

## License

The client node is licensed under the Apache License 2.0. This license applies only to the code in this repository. MiniMax H3 model weights and services remain subject to their own license, commercial-use terms, and regional restrictions.
