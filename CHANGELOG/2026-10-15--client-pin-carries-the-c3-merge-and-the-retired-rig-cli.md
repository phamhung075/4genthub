# The client pin carries the C3 merge and the retired rig CLI

### Changed
- `agenthub_client` pin bumped to `3a9148c`: the `4genthub-min/c3-printed-rig` branch is merged (send receipt, failed state reads, rail per request, seat socket), and the `rig` CLI is off the path.

### Testing
- `go test ./...` and `cargo test --offline` (90 passed) pass in the client; no server code changed.
