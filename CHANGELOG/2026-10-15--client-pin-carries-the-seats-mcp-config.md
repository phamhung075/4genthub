## 2026-10-15 - Client pin carries the seats MCP config

### Changed
- `agenthub_client`: pin bumped to the commit that writes the agenthub MCP config into every seat.

### Testing
- Client cargo test (92 passed); live check: `go-dev` called `manage_project list` over MCP.
