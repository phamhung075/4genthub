# Client pin: tmux server root and native room resolution

### Changed
- `agenthub_client` gitlink moved from `a118585` to `520b479` (`feat/support-agy-watch`).
  - `860aac3`: every client tmux call reaches the runtime's own tmux server (`internal/clientenv/tmux.go`).
  - `520b479`: `feed`, `watch`, `grid` and the input check resolve native rooms (`<state>/rooms/<room>/seats/<seat>`); seat naming comes from the runtime's `SeatSessionName`.

### Impact
`4genteam ps/feed/watch` see rooms started by `agenthub-runtime` from a plain shell, with no 4genteam on the machine.

### Testing
Client: `go build`, `go vet`, `go test ./...` green at `520b479`. Parent: `cd agenthub_go && go build ./... && go test ./...`.
