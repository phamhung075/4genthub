## 2026-10-16 — Client pin carries the herdr cleanup on stop

### Changed
- `agenthub_client` pin moves to `462e969`: `4genteam stop` and `room stop` close the rig's herdr watch workspaces ("<rig> grid", "<rig> lead"), so the `feed`/`input` helpers no longer poll forever after a stop.

### Tested
- Client `go vet`, `go test ./...` and `cargo test --offline` pass. Closing a pane ending the helpers is verified at the next restart.
