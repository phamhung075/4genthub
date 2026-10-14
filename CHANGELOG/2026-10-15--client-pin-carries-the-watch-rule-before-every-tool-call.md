# The client pin carries the watch rule before every tool call

### Changed
- `agenthub_client` pin bumped to `578d1c4`: `watch` and `feed` print a plain rule in the tool kind's colour before every tool call (`internal/clientwatch/feed.go`, `view.go`).

### Testing
- `go test ./internal/clientwatch` passes in the client; no server code changed.
