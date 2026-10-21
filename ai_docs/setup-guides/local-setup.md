# Local setup

How to run the server, the dashboard and the client on one machine. Each command is the source of truth for
its own output; this page says which to run and which variables they read.

## Prerequisites

| Tool | Version | Used by |
|---|---|---|
| Go | 1.26 (`go.mod`) | `agenthub_go` (server), `agenthub_client` (client) |
| Node.js + pnpm | Node 22, pnpm 10 (as `ci.yml` uses) | `agenthub-frontend` |
| Rust (cargo) | stable | `agenthub_client/rust/agenthub-runtime` (the seat runtime) |
| PostgreSQL | any current release | the server's only database |
| tmux, herdr | - | running and watching a room |

## 1. Server (`agenthub_go`)

```bash
cd agenthub_go
AUTO_MIGRATE=true go run ./cmd/agenthub     # first boot on an empty database: applies the migrations
go run ./cmd/agenthub                       # later boots: no DDL unless AUTO_MIGRATE=true
curl -s http://localhost:8000/health        # reports the running version
```

The schema is the embedded migration set in
`fastmcp/task_management/infrastructure/database/migrations/` (`NNNN_slug.sql`, applied in filename order,
recorded in `applied_migrations`); its `README.md` states the rules. A database built by another creator
needs the baseline mark before `0003` will run (`ai_docs/verification/of4-local-stack.md` shows the step).

Variables the server reads (names only; values live in the environment, never in a tracked file):

| Group | Variables |
|---|---|
| Listen | `FASTMCP_HOST`, `FASTMCP_PORT` (default 8000), `CORS_ORIGINS` |
| Database | `DATABASE_URL`, or `DATABASE_TYPE` + `DATABASE_HOST`, `DATABASE_PORT`, `DATABASE_NAME`, `DATABASE_USER`, `DATABASE_PASSWORD`, `DATABASE_SSL_MODE` (default `prefer`); `AUTO_MIGRATE` |
| Auth | `AUTH_ENABLED` (default `true`), `AUTH_PROVIDER` (default `keycloak`), `MCP_AUTH_MODE` (default `production`), `JWT_SECRET_KEY`, `JWT_ALGORITHM`, `JWT_ISSUER` |
| Keycloak | `KEYCLOAK_URL`, `KEYCLOAK_REALM`, `KEYCLOAK_CLIENT_ID`, `KEYCLOAK_CLIENT_SECRET`, `KEYCLOAK_SERVICE_CLIENT_ID`, `KEYCLOAK_SERVICE_CLIENT_SECRET`, `KEYCLOAK_TOKEN_AUDIENCE`, `KEYCLOAK_VERIFY_TOKEN_AUDIENCE` |
| Supabase | `SUPABASE_ENABLED`, `SUPABASE_URL`, `SUPABASE_ANON_KEY`, `SUPABASE_SERVICE_ROLE_KEY`, `SUPABASE_JWT_SECRET` |
| Task sweeper | `TASK_SWEEP_INTERVAL`, `TASK_ESCALATE_AFTER`, `TASK_BLOCK_AFTER`, `TASK_PRUNE_AFTER` (`ai_docs/development-guides/task-lifecycle-sweeper.md`) |
| Logs | `LOG_LEVEL`, `LOG_FORMAT`, `LOG_DIR` |

To list them from the code: `cd agenthub_go && grep -rhoE 'os\.(Getenv|LookupEnv)\("[A-Z0-9_]+"\)|envOr[A-Za-z]*\("[A-Z0-9_]+"' --include='*.go' --exclude='*_test.go' . | sort -u`.

**Authentication.** Keycloak is the source of truth for users. A browser session signs in through
Keycloak; a machine (the client, a seat, the MCP endpoint) sends `Authorization: Bearer <API token>`. API
tokens are created by a signed-in user through `/api/v2/tokens`. The MCP
endpoint is `<server>/mcp`.

## 2. Dashboard (`agenthub-frontend`)

```bash
cd agenthub-frontend
pnpm install
pnpm start          # vite dev server on http://localhost:3800
pnpm typecheck && pnpm lint && pnpm test && pnpm build    # the checks ci.yml runs
```

## 3. Client (`agenthub_client`, the `4genteam` binary)

```bash
cd agenthub_client && ./scripts/build.sh --no-test    # installs ~/.local/bin/4genteam and agenthub-runtime
4genteam doctor                                       # read-only report of every safeguard
```

The client's configuration is one file, `~/.config/4genthub/.env`: at least `AGENTHUB_URL` (the server) and
`AGENTHUB_TOKEN` (an API token). Every seat gets this file and the `agenthub_http` MCP config when it
starts; a running seat re-reads neither, so after changing it run `agenthub_client/scripts/respawn.sh <room>`.
The `install` skill walks a new machine through this setup.

## 4. Docker instead

`docker-system/docker-menu.sh` starts PostgreSQL, the backend and the frontend in containers and has
log, shell and clean-up entries. Production does not use it: see `ai_docs/operations/operations-guide.md`.
