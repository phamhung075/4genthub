## The server holds no Jev: the decision ladder and the completion gate run on the user's client

### Changed
- Owner ruling 2026-10-14: Jev (TypeSafe System One) runs on the user's client, like the LLM on a seat. The server stores asks and tasks and no longer evaluates anything.
- `agenthub_go/fastmcp/room_decisions/application/services/room_decision_service.go`: `Create` no longer auto-answers an ask through an evaluator; the evaluator interface, the owner-only set, the Jev decision log and `DecisionChoiceSelection` are gone.
- `agenthub_go/fastmcp/server/httpapp/room_decisions_mount.go`: `POST /api/v2/openrig/decisions/evaluate` and its handler are removed.
- `agenthub_go/fastmcp/task_management/application/use_cases/complete_task.go` and `agenthub_go/fastmcp/server/httpapp/task_wiring.go`: completing a task no longer runs a validation gate or reads `VALIDATION_GATE_ENFORCEMENT`, `TYPESAFE_*` or `JEV_*`.
- `agenthub-frontend/src/docs/apiReference.ts` regenerated with `go run ./cmd/apirefgen` (the evaluate route is gone).
- `.env.sample`: the `TYPESAFE_*`, `JEV_*` and `VALIDATION_GATE_ENFORCEMENT` entries are removed; they live in the client's `.env.sample`. `NEXT-GEN2.md` (O5, C6) records the move.

### Removed
- `room_decision_ladder.go` (+ test), `domain/decisions/ladder.go`, `httpapp/room_decisions_ladder_test.go`, `task_management/domain/services/validation_gate_service.go` (+ test), `infrastructure/ai_services/typesafe_jev_client.go` (+ test), `use_cases/complete_task_validation_gate_test.go`.
- The `gate_verdict` ledger event kind and its recorder in `status_ledger.go` are left in place; nothing on the server writes them now.
- The gate's in-process daily token cap (1M tokens) has no client equivalent yet: a client process lives one call, so a cap would need a persisted counter.

### Added
- Client side (separate repo `agenthub_client`, commit `a544882`): `4genteam decide` runs the ladder locally; the new `4genteam complete` runs the gate before it calls the server. See `agenthub_client/CHANGELOG/2026-10-14--jev-runs-on-the-client-decide-and-complete.md`.

### Tested
- `go build ./... && go vet ./... && go test ./...` in `agenthub_go` pass (whole module, including `internal/apiref`, which checks the committed artefact against the routes).
