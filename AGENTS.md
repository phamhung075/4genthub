<!-- 4genthub project agent instructions. Renamed from CLAUDE.md on 2026-10-05: Claude Code reads
     AGENTS.md natively and it is the cross-tool convention (Codex, Gemini, omp seats read it too).
     HAZARD: OpenRig writes its OWN generated AGENTS.md into a rig's launch cwd. Launch rigs with
     their spec cwd (the rig directory), never with --cwd pointing at this repo, or this file is
     overwritten. The generated copy that used to live here is preserved at
     ~/.openrig/agenthub-seats/4genthub-min/backup/AGENTS.md.openrig-generated-2026-10-05. -->

# 4genthub agent instructions

**Deliberately thin.** The full context is no longer carried here: each seat receives its own role
file at launch, so a large root file would only go stale in every seat. This file carries identity,
where context lives, the hard rules every seat shares, and pointers; the rest lives in `ai_docs/`.

## 1. Identity first

Run `rig whoami --json`. It returns your rig, pod, member, peers, edges and transcript path, and it
is ground truth — a startup overlay can be stale. Re-run it after any compaction, restart or
restore, before concluding anything about where you are.

## 2. Where context lives

- **Your seat's role** — `agents/<seat>/agent.yaml` and `guidance/role.md`, written into the launch
  directory by the launch.
- **The work queue** — `rig queue` (owned work, handoffs, block/wake state).
- **The board and decisions** — `agenthub_go/NEXT_GEN.md`.
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
3. **Changelog duties.** Update `CHANGELOG.md` for changes that ship and `TEST-CHANGELOG.md` for
   test-suite changes. Detail: same file.
4. **Keep-out files and staging.** `.claude/` and `agenthub_go/seatcheck` never enter a commit.
   Stage by explicit path; never `git add -A`. (The old "`CLAUDE.md` stays out of every commit"
   rule is superseded — that file was renamed to `AGENTS.md`, which is tracked; see
   `agenthub_go/NEXT_GEN.md`.)
5. **The owner approves every push.** Never push, deploy or touch production or another rig without
   the owner's explicit go-ahead.

## 4. Pointers

- `ai_docs/agent-system/repo-agent-rules.md` — the hard rules in full: clean-code policy,
  test-fixing priority and the source-of-truth hierarchy, changelog and keep-out detail, docs
  conventions.
- `ai_docs/agent-system/seat-model-and-mcp-surface.md` — the seat model, tool scope by seat, and
  the ten published MCP tools.
- `ai_docs/agent-system/task-workflow-and-reporting.md` — MCP task/subtask tracking and reporting
  guidance (product usage).
- `ai_docs/agent-system/agents-md-migration-map.md` — what this file used to carry and where each
  section went.

## 5. Record work in 4genthub through its MCP tools

**The owner's instruction to every seat (2026-10-06): record tasks and context in 4genthub itself through
`manage_task` and `manage_context`.**

- **How to call them.** Write the JSON argument object to the device path `xd://mcp__agenthub_http_<toolname>`
  — `manage_task` for work items, `manage_context` for the context a later reader needs to understand one.
  **Reading the same path returns that tool's schema**, which is where the argument names come from; the
  server's surface is the **ten** `agenthub_http` tools (`call_seat`, `manage_agent`, `manage_connection`,
  `manage_context`, `manage_git_branch`, `manage_project`, `manage_seat`, `manage_subtask`, `manage_task`,
  `submit_feedback`).
- **Record as you go rather than at the end.** A task carries a state and an owner, and a row written after
  the work is a row nobody acted on.
- **IF THE TOOL IS NOT THERE, SAY SO RATHER THAN CONCLUDING IT DOES NOT EXIST.** A call that answers
  `No such tool xd://mcp__agenthub_http_…` while the device list holds only the `deepseek` tools means the
  server is **not mounted into THIS session** — not that it is missing. **The mount is per session:** `omp`'s
  MCP discovery has a **250 ms startup budget** that the HTTPS `agenthub_http` server misses, so the seat's
  agent dir carries `mcp.startupTimeoutMs 0`, and **a session gets the tools only after that config plus a
  start or a relaunch.** Report that state to the lead rather than working around it silently.
