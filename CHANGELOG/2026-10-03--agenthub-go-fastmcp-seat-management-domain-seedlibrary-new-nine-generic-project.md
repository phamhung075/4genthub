### Changed

**Generic seat library embedded in the binary** (2026-10-03)

- `agenthub_go/fastmcp/seat_management/domain/seedlibrary/` (new): nine generic, project-agnostic seat types (`lead`, `planner`, `architect`, `developer`, `reviewer`, `tester`, `debugger`, `researcher`, `writer`) written for OpenRig seats, embedded with `go:embed`; strict YAML loader.
- `agenthub_go/fastmcp/seat_management/domain/seedmap/seedmap.go`: `FromSpec` replaces `Map`/`MapAll` (no more `AgentTemplate` input).
- `agenthub_go/fastmcp/server/httpapp/seat_mount.go`: `POST /api/v2/openrig/seat-types/seed` no longer reads `AGENT_LIBRARY_DIR_PATH`, so it works in the distroless production image.
- `/health` reports `0.0.8`.
- Seat types seeded from the old `agenthub_main/agent-library` (32 types, for example `coding-agent`) are not removed from databases that already hold them; `call_agent` and the AgentSpec route still use that library.
