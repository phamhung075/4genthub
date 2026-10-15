# The client pin carries the idle-room guard

### Added
- `agenthub_client` pin bumped to `516f8ed`: `4genteam idle-run` (safeguard `roomguard`, started by `rigd`) asks Jev when every seat is idle and messages the lead, and nudges a seat that went quiet mid-job (`internal/clientlifecycle/idleguard.go`).
- `watch` and `feed` print a labelled rule when the tool kind changes (`internal/clientwatch/view.go`).

### Testing
- `go test ./...` passes in the client; no server code changed.
