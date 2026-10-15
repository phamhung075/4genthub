## 2026-10-15 - Client pin carries seats starting with the state root's .env

### Changed
- `agenthub_client`: pin bumped to `ad2fcd4`, where every seat starts with `~/.config/4genthub/.env` in its environment.

### Testing
- Client `cargo test --offline` (91 passed), `go vet` and `go test ./...` clean.
