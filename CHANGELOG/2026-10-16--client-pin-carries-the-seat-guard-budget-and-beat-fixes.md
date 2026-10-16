## Client pin carries the seat guard, the budget safeguard and the beat fix

### Changed
- `agenthub_client` pin `462e969` -> `5bf9570` (19 commits): the seat guard refuses edits to its own config and log and deletes of what it protects, and allows a seat's own `wt/<seat>` worktrees; the budget safeguard parks a runaway seat; the park semantics; and `verifyRow` accepts a fresh beat from any live match, so a second `bridge run` no longer reads "silent" at age 0s.

### Testing
- Client: `go test ./...` and `cargo test --offline` in `rust/agenthub-runtime` (130 unit + 10 `seat_guard`) at the seat-guard commit; `go test ./internal/clientservices/` after the beat fix.
