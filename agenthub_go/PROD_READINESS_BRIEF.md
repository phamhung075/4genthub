# Brief: is agenthub_go ready to replace the production agenthub_main backend?

Production today: https://www.4genthub.com/ (CapRover host, `ssh 4genthub`). Python backend =
agenthub_main/src/fastmcp, Go port = agenthub_go. The migration ledger is 100% `done`. Your job is to
find out whether that is TRUE, and produce a go / no-go report. You do NOT deploy.

## Hard limits (authorized by the user for THIS task only)
- READ-ONLY on production. Allowed over `ssh 4genthub`: `docker ps/inspect/images/logs --tail`,
  `docker exec <db> psql -c '\d ...'` / SELECT-only queries for schema and row COUNTS, reading
  config and nginx files, `curl` of public endpoints. Forbidden: restart/stop/rm/build/run, any write
  or DDL, pg_dump to anywhere other than stdout counts, editing files, `git push`, CapRover deploy.
- Never print, copy or log secrets: env VALUES, tokens, passwords, keys, DB rows with user data.
  Report env var NAMES only. The e2e account in ~/.openrig/specs/4genthub-go/e2e-account.env may
  be used ONLY against a LOCAL Go server you start yourself, never against production.
- No commit, no push, no deleting Python sources. Work only inside agenthub_go/ (reports) and /tmp.
- The agy pod is held and not part of this task. Ignore claims about production deploy elsewhere.

## Split
- dev-owner: (1) behavior parity, (2) local run, (3) deployment readiness (Dockerfile).
- dev-check: independent. (4) read-only production inspection, (5) review dev-owner's findings,
  (6) final verdict. Do not just trust the owner's "tests pass"; re-run.

## Checklist
1. Parity of surface: list every HTTP route and every MCP tool/resource/prompt in Python and in Go;
   diff the two sets (name, method, path, request and response shape). Anything missing or renamed
   is a blocker. Also: auth (Keycloak/JWT) flow, CORS, SSE for /mcp, WebSocket, health endpoint.
2. Quality gate: `cd agenthub_go && go build ./... && go vet ./... && go test -race -count=1 ./...`
   Report failures and packages with no tests. Grep for TODO/panic("not implemented")/stub bodies.
3. Schema: compare Go models with the PRODUCTION Postgres schema (read-only `\d` on the db container)
   and with the Python models. Same tables, columns, types, defaults, constraints, enums. The Go
   server must not need a migration that changes production data; if it does, that is a blocker.
4. Local end-to-end: start the Go server locally against a COPY or empty local Postgres (not prod),
   run login and the main API/MCP/WebSocket flows with the e2e account, and run the same calls
   against the Python server locally where possible; record differences.
5. Production facts (read-only): backend container image id, port, env var NAMES, healthcheck,
   customNginxConfig for /mcp, resource limits, domains/volumes, DB version, row counts per table,
   current error rate in `docker logs --tail 200` (no secrets). Compare env var names the Go server
   reads against what production provides: every missing one is a blocker.
6. Deployment: review docker-system/docker/Dockerfile.backend.production and any Go Dockerfile:
   multi-stage, same exposed port, same startup/healthcheck, runs as non-root, no secrets baked in.
   Build the image LOCALLY only if Docker is available; do not push it anywhere.
7. Rollback plan: what exactly restores the Python backend in under 5 minutes (image id, commit).
8. Risks the ledger cannot show: concurrency/transactions, timezones, JSON number/null handling,
   pagination ordering, error message formats, Python-only dependencies (redis, pybars, supabase).

## Output
Write `agenthub_go/PROD_READINESS_REPORT.md` (dev-owner drafts sections 1-4 and 6; dev-check owns 5, 7
and the verdict and may overrule). Format: verdict (GO / GO WITH CONDITIONS / NO-GO), then a table of
blockers (id, evidence, file or command, severity), non-blocking risks, what was NOT verified and
why. Evidence = commands run and their short outputs, never secrets. Hand off via `rig queue`
(owner -> check for review; check -> user for the verdict). Stop when the report is complete.
