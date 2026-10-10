## 2026-10-10 — client pin moves to `bae2c86`; the Python client is gone

### Changed
- `agenthub_client` gitlink `c401888b` → `bae2c86` (86+ client commits, pushed to `phamhung075/4genthub-client`).
  The client tree holds no `.py` and no `pyproject.toml`; every verb (`team`, `watch`, `up`, `seat`, `policy`, `feedback`) is Go.

### Validated
- Fresh clone of `bae2c86`: `go build ./...` and `go test ./...` pass; 0 `.py` files. `python3` was still on PATH (`/usr/bin`), so absence of Python is not proven, only that nothing in the build or tests needs it.

### Added
- The client starts its own status bridge when a verb runs and none is running (`bae2c86`), and the bridge process pattern is anchored. The machine no longer goes offline because nobody started a service.
