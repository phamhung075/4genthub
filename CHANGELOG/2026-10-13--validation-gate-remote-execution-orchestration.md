# Validation Gate, Remote Execution, and Orchestration Work Routing (O5, O6, O7, P7, D4/F5)

Delivered Tracks 1 & 2 items for Next-Gen Architecture:

1. **Validation Gate & Shadow Mode (O5) & Gate Enforcement (O6):**
   - Implemented `ValidationGateService` in `agenthub_go/fastmcp/task_management/domain/services/validation_gate_service.go` evaluating deterministic checks D1–D5 (syntax, types, test command exit code/failures, clean diff keep-out scan, numstat bounds) and Jev model (`jev-1.13.0`) criteria verification.
   - Enforced daily token budget cap (1M input tokens/day) with fail-safe fallback to `uncertain` (never `accept`) on timeout or budget exhaustion.
   - Integrated with `CompleteTaskUseCase`:
     - Shadow mode records `gate_verdict` events on the ledger without blocking task completion.
     - Enforcement mode transitions tasks to `review`, moving to `done` on `accept`, reverting to `in_progress` with recorded reasons on `reject`, or escalating on `uncertain`.
   - Added `RecordGateVerdict` to ledger recorder and updated test doubles. Verified via `validation_gate_service_test.go` and `complete_task_validation_gate_test.go`.

2. **Context Updates on Ledger Cursor (P7):**
   - Wired `ContextEventWriter` / `ContextEventAppender` into `update_context.go`, `unified_context_service.go`, `unified_context_facade_factory.go`, and `app.go`.
   - Task context mutations emit `context_updated {level, id, version}` events into `task_events`.
   - Client `internal/clientoutbox/manager.go` reacts to `context_updated` by triggering background prefetch and refresh of local disk resume cache.

3. **Routing & Wake-on-Open-Work (O7):**
   - Added `ClaimedBy` / `ClaimedAt` fields and `Claim()` method to `Task` entity in `task.go`.
   - Added endpoint `GET /api/v2/machines/{machine}/work` in `fastmcp/server/routes/machine_work_routes.go` and mounted in `task_routes.go`, listing active tasks assigned to the machine's seats.
   - Client `internal/clientoutbox/manager.go` implemented `FetchWork` and `WakeSeatsForWork` with duplicate suppression when tasks are claimed, exposed via `4genteam ledger work`.

4. **Remote Execution via Connector (D4 & F5):**
   - Added `CapabilityCommands = "commands"` to `/ws/connector` client in `agenthub_client/internal/clientsync/connector.go`.
   - Added opt-in remote execution handler `handleRemoteCommand` in `rigd.go` supporting `send_to_seat`, `up`, and `down`.
   - Strict security guardrails: human-only issuer check, token scope `sessions:command` validation, action whitelist, room whitelist, and fail-closed structured refusal codes.
   - Verified via unit tests in `remote_commands_test.go`.
