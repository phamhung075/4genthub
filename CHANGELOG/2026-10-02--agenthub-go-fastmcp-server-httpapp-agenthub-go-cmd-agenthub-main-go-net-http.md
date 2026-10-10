### Added

**Go port of the server (`agenthub_go/`) - HTTP composition root with projects, branches, tasks and subtasks live** (2026-10-02)

- `agenthub_go/fastmcp/server/httpapp/*` + `agenthub_go/cmd/agenthub/main.go`: `net/http` composition root serving `/health`, `/api/v2/projects`, `/api/v2/branches`, `/api/v2/tasks`, `/api/v2/subtasks` with the Python JSON shapes; Python sources untouched.
- `task_application_facade.go` fully ported; `subtask_application_facade.go` wired (context sync, parent-task progress via new `TaskProgressStore`).
- Parity fixes found by differential testing: Python slice semantics in `ListTasksSummary`, `ORMTaskRepository.GetTask` swallows query errors, typed-nil `OrderedMap` serialises as `null`, `/mcp` scope user (`email` null, `auth_type` method), non-UUID project ids compared as text in git-branch repo.
- Progress and ownership tracked in `agenthub_go/MIGRATION.md` and `agenthub_go/TEAM_SPLIT.md`.

**OpenRig client / 4genthub cloud: agents served as OpenRig AgentSpecs** (2026-10-02)

OpenRig `agent_ref` accepts only `local:`/`path:` (remote refs rejected), so the cloud renders AgentSpec directories and the client writes them to disk.

- `agent_management/application/services/openrig_spec_renderer.go`: template + instance config -> `agent.yaml`, `guidance/role.md` (prompt, rules, output format; delivered via `send_text`), `runtime/claude-mcp.fragment.json` (`agenthub_http`, `Bearer ${AGENTHUB_TOKEN}`; no secret in the spec).
- `server/httpapp/openrig_mount.go`: `GET /api/v2/openrig/agents[/{slug}]`, rendered from the caller's agent instance. Requires `AGENTHUB_PUBLIC_URL`.
- `scripts/openrig_sync.py`: downloads the specs (`AGENTHUB_URL`, `AGENTHUB_TOKEN`) for `agent_ref: "path:<dir>/<slug>"`.
- `cmd/agenthub -seed-agents` + `agent_template_seeder.go`: upserts `agent_templates` by slug from `AGENT_LIBRARY_DIR_PATH`; fails if any agent directory does not load.
- Tested (local Postgres, throwaway): seed 32 templates twice -> 32 rows; endpoint, 404 and 403 paths; all 32 specs pass `rig agent validate`; a rig using `path:` refs passes `rig spec validate` and `rig spec preflight`. Go unit tests for the renderer are pending a valid test path (pre-tool hook).
- `agenthub_go/MIGRATION.md` split: it keeps only the Python → Go port (slices, groups A–B, Request 5) and can be closed at `Final`; new work moved to `agenthub_go/NEXT_GEN.md` (groups C–F, Requests 1–4 and 6–10). Group F was rewritten from "full OpenRig runtime in Go (`rigd`)" to "OpenRig is the client, 4genthub is cloud data". Request 11 (company-workplace model: seats, rooms, occupants, modules) recorded with the owner's four decisions (enforced communication, offline mode via OpenRig bundles, pin by default, Jev as an optional completion gate) and planned as group G (G1 to G7).

**Seat management building blocks (company-workplace model, group G)** (2026-10-03)

- `agenthub_go/fastmcp/seat_management/domain/resolver`: pure resolver (company, room, seat overlays; add/remove/override/pin; follow-latest resolved to concrete versions; deterministic sha256).
- `seat_management/domain/seatrenderer`: renders a resolved seat as an OpenRig AgentSpec for `claude-code` and `codex`; validated with `rig agent validate`.
- `seat_management/domain/commpolicy`: default-deny communication policy (L2 guarded enforcement), policy hash, audit record, bypass detection.
- `seat_management/infrastructure/schema/seat_management_postgresql.sql` and `.../database/seat_orm.go`: draft tables and ORM structs (not applied to a database yet).
- `agent_management/application/services/openrig_spec_renderer_test.go`: renderer and seeder tests; `.claude/hooks/config/__claude_hook__valid_test_paths` now allows `agenthub_go`.
- `seat_management/infrastructure/repositories/orm`, `application/services` (`SeatResolutionService`, `SeedSeatTypes`), `domain/seedmap`: repositories over the seat tables, resolve-render-store use case, and the 32 agents as seat types. Verified on a real Postgres 18 (integration test and an end-to-end run of the real server over HTTP).
- `server/httpapp/seat_mount.go`, `seat_admin_mount.go`: `GET /api/v2/openrig/seats/{room}/{seat}`, `POST /api/v2/openrig/seat-types/seed`, and the rooms/seats/overlays/links admin API (pin by default).
- `cmd/seatcheck`: local L2 communication checker with audit log and bypass scan.
- `scripts/openrig_seat_sync.py`: pulls a resolved seat, keeps a pin lock, builds an offline `.rigbundle` on explicit request.
- `seat_settings` table and `GET|PUT /api/v2/openrig/settings` (company `follow_latest`, default off); read API for the composer: `GET /api/v2/openrig/seat-types`, `/modules/{slug}/versions/{version}`, `/overlay`, `/rooms/{room}/overlay`, `/rooms/{room}/seats/{seat}/overlay`. Verified live over HTTP on a real Postgres.
- `agenthub-frontend`: Seats pages (`/seats`, `/seats/:room/:seat`) to create rooms and seats, edit overlays, set links, preview the resolved seat and toggle company follow-latest (details in `agenthub-frontend/CHANGELOG.md`). Seat bodies now include the `seat_type` slug.
- Fixed before release: a seat-scoped overlay was written with a room id and violated `ck_overlays_scope_target`; `Overlay.ValidateTarget` now guards it.
- Finding: production `call_agent` fails because the 32 templates and 58 instances store `rules` in the Python format; see `NEXT_GEN.md` F0b. No production change was made.
