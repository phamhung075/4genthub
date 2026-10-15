# The client pin carries bodies back to the left

### Changed
- `agenthub_client` pin bumped to `8477884`: watch continuation lines are no longer padded to the step glyph.

### Testing
- `go test ./internal/clientwatch` passes in the client; no server code changed.
