# The client pin carries the responsible-engineer skill, whole blocked commands and the .env rule fix

### Changed
- `agenthub_client` pin `338f192` -> `908c2fe`: the `responsible-engineer` skill is shared with every seat, the seat tool hook keeps a blocked command whole (2000 chars), and its `env-secret` rule names a `.env` file instead of matching any text containing `.env` (so `import.meta.env.VITE` and `.env.sample` pass).

### Testing
- `go test ./internal/clientskills ./internal/clientsync ./internal/clientactivity` and the runtime's `cargo test --offline seat` (24) pass in the client; `go build ./...` passes in `agenthub_go` on the merged tree. All five seats were reseated on this build and confirmed the skill loaded.
