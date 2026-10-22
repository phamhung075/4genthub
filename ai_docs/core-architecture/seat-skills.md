# Seat skills: one source, installed by the runtime, checked at launch

Every skill a seat uses lives under `agenthub_client/skills`. Nothing else is a source for a seat: not the
cloud snapshot, not `.agents/skills`, not `~/.claude/skills`, not user-installed plugins.

## 1. Levels: each skill lives in exactly one place

| Level | Holds |
|---|---|
| `share/` | a skill used by more than one room |
| `rooms/<room>/` | a skill used by more than one seat of one room |
| `rooms/<room>/<seat>/` | a skill used by one seat, including its `<seat>-role` and `<seat>-workflow` |
| `client/` | skills for the LLM running the client (the owner's session); never installed into a seat |

A copy at two levels is not allowed.

## 2. Installation

At every seat start the runtime (`install_seat_skills`, `agenthub_client/rust/agenthub-runtime/src/supervisor/mod.rs`)
resolves the tree named by `AGENTHUB_CLIENT_SKILLS` (`share`, then `rooms/<room>`, then `rooms/<room>/<seat>`,
the more specific replacing a shared skill of the same name) and writes it to `<seat dir>/skills/`, replacing
what was there, so a skill removed from the tree does not linger. The body of the seat's `<seat>-workflow`
skill is also written to `<seat dir>/AGENTS.md`, so the seat's method is always in context.

A change to the tree reaches a seat at its next start: `4genteam room reseat <room> <seat>`, or
`agenthub_client/scripts/respawn.sh <room>` for the whole room.

## 3. What each runtime loads

- **omp** loads skills from its agent directory, which is the seat directory.
- **claude-code** gets the seat's MCP file with `--mcp-config <seat dir>/mcp.json` and the workflow with
  `--append-system-prompt-file <seat dir>/AGENTS.md` (`rust/agenthub-runtime/src/runner/mod.rs`).

A seat works in its own worktree (`seat-worktrees.md`), where the ignored `.agents/` does not exist.

## 6. The check, run by `up` after every seat launch

`internal/clientlifecycle/skillscheck.go`. A failure exits 3 with one line per failure,
`seat <seat>: <code> <detail>`; `4genteam doctor` reports the same as `skills_stale` on the seats row.

| Code | Fails when |
|---|---|
| `F1 cwd` | the seat's cwd is not its derived worktree |
| `F2 foreign` | the runtime loaded a skill the resolution did not deliver |
| `F3 missing` | a skill in the resolved set is not loaded |
| `F4 path` | a loaded skill of the set resolves outside `<seat dir>/skills/` |
| `F5 stale` | an installed copy differs from the client tree's copy at the current commit |

Evidence: for omp, `omp skill list --json` with the seat's launch environment and cwd; for claude, the
`system/init` event of a headless probe with the seat's argv, killed on that line. A running seat is never
killed to fix its skills; it picks up the tree at its next start.
