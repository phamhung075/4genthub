# The client pin carries the seat-guard fix, the agy header model and the connector-token filter

### Changed
- `agenthub_client` moves from `f9bd9dc` to `de98247`:
  - `44df8d1` the guard's push, docker and tmux rules judge the command run, not words in quoted text (a queue body mentioning `git push` was refused).
  - `de98247` the feed header and `ps` name an agy seat's model, read from the room's `spec.json`.
  - `f77d506` the connector token leaves the seat env, the `-e` argv and the tmux server (a seat's commit).
  - `f17f84e` the pane tests take the process tmux root in turn (a seat's commit).

### Testing
- `go vet ./...`, `go test ./...` and `cargo test --offline` (110) pass in the client.
