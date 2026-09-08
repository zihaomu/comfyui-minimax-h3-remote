# Changelog

All notable changes to this project are documented here.

## [0.1.1] - 2026-09-08

### Added

- Authenticated `/v1/capabilities` discovery and compatibility preflight.
- Explicit support policy for API v1 and server 0.1.x.
- Reusable joint smoke command for contract-only and real generation validation.
- Published client/server compatibility matrix.

### Validated

- Real joint T2V against server 0.1.0 on W7900: 22/22 unique frames, 32 kHz stereo, and matching download/server SHA-256.

## [0.1.0] - 2026-09-08

### Added

- `MiniMax H3 (remote)` ComfyUI output node.
- T2V, I2V, FL2V, and R2V request modes.
- Asynchronous job submission, polling, cancellation, and atomic result download.
- Native `VIDEO`, `IMAGE`, `AUDIO`, FPS, and `job_id` outputs.
- Environment-based endpoint and API-key configuration.
- Four ComfyUI v1.0 example workflow templates.
- Dependency-free protocol, node-contract, workflow, metadata, and secret-hygiene tests.
- GitHub Actions coverage for Python 3.10, 3.11, and 3.12.
- Installation, troubleshooting, architecture, and acceptance documentation.

### Validated

- Clean installation in ComfyUI v0.34.0.
- Browser discovery and loading of all four templates.
- Real T2V and I2V execution through ComfyUI against a self-hosted W7900 server.
