# Fix plan: close every blocker in PROD_READINESS_REPORT.md

Input: agenthub_go/PROD_READINESS_REPORT.md (verdict NO-GO, blockers B1-B6 plus the "Minimum work"
list). Goal: reach GO WITH CONDITIONS. Same hard limits as PROD_READINESS_BRIEF.md: production is
read-only (and you do not need it for this task), no deploy, no `git push`, no commit unless the
user asks, no secrets printed, e2e account only against a LOCAL Go server. Work inside agenthub_go/
(and new deploy files listed in WP4). Do not delete or modify Python sources.

## Team structure (mandatory): dev-owner LEADS DeepSeek workers, dev-check reviews
dev-owner is the leader and the DeepSeek jobs are the workers. For EVERY work package: split it
into self-contained jobs (one per file or small group), start them ALL first, detached:
  cd /home/daihu/__projects__/4genthub && node .agents/skills/deepseek-offload/scripts/dsh-offload.mjs start --detach --label <wp>-<n> "<self-contained prompt>"
then review each result against the report and the Python source while the rest run, integrate,
run the gate, and queue the package to dev-check. Job contract: exact file paths to edit (only inside
agenthub_go/ and only the files named), what to reuse (`PyJSONDumps`, `ToolDefinitions()`,
the existing `fastmcp/server/routes/*.go`), the acceptance test to run, "never commit or push,
never read or print credentials or .env files, never touch agenthub_main/". A job result is a draft:
read the diff, run `go build ./... && go vet ./... && go test -race -count=1 ./...`, fix by hand only
when a job failed twice. Write by hand only design-critical wiring (WP1/WP2 composition root).
First action: tell the user (rig queue) the DeepSeek job ids you started. If every job fails with
"Insufficient Balance", stop and report once; do not loop.

## Work packages (each has a measurable acceptance check)
- WP1 (B1, B4) MCP: serialize tool results with `PyJSONDumps` (never json.Marshal on OrderedMap);
  rebuild `/mcp` on `ToolDefinitions()`; publish the real tool registry (`interface/testdata/tools_golden.json`
  is the expected `tools/list`); add `resources/list` and `prompts/list`; require auth on `initialize` and
  `tools/list` when AUTH_ENABLED=true; streamable-HTTP/SSE for `GET /mcp` (406 without the SSE Accept
  header, like production); wire every facade factory (project, branch, agent, context) and return the
  `NewDDDCompliantMCPTools` constructor error instead of discarding it.
  ACCEPT: a local `tools/call` for 5 tools returns the same JSON as the Python server for the same input;
  `tools/list` equals tools_golden.json.
- WP2 (B2, B3) HTTP surface: mount every route from `fastmcp/server/routes/*.go` in `httpapp.Handler()`;
  add `/ws/realtime` and `/ws/connector`; apply the CORS middleware (OPTIONS -> 200 with
  `Access-Control-Allow-Origin` echo, `-Credentials: true`, methods, max-age 600).
  ACCEPT: re-run the live route probe you used for the report: 0 of 103 Python routes missing, both
  WebSockets accept a connection, preflight from https://www.4genthub.com returns 200 with those headers.
- WP3 (B6) Schema safety: the Go server must NOT run `CreateTables`/`EnsureAIColumnsExist` against an
  existing database by default (opt-in env `AUTO_MIGRATE=true`, default off in production); add Go models
  for the eight unknown tables (`agent_import_history`, `agent_templates`, `applied_migrations`,
  `token_transactions`, `user_agent_configurations_md`, `user_api_tokens`, `user_sessions`,
  `user_agent_instances`) matching production types; `user_agent_instances` (58 rows) and
  `agent_templates` (32 rows) must round-trip on a local DB built from `prod_like.sql`.
  > **Superseded (2026-10-05):** the table half of WP3 is void. `agent_templates` and
  > `user_agent_instances` were dropped from the schema (T7/T8) and no code path reads them
  > (`grep -rn 'agent_templates\|user_agent_instances' agenthub_go --include='*.go' --include='*.sql'`
  > → NO MATCH; the export-then-drop is recorded in `NEXT_GEN.md` T5/T7). `models_prod.go` now declares
  > **six** `ProductionTables` — `agent_import_history`, `applied_migrations`, `token_transactions`,
  > `user_agent_configurations_md`, `user_api_tokens`, `user_sessions` — not eight
  > (`fastmcp/task_management/infrastructure/database/models_prod.go:96`). The `AUTO_MIGRATE` half of
  > WP3 stands; see `ai_docs/api-integration/surface-inventory.md` §3.4 and §4.
  ACCEPT: start the Go server against the prod-like local DB with AUTO_MIGRATE unset and verify via `\dt`
  that no table was created; CRUD on the six remaining models passes.
- WP4 (B5) Deploy artefacts, WITHOUT changing production definitions: create `docker-system/docker/Dockerfile.backend.go`
  (multi-stage as proposed in the report; non-root; EXPOSE 8000), `.dockerignore` for agenthub_go
  (.gocache, .gomodcache, scratch), a `-healthcheck` flag in `cmd/agenthub` (HTTP GET /health, exit code,
  no curl), and a NEW `captain-definition.backend.go`. Leave `captain-definition.backend` and
  `Dockerfile.backend.production` untouched until the user decides the cutover. Add server timeouts
  (read-header, read, write, idle) and graceful shutdown on SIGTERM/SIGINT to `main.go`.
  ACCEPT: `CGO_ENABLED=0 go build ./cmd/agenthub` works, `agenthub -healthcheck` returns 0 against a
  running local server and non-zero otherwise. (Docker is not installed: say the image was not built.)
- WP5 Parity and tests: make `/health` return the Python payload shape; run `gofmt -w` on the 5 files;
  add tests for `httpapp` and `cmd/agenthub` covering the WP1-WP4 acceptance checks; resolve the two open
  parity questions (`GET /api/v2/tasks/stats/summary` 500; `PUT /api/v2/tasks/{id}` task_id in body) by
  comparing with the Python behaviour.
  ACCEPT: `go build`, `go vet`, `gofmt -l` empty, `go test -race -count=1 ./...` green and httpapp/cmd
  no longer "no test files".
- WP6 Auth: Keycloak cannot run here. Implement RS256/JWKS validation against a LOCAL fake JWKS server in
  a test (keys generated in the test), and document in the report that real Keycloak login with the e2e
  account is NOT verified and needs a staging environment.

## Division of labour
dev-owner: WP1, WP2, WP3, WP5 with DeepSeek workers. dev-check: reviews each package from the queue
(re-run the gates; do the live route probe yourself), then WP4 and WP6 as a second worker lead using the
same DeepSeek rule. Do not both edit the same file: owner owns `fastmcp/server/httpapp/*` and the models,
check owns `cmd/agenthub/*`, Dockerfile/captain files and the auth tests.

## Output
Update agenthub_go/PROD_READINESS_REPORT.md: keep the old verdict section, add "Re-review after fixes"
with each blocker B1-B6 as FIXED / PARTIAL / OPEN, the evidence (command + short output) and what is
still NOT verified. Final verdict by dev-check. Hand off through `rig queue`. Stop when done.
