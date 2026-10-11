### Added

**Per-machine tokens for the bridge** (2026-10-03)

- `POST /api/v2/openrig/machines` `{machine_id}` (user token) registers a machine and returns its token once (`mt_` plus 256 random bits, `Cache-Control: no-store`); 409 while the machine has an active token, 400 for an invalid id. `DELETE /api/v2/openrig/machines/{machine}/token` revokes it (404 when this user has no active token for that machine, so another user's machine looks absent).
- `POST /api/v2/openrig/seat-status` now takes only a machine token, no longer a user token: 403 without a header, 401 for an unknown, revoked or malformed token, 403 when the report's `machine_id` is not the token's machine. The report is stored under the token's user and machine. A machine token is rejected everywhere else. `GET /api/v2/openrig/machines` still takes the user token. Breaking for existing bridges: register the machine and set `AGENTHUB_TOKEN` to the new token.
- `agenthub_go/fastmcp/server/httpapp/machine_token_mount.go`, `seat_management/application/services/machine_token_service.go`, `infrastructure/repositories/orm/machine_token_repository.go`; table `machine_tokens` (`token_hash` SHA-256 hex only, `revoked_at`, partial unique index on `(user_id, machine_id) WHERE revoked_at IS NULL`) in the ORM structs, `seat_tables.go` and `seat_management_postgresql.sql`. The token is never stored, logged or returned again.
- Production note: `machine_tokens` is a new table; apply the DDL there before deploying, or the bridge cannot authenticate.
- `scripts/openrig_bridge.py`: docstring describes the machine token.

**Delete a seat link and delete a room** (2026-10-03)

- `agenthub_go/fastmcp/server/httpapp/seat_admin_mount.go`: `DELETE /api/v2/openrig/rooms/{room}/seats/{seat}/links/{to}/{kind}` removes one link (404 unknown room, seat or link; 400 bad kind; the target may be a removed seat). `DELETE /api/v2/openrig/rooms/{room}` hard-deletes the room.
- `agenthub_go/fastmcp/seat_management/application/services/room_deletion_service.go`: application-layer cascade in one transaction, in dependency order: per seat (including removed ones) its links, overlay, resolved snapshots, then the seat; then the room overlay and the room. No foreign-key cascade. Company overlay and other rooms are untouched. The rendered rigspec no longer contains deleted links.
- Repositories: `Delete`/`DeleteBySeat` (links), `DeleteForRoom`/`DeleteForSeat` (overlays), `DeleteBySeat` (resolved seats), `Delete` (seats, rooms); every statement filters `user_id`, so another user's request deletes nothing (404 at the API).
- Not cleaned: `seat_status` rows of a deleted room (reported names, replaced by the next bridge report).

**Module list and seat-type versions API** (2026-10-03)

- `agenthub_go/fastmcp/server/httpapp/seat_admin_mount.go`: `GET /api/v2/openrig/modules` lists the latest version of each module (`slug`, `kind`, `version`, `sha256`, no content). `POST /api/v2/openrig/seat-types/{slug}/versions` with `{module_refs: ["slug@version"], default_runtime}` appends the next patch version (`1.0.0` when none); 404 unknown seat type, 400 malformed, duplicate or unknown module refs and invalid runtime.
- `seat_management`: `ModuleRepository.ListLatest`, `SeatTypeRepository.SetDefaultRuntime`, `ParseModuleRef`, `NextPatchVersion`.
- Note: `default_runtime` is a column of `seat_types`, not of a version, so the POST updates it on the seat type for every version.

**Switch a seat's LLM, Claude bypass policy, delegation rule** (2026-10-03)

- `agenthub_go/fastmcp/server/httpapp/seat_admin_mount.go`, `seat_management/application/services/seat_admin_service.go`: `PUT /api/v2/openrig/rooms/{room}/seats/{seat}/occupant` changes a seat's runtime (`claude-code`, `codex`) and model; one `SeatAdminService` serves REST and MCP.
- `agenthub_go/fastmcp/seat_management/interface/mcp_controllers/manage_seat_controller.go`: MCP tool `manage_seat` (`list`, `get`, `set_occupant`).
- `scripts/openrig_seat_sync.py`: `switch ROOM SEAT [--runtime] [--model] [--apply none|set-model|restart]` records the change in 4genthub and applies a model change with `rig seat set-model` (runtime changes need `rig down`/`rig up`, printed as manual steps); `rig ROOM --permission-policy locked|standard|open|yolo|none`.
- `GET /api/v2/openrig/rooms/{room}/rigspec?permission_policy=...` renders a rig-level `permission_policy: builtin:<name>`; `yolo` makes OpenRig launch Claude with `--dangerously-skip-permissions` (verified: `rig spec preflight` reports `launch_posture=full_bypass`).
- `scripts/team/4genthub/delegate-deepseek.txt`: company-wide rule to delegate parallel work to deepseek-offload workers.
- Frontend: "LLM" tab on the seat page, see `agenthub-frontend/CHANGELOG.md`.
- `/health` reports `0.0.10`.
- Production note: the `seat_links` check constraint `ck_seat_links_kind` created by the first seat deploy still lists the old kinds; `collaborates_with`, `spawned_by` and `can_observe` links fail there until the constraint is replaced by hand.
