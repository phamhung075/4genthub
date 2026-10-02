# Team split — who ports which todo rows

Two pods work on MIGRATION.md in parallel. Ownership is by the first path segment of the
Python module (the bounded context), across ALL slices. Only touch rows you own.

| Team | Seats | Owns (Python module first segment) | Todo rows |
|---|---|---|---|
| Claude | dev-owner / dev-check @4genthub-go | Paused due to session limit (resets 11:20 AM) | Handed over to Agy |
| Agy | agy-owner / agy-check @4genthub-go | ALL contexts: `task_management` (takeover), `agent_management`, `ai_task_planning`, `auth`, `connection_management`, `middleware`, `prompts`, `resources`, `server`, `tools`, `websocket` | 112 remaining (`task_management`) |

Rules
- Claude team is rate-limited until 11:20 AM. Agy team has taken over all remaining `task_management` rows.
- Pick the next `todo` row in slice order (3 -> 4 -> 5 -> 6).
- Update MIGRATION.md with targeted edits as each module is ported and verified.
- Shared files (go.mod, go.sum, shared helpers under fastmcp/shared or utilities): add only,
  do not modify existing definitions. Run `go build ./...` before and after.
- agy-owner plans slices, fans out mechanical ports to DeepSeek workers, reviews/integrates, and queues to agy-check.
- agy-check verifies via `go build ./...`, `go vet ./...`, and `go test ./...`.

# Culture (shared by all four seats)
Mirrors ~/.openrig/specs/4genthub-go/CULTURE.md. Repository: /home/daihu/__projects__/4genthub. Goal: port the Python server (agenthub_main/src/fastmcp) to Go in agenthub_go/ with the same DDD layout, file names, HTTP/MCP API and DB schema. Behavior must not change. Never revert uncommitted user changes; never delete the Python server.

## Teams and standing mission (4 seats)

Two pods are configured in the repo: Claude (dev-owner / dev-check) and Agy
(agy-owner / agy-check). Because the Claude team is currently rate-limited until 11:20 AM,
the Agy team (agy-owner / agy-check) has taken over all remaining rows in `task_management`.

Standing mission: port every `todo` row in agenthub_go/MIGRATION.md (same
file layout and behavior as the Python original, which stays untouched), then mark it `done`.
Work in slice order (3 -> 4 -> 5 -> 6). Owner: do not wait for the checker; queue each finished
slice for review and start the next. Checker: review your team's queued slices promptly and
return findings. Both: after each turn re-read MIGRATION.md; if any `todo` rows remain,
continue. Stop only when none remain or you need information only the user can give.
Hand off through `rig queue`, not chat. Do not commit or push unless the user asks.

## Team structure: each owner leads DeepSeek workers

Each team is a ladder. The owner is the team leader and the DeepSeek jobs are its workers; the
checker reviews the leader's output. The owner plans a slice, splits it into self-contained
module jobs, fans them out to DeepSeek workers in parallel, reviews and integrates what comes
back, and queues the slice to the checker. The owner writes code by hand only for design-heavy
modules, for fixing a job that failed the build twice, or when the worker is unavailable.
Delegation is the DEFAULT for mechanical ports, not an option. Before each slice, start jobs
first (dsh-offload.mjs start --detach, or deepseek_agent), then review while they run.
If a job fails with "Insufficient Balance" (or `doctor`/a test job fails the same way), do not
stall and do not retry in a loop: port directly, and tell the user once through rig queue that
DeepSeek needs a balance top-up.

## Offloading to DeepSeek (default delegation path)

The `deepseek` MCP server (mcp__deepseek__deepseek_agent, from the repo .mcp.json) and the CLI
`node .agents/skills/deepseek-offload/scripts/dsh-offload.mjs` (run `doctor` first) are available
to all four seats. Read .agents/skills/deepseek-offload/SKILL.md once before the first job.

- Offload (owners): mechanical ports of self-contained modules (entities, enums, DTOs,
  repositories, converters, utilities, config, route handlers), one module or small group per job.
- Offload (checkers): long build/test output triage and repo-wide audits, as read-only jobs.
- Keep in the seat: design decisions, anything needing your conversation context, credentials,
  and all git operations.
- Job contract: give the exact Python source path, the Go target path from MIGRATION.md, the package
  name, the already-ported Go types to reuse, "same behavior, keep quirks, one .go file per .py
  module", and the check to run (`cd agenthub_go && go build ./... && go vet ./... && go test
  ./<pkg>/...`). Tell the job to write ONLY under agenthub_go/ inside your team's contexts, never
  edit agenthub_main/ or other existing files, never commit or push, never read or print
  credentials or .env files.
- Review gate: a job result is a draft. Read the diff against the Python source and run
  go build/vet/test before marking a row `done`. A job that fails the build twice is finished by the
  seat directly. Never trust a job's own "tests pass". Put no credentials or production details
  in a prompt.

## End-to-end test (only after BOTH teams have no `todo` rows)

Only dev-owner runs it. Test only the Go server (login, then the main API/MCP/WebSocket flows)
with the account in ~/.openrig/specs/4genthub-go/e2e-account.env (E2E_EMAIL / E2E_PASSWORD, read
at test time; never copy credentials into the repo, logs, commits or queue items). Fix failures
and re-run until green. Replacing the production backend is NOT authorized by this file: ask the
user first.
