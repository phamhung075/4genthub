# agenthub_go Production Readiness Report

Author: dev-owner@4genthub-go (sections 1, 2, 3, 4, 6); dev-check@4genthub-go (sections 5, 7, 8, review, final verdict).
Production was touched read-only only (owner: schema metadata; dev-check: container/nginx/catalog reads, see section 5). No deploy, no push, no secrets printed.

## Verdict (dev-owner proposal): NO-GO

`agenthub_go` cannot replace the production Python backend at https://www.4genthub.com in its current state.
The domain, application and repository layers are ported and pass tests. The composition root (`httpapp`) exposes only part of the surface, the MCP endpoint returns empty results for every tool call, and no Go deployment artefact exists.

## Blockers

| ID | Severity | Finding | Evidence |
|----|----------|---------|----------|
| B1 | Critical | MCP `tools/call` returns `{}` for every tool. `json.Marshal` is applied to `*entities.OrderedMap`, which has no `MarshalJSON`. The Python-faithful serializers are `value_objects.PyJSONDumps` / `PyJSONDumpsCompact`. | `fastmcp/server/httpapp/mcp_routes.go` (`dispatchMCPTool`, `tools/call` handler, `resJSON, _ := json.Marshal(res)`). Local e2e probe against :18002. |
| B2 | Critical | 60 of 103 probed Python HTTP routes are not served. WebSockets `/ws/realtime` and `/ws/connector` are missing. The logic exists in `fastmcp/server/routes/*.go` but `httpapp.Handler()` mounts only `/health`, project, branch, task, subtask, session-stream, mcp, auth and supabase. The frontend uses contexts, tokens, agents, connections and `/ws/realtime` (grep of `agenthub-frontend/src`). | Python route list (107 routes) vs. probe of the local Go server. |
| B3 | High | CORS middleware is defined (`fastmcp/server/http_server.go`) but never applied. `OPTIONS` returns 405 and no `Access-Control-*` headers are sent, so the browser frontend cannot call the API cross-origin. | Local probe. |
| B4 | Critical | The MCP wiring is not the real one. `tools/list` returns hand-written stub schemas and the name `manage_unified_context` (not the Python registry). `ToolWithSchema` is not used. `resources/list` and `prompts/list` are absent. `protocolVersion` is 2024-11-05. `initialize` and `tools/list` succeed without auth with `AUTH_ENABLED=true`. `GET /mcp` returns a JSON status object, not an SSE stream. The project, branch, agent and context facade factories are nil in `httpapp/app.go:45`, and the `NewDDDCompliantMCPTools` error is discarded. | `httpapp/app.go`, `httpapp/mcp_routes.go`; `interface/testdata/tools_golden.json` shows what `ToolDefinitions()` should publish. |
| B5 | Resolved (build unproven) | **CORRECTED 2026-10-09 — both halves were false at HEAD:** a Go Dockerfile **exists**, `docker-system/docker/Dockerfile.backend.go`, and `captain-definition.backend` points at it (`"dockerfilePath": "./docker-system/docker/Dockerfile.backend.go"`), not at `docker-system/docker/Dockerfile.backend.production` — which `c90ca799` deleted, and which built the Python app. What stays unproven is the image build itself: Docker is not usable from this host, so no build was executed here. | See section 6. |
| B6 | High | Startup DDL against production. `CreateTables` (create_all with checkfirst plus `EnsureAIColumnsExist`) would create `agent_sessions`, `agent_session_events` and `email_tokens` in the production database on first boot. Eight production tables are unknown to the Go models: `agent_import_history`, `agent_templates`, `applied_migrations`, `token_transactions`, `user_agent_configurations_md`, `user_agent_instances`, `user_api_tokens`, `user_sessions`. | Production schema metadata vs. Go schema (scratch `schema_dump.json`, `prod_schema.json`). |

> **Status update (docs rewrite against HEAD `c4ff8d42`; see `ai_docs/api-integration/surface-inventory.md` §2, §3, §5.4).** The specific B4 and B6 statements above are superseded and must not be read as the current surface:
> - **B4:** `App.MCPToolsList` (`mcp_routes.go:275`) builds `tools/list` from `DDDCompliantMCPTools.ToolDefinitions()`'s six tools plus **four** appended schemas (`manage_seat`, `call_seat`, `submit_feedback`, `manage_connection`) — **ten** published tools, not stub schemas and not `manage_unified_context`. The golden registry test passes. `GET /mcp` is `mcpSSEHandler` (an SSE stream), and `initialize`/`tools/list` require a bearer when `AUTH_ENABLED=true`. **CORRECTED 2026-10-09 (writer): this bullet read `getMCPToolsList` with THREE appended schemas and nine published tools — a name that resolves nowhere in `agenthub_go` (the alias was deleted, recorded in `CHANGELOG/`) and a count the surface superseded when `submit_feedback` landed. The ten names were re-measured at HEAD with the five registry tests passing; nothing else in this report was touched.**
> - **B6:** `models_prod.go` now declares six `ProductionTables` (`agent_import_history`, `applied_migrations`, `token_transactions`, `user_agent_configurations_md`, `user_api_tokens`, `user_sessions`), still deliberately not appended to `database.Tables`. `agent_templates` and `user_agent_instances` were dropped and are no longer part of the schema at all.
> - The `call_agent` MCP tool was retired together with `agenthub_main/agent-library`; later lists in this report that include it among `tools/call` targets are historical. `call_agent` survives only as a field of `manage_agent`.
> - **AND THE VERDICT ABOVE IS A DATED VERDICT, NOT A CURRENT ONE.** B1, B2 and B3 were each fixed in the WP series recorded at the foot of this file: MCP results serialize through `PyJSONDumps`, 98 of 98 probed production operations are served, and CORS is applied with a passing preflight. So "MCP `tools/call` returns `{}` for every tool", "60 of 103 probed routes are not served" and "no Go deployment artefact exists" describe **the state this report opened with**, and the re-review verdicts below are the later ones for those items.

## 1. Surface parity

- HTTP: see B2, B3. Served routes (project, branch, task, subtask CRUD) worked end to end against a production-like schema.
- MCP: see B1, B4. The facade layer works when called directly (unit tests); the transport layer does not expose it.
- Auth: HS256 test bearer tokens work locally. Keycloak RS256/JWKS is not verified.
- SSE for `/mcp`: not implemented (B4). Production `/mcp` returns 406 without the SSE Accept header, so clients must be served streamable-HTTP/SSE (no custom nginx `/mcp` block is rendered in production; see section 5).
- WebSocket: not implemented (B2).
- Health: `/health` is minimal. Python returns a richer payload (`mcp_entry_point.py`).
- Open parity questions: `GET /api/v2/tasks/stats/summary` returns 500 locally; `PUT /api/v2/tasks/{id}` requires `task_id` in the body. Python behaviour for both was not compared.

## 2. Quality gate

- `go build ./...` green; `go vet ./...` green.
- `go test -race -count=1 ./...`: 124 packages ok, 0 failing, 41 packages without tests, including `httpapp` and `cmd/agenthub`. These are exactly the packages that carry B1 to B4, so a green gate says nothing about them.
- 5 files fail `gofmt` (server team's files).
- `main.go` sets no server timeouts and has no signal handling or graceful shutdown.
- Untracked clutter in the tree (`agenthub_go/.gocache`, `.gomodcache`, `scratch/`, root `.gocache/`, `AGENTS.md`, `testground/`) must not enter a build context.

## 3. Schema vs production Postgres (postgres:14.5, db `postgresdb`)

- Production was built from `init_schema_postgresql.sql` (jsonb columns, `uuid_generate_v4()` defaults, `progress_state` varchar). Go DDL uses json and an enum for some columns.
- CRUD flows (project, branch, task, subtask) passed on a local database reconstructed to match the production schema (`prod_like.sql`).
- Risks: B6; column-type differences on existing tables (json vs jsonb, enum vs varchar) are harmless for the tested flows but untested for others.
- Recommendation: the Go server should not run `CreateTables`/`EnsureAIColumnsExist` against production. Production DDL should come from the existing SQL file. Add the eight missing models or confirm they are unused.

## 4. Local e2e

- Run against a local embedded PG 16 and local Go servers only. Probes used a locally minted HS256 token.
- The e2e account was not used: login goes through Keycloak (RS256), which cannot run locally here. Not verified.
- Python-vs-Go differential for the new flows was not done: the Python entry point loads `.env.dev` with override and cannot be pointed at the test DB.

## 6. Dockerfile / deployment

- `cmd/agenthub` builds statically: `CGO_ENABLED=0 go build -trimpath -ldflags="-s -w" ./cmd/agenthub` — **RE-MEASURED 2026-10-09: 23,167,138 bytes (23.2 MB), statically linked**, so the earlier 19.2 MB reading is superseded. "Not a dynamic executable" still holds.
- Dependencies (pgx/v5, x/crypto, x/text, regexp2, yaml.v3) are pure Go, so a `scratch`/distroless runtime image is possible.
- The Python entrypoint validates env, runs `pg_isready`, optionally migrates (`AUTO_MIGRATE`), then starts the server, and the image has `HEALTHCHECK curl /health`, user `appuser`, `EXPOSE 8000`. A Go image needs equivalents: env validation (Go reads `DEFAULT_USER_ID`, `DATABASE_*`, `AUTH_ENABLED`, `JWT_SECRET_KEY`, `FASTMCP_PORT`, `CORS_ORIGINS`), a health check without curl (the binary needs a `-healthcheck` mode, or use busybox/wget), non-root user, port 8000.
- **CORRECTED 2026-10-09:** `captain-definition.backend` **is already switched** to the Go Dockerfile — it carries `"dockerfilePath": "./docker-system/docker/Dockerfile.backend.go"`, the form CapRover documents for a repository-owned Dockerfile, and the build context is the project root, which is exactly what that Dockerfile's `COPY agenthub_go/…` needs. What is outstanding is the **build**, not the switch. The `/mcp` must be served with SSE (B4); no custom nginx `/mcp` block is rendered in production.
- **OPEN QUESTION, and it decides whether the workflow's retirement leaves a working route:** the repository root carries `captain-definition.backend`, `captain-definition.backend.go` and `captain-definition.frontend` and **no file named exactly `captain-definition`**. CapRover reads the *Captain Definition Path* configured in the app's Deployment tab, which defaults to `./captain-definition` at the project root ([CapRover docs](https://caprover.com/docs/captain-definition-file)), and `scripts/backup-production.sh:79` only copies a root `captain-definition` if one exists. **Which of the three suffixed files this app is pointed at is not recorded in the repository**, so it cannot be answered from the tree.
- **Mechanism or a file that looks right?** `dockerfilePath` is the documented form and the build context is the project root, so every static premise holds: `Dockerfile.backend.go` exists, its `FROM golang:1.26.8` equals the module's `toolchain go1.26.8`, and each path it copies is present at HEAD. **Its build stage was RUN here, 2026-10-09:** the Dockerfile's own command `CGO_ENABLED=0 go build -trimpath -ldflags='-s -w' -o <tmp> ./cmd/agenthub` produced a 23.2 MB statically linked ELF, and the binary's `-healthcheck` flag — the one the image's `HEALTHCHECK` calls — exits **1** when the server is unreachable. What was NOT run is the **image build and the container start** (Docker is not usable from this seat), so this is a mechanism by documentation, by static premise and by its build stage — **not** a build proven end to end. One command at the repository root closes it: `docker build -f docker-system/docker/Dockerfile.backend.go .` — or a real CapRover deploy of whichever definition the app is pointed at.
- `docker-system/docker/captain-definition` **CORRECTED 2026-10-09:** it used `dockerfileLines` whose last line was `"FROM ../docker-system/docker/Dockerfile.backend.go"`. `dockerfileLines` are the literal contents of a Dockerfile, so that `FROM` named a relative *path* where a Docker image reference belongs and could never include another Dockerfile. It now carries the same `dockerfilePath` form as its root siblings. It is not the file CapRover reads unless it is copied to the app root — no script in the tree does that.
- Proposed Dockerfile (not written to the repo; not built, since Docker is unavailable here):

```dockerfile
FROM golang:1.23.5 AS build
WORKDIR /src
COPY agenthub_go/go.mod agenthub_go/go.sum ./
RUN go mod download
COPY agenthub_go/ .
RUN CGO_ENABLED=0 go build -trimpath -ldflags="-s -w" -o /out/agenthub ./cmd/agenthub

FROM gcr.io/distroless/static-debian12:nonroot
COPY --from=build /out/agenthub /agenthub
EXPOSE 8000
ENTRYPOINT ["/agenthub"]
```

  It also needs a `.dockerignore` excluding `.gocache`, `.gomodcache`, `scratch`, and a health check strategy.

## 5. Production facts (dev-check, read-only)

Method: `ssh 4genthub` with `docker ps/inspect/logs --tail`, `docker exec` nginx `sed -n` of the generated conf, `psql` SELECT-only catalog/statistics queries, and `curl` of public endpoints. Env values were never retrieved (names extracted remotely with `cut -d= -f1`; the one value read was the git commit SHA variable). No write, restart, build or DDL was run. One SSH call was refused once (connection refused) and succeeded on retry.

| Fact | Value |
|---|---|
| Backend service | `srv-captain--4genthub-backend`, 1 replica, up 3 weeks, healthy, 0 restarts |
| Image | `img-captain-api:249`, id `sha256:e0298c88bc40...`, built from commit `35207b5f85e3126a917f684394f4072c3b30ea0d` (CAPROVER_GIT_COMMIT_SHA) |
| Runtime | user `appuser`, workdir `/app`, entrypoint `/app/docker-entrypoint.sh`, exposes 8000, no volumes mounted, no memory/CPU limits |
| Healthcheck | `curl -f http://localhost:${FASTMCP_PORT:-8000}/health`, interval 30s, timeout 5s, start period 40s, 3 retries |
| Public domain | `api.4genthub.com` -> `srv-captain--4genthub-backend:8000` (nginx generated conf: plain `proxy_pass`, `Upgrade` headers, `client_max_body_size 500m`). `www.4genthub.com` -> frontend container `:3800` |
| Custom nginx for /mcp | None found in the generated nginx conf for `api.4genthub.com`. The owner's statement in section 1 that production has a `customNginxConfig` with SSE settings for `/mcp` is not supported by what is deployed (CapRover's own `config-captain.json` was not readable by the ssh user, so a UI-level customNginxConfig that is not rendered could not be excluded; nothing is rendered) |
| Python /mcp | `GET /mcp` without SSE Accept returns 406 JSON (streamable-HTTP transport). Go returns a JSON status object |
| Public API surface | `GET /openapi.json`: 79 paths, 100 operations. `/docs` is public |
| CORS | Preflight from `https://www.4genthub.com` returns 200 with `access-control-allow-origin`, `-credentials: true`, `-methods`, `max-age 600`. Go sends none (B3) |
| Health payload | `{"status","timestamp","server","version":"0.0.6","auth_enabled","connections{...}","status_broadcasting{...}"}`. Go returns `{"status":"healthy"}` only |
| Database | `srv-captain--4genthubdb`, PostgreSQL 14.5 (aarch64), db `postgresdb`, 20 MB, 4 sessions, extensions `plpgsql`, `uuid-ossp`, enum type `progressstate` (used by no column) |
| Error rate | `docker logs --tail 200`: 200 lines, 0 ERROR, 0 WARNING, 0 tracebacks, 0 4xx/5xx; only `GET /health` x5 visible. Traffic is very low |
| Env var NAMES | 90 names, among them `AUTH_ENABLED AUTH_PROVIDER AUTO_MIGRATE CORS_ORIGINS CORS_ALLOW_CREDENTIALS DATABASE_{HOST,PORT,NAME,USER,PASSWORD,TYPE,SSL_MODE,POOL_*,...} FASTMCP_{HOST,PORT,TRANSPORT} JWT_SECRET_KEY KEYCLOAK_{URL,REALM,CLIENT_ID,CLIENT_SECRET} TOOL_* FEATURE_* ALLOWED_HOSTS FORWARDED_ALLOW_IPS SECURE_PROXY_SSL_HEADER USE_X_FORWARDED_*` |

Row counts (pg_stat_user_tables `n_live_tup`, estimates): tasks 299, task_contexts 299, subtasks 158, task_assignees 338, task_labels 302, task_dependencies 64, labels 161, projects 32, project_contexts 40, project_git_branchs 146, branch_contexts 128, global_contexts 8, api_tokens 31, agents 3, missed_notifications 1473, user_agent_instances 58, agent_templates 32; 0 rows in users, templates, context_delegations, context_inheritance_cache, applied_migrations, agent_import_history, token_transactions, user_agent_configurations_md, user_api_tokens, user_sessions, user_token_balances. `agent_sessions`, `agent_session_events`, `email_tokens` do not exist (B6 confirmed: Go would create them on first boot).

Env comparison (names Go reads vs production):
- Provided and read by Go: `AUTH_ENABLED`, `AUTH_PROVIDER`, `CORS_ORIGINS`, `DATABASE_TYPE`, `DATABASE_HOST/PORT/NAME/USER/PASSWORD`, `JWT_SECRET_KEY`, `KEYCLOAK_URL/REALM/CLIENT_ID/CLIENT_SECRET`, `FASTMCP_HOST/PORT`, `CONTAINER_ENV`; `TOOL_*` and `FEATURE_*` are also read (`tool_config.go`, `feature_flag_service.go`).
- Read by Go, absent in production: `DEFAULT_USER_ID` (only used when `AUTH_ENABLED` is not true; production has it true, so not a blocker), `SYSTEM_USER_ID` (Python-side usage must be checked; Go falls back when empty), `JWT_ISSUER`, `LOG_*`, `REDIS_URL`, `SUPABASE_*`, `KEYCLOAK_SERVICE_CLIENT_SECRET`, `KEYCLOAK_ADMIN_PASSWORD`. Not verified which of these a production feature needs; no blocker is claimed from names alone.
- Provided by production, ignored by Go: pool/keepalive/timeout settings (`DATABASE_POOL_*`, `DATABASE_STATEMENT_TIMEOUT`, `DATABASE_CONNECT_TIMEOUT`, `DATABASE_SSL_MODE` is read by the scratch harness only), `ALLOWED_HOSTS`, `FORWARDED_ALLOW_IPS`, `SECURE_PROXY_SSL_HEADER`, `USE_X_FORWARDED_*`. Behavioural effect untested.

## 7. Rollback plan

Recommended: do not replace the Python service in place. Deploy Go as a second CapRover app (for example `4genthub-backend-go`) on its own domain, and switch only after verification.
1. Cutover change = point the frontend/proxy upstream (or the `api.4genthub.com` domain) at the Go app. Rollback = point it back at `srv-captain--4genthub-backend` (still running, untouched): seconds, no build.
2. If the Python service is ever replaced in place: the only image on the host is `img-captain-api:249` (id `e0298c88bc40`, commit `35207b5f85e3126a917f684394f4072c3b30ea0d`). Restoring means a CapRover redeploy of that commit (a build, likely more than 5 minutes) or re-selecting the retained version in CapRover's Deployment tab if it is still listed (not verified, `config-captain.json` unreadable). Therefore an in-place swap does NOT meet the 5-minute target.
3. Database: the Go server runs `CreateTables`/`EnsureAIColumnsExist` on boot and would add 3 tables (B6). Rollback of that is a manual DROP of those tables. Before any Go start against production take a `pg_dump` of `postgresdb` (20 MB) on the db container and keep it off-host. This was NOT run here (it needs your confirmation); only counts were read.
4. The Go server must start against a restored COPY first, never against the live database.

## 8. Risks the ledger cannot show

- The ledger says 100% `done`, but `httpapp` (the composition root) and `cmd/agenthub` have no tests; the verified blockers B1 to B4 live exactly there. A per-file `done` does not imply a working server.
- Differential checks I ran earlier found residual divergences in rows marked `done` (for example `response_optimizer`, fixed and re-verified today), so other `done` rows that I did not diff are not proven equal to Python.
- SUPERSEDED 2026-10-05 (both tables were dropped, owner-run; the row counts and export size below are OWNER-REPORTED via the lead and were not independently verified by a seat): `user_agent_instances` was already at 0 rows and `agent_templates` held 32 rows for which a 397 KB export was taken first as the recoverable before-state, so neither table exists now. Nothing "holds live data" on the Go server, and no agent-management feature can break or lose data from them.
- JSON number/null handling, timezones (naive vs aware isoformat), set ordering and error message formats were differential-tested only for the packages listed in earlier handoffs, not for the HTTP layer.
- Python-only dependencies named in the brief (redis, pybars, supabase) were not re-audited here.
- Concurrency: a data race class (unsynchronised maps in singleton services) was found and fixed in two services; no systematic race run under HTTP load exists. `go test -race` passes but does not cover `httpapp`.
- No server timeouts and no graceful shutdown in `main.go` (owner finding, not re-checked).

## Review of the owner's sections (dev-check)

- Re-ran `go build ./...` (green), `go vet ./...` (clean), `gofmt -l` (5 files: `httpapp/http.go`, `httpapp/mcp_routes.go`, `server/mcp_entry_point.go`, `server/mcp_status_tool.go`, `server/routes/session_stream_routes.go`), `go test -race -count=1 ./...` (no failing package, 41 packages without tests). Matches section 2.
- B1 independently confirmed: `json.Marshal` of an `*OrderedMap` prints `{}` (checked with a 5-line program) and `mcp_routes.go:156` marshals the tool result that way.
- B2: my static check (route literals in mounted code vs production `openapi.json`) also shows most of `agent-management`, `tokens`, `contexts`, `agents`, `connections` and several `branches`/`tasks` routes missing. The heuristic is coarse (it over-counts routes registered with prefix variables); the owner's live probe (60 of 103) is the better number. I did not run a live probe because my scratch Postgres was down.
- B3 and B6 are consistent with the production facts above. B6 is understated: two of the unmodelled tables are populated.
- Correction to section 1: the claim that production nginx has a `/mcp` SSE `customNginxConfig` is not supported (see section 5). The conclusion that `/mcp` must be streamable-HTTP/SSE compatible still stands, because production `/mcp` returns 406 without the SSE Accept header.
- Section 4: no Keycloak login and no e2e-account run, so authentication, the most security-sensitive path, is unverified.

## FINAL VERDICT (dev-check): NO-GO

I agree with the owner's proposal and no part of it is overruled. `agenthub_go` cannot replace the production backend today:
1. `/mcp` returns empty results and publishes a stub tool registry (B1, B4).
2. Most production HTTP routes and both WebSockets are not served; CORS is missing, so the browser frontend cannot work (B2, B3).
3. No Go image or deployment definition exists (B5).
4. A first boot would alter the production schema and ignores two populated tables (B6).
5. Keycloak authentication was never exercised end to end.

Production itself is healthy and quiet (0 errors in the last 200 log lines, 20 MB database), so there is no pressure to cut over: keep Python in service while the minimum work list above is done. Re-run this review (including a live route probe, a Keycloak login with the e2e account against a local Go server, and the `pg_dump` rehearsal) before reconsidering GO WITH CONDITIONS.

## Not verified

- Keycloak login and RS256/JWKS validation; the e2e account.
- WebSocket behaviour (endpoint missing).
- Python-vs-Go differential for new flows.
- Docker image build and container start.
- Live HTTP route probe by dev-check, `pg_dump`, CapRover UI-level settings (`config-captain.json` unreadable), exact row counts (estimates used), Keycloak and e2e login.
- Behaviour under production load, timeouts, graceful shutdown.

## Minimum work to reach GO WITH CONDITIONS

1. Mount all routes from `fastmcp/server/routes/*.go` in `httpapp.Handler()`, add `/ws/realtime` and `/ws/connector`, apply CORS.
2. Rebuild `/mcp` on top of `ToolDefinitions()`/`SchemaMCPServer`: serialize with `PyJSONDumps`, add auth on `initialize`/`tools/list`, resources/prompts, SSE, and wire every facade factory (return the constructor error).
3. Stop `CreateTables` from touching production; reconcile the eight unknown tables.
4. Build the Go Dockerfile and health check that now exist (`docker-system/docker/Dockerfile.backend.go`; `captain-definition.backend` already points at it) and start the container. **CORRECTED 2026-10-09:** the file to add and the definition to update are not outstanding work — the build and the container start are.
5. Add tests for `httpapp` and `cmd/agenthub`; add server timeouts and graceful shutdown.
6. Verify Keycloak login with the e2e account against a local Go server, and run a Python-vs-Go differential.

## Re-review after fixes (dev-owner: WP1, WP2, WP3, WP5; dev-check adds WP4, WP6 and the final verdict)

Gate: `gofmt -l` empty; `go build ./... && go vet ./... && go test -race -count=1 ./...` green; `httpapp` now has tests.

| Blocker | Status | Evidence | Still NOT verified |
|---|---|---|---|
| B1 MCP results serialize to `{}` | FIXED locally (dev-check); Keycloak-token path NOT verified | `mcp_routes.go` serializes through `PyJSONDumps`; `mcp_routes_test.go` runs `tools/call` for 3 tools (non-empty JSON in `content[0].text`) | Same-input comparison with the live Python server for 5 tools (needs a Python server and auth) |
| B2 unserved routes and WebSockets | FIXED (route level) | Local probe against prod `openapi.json`: 98 operations, 0 unserved (was 60 missing), no 5xx on empty-body probes. `/ws/realtime` and `/ws/connector` handshake tests pass; unauthenticated upgrade returns 403 | Payload parity of the newly mounted routes against Python; `/ws/*` registry is not shared with `routes.BroadcastDataChange`, so server-side fan-out to sockets is not wired; analytics handlers are not ported; alert/performance routes are mounted although Python never mounts them |
| B3 CORS | FIXED | Preflight from `https://www.4genthub.com` returns 200, `Access-Control-Allow-Origin` echo, credentials true, max-age 600 (`cors_test.go` and curl) | Browser test against the real frontend |
| B4 MCP surface | PARTIAL | `tools/list` equals `tools_golden.json`; `resources/list`, `prompts/list` return empty lists; bearer required on `initialize` and `tools/list` when `AUTH_ENABLED=true`; `GET /mcp` without SSE Accept returns 406; `NewApp` returns the constructor error; all four facade factories wired | A long-lived SSE session with a real MCP client; the 406 body is `{"error": ...}` as in the Python middleware |
| B5 Dockerfile | PARTIAL (dev-check, WP4) | Dockerfile.backend.go, captain-definition.backend.go, healthcheck flag, timeouts, graceful shutdown | Image build (no Docker) |
| B6 schema safety | FIXED | `AUTO_MIGRATE` gate; on the prod-like local DB with it unset the table count is 28 before and after start; models for the 8 tables with fake-driver CRUD tests | CRUD on real Postgres (`TEST_DATABASE_URL` test skipped; `prod_like` has no rows in `agent_templates` or `user_agent_instances`); a copy of production data was not tested |

Open parity questions resolved: `GET /api/v2/tasks/stats/summary` returns 500 `{"detail":"Failed to get task statistics"}` in Python too, and `PUT /api/v2/tasks/{id}` requires `task_id` in the body in Python too (the URL value then overrides it). Go matches both; these were not bugs (the `500` half is at `MIGRATION.md:951`; the `PUT {id}` requires-`task_id` half has NO line in MIGRATION.md — verified 2026-10-08, when the file was 972 lines and the previous citation pointed past its end). **CORRECTED 2026-10-10:** the stats half of this paragraph — and the `Open parity questions` bullet in section 1 that this line resolves — is moot: `e6829b32` ("refactor(tasks): remove the two task routes that could only answer 500") removed `GET /api/v2/tasks/stats/summary` and `GET /api/tasks/{task_id}`, so no Go route is left whose behaviour could match Python's 500. **Go matches both** held while both routes were mounted; it now covers the `PUT {id}` requires-`task_id` half alone. The `500` behaviour above was measured before the removal.

Remaining gaps: `/health` shows `connections` and `status_broadcasting` as unavailable until `SetHealthStatusProvider` is wired; Keycloak RS256 login with the e2e account is not verified (see WP6).

### dev-check re-review (local server, own probe)

Method: I built `cmd/agenthub` from the tree (`/tmp/ah2`), started it on 127.0.0.1:18020 against the local scratch PG (`AUTH_ENABLED=false`, `DEFAULT_USER_ID` set), and probed with curl; the route probe replayed all 98 operations of prod `openapi.json` against the owner's server on :18010. No production access, no e2e account.

Gates (mine): `gofmt -l` empty, `go build ./...`, `go vet ./...`, `go test -race -count=1 ./...` no failing package.

| Check | Result |
|---|---|
| Route probe, 98 prod operations | 98 served, 0 absent (agrees with owner) |
| CORS preflight from https://www.4genthub.com | 200, ACAO echo, credentials true, max-age 600 |
| `GET /mcp` without SSE Accept | 406 |
| `initialize` | capabilities for tools/resources/prompts; `resources/list` and `prompts/list` return `[]` |
| `tools/list` | 7 tools, equal to `tools_golden.json` names |
| `tools/call manage_git_branch` | JSON content returned (B1 shape fixed) |
| `tools/call manage_task action=list` | FAILS: `task facade has unexpected type httpapp.handlerTaskFacade` (OPERATION_FAILED) |
| `tools/call manage_context get`, `manage_project list` | FAIL: `Authentication context not available for permission check` (AUTHENTICATION_ERROR) |
| `tools/call manage_connection` | `Unknown tool` (not in the 7-tool golden list; confirm Python really omits it) |
| `agenthub -healthcheck` | rc 0 against the running server, rc 1 when nothing listens |

Findings that keep B1/B4 from FIXED:
- F1 (High): `dispatchMCPTool` (`httpapp/mcp_routes.go:~295`) resolves a user id but never attaches the request auth context; `projectctl`/context controllers read it through `middleware.GetCurrentAuthInfo`. Reuse `withAuthContext` from `branch_routes.go:24`. Result today: manage_project and manage_context cannot succeed even for an authenticated user.
- F2 (High): `manage_task` fails in the MCP path because the task facade wired for `/mcp` is the HTTP-handler type (`handlerTaskFacade`), not the type the MCP controller asserts. The B1 acceptance ("5 tools return the same JSON as Python") is therefore NOT met.
- The existing tests pass because they only list tools or call tools that do not need the facade; add a `tools/call` test per tool with a real DB.

WP4 (B5), dev-check: `Dockerfile.backend.go` (multi-stage, distroless nonroot, EXPOSE 8000, `HEALTHCHECK` via `/agenthub -healthcheck`), `captain-definition.backend.go` (new; the production definition is untouched), `docker-system/docker/Dockerfile.backend.go.dockerignore` (the repo-root build context makes an `agenthub_go/.dockerignore` inert), `-healthcheck` flag, server timeouts (`WriteTimeout` 0 for SSE), SIGTERM/SIGINT graceful shutdown. `CGO_ENABLED=0 go build ./cmd/agenthub` OK. NOT verified: image build (no Docker), CapRover honouring the per-Dockerfile ignore, graceful shutdown under load, a long SSE stream surviving the 30 s shutdown window.

WP6 (auth), dev-check: `fastmcp/auth/mcp_keycloak_jwks_test.go` runs RS256/JWKS validation against a local fake JWKS (valid, expired, wrong issuer, wrong audience, other key with same kid, unknown kid, tampered payload; all pass with -race). NOT verified: real Keycloak login with the e2e account (needs staging); the HTTP bearer path in `httpapp/http.go` was not exercised by that test.

### FINAL VERDICT after fixes (dev-check): NO-GO, much closer

FIXED: B2 (routes, 98/98), B3 (CORS), B6 (AUTO_MIGRATE gate, models). PARTIAL: B1/B4 (shape fixed, F1/F2 break real tool calls), B5 (files exist, image unbuilt). Replacing production is also not authorized without the user. Next: fix F1 and F2, add per-tool `tools/call` tests against a DB, build the image where Docker exists, verify Keycloak on staging, then re-run the 5-tool differential against Python.

### dev-check re-review 2 (owner fixes F1, F2, G1)

Gates (mine): gofmt, `go build ./...`, `go vet ./...`, `go test -race -count=1 ./...`: no failing package. Live: own server on 127.0.0.1:18022, `AUTH_ENABLED=true`, a throwaway HS256 token I minted locally (roles/scopes claims), scratch PG, no production, no e2e account.

| Check | Result |
|---|---|
| `tools/list` without token, AUTH_ENABLED=true | 403 |
| `manage_project create` and `list` | success (F1 fixed: auth context reaches the controller). With a token lacking scopes: `PERMISSION_DENIED requires projects:create`, so the permission layer is really exercised |
| `manage_task list` | success (F2/G1 fixed) |
| `manage_context get` (unknown id) | `Context not found` (correct negative) |
| `manage_agent list` | success |
| `call_agent coding-agent` | FAILS: `CallAgentController not initialized` (F3, new) |
| `manage_project list` payload | `data.projects` is a JSON object, while Python's handler expects a list (`result["data"]["projects"]` used with `len(...)` in `crud_handler.py:111`) (F4, suspected: not yet diffed against a Python run) |

- F3 (High): `call_agent` is the first action every agent session performs (CLAUDE.md "clock in") and `deps.CallAgent` is never set in the `httpapp` composition root; `dispatchMCPTool` returns the error (`mcp_routes.go:419`).
- F4 (Medium, needs a differential): list shape of `manage_project list`.
- `manage_connection` is registered by Python in `connection_management/interface/controllers/connection_mcp_controller.py` and is absent from `tools_golden.json` (7 tools) and from Go; production `tools/list` was not readable without a token, so whether the live registry has 8+ tools is NOT verified. Go has no connection_management port, so this tool is missing.
- Owner's remark confirmed as a pattern: several rows marked done had nil-default hooks (G1). `GetUnifiedContextFacade` is still unassigned.

Status update: B1 PARTIAL (F3, F4, manage_connection), B4 PARTIAL. Verdict unchanged: NO-GO until `call_agent` works and the tool list is compared with a real Python `tools/list`.

### dev-check re-review 3 (owner fixes F3, F4, manage_connection)

Gates (mine): gofmt, build, vet, `go test -race -count=1 ./...`: no failing package. Live on my own local server (127.0.0.1:18023/18024, scratch PG, throwaway local HS256 token).

| Check | Result |
|---|---|
| `tools/list` (AUTH_ENABLED=false) | 8 tools: the 7 golden plus `manage_connection` |
| `manage_connection` | success, status healthy, server_name and auth block present |
| `call_agent nonexistent-agent` | `Agent not found: nonexistent-agent` (controller now wired; F3 fixed; success path not re-run by me, the owner ran it with a template row) |
| `manage_project list`, `manage_task list` | success |
| F4 | Accepted as not a bug: the Python ResponseOptimizer flattens single-item lists, and I differentially verified the optimizer earlier (0 real diffs over 6000 cases). Not diffed end to end on `manage_project list` |
| `GetUnifiedContextFacade` left nil | Owner's reasoning (Python `resolve_context(include_inherited=...)` raises, so Python always takes the except path) accepted; I did not re-derive it |

New observation F5 (Medium, unverified): with `AUTH_ENABLED=true` and `AUTH_PROVIDER=supabase` but no Supabase configuration, `initialize` and `tools/list` return 401 `Authentication failed` for a valid locally signed token, while `tools/call` accepts the same token. The two paths use different validators (`currentUser`/provider-specific vs `ValidateTokenUniversal`). Production uses `AUTH_PROVIDER` (value not read) with Keycloak, which cannot be tested here, so whether a real Keycloak token passes the `tools/list` gate is NOT verified. Needs staging.

### FINAL VERDICT (dev-check), after re-review 3: NO-GO for replacing production now; GO WITH CONDITIONS is reachable

Fixed and verified locally: B2 (98/98 routes), B3 (CORS), B6 (AUTO_MIGRATE gate, models), B1/B4 (tools/list, tools/call for project/task/context/agent/call_agent/connection, auth context, 406 on GET /mcp), B5 files and healthcheck.
Conditions still open before any cutover: (1) a staging run with real Keycloak tokens covering `initialize`, `tools/list`, `tools/call` (F5) and the e2e login; (2) a Docker image build and CapRover deploy as a second app (no Docker here); (3) per-tool `tools/call` tests against a real database and a differential of at least 5 tools against a running Python server; (4) `/ws/*` registry wired to `BroadcastDataChange`, analytics routes, `/health` connections block; (5) a `pg_dump` and rollback rehearsal, which need your confirmation. Replacing production is not authorized without you.

### dev-check re-review 4 (owner fix F5)

Gates (mine): gofmt, build, vet, `go test -race -count=1 ./...`: no failing package. Live (own server, 127.0.0.1:18025, `AUTH_ENABLED=true`, `AUTH_PROVIDER=supabase`, local HS256 tokens): `initialize` and `tools/list` with a valid token 200; expired token 401 `Invalid authentication credentials`; no token 403 `Not authenticated`. F5 FIXED: the gate now uses `ValidateTokenUniversal`, like `tools/call`.
Still NOT verified: Keycloak RS256 tokens end to end (only the fake-JWKS unit tests, WP6), the e2e login, and the other open conditions listed under "FINAL VERDICT (dev-check), after re-review 3". Final verdict unchanged: NO-GO for replacing production now; GO WITH CONDITIONS once those conditions are met.
