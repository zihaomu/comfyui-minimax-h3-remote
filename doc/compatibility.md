# Compatibility Matrix

The client and server are independently released. The API major version is the stable boundary.

| ComfyUI client | API | Server | Status | Evidence |
|---|---|---|---|---|
| `0.1.0` | `v1` | `0.1.x` | Supported | C1 real T2V/I2V and X1 joint T2V smoke |
| `0.1.1` | `v1` | `0.1.x` | Supported and recommended | Compatibility preflight, X1 unit/CI gates |

Client `0.1.1` calls authenticated `GET /v1/capabilities` before uploading media or submitting work. It requires `api_version == "v1"` and a semantic server version in the `0.1.x` series. An unsupported combination fails before consuming queue or GPU capacity.

The server may add response fields within API v1. Clients must ignore fields they do not understand. Removing fields, changing field types, or changing job-state semantics requires a new API major version.

## Joint Smoke

From this repository:

```bash
export H3_API_URL=https://h3.example.com
export H3_API_KEY='<server API key>'
python scripts/joint_smoke.py
python scripts/joint_smoke.py --generate --output h3-joint-smoke.webm
```

The first command checks health and compatibility without submitting work. `--generate` additionally runs a 640x384, 22-frame, 4-step T2V job, polls it, downloads the output atomically, and compares the local byte count and SHA-256 with server metrics.
