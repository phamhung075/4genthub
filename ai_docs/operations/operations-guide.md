# Operations guide

Deploying, checking and repairing the server and the dashboard. Rooms and seats: `client-seat-limits.md`,
`seat-compaction-supervisor.md`, and the client's `docs/WATCH.md`.

## Deploy

- **Who pushes.** The lead pushes `main` and `frontend` after the reviewer gate and a green test run (owner
  ruling 2026-10-18; `ai_docs/agent-system/repo-agent-rules.md`, "Push approval"). Other seats never push.
- **Frontend.** The dashboard ships from the `frontend` branch: merge `origin/main` into `frontend` and push
  it. The push fires CapRover's GitHub webhook for app `4genthub-frontend`, which builds
  `docker-system/docker/Dockerfile.frontend.production` (named by `captain-definition.frontend`). A build
  takes about 4-11 minutes.
- **A webhook 200 is delivery, not a build.** A trigger can be lost while the webhook still answers 200.
  Prove the deploy by what is served:

  ```bash
  curl -sI https://www.4genthub.com/ | grep -i last-modified      # must move past the push time
  curl -s https://www.4genthub.com | grep -o '<script[^>]*src="/assets/index-[A-Za-z0-9_-]*\.js"'
  python3 scripts/check_served_frontend.py --base-url https://www.4genthub.com --expect-dist agenthub-frontend/build
  ```

  The check refuses (exit 2) when the local build is older than the last frontend commit
  (`CANNOT-MEASURE`) or was built with a different `VITE_*` environment than the deploy image
  (`FOREIGN-ENV`); only an equal environment makes a hash comparison a verdict. When no build follows the
  200, re-trigger from the CapRover app's deployment tab and check again.
- **Which build definition an app reads** (`captain-definition.backend`, `.backend.go`, `.frontend`) is a
  CapRover app setting the repository does not record.
- **Version marker.** Bump `agenthub_go/fastmcp/config/version.go` in the commit set that must be
  confirmable after a deploy; `GET /health` reports it (backend only).
- **CapRover helpers:** `scripts/deployment/caprover-env-setup.sh`, `scripts/deployment/force-caprover-rebuild.sh`.
  Production PostgreSQL is the container `srv-captain--4genthubdb` and needs `DATABASE_SSL_MODE=disable`.

## CI

`.github/workflows/ci.yml` runs on a push to `main` and on pull requests:

| Job | Runs |
|---|---|
| `go` | `scripts/gofmt-check.sh`, `go vet ./...`, `go test ./...` (full history checkout; the repoguards tests read it) |
| `scripts` | `python3 scripts/DOC-CITATIONS.py` and its tests |
| `frontend` | `pnpm install --frozen-lockfile`, `pnpm typecheck`, `pnpm lint`, `pnpm test`, `pnpm build` |

The `go` job has no PostgreSQL service, so the tests gated on `AGENTHUB_TEST_PG_URL` skip in CI; a green
run says nothing about them. Run them locally against `agenthub_go/tools/testpg`.

## Schema changes

The schema is the embedded migration set
(`agenthub_go/fastmcp/task_management/infrastructure/database/migrations/`, rules in its `README.md`).
A boot applies pending steps only with `AUTO_MIGRATE=true`. To change the schema: add the next
`NNNN_slug.sql` step, update the Go table definition it mirrors, and run the schema-upgrade gate
(`ai_docs/verification/schema-upgrade-gate.md`) before it reaches production. Never rename or reorder an
applied step. Back up first: `pg_dump -Fc <db> > backup.dump` (`scripts/backup-production.sh` wraps it).

## Health and metrics

```bash
curl -sS http://localhost:8000/health                                   # liveness + deployed version
curl -sS http://localhost:8000/ws/metrics                               # websocket metrics (Prometheus text)
curl -sS http://localhost:8000/api/v1/performance/metrics/overview      # request performance
```

The server logs to stdout/stderr (the container log in production). The repository defines no
Prometheus, Grafana or Redis; the performance cache is in-process
(`POST /api/v1/performance/metrics/clear-cache` clears it).

## Troubleshooting

| Symptom | Check |
|---|---|
| Server exits at boot on the database | `pg_isready -h $DATABASE_HOST -p $DATABASE_PORT`; on CapRover `DATABASE_SSL_MODE=disable`, on managed Postgres `require` |
| Boot refuses step `0003` (`SQLSTATE P0001`) | the database was built by another creator and lacks the baseline mark; `ai_docs/verification/of4-local-stack.md` section 2a |
| A table is missing | the boot ran without `AUTO_MIGRATE=true`; a normal boot logs the missing tables |
| `401` on `/mcp` or the API | the bearer token is wrong or revoked; for seats, fix `~/.config/4genthub/.env` and run `agenthub_client/scripts/respawn.sh <room>` |
| Every page says "Not authenticated" locally | `ai_docs/verification/of4-local-stack.md` section 3 |
| The dashboard shows an old build | the frontend deploy did not build; see Deploy above |
