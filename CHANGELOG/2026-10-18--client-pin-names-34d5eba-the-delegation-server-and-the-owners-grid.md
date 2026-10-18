# The client pin names `34d5eba`: every seat gets the delegation server, and the grid is the owner's wall

`agenthub_client` moves `56ed713` -> `34d5eba`:

### Added
- `d1b97c0` - the runtime writes a `deepseek` MCP server into every seat's `mcp.json` (omp and claude) and
  a guarded entry into agy's `mcp_config.json`, from `DEEPSEEK_MCP_SERVER` in the environment. With the
  variable unset the file is `SEAT_MCP_CONFIG` verbatim; the job's directory is the seat's own scope.
  New seat skill `deepseek-delegation`.
- `27eeb28` - `4genteam grid` builds the owner's wall: lead one tall pane on the left, the other seats
  filling the rest, one pane per seat at any count, no empty pane.

### Fixed
- `37cb7b6` - the dot-env rule reads the OMP record vocabulary.

### Changed
- `34d5eba` - the `watch-team` skill teaches the shipped grid; the python workaround is deleted.

Testing: client `go test ./...` and `cargo test --offline` (179 passed) green on `34d5eba`, run before
the client push (`56ed713..34d5eba`). Reseat every seat to give them the delegation server.
