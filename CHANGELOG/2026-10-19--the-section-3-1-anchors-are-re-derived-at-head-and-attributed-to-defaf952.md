# The surface inventory's section 3.1 anchors are re-derived at HEAD and attributed to `defaf952`

## Fixed

`ai_docs/api-integration/surface-inventory.md` §3.1 — **all nineteen `models.go` declaration anchors
were one commit behind at `1caaadf1`**, and each row now cites the line the instrument measured there.
`scripts/S3-REDERIVE.py` reported `FRESH 48  STALE->BATCH 19  STALE->EARLIER 0  UNRESOLVED 0`
before the edit and `FRESH 67  STALE->BATCH 0  STALE->EARLIER 0  UNRESOLVED 0` after it.

**The cause is one commit, not nineteen coincidences.** `defaf952 fix(task-management): a done task
keeps its result line and its author` is the only commit to touch
`agenthub_go/fastmcp/task_management/infrastructure/database/models.go` since the previous
re-derivation at `072fbf02`:

```
git log --oneline 072fbf02..1caaadf1 -- agenthub_go/fastmcp/task_management/infrastructure/database/models.go
defaf952 fix(task-management): a done task keeps its result line and its author
```

Its `git diff -U0` carries exactly two insertions, both above declarations this section cites:

- `CompletedBy string` at `models.go:411`, inside `type Task struct` — above every §3.1 anchor, so
  **+1 for all nineteen rows**.
- `{Name: "completed_by", …}` at `models.go:845`, inside `var Tables` between `tasks`' own
  `completed_at` and `completion_summary` entries — above `subtasks` and every row below it, so
  **+1 more for those five**.

The commit's third hunk (`models.go:862 -> :864`) rewrites the `tasks` DDL string in place and moves
no line. The measured split is therefore **fourteen rows +1 and five rows +2** (the task description's
"twelve +1, seven +2" is not what the instrument reads).

**The mapping applied, cited -> new:** `agent_sessions` 592->593, `api_tokens` 611->612,
`context_delegations` 628->629, `context_inheritance_cache` 657->658, `global_contexts` 681->682,
`labels` 700->701, `missed_notifications` 711->712, `projects` 726->727, `templates` 738->739,
`agent_session_events` 759->760, `project_contexts` 771->772, `project_git_branchs` 793->794,
`branch_contexts` 811->812, `tasks` 832->833, `subtasks` 868->870, `task_assignees` 902->904,
`task_contexts` 915->917, `task_dependencies` 940->942, `task_labels` 950->952.

The table's dated record gains the 2026-10-19 paragraph carrying this attribution; the 2026-10-11
paragraph below it is left as the measurement it records.

## Verified

- `python3 scripts/S3-REDERIVE.py origin/main a7990665 --doc-file surface-inventory.md` -> `rows=46
  anchors=67`, `FRESH 67  STALE->BATCH 0  STALE->EARLIER 0  UNRESOLVED 0`, exit 0. The instrument reads
  the committed document, so this is the doc-file form; the `HEAD` form is the landing check.
- The instrument's self-test logic on the patched document: baseline 0 not-fresh, one perturbation ->
  1 not-fresh with the row named (`PASS`).
- `python3 scripts/COUNTS-AUDIT.py` on the patched worktree: every row matches, exit 0.
- Every one of the nineteen §3.1 cells checked against `git show origin/main:.../models.go`: 19
  checked, 0 bad.
- The census file at `1caaadf1` is `5 failed, 8 passed`. This patch set clears the three S3 cases, so
  the landed result is expected to be `2 failed, 11 passed`, both failures being `CITATION-AUDIT`'s
  §1 cases (below); the `HEAD`-form instrument run and the test file are the landing checks.
- Docs only: no `.go`, `.sql` or test file changed.

## Not in this change

- **The other two census reds are §1's, not §3.1's.** `CITATION-AUDIT.py` at `1caaadf1` reports
  `rows 148  stale 51  unresolved 0`: seven `app.go` rows (+7 each) and forty-four
  `routes_mount.go` rows (+1 each). One commit after the inventory's last route sync (`51f3dc01`)
  accounts for all of it — `ffe4f07f fix(context): the factory refuses instead of installing a mock`
  inserted three lines at `app.go:34` and four net at `app.go:74`, plus one at `routes_mount.go:53`,
  and every cited registration sits below those insertions. Re-deriving §1 is its own row; the board
  item (`8a80be86`) excludes the document's other sections.
- The §3 header's prose anchor `models.go:581` (the `database.Tables` registry) is outside the
  instrument's §3 row coverage and reads `:592` at `1caaadf1`; the prose class is declared-uncovered
  by `S3-REDERIVE.py` and is not repaired here.
