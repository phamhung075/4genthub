<!-- 4genthub project agent instructions. Renamed from CLAUDE.md on 2026-10-05: Claude Code reads
     AGENTS.md natively and it is the cross-tool convention (Codex, Gemini, omp seats read it too).
     4genteam is retired and kept only in its directory for review. Native 4genteam is the single
     orchestrator. -->

# 4genthub agent instructions

**Deliberately thin.** The full context is no longer carried here: each seat receives its own role
file at launch, so a large root file would only go stale in every seat. This file carries identity,
where context lives, the hard rules every seat shares, and pointers; the rest lives in `ai_docs/`.

## 1. Identity first

Run `4genteam whoami --json`. It returns your rig, seat, peers, edges and transcript path, and it
is ground truth — a startup overlay can be stale. Re-run it after any compaction, restart or
restore, before concluding anything about where you are.

## 2. Where context lives

- **Your seat's role** — `agents/<seat>/agent.yaml` and `guidance/role.md`, written into the launch
  directory by the launch.
- **The work queue** — `4genteam room queue` (`list` / `show` / `create` / `update` / `claim` / `close`;
  owned work, handoffs, block/wake state).
- **The board and decisions** — `NEXT-GEN2.md` (repo root).
- **Project skills** — one source: `agenthub_client/skills/` (`share/` and `rooms/<room>/` reach a seat when
  its restart delivers them — `4genteam seat reseat`; `client/` is for the LLM running the client, e.g. `install`, `rig-runtime-switch`,
  `seat-runtime-switch`, `spawn-team`, `watch-team`). Ruling: `ai_docs/core-architecture/seat-skills.md`.
  `.agents/skills` is being retired; do not add skills there.
- **4genthub's own records** — tasks and context go into 4genthub itself through the `agenthub_http` MCP
  tools (`manage_task`, `manage_context`). **See §5** for how to call them, and for what to do when the
  device is not mounted in your session yet.
- **Everything else** — `ai_docs/` (see §4).

These are pointers; never copy their content into this file.

## 3. Hard rules (every seat, any role)

1. **Clean code only.** Never add backward compatibility, legacy code, fallback mechanisms,
   migration helpers, deprecation warnings, version checks or compatibility layers. Development
   phase, clean breaks allowed. **Clean code > passing tests.** Full policy:
   `ai_docs/agent-system/repo-agent-rules.md`.
2. **The entity/ORM is the source of truth, over the tests.** Order: prompt input → ORM/entity
   model → database → tests → code. A failing test means fix the code (or the test) to match the
   model; never add compatibility code to make tests pass. Rules and locations: same file.
3. **Changelog duties.** Update the changelog for changes that ship (one new file
   `CHANGELOG/<date>--<title>.md`) and `TEST-CHANGELOG.md` for
   test-suite changes. Detail: same file.
4. **Keep-out files and staging.** `.claude/` and `agenthub_go/seatcheck` never enter a commit.
   **Stage by explicit path; never `git add -A`** is **RETIRED** — the index is shared with every other
   seat working in this worktree, so a staged line can be taken by another seat's commit. **Commit by
   pathspec and do not stage first:** `git commit -m "<type(scope): subject>" -- <paths>`, and a
   brand-new file is the one exception, marked with `git add -N -- <new>` (intent-to-add, nothing enters
   the index) before the same commit. Never `git add .`, `-A` or `--amend`. **A removal is attributed by
   the COMMIT that carries it, never by the staging area** (`git show --numstat --format= <sha> -- <path>`);
   **a changelog entry is ONE new file `CHANGELOG/<date>--<title>.md`**, so no changelog commit can carry another seat's
   entry; any other shared file takes the WHOLE file, so check it is clear of other seats' lines, or sequence
   with that seat, or name what you carry. **If the pre-commit framework refuses a pathspec commit because
   the config is unstaged:** if the config is yours, commit it by itself by pathspec and the guard clears
   itself; if it is not, ask its owner; `--no-verify` only as a last resort, with the hooks run over your
   own paths and the skipped ones named. **The hooks also rewrite a path you named**, so read
   `git show --numstat` after committing. (`b059b863`; the full text and the checks: the file below.)
   (The old "`CLAUDE.md` stays out of every commit" rule is superseded — that file was renamed to
   `AGENTS.md`, which is tracked; see `agenthub_go/NEXT_GEN.md`.)
5. **The owner approves every push.** Never push, deploy or touch production or another rig without
   the owner's explicit go-ahead. **The remote carries only `main` and `frontend`.** A seat works in a
   local branch or worktree, merges into `main`, and pushes `main` (`frontend` for the frontend line);
   pushing any other remote branch or tag is refused by the `pre-push` hook (`scripts/git-hooks/pre-push-branches`).
6. **Launch and resume teams with `4genteam`, NEVER legacy 4genteam.** Always run `4genteam up <rig> [--allow-peak]`
   or `4genteam continue <rig>`. 4genteam daemon and runtime orchestration are retired; `4genteam` runs the full client
   supervisor stack (`agent`, the auto-compaction supervisor `compact-run`, `watchdog`, status `bridge`, and the styled
   `watch` grid). When asked to show the live team, always run `4genteam watch --room <rig>`.

## 4. Pointers

- `ai_docs/agent-system/repo-agent-rules.md` — the hard rules in full: clean-code policy,
  test-fixing priority and the source-of-truth hierarchy, changelog and keep-out detail, docs
  conventions.
- `ai_docs/agent-system/seat-model-and-mcp-surface.md` — the seat model, tool scope by seat, and
  the nine published MCP tools.
- `ai_docs/agent-system/task-workflow-and-reporting.md` — MCP task/subtask tracking and reporting
  guidance (product usage).

## 5. Record work in 4genthub through its MCP tools

**The owner's instruction to every seat (2026-10-06): record tasks and context in 4genthub itself through
`manage_task` and `manage_context`.**

- **How to call them.** Write the JSON argument object to the device path `xd://mcp__agenthub_http_<toolname>`
  — `manage_task` for work items, `manage_context` for the context a later reader needs to understand one.
  **Reading the same path returns that tool's schema**, which is where the argument names come from; the
  server's surface is the **nine** `agenthub_http` tools (`call_seat`, `manage_connection`,
  `manage_context`, `manage_git_branch`, `manage_project`, `manage_seat`, `manage_subtask`, `manage_task`,
  `submit_feedback`). `manage_agent` is not one of them: it was retired 2026-10-10 with the `agents` table
  and the 32-role registry, and `fastmcp/server/httpapp/manage_agent_absent_test.go` fails the build if it
  is published again. `manage_seat` is how a seat is read, and `@<seat_key>` is the only assignee identity.
- **Record as you go rather than at the end.** A task carries a state and an owner, and a row written after
  the work is a row nobody acted on.
- **IF THE TOOL IS NOT THERE, SAY SO RATHER THAN CONCLUDING IT DOES NOT EXIST.** A call that answers
  `No such tool xd://mcp__agenthub_http_…` while the device list holds only the `deepseek` tools means the
  server is **not mounted into THIS session** — not that it is missing. **The mount is per session:** a
  session gets the tools only at its start, so a fix applies only after a relaunch. Measured 2026-10-14: the
  cause was not a startup budget. `omp` also reads the project's `.gemini/settings.json`, and a stale
  `agenthub_http` entry there (a stdio `mcp-proxy` to `localhost:8000`) overrode the `.mcp.json` entry and failed
  with `MCP subprocess closed stdout before responding`; with the entry removed the same fresh `omp` mounts the
  nine tools. Report a missing mount to the lead rather than working around it silently.
- **How a seat gets the server (2026-10-15).** The client runtime starts every seat with
  `~/.config/4genthub/.env` in its environment (the seat spec's `env` wins over the file; the runtime's
  `AGENTHUB_*` keys win over both) and writes `<seat dir>/mcp.json` naming `${AGENTHUB_URL}/mcp` and
  `Bearer ${AGENTHUB_TOKEN}`. A running seat never re-reads either: after a change run
  `4genteam room reseat <rig> <seat>`. Verified: a reseated `go-dev` listed the nine tools and `manage_project`
  `list` returned the projects. Never read or print the token; check presence only.
