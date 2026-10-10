## Unreleased — one credential: `AGENTHUB_TOKEN` replaces the per-machine token

### Changed
- Every client and bridge now authenticates with the user token `AGENTHUB_TOKEN`. `AGENTHUB_MACHINE_TOKEN` no longer exists. The five routes that took a machine token (`POST /api/v2/openrig/seat-status`, broadcast notify, `POST /api/v2/openrig/feedback`, seat message pull and ack) use `authed`; the tenant is the token's user id.
- The machine id is now data in the request, not bound to a credential: the seat-status body already carried it, and `POST .../messages/{id}/ack` takes a required `machine_id` in its JSON body (`agenthub_go/fastmcp/server/httpapp/seat_mount.go`).
- `agenthub_go/internal/clientbridge/commands.go`, `bridge.go`, `agenthub_go/internal/clientsync/messagesverb.go`: the Go client reads `AGENTHUB_URL` and `AGENTHUB_TOKEN`; the `register` verb is gone; the ack sends `clientbridge.HostMachineID()`.
- `agenthub_client` (submodule, commit `a9662e6`): `bridge register`, `register_machine`, `write_env_file` and `REGISTER_PATH` are removed; `bridge run` and `once` read `AGENTHUB_TOKEN`; `.env.sample` and `README.md` drop the variable.
- `agenthub-frontend/src/components/seats/MachinesPanel.tsx`: the empty-state hint reads "Run 4genteam bridge run on your PC."
- `ai_docs/api-integration/surface-inventory.md`, `ai_docs/core-architecture/agenthub-system-architecture.md`: machine-token rows and sentences removed. Line pointers of the edited mounts were not re-resolved. `agenthub_go/NEXT_GEN.md` keeps its dated decision records unchanged.

### Removed
- `POST /api/v2/openrig/machines` and `DELETE /api/v2/openrig/machines/{machine}/token`; `machine_token_mount.go`, `machine_token_service.go`, `machine_token_repository.go` and their tests; `MachineTokenORM` and the `machine_tokens` DDL in `seat_management_postgresql.sql`.
- `agenthub-frontend/src/docs/apiReference.ts` regenerated (144 routes).

### Deployment
- Deploy the server first. Clients that still send a machine token get 401 afterwards: set `AGENTHUB_TOKEN` in the client `.env` (the Python client no longer reads `~/.config/agenthub-bridge.env`; its service unit now loads the client `.env`) and restart the bridge and seats.
- The `machine_tokens` table stays in existing databases until dropped by hand.

### Tested
- `go build ./...`; `go test` over `fastmcp/server/...`, `fastmcp/seat_management/...`, `internal/...`, `cmd/...`: pass.
- `agenthub_client`: 284 passed, 4 failed in `test_compact_supervisor.py` (an empty integer variable from the local `.env`, unrelated).
- `SeatsPage.test.tsx` 32 passed; `scripts/tests/test_check_served_frontend.py` 13 passed.
