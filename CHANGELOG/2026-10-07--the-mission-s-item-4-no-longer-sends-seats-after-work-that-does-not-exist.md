## The mission's item 4 no longer sends seats after work that does not exist

- **What it said, and why it mattered:** the standing mission (`scripts/team/4genthub/mission.md`, the source of the
  `mission-4genthub` module every seat in that room carries) listed two cleanups under item 4 — `the 23 TypeScript
  errors` (already struck) and **`the gofmt finding in the subtask controller`**, which was listed as though it were
  live work. It had been **measured as not existing** twice already (`NEXT_GEN.md:571`, `:94` under rule 20) and was
  measured again for this change: `git ls-files '*.go' | xargs gofmt -l` prints **nothing**, `gofmt -l
  fastmcp/task_management/` prints **nothing**. **A STANDING INSTRUCTION WAS SENDING SEATS AFTER DEAD WORK**, and
  because the mission is the one document nobody re-measures and everybody obeys, nothing downstream caught it.
- **What it says now:** item 4 points at the **live set** — the unticked Checklist boxes in `NEXT_GEN.md` — strikes
  **both** cleanups with their measurements inline, and names the rule that makes the entry self-checking
  (`NEXT_GEN.md:571`, `:94`, rule 20: *a cleanup-list entry is a claim like any other, measured before it is worked
  or repeated*). A reader can now tell dead work from live work **without running `gofmt` and `tsc` first**, which
  is the whole of what this change was for.
- Files: `scripts/team/4genthub/mission.md`, `CHANGELOG.md`.
