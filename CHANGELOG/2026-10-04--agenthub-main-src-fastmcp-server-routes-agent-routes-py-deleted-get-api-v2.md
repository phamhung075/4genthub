### Fixed

**Six agent routes that always answered 500 are removed** (2026-10-04)

- `agenthub_main/src/fastmcp/server/routes/agent_routes.py`: deleted `GET /api/v2/agents/{agent_name}`, `POST /assign`, `DELETE /unassign/{branch_id}`, `GET /branch/{branch_id}/assignment`, `GET /project/{project_id}/assignments` and `GET /capabilities`. Each called an `AgentAPIController` method that does not exist (`get_single_agent_metadata`, `assign_agent`, `unassign_agent`, `get_branch_assignment`, `get_project_assignments`, `get_all_capabilities`), so it answered 500 on every request; `GET /capabilities` was also unreachable behind `GET /{agent_name}`. The frontend `agentApiV2` functions for them had no importer outside test mocks, and no Python, MCP or script caller exists. `GET /metadata` and `POST /call` stay. The Go mirrors (`agents_mount.go`) and the frontend functions are removed by their owners.

**`GET /api/v2/agents/metadata` no longer returns 500** (2026-10-04)

- `agenthub_main/src/fastmcp/server/routes/agent_routes.py` (`get_all_agents_metadata`): `AgentAPIController.get_agent_metadata` returns a plain dict, but the route read `result.success` and called `result.model_dump`, so every request raised `'dict' object has no attribute 'success'` and answered 500. The route now reads `result.get("success")` and returns the dict; a failed result still answers 500 with the controller `message`.
- Not fixed, reported to the lead: the other six routes in that file call controller methods that do not exist (`get_single_agent_metadata`, `assign_agent`, `unassign_agent`, `get_branch_assignment`, `get_project_assignments`, `get_all_capabilities`), so they always answer 500; `GET /capabilities` is also shadowed by `GET /{agent_name}`. The controller falls back to static metadata when the facade fails (`agent_api_controller.py` lines 49-56 and 68-78), which conflicts with the no-fallback rule.

**The seatcheck PATH check reads the PATH seats inherit** (2026-10-04)

- `scripts/openrig_seat_sync.py`: `resolve_checker` and `describe_found` now resolve `seatcheck` against `tmux show-environment -g PATH` (new `tmux_global_path`, `seat_path`) when a tmux server answers, instead of this shell's PATH. With no tmux server (no seat exists yet) they check the shell PATH and print `note: checked seatcheck on the shell PATH (no tmux server is running, ...)` to stderr; failure messages name the PATH that was checked, and `PATH_LIMIT` now describes the cold-start case (the first seat inherits the daemon's PATH) and says that only the default tmux socket is queried. The tmux call has a 5 second timeout; a hung server counts as no server. Not verified: the cold start case, and a non-default tmux socket.

**`openrig_seat_sync.py switch` accepts the agy runtime** (2026-10-04)

- `scripts/openrig_seat_sync.py`: `RUNTIMES` now includes `agy`, so `switch ROOM SEAT --runtime agy --model <model>` is no longer rejected with exit 2 by the client before the server sees it. The Python lists in `openrig_bridge.py` and this script are still separate from Go's `resolver.CheckRuntime`; the single-source claim of the status-report entry above holds for Go only.

**Seat status reports accept the agy runtime** (2026-10-03)

- `agenthub_go/fastmcp/server/httpapp/seat_status_mount.go`: `validSeatRuntime` replaces the hard-coded `seatRuntimes` map; it accepts every runtime `resolver.CheckRuntime` accepts (claude-code, codex, agy) plus `terminal` and `unknown`, so the runtime list has one source.
- `scripts/openrig_bridge.py`: `RUNTIMES` includes `agy`, so an agy seat reports `agy` instead of `unknown`.
- Tests: `TestSeatStatusPostAcceptsEverySeatRuntime`, `test_runtime_mapping_keeps_every_supported_runtime`.

**Decouple seat types seed from AGENTHUB_PUBLIC_URL requirement** (2026-10-03)

- `agenthub_go/fastmcp/server/httpapp/seat_mount.go`: `handleSeedSeatTypes` was coupled to `AGENTHUB_PUBLIC_URL` validation through `seatSourceFor`, causing `POST /api/v2/openrig/seat-types/seed` to return 500 when `AGENTHUB_PUBLIC_URL` was unset. Seeding only inserts seed modules and seat type definitions and does not render specs. `seatSourceFor` now decouples the public URL check from source creation, allowing seeding without `AGENTHUB_PUBLIC_URL`, while `handleResolveSeat` preserves the requirement.
- Tests: `TestSeedSeatTypesWorksWithoutPublicURL` and `TestSeedSeatTypesErrorMapping` in `seat_mount_test.go`.
