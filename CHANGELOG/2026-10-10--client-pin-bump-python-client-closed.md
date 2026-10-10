## 2026-10-10 — client pin moves to `eaa6ba7`; the Python client is gone

### Changed
- `agenthub_client` gitlink `c401888b` → `eaa6ba7` (86+ client commits, pushed to `phamhung075/4genthub-client`).
  The client tree holds no `.py` and no `pyproject.toml`; every verb (`team`, `watch`, `up`, `seat`, `policy`, `feedback`) is Go.

### Validated
- Fresh clone of `eaa6ba7`: `go build ./...` and `go test ./...` pass; 0 `.py` files. `python3` was still on PATH (`/usr/bin`), so absence of Python is not proven, only that nothing in the build or tests needs it.
