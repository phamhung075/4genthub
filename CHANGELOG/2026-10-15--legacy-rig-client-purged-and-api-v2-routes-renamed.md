## The legacy rig-client code is purged and the client routes move up to `/api/v2/*`

### Changed
- BREAKING: every route under the old client sub-prefix is mounted directly at `/api/v2/` (Go server in `agenthub_go/`, frontend in `agenthub-frontend/src/`, client in `agenthub_client/`, tests, `apiReference.ts`, docs). Deploy server, frontend and client together.
- BREAKING: the `seat_feedback.layer` value naming the old client is now `client` (`feedback.go` `LayerClient`, `seat_tables.go`, `seat_management_postgresql.sql`, `0001_baseline.sql`, MCP tool descriptions, `agenthub-frontend/src/types/feedback.ts`, `FeedbackPage.tsx`).
- `rigspec` package renamed `linkgraph`; seed library (11 seat types, blocks, `skill-library.json`, `comm-guard.json`) reworded for the 4genteam client; `comm-guard.json` now denies `4genteam send`/`4genteam input`/tmux send-keys/paste-buffer and allows `seatcheck send`/`4genteam whoami`; `seedVersion` 1.4.3 -> 1.4.4 with `guides.lock.json` and `seedcontent.lock.json` updated.
- The old client's environment variables are renamed `AGENTHUB_*`; the state home is `~/.config/4genthub`.
- Every mention of the old client is removed from CHANGELOG/, ai_docs/, TEST-CHANGELOG.md, NEXT_GEN*.md, scripts, hooks and the frontend copy. The `agenthub_client` pin moves with its own matching change (Rust env deny list, retired verbs, route prefix).

### Added
- `agenthub_go/fastmcp/task_management/infrastructure/database/migrations/0004_seat_feedback_layer_client.sql`: drops the layer CHECK, rewrites the old rows to `client`, re-adds the CHECK. Idempotent; run it on production before the deploying push. It is the only file that still names the old value, by necessity.

### Removed
- `agenthub_go/cmd/agenthubclient`, `internal/clientbridge`, `internal/clientcmd`, `internal/clientsync`, the rigspec mount and renderer, and `TestRenderSeatRigValidate` (needed the external binary).

### Testing
- `cd agenthub_go && gofmt -l . && go vet ./... && go test ./...` clean; `python3 -m pytest scripts/tests -q` 91 passed; client `go vet ./... && go test ./...` and `cargo test --offline` (103) pass. Frontend was type-checked only, not built.
