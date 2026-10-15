## The missing `agenthub_http` mount was a stale `.gemini/settings.json` entry, not a startup budget

### Fixed
- `AGENTS.md` (section 5): the "250 ms startup budget" explanation is replaced by the measured cause. `omp` also reads the project's `.gemini/settings.json`; its `agenthub_http` entry (a stdio `mcp-proxy` to `localhost:8000`) overrode the `.mcp.json` entry and failed with `MCP subprocess closed stdout before responding`. A `mcp.startupTimeoutMs: 0` config did not help.
- The entry was removed from the local, git-ignored `.gemini/settings.json`; the seats were reseated and mount the nine `agenthub_http` tools.

### Tested
A fresh `omp -p` with the seat's environment and an empty agent dir listed the nine `mcp__agenthub_http_*` devices after the removal and none before. fe-dev and architect, reseated, listed the same nine.

### Changed
- `agenthub_client` pin: bumped to `658588a` (Jev on the client: `decide`, `complete`, the `jev-decisions` skill; the install creates `~/.config/4genthub/.env`).
