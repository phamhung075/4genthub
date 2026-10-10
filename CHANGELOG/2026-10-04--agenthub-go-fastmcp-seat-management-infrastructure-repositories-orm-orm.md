### Added

**Cross-tenant coverage for every seat table (OF2)** (2026-10-04)

- `agenthub_go/fastmcp/seat_management/infrastructure/repositories/orm/orm_repositories_test.go`: five tests assert the `user_id` filter on the statements of `module_versions`, `seat_type_versions`, `rooms`, `seat_links` and `resolved_seats` — the five seat tables that had none (`TestModuleVersionStatementsAreTenantScoped`, `TestSeatTypeVersionStatementsAreTenantScoped`, `TestRoomStatementsAreTenantScoped`, `TestSeatLinkStatementsAreTenantScoped`, `TestResolvedSeatStatementsAreTenantScoped`). All nine seat tables now have one; each new test was mutation-proved (dropping `user_id` from that table's statement makes it fail).
- `agenthub_go/NEXT_GEN.md` G1: the inherited "SQLite and Postgres schemas identical" clause is removed — the Go server is Postgres-only, `grep -rn sqlite agenthub_go/fastmcp/seat_management` finds nothing, and no SQLite dialect was added to satisfy it. The check now states the Postgres schema and the per-table cross-tenant tests, with the evidence.

**Session-stream handler tests: the Python suite ported in full (A4/A6/A7)** (2026-10-04)

- `agenthub_go/fastmcp/server/httpapp/ws_connector_test.go`: six connector-ingest scenarios ported from `agenthub_main/src/tests/session_stream/session_stream_test.py` (bad token refused before the upgrade, events for an unregistered session key, a second `hello`, non-object events plus a non-string `project`, disconnect marks the connector's sessions offline, a reconnect keeps them online until the last socket closes), `TestSessionViewerReplaysIngestedEventsFromTheDatabase` (the viewer's real-Postgres path) and `TestSessionListIsNewestLastSeenFirst`.
- `agenthub_go/fastmcp/session_stream/repository_test.go`: `TestSessionTimestampsRenderAsNaiveUTC`.
- The audit found 16 Python tests (MIGRATION said 9); the full test-to-test mapping and the A1–A7 verification run are recorded in `agenthub_go/MIGRATION.md`.

**`WS /ws/sessions/{id}`, the session viewer (A5)** (2026-10-04)

- `agenthub_go/fastmcp/server/httpapp/ws_session_viewer.go`, mounted in `ws_mount.go`. Token from `?token=` through `auth.ValidateTokenUniversal`; a missing id and a session of another user both close with 4004 "Session not found". The viewer subscribes to the hub before it replays `after_seq` in pages of 500, then follows live events (events at or below the last sent seq are skipped), keeps reading the socket so a client that closed while idle releases its subscription, and closes a viewer the hub dropped as too slow with 1013 "Too slow, reconnect". Ports `session_viewer` in `session_stream_routes.py`.
- Deviation from Python, to confirm: the 4004 close is sent after the upgrade. Starlette closing before `accept` rejects the handshake with HTTP 403, so a Python client sees 403, not 4004. Auth failure is HTTP 403 before the upgrade, as for `/ws/connector`.
- `session_stream.SessionHub.Subscribers(sessionID)` added (used by the tests).
