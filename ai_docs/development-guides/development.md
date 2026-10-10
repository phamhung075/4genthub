# Development

Commands that run the project. Each one is the source of truth for its own output; this page only says which to run.

| Task | Command (repo root) |
|---|---|
| Go tests | `cd agenthub_go && go test ./...` |
| Go vet | `cd agenthub_go && go vet ./...` |
| Client tests | `cd agenthub_client && PYTHONPATH=src python3 -m pytest` |
| Frontend tests | `cd agenthub-frontend && pnpm test` |
| Frontend dev server (port 3800) | `cd agenthub-frontend && pnpm start` |
| Frontend build | `cd agenthub-frontend && pnpm build` |
| Rebuild and restart the backend in Docker | `echo "R" \| ./docker-system/docker-menu.sh` |
| Seat room status | `4genteam up` (starts bridge, compaction supervisor and grid) |

CI runs the Go and frontend jobs from `.github/workflows/ci.yml`.

## Where to look

- Architecture and decisions: `ai_docs/core-architecture/agenthub-system-architecture.md`
- Routes, MCP tools, tables: `ai_docs/api-integration/surface-inventory.md` (re-runnable checks in its appendix)
- Agent and seat rules: `AGENTS.md`, then `ai_docs/agent-system/`
- Schema: `agenthub_go/fastmcp/task_management/infrastructure/database/init_schema_postgresql.sql`, changed together with its entity struct

## Rules that bite

- The Python backend is gone. Python in this repo is the client (`agenthub_client`) and scripts.
- A change to Go code needs a backend restart to run; a tests-only change does not.
- Tests follow the entity definition, not the other way round.
