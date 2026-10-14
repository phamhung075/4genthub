# The client pin carries the step rule before think, say and in

### Changed
- `agenthub_client` pin bumped to `73d6bca`: `watch` and `feed` print the coloured step rule before `~ think`, `▸ say` and `◂ in` as well as before tool calls (`internal/clientwatch/feed.go`, `view.go`).

### Testing
- `go test ./internal/clientwatch` passes in the client; no server code changed.
