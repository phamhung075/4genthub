# The client pin carries the clock and meter on the rule

### Changed
- `agenthub_client` pin bumped to `937b81a`: in a watch pane the clock and meter ride on the rule and step lines start at column 0.

### Testing
- `go test ./internal/clientwatch` passes in the client; no server code changed.
