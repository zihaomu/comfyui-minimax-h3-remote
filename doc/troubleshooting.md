# Troubleshooting

## Node Does Not Appear

Confirm the directory layout:

```text
ComfyUI/custom_nodes/comfyui-minimax-h3-remote/
├── __init__.py
├── node.py
└── h3_client.py
```

Restart ComfyUI and inspect its startup log for an import error. A current ComfyUI release with native `VIDEO` support is required.

## `server_url must be an http:// or https:// URL`

Set `H3_API_URL` in the environment that launches ComfyUI, or enter a complete URL in the node. For an SSH tunnel, use `http://127.0.0.1:18000`.

## `api_key is required`

Set `H3_API_KEY` before starting ComfyUI. Environment changes made after ComfyUI starts do not update the running Python process; restart it.

## HTTP 401

The key does not match the server. Do not add the `Bearer` prefix yourself; the client adds it automatically.

## Connection Refused or Timeout Before Submission

Check:

1. The API server is running.
2. The URL and port are reachable from the ComfyUI machine.
3. The SSH tunnel, VPN, reverse proxy, DNS, and TLS certificate are active.
4. A firewall is not blocking the route.

## Job Remains Queued

The server serializes GPU work. Another job is running, or the service was configured with a queue. Keep the workflow active; the node polls until its job starts.

## Job Times Out Locally

Increase `timeout_minutes` for high-resolution or long clips. A client timeout does not guarantee the server process has already stopped; use the returned `job_id` and server logs when diagnosing it.

## I2V, FL2V, or R2V Input Error

Mode rules are strict:

- `t2v`: no conditioning inputs;
- `i2v`: `first_frame` only;
- `fl2v`: both `first_frame` and `last_frame`;
- `r2v`: at least one reference image, video, or audio, with no first/last frame.

## Workflow Contains a Secret

Clear the `api_key` widget, set `H3_API_KEY` in the ComfyUI process environment, and save the workflow again. Before sharing a workflow, search its JSON for `api_key` and `Bearer` values.

## Server-Side Generation Failure

Record the node's `job_id`. The server uses it to locate the persisted request, command, logs, validation metrics, and result. Do not include the API key in issue reports.
