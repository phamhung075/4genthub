# The client pin carries wrapped rows that fit the pane

### Fixed
- `agenthub_client` pin bumped to `8b09122`: watch wraps rows at the width minus the head and indent, so wrapped rows stay indented.

### Testing
- `go test ./internal/clientwatch` passes in the client; no server code changed.
