# The client pin carries the folded watch view and its filters

### Changed
- `agenthub_client` pin bumped to `1046e41`: `4genteam watch`, `grid` and `feed` fold results, stamp the seat's own record time, show a line diff for edits, take `--only`, `--errors`, `--changes`, `--expand`, and default `--width` to the pane width (`internal/clientwatch/view.go`, `render.go`, `feed.go`).

### Testing
- `go test ./...` passes in the client; no server code changed.
