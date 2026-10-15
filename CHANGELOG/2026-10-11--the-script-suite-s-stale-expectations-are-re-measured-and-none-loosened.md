## The script suite's stale expectations, re-measured case by case and none loosened

### What changed
Row `qitem-20261011035828` (urgent). The suite ran **12 failed / 76 passed at the certified batch tip `708e3131`**, identical at pre-batch main, so nothing in it was the batch's. **That is the sealed revision's own clean-tree result, re-verified 2026-10-11 in a detached worktree with `GIT_DIR` unset**; the tip this entry ships to is `92 passed, 0 failed`, and the commits below are what closed the gap. Read the numbers here as the progression's start, not as the tip's state. The counts row
(`7c358c4b`) then took it to **9 failed / 79 passed**. This entry closes the remaining six
non-instrument cases and re-derives the nineteen anchors the seventh reads, and for each one the side
that was wrong is a measurement, not a preference:

- **`test_team_roster.py` — the EXPECTATION was stale.** `rig ps --nodes --rig 4genthub-min --json`
  reports **five** nodes: one `claude-code` and four `omp`. The room's `team.json` declares exactly
  those five (`architect` on claude-code; `fe-dev`, `go-dev`, `lead`, `reviewer` on omp), so the room
  and the rig agree at five and `LIVE_SEATS`/`OMP_SEATS` — written at ten on 2026-10-08 — were the
  stale side. They are re-measured, and `test_the_declared_seats_are_the_live_ten` is renamed
  `..._the_live_roster` because the name asserted the number that moved. **The comparison itself is
  untouched** (`declared == sorted(LIVE_SEATS)`), so it still fails on any drift.
- **`test_seat_policy_commit_form.py` — the EXPECTATION was stale.** The room declares five seats and
  holds five `policy-*.json` files, so `len(names) == 10` and "commit-form siblings in all ten
  modules" became five. **No rule was weakened:** `test_no_sibling_prescribes_the_old_commit_form`
  and both agreement assertions are byte-unchanged, and the count stays a hard number rather than a
  set derived from the file it is checking.
- **`test_team_definition.py[4genthub-min]` — the BAND TABLE was stale.** The room declares one
  room-local instruction module, `guide-e2e-dev -> guide-e2e-dev.md` (355 words), and
  `ROOM_WORD_LIMITS["4genthub-min"]` was empty with a comment saying every module it names lives in
  the Go seed library. The band `(300, 420)` is added and the comment corrected; both ends still
  bite, which is the point of a band.
- **`test_team_definition.py[4genthub-ab]` — the ROOM DATA was wrong, not the test.** `ab-policy-lead`
  and `ab-policy-go-dev` resolved to `../4genthub-min/policy-lead.json` and `.../policy-go-dev.json`,
  outside the room that declares them, which the rule forbids for the reason `b4ca5c68` fixed for
  `4genthub-client`: a sibling's rename or edit breaks the room silently. **The two files are copied
  into the room byte-identically** (sha256 `97f1407a…` and `a72b59e7…` — checked, not assumed) and the
  entries point at them, so the room is self-contained and the published module content is the same
  bytes it was.
- **`test_census_audits.py[script2]` (three cases) — the nineteen §3.1 ANCHORS were stale.**
  `ai_docs/api-integration/surface-inventory.md` cited `models.go:582 … :938` while the TableDef
  entries sit at `596 … 958`, shifted by +14 to +20 lines, and **every shift is attributed to the
  hunk that caused it, read from `git diff -U0` rather than assumed**: `0e03b3f7` added ten lines in
  `AgentSession` at `models.go:86` and two in the TableDef list above `api_tokens`; `d5a59667` added
  two inside `Task` (`models.go:418`) and two inside `Subtask` (`models.go:483`) — the four that sit
  above `agent_sessions` — plus two above `subtasks` (`models.go:853`) and two above `task_assignees`
  (`models.go:891`). That is the whole ladder: `agent_sessions` +14, the thirteen rows from
  `api_tokens` to `tasks` +16, `subtasks` +18, the four rows from `task_assignees` to `task_labels`
  +20. Each row was re-resolved by searching for its own TableDef entry rather than by adding an
  offset, because the steps differ per band and a constant would have been wrong.

### Verified
- `python3 -m pytest --noconftest -p no:cacheprovider scripts/tests -q` -> **12 failed, 76 passed**
  before any of this work (**at `708e3131`**), **9 failed, 79 passed** after the counts row, and **3 failed, 85 passed** in
  the worktree after these edits. The three are S3's own cases, and that instrument resolves the
  document **at `rev` through `git show`, never the worktree** (its header says so), so they read the
  pre-commit file: this commit is what they read, and they go green with it.
- `python3 scripts/S3-REDERIVE.py` -> `FRESH 46  STALE→BATCH 0  … 19 not fresh` in the worktree, with
  the nineteen marked `STALE (unattributed)` because the fixture they are compared against is the
  committed copy. Stated rather than smoothed: the pre-commit reading is not the verdict.
- The four roster/band/policy cases, run by name, pass.
- `sha256sum` over each copied policy and its source: identical, both pairs.

### What this does NOT do
No assertion was loosened into a tautology: a count moved from ten to five because the room holds
five, not because five was easier; the roster case still compares the file against a measured list
that is not derived from it; the sibling rules are untouched; and no case was deleted.

Nothing in `scripts/team/4genthub-min/` changed. The room was already the five-seat room — the tests
were describing one that no longer exists.

The count instruments' own history is untouched; the corrections they needed were `7c358c4b`.

Row: `qitem-20261011035828`.
