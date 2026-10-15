# The client pin carries `agent`, `--room`, the audit fix and the Jev threshold fix

### Changed
- `agenthub_client` pin moved to `bc725e6`: `rigd` is `agent`, `--rig` is `--room`, `sync rig` is `sync room`, the seat audit survives a lagged burst and writes `SessionTerminated`, the Jev criteria check follows `JEV_DECISION_THRESHOLD`, the idle guard no longer repeats its question, and a task with no acceptance criteria is no longer accepted by the gate. Details: the client's `CHANGELOG/2026-10-15--*`.
- The wire and storage names the server shares (`/rigspec`, `rig_name`, `rig_safeguard`) are unchanged.

### Testing
- `cd agenthub_go && go build ./... && go test ./...` clean; the client's `go test ./...` and `cargo test --offline` clean.
