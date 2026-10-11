### Fixed

**The seatcheck PATH check reads the daemon's PATH at cold start** (2026-10-04)

- `scripts/openrig_seat_sync.py`: at cold start (no tmux server) `resolve_checker` checked the operator's shell PATH, but the first seat inherits the PATH of the rig daemon that starts the first tmux server. It now reads that PATH from the daemon process: `openrig_daemon_port` takes `OPENRIG_PORT` (else the port in `OPENRIG_URL`), `openrig_daemon_pid` finds the listening pid with `ss -ltnp`, and `proc_env_path` reads `/proc/<pid>/environ`. `seat_path` returns the daemon PATH with the source `rig daemon PATH`, falling back to the shell PATH only when neither a tmux server nor a readable daemon PATH exists (and saying so). The module docstring and `PATH_LIMIT` are updated. No OpenRig or `cmd/seatcheck` change.

**Subtask assignee filter works on PostgreSQL (N2)** (2026-10-04)

- `agenthub_go/fastmcp/task_management/infrastructure/repositories/subtask_repository.go`: `FindByAssignee` and `GetSubtasksByAssignee` filtered with `"assignees" LIKE '%' || $1::json || '%'`, which PostgreSQL rejects for a json/jsonb column, so both raised for any plain name — the filter was unusable. They now use jsonb array containment (`"assignees"::jsonb @> $1::jsonb`), so an `@seat_key` (or any exact element) is found; the `user_id` cross-tenant filter is unchanged and `GetSubtasksByAssignee` keeps no user filter (Python parity). Intentional deviation, recorded as N2 in `MIGRATION.md`.
- Tests: `TestSubtaskRepositoryFindByAssigneeUsesJsonbContainment` replaces the defect-pinning test (owner found; another user not found; a bare name and an absent name match nothing).

**Database migrator recognises both PostgreSQL schemes (defect)** (2026-10-04)

- `agenthub_go/fastmcp/database_migrations.go`: `RunMigrations` and `InitializeDatabase` gated on `strings.Contains(url, "postgresql")`, so a valid `postgres://` DSN (what pgx and the throwaway-Postgres tests use) was treated as non-PostgreSQL and the progress-history migration silently skipped; `TestDatabaseMigratorRunMigrations` was red. Both now use `isPostgresURL`, which accepts `postgres://` and `postgresql://`. The app's own URL builder emits `postgresql://`, so production behaviour is unchanged; the guard no longer depends on which valid scheme a caller passes.

**Session list order is deterministic on a `last_seen` tie (A6)** (2026-10-04)

- `agenthub_go/fastmcp/session_stream/repository.go`: `ListSessions` orders `last_seen DESC, id` so a tie in `last_seen` no longer leaves the order undefined; the uuid5 `id` is a stable tiebreaker and the output is unchanged when timestamps differ. Found by the reviewer as a flake risk in the new ordering test.

**Stored subtasks with an old-style assignee load again (D6e)** (2026-10-04)

- `entities.RestoreSubtask` (new, `domain/entities/subtask.go`) rebuilds a subtask from stored data without judging its assignees; `subtask_repository.go` hydration uses it. D6d had routed hydration through the validating `NewSubtask`, so one row holding a bare unknown name (for example `["go-dev"]`) made every list containing it fail. `NewSubtask` still validates; the rule applies to what is written. A stored known role or `@` name is shown in its `@` form; any other stored name stays as stored. The subtask-create error is now the entity's one message ('An assignee is `@<seat_key>` or a known agent role.').

**Connector message cap counts characters; websocket reads are bounded at 4 MiB (A4)** (2026-10-04)

- `agenthub_go/fastmcp/server/httpapp/ws_mount.go`: the 1 MiB connector limit (`MAX_MESSAGE_CHARS`) counts characters (`utf8.RuneCountInString`), as Python's `len(str)` does; it counted bytes, so a multibyte message of up to 1 MiB characters was refused. The read itself is bounded at `wsMaxMessageBytes` = 4 MiB (4 bytes per character, the most 1 MiB characters can take) per message: the bound was 64 MiB per frame and fragments of one message were not bounded at all; now the fragments of a message count together and an over-bound message ends the connection. The bound also applies to `/ws/realtime` and the session viewer, which share the reader.

**Session REST routes answer `{"sessions": [...]}` and `{"events": [...]}` (A6)** (2026-10-04)

- `agenthub_go/fastmcp/server/httpapp/session_stream_routes.go` and `http.go` (`writeKeyedSliceResult`): `GET /api/v2/sessions` and `GET /api/v2/sessions/{id}/events` return the object the Python routes return (also when empty) instead of a bare array. No caller of these routes exists in `agenthub-frontend`, in the Go code or in the connector.

**Session events route default page is 500 events (A6)** (2026-10-04)

- `agenthub_go/fastmcp/server/httpapp/session_stream_routes.go`: `limit` defaults to 500 as in the Python route (it was 100). The page is still clamped to 1000.

**Session events route answers 404 for an unknown or foreign session (A6)** (2026-10-04)

- `agenthub_go/fastmcp/server/routes/session_stream_routes.go`: `GetSessionEvents` checks `GetSessionForUser` first, as the Python route does: a session that does not exist and one that belongs to another user both give 404 "Session not found". It returned 200 `[]`, and mapped every database error to 404; a database error is now a 500.

**`GET /api/v2/sessions/{id}/events` returned no events (A6)** (2026-10-04)

- `agenthub_go/fastmcp/server/routes/session_stream_routes.go`: `GetSessionEvents` passed `(sessionID, userID)` to `session_stream.ListEvents`, whose parameters are `(userID, sessionID)`, so the query never matched a row and the route always answered `[]`. Live in 0.0.14. Found by the new real-Postgres handler tests.

**MCP `manage_task` create accepts `@<seat_key>` assignees (D6c)** (2026-10-04)

- `agenthub_go/fastmcp/task_management/interface/mcp_controllers/task_mcp_controller/handlers/crud_handler.go`: the inline role allow-list (`@name` only if `IsValidRole(name)`) is replaced by `Task.ValidateAssigneeList`, the validator subtask creation already uses. One rule for MCP create and subtask create: `@<name>` (a seat key or a role) is kept, a bare known role or legacy name becomes `@<role>`, any other bare name is rejected. Whitespace around an assignee is stripped first.
- Tool description of `manage_task` (`manage_task_description.go`) and `interface/testdata/tools_golden.json` now describe `@seat-key` assignees instead of the 42-agent library.
- Not changed, on purpose: `Task.UpdateAssignees`, `Subtask.UpdateAssignees` and REST create keep any bare name (a Python-parity test pins `custom` kept), so they never reject a seat key; REST create's own `ResolveLegacyRole` maps `coding-agent` to `@senior_developer` while MCP create gives `@coding-agent`.
