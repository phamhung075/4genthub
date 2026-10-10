### Fixed

**Resolved seat snapshot: losing the first-save race is not a failure** (2026-10-04)

- `agenthub_go/fastmcp/seat_management/infrastructure/repositories/orm/resolved_seat_repository.go`: `Save` read the snapshot and then inserted it without a lock, so two concurrent first resolves of the same seat hit `uq_resolved_seats_seat_hash` and one surfaced as a failure (`call_seat` and the resolved-seat route). A unique violation now re-reads and returns the row the other writer stored, like `AddVersion` of a seat type; any other insert error is returned as before, and a failing re-read is reported.
- Test: `TestResolvedSeatSaveLostRace` (lost race returns the winner after one re-read, other errors are not re-read, a failing re-read is reported); it fails without the change. `go vet` and `go test` for `fastmcp/seat_management/...` and `fastmcp/server/httpapp/...` pass.

**call_seat: description matches the response, input is trimmed** (2026-10-04)

- `agenthub_go/fastmcp/seat_management/interface/mcp_controllers/call_seat_controller.go`: `CallSeatToolDescription` no longer promises a `model` (`CallSeat` never returned one and the snapshot has no model column) and says that a new hash writes a `resolved_seats` row; `SeatResolver` states that `ResolveSeat` returns a non-nil seat whenever the error is nil; `room` and `seat` are trimmed, so a whitespace-only value is the same `room and seat are required` failure as a missing one.
- Tests: `call_seat_controller_test.go` asserts the `policy` field and a whitespace-only room. `go vet` and `go test` for `fastmcp/seat_management/...` and `fastmcp/server/httpapp/...` pass.

**omp seat gets no runtime fragment: the assertion added** (2026-10-04)

- `agenthub_go/fastmcp/seat_management/domain/seatrenderer/renderer_test.go`: the "no `runtime/` file" loop covered `codex` and `agy` only, so the narrowed `receivesClaudeFragments` for `omp` was unasserted — flagged by the DeepSeek supervisor seat, not by reading. `omp` added to the loop. Proven by mutation rather than by the test passing: restoring the old predicate makes it fail with `omp seat has a runtime file "runtime/claude-mcp.fragment.json"`, and the correct implementation was restored exactly (`git diff` on `renderer.go` is empty). Coverage only, no behavior change. `go vet ./...` and `go test ./...` green.

**omp accepted by the API but rejected by the UI, the sync CLI and the bridge** (2026-10-04)

Found by a headless DeepSeek review of `2c8d05f3` and confirmed by reading every file it named: the server was taught to accept `omp`, but each client-side enumeration of runtimes was left behind, so "a seat can run DeepSeek" held only through the raw API or MCP.

- `agenthub-frontend/src/types/seatTypes.ts`: `SeatRuntime` and `SEAT_RUNTIMES` listed only `claude-code` and `codex` — `agy` had been missing too. Both now carry all four runtimes. Consequence before the fix: the occupant switcher in `SeatLlmPanel.tsx`, `SeatTypeVersionForm.tsx` and `SeatsPage.tsx` could not select `omp`, and a seat already stored as `omp` rendered with an unmatched option, so any edit rewrote the occupant.
- `scripts/openrig_seat_sync.py` (`RUNTIMES`, used by `switch`): `omp` added, so `switch --runtime omp` no longer exits with a usage error before reaching a server that accepts it.
- `scripts/openrig_bridge.py` (`RUNTIMES`): `omp` added. Before the fix the bridge coerced an `omp` node's runtime to `"unknown"` before posting, so the DeepSeek supervisor seat would have reached the cloud mislabelled — the same declared-versus-live drift already recorded for the nine `agy`-labelled `4genthub-dev` seats. The Go side already accepted it, so the existing Go test was verified only against a producer that could never emit `omp`.
- `agenthub_go/NEXT_GEN.md`: Request 16's line and T3 no longer quote a three-runtime list, and T3 no longer cites line numbers that the change invalidated.
- Checked: `tsc --noEmit` reports 0 errors, the three affected vitest suites pass (54 tests across `SeatAuthoringPage`, `SeatDetailPage`, `SeatsPage`), and both scripts compile (`python3 -m py_compile`).

**Deleted the unused Go port of agent_routes.py** (2026-10-04)

- `agenthub_go/fastmcp/server/routes/agent_routes.go`: removed. Its `AgentController` interface, request types and handlers (`GetAllAgentsMetadata`, `GetSingleAgentMetadata`, `RegisterAgent`, `ListAgents`, `UpdateAgent`, `DeleteAgent`, `AssignAgent`, `UnassignAgent`) had no caller or test anywhere in the module; the served agent routes are in `httpapp/routes_mount.go` and `httpapp/agents_mount.go`. Checked: `go build ./...`, `go vet ./fastmcp/server/...`, `go test ./fastmcp/server/...`; the helpers it used (`httpErr`, `pyOrStr`, `currentUserID`, `containsNotFound`) are still used by other route files.

**Removed the four Go agent assignment stubs that faked Python 500 errors** (2026-10-04)

- `agenthub_go/fastmcp/server/httpapp/agents_mount.go`: deleted `POST /api/v2/agents/assign`, `DELETE /api/v2/agents/unassign/{branch_id}`, `GET /api/v2/agents/branch/{branch_id}/assignment` and `GET /api/v2/agents/project/{project_id}/assignments`. The controller has no assignment methods; each handler only returned a hard-coded 500 to preserve a Python quirk. `POST /call` stays; `GET /metadata` and `GET /{agent_name}` stay in `routes_mount.go`. The header comment now describes only `/call`.
- Impact: those four paths now answer 404 or 405. No live frontend caller exists (the client functions are removed by web-dev).

**Pinned seats no longer move when a module is published: overlay `add` requires a concrete version** (2026-10-04)

- `agenthub_go/fastmcp/server/httpapp/seat_admin_mount.go`: an overlay `add` op with a missing version or `"latest"` is rejected with 400 `add requires a concrete version`, like `pin`. `seatAdminOverlayModulesExist` now only looks up concrete versions (the latest-version branch is deleted).
- `agenthub_go/fastmcp/seat_management/domain/resolver/resolver.go`: `Resolve` rejects an empty or `"latest"` version on seat type refs, `add` and `pin` ops (`requireConcrete`). The follow-latest path and `Catalog.Latest` are removed (`catalog.go` `DBCatalog.Latest` too). Found by the reviewer: a pinned seat's hash changed when only a module version was published, because an overlay `add rules latest` followed the catalog. No compatibility path: a stored overlay holding `""` or `"latest"` on an `add` now fails to resolve with an explicit error until it is edited (dev phase).
- `agenthub_go/fastmcp/seat_management/infrastructure/repositories/orm/module_repository.go` and `domain/repositories/repositories.go`: `ModuleRepository.LatestVersion` is deleted (no non-test caller remained; `ListLatest` stays). Stored overlays that hold `""` or `"latest"` on an `add` must be edited by hand: there is no migration.
- `agenthub_go/NEXT_GEN.md` (G5): the verified sentence is corrected (overlay `add` was the exception to "references are concrete"). G5 stays unticked; the check wording will be corrected when it is ticked.
- Frontend not changed here: `agenthub-frontend/src/pages/SeatDetailPage.tsx:177-178` `canAdd` requires a version only for `pin`; it must also require one for `add`.
