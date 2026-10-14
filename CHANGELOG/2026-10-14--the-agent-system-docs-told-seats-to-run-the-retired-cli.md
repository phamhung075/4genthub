# The agent-system docs told seats to run the retired CLI

## What was wrong
`AGENTS.md` §4 points every seat at three `ai_docs/agent-system/` files as the canonical detail. Two of
them, plus `AGENTS.md` itself, carried instructions to run `rig` — which on this box is the OpenRig node
CLI (`0.6.10`, `@openrig/cli`), whose daemon is retired and which answers `rig whoami` with
`daemon unreachable … Node ID: —`. Measured 2026-10-14:

| file | said | now says |
|---|---|---|
| `AGENTS.md:22` | "**The work queue** — `rig queue`" | `4genteam room queue` with its sub-verbs |
| `AGENTS.md:23` | "**The board and decisions** — `agenthub_go/NEXT_GEN.md`" | `NEXT-GEN2.md` (repo root) |
| `ai_docs/agent-system/seat-model-and-mcp-surface.md:9` | "Run `rig whoami --json`. It returns your rig, **pod**, member, peers, edges and transcript path" | `4genteam whoami --json`, "your rig, seat, peers, edges and transcript path" |
| same, `:27` | "Identity comes from `rig whoami --json`" | `4genteam whoami --json` |
| same, `:39` | "Know your seat first: `rig whoami --json`." | `4genteam whoami --json` |
| `ai_docs/agent-system/task-workflow-and-reporting.md:5` | "through the queue (`rig queue`)" | `4genteam room queue` |
| same, `:40` | "routed through `rig queue`" | `4genteam room queue` |

Two of these were dead *pointers*, not just retired names: `agenthub_go/NEXT_GEN.md` is removed from this
worktree — the removal is carried by no commit yet, so HEAD still carries the file — and the board has been
`NEXT-GEN2.md` at the repo root since the rewrite; `rig queue` resolves to a CLI that cannot reach a daemon.

The native spellings are measured, not guessed: `4genteam room queue --help` prints
`(list ROOM | show ROOM QITEM_ID | create ROOM --to SESSION --summary TEXT | update ROOM QITEM_ID | claim
ROOM QITEM_ID | close ROOM QITEM_ID --reason R)`, writes act as the seat's own session read from
`$AGENTHUB_SESSION_NAME`, and `4genteam whoami --json` exits 0 with
`identity{rigName, memberId, runtime, sessionName, logical_id, role, model}`, `peers`, `edges` and the
transcript path.

## Scope, and what was deliberately left alone
Only the files a seat or the client's own LLM is told to read. `ai_docs/core-architecture/*` still
describes the OpenRig design in many places (`rigd-boundaries.md`, `agenthub-system-architecture.md`,
`seat-skills.md`; `git grep -I -o -i openrig -- 'ai_docs/core-architecture/*' | wc -l` counts 66 there and
2146 across the repo) and those are the design record of the thing being
retired — rewriting them is C5/C7 territory, not a doc sweep, so they are untouched here.

## Evidence
`git show --numstat` on this commit (three files, eight lines); the two measured invocations above.
