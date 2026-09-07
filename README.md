# MiniMax H3 (remote) for ComfyUI

Copy this directory into the local ComfyUI `custom_nodes/` directory and restart ComfyUI.

The node appears under `MiniMax H3/remote`. It supports `t2v`, `i2v`, `fl2v`, and `r2v`, polls the remote asynchronous API, and returns `VIDEO`, decoded `IMAGE` frames, `AUDIO`, 24 FPS, and the server `job_id`.

Set `H3_API_URL` and `H3_API_KEY` in the ComfyUI process environment to avoid storing the key in workflow JSON. A non-empty `api_key` widget overrides the environment variable.

This node uses dependencies already shipped with current ComfyUI: PyTorch, Pillow, NumPy, PyAV, and the Python standard library.

## License

The client node is licensed under the Apache License 2.0. This license applies only to the code in this repository. MiniMax H3 model weights and services remain subject to their own license, commercial-use terms, and regional restrictions.
