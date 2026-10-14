# The client pin carries the edit diff in watch

### Changed
- `agenthub_client` pin bumped to `16d2257`: `4genteam watch` and `feed` show an `edit` call as red `-` and green `+` lines (`internal/clientwatch/render.go`).

### Testing
- `go test ./internal/clientwatch` passes in the client; no server code changed.
