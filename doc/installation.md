# Installation and Connection Guide

## 1. Install the Node

Clone this repository into the local ComfyUI `custom_nodes` directory:

```bash
cd /path/to/ComfyUI/custom_nodes
git clone https://github.com/zihaomu/comfyui-minimax-h3-remote.git
```

Restart ComfyUI. The node should appear at:

```text
MiniMax H3 / remote / MiniMax H3 (remote)
```

No additional package installation is normally required. The node uses PyTorch, Pillow, NumPy, and PyAV from the ComfyUI environment.

## 2. Configure the Connection

Set configuration in the same shell or service environment that starts ComfyUI:

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

Keep the `server_url` and `api_key` node widgets empty to use these environment variables. This prevents the credential from being saved into workflow JSON.

### SSH Tunnel for Initial Testing

When the server listens only on its loopback interface, create a tunnel on the ComfyUI machine:

```bash
ssh -N -L 18000:127.0.0.1:18000 user@gpu-server
```

Then start ComfyUI with:

```bash
export H3_API_URL=http://127.0.0.1:18000
export H3_API_KEY='<server API key>'
python main.py
```

Use HTTPS or a private network such as Tailscale/WireGuard for production. Do not expose an unauthenticated GPU service directly to the internet.

## 3. Import an Example

ComfyUI automatically discovers templates under `example_workflows/`. You can also drag one of the JSON files onto the canvas.

| Template | Required local input |
|---|---|
| `minimax_h3_remote_t2v.json` | None |
| `minimax_h3_remote_i2v.json` | Replace `first_frame.png` |
| `minimax_h3_remote_fl2v.json` | Replace `first_frame.png` and `last_frame.png` |
| `minimax_h3_remote_r2v.json` | Replace `reference.png` |

The examples use the 640x384, 22-frame, 4-step smoke profile. Increase quality settings only after confirming the complete remote path works.

## 4. Save the Result

The remote node itself is executable and returns generated media. Connect:

- `VIDEO` to ComfyUI **Save Video** or **Preview Video**;
- `IMAGE` to frame-based image processing nodes;
- `AUDIO` to audio preview or save nodes;
- `job_id` to text display or logging nodes when diagnosing a request.

## 5. Security

- Prefer `H3_API_KEY` over the visible node widget.
- Never commit a workflow containing a real key.
- Verify the server certificate when using HTTPS.
- Use a different key per customer or installation once the server supports per-key management.
