# Task workflow and reporting

> This is guidance for the agenthub
> **MCP task surface** (`manage_task` / `manage_subtask`). A seat in a room moves its own work
> through the queue (`4genteam room queue`), not through MCP tasks; the MCP surface is the product the user
> drives.

## Task duplication prevention

Always check for existing tasks before creating new ones:

```python
existing_tasks = mcp__agenthub_http__manage_task(action="list", git_branch_id="branch-uuid")
# If a relevant task exists -> UPDATE it, don't create a duplicate.
# If no matching task -> CREATE a new one.
```

## Tiered task workflow

Choose the right tier for the complexity. Log the work in MCP before modifying files.

### Tier 1 — simple (1 file, quick change)

1. **Create the task**: `manage_task(action="create", title="...", assignees="@<seat-or-role>", git_branch_id="...")`.
2. **Do the work yourself** (no team needed).
3. **Complete the task**: `manage_task(action="complete", task_id="...", completion_summary="...")`.

### Tier 2 — medium (2-3 files, sequential work)

1. **Create the task**, with a description covering all files.
2. **Do the work yourself** — read, change, verify.
3. **Update progress** as you go: `manage_task(action="update", task_id="...", status="in_progress", details="...")`.
4. **Complete the task** with a summary of all changes.

### Complex work

Complex work is split across seats and routed through `4genteam room queue`; see
[`seat-model-and-mcp-surface.md`](./seat-model-and-mcp-surface.md).

## Reporting pattern

- Every task is logged before work starts.
- Progress is updated as it happens (roughly every 25%).
- Every completion carries a detailed summary.
- Every blocker is raised immediately through an update.

```python
# 1. CREATE (before any work)
task = mcp__agenthub_http__manage_task(
    action="create",
    git_branch_id="branch-uuid",
    title="Implement JWT authentication",
    assignees="@<seat-or-role>",
    details="""
    Requirements: full auth with refresh tokens
    Files: <path>:<line>-<end> (functionName), <path>:<line>-<end> (functionName)
    Acceptance: login/logout works, tokens refresh correctly
    """
)
task_id = task["task"]["id"]

# 2. UPDATE PROGRESS
mcp__agenthub_http__manage_task(
    action="update", task_id=task_id,
    details="Login endpoint done, working on refresh tokens",
    progress_percentage=60
)

# 3. COMPLETE WITH REPORT
mcp__agenthub_http__manage_task(
    action="complete", task_id=task_id,
    completion_summary="JWT auth with refresh tokens, 2h expiry",
    testing_notes="Unit tests added, manual login/logout verified"
)
```

### Which verb writes which surface

- **Progress, notes and status of a TASK**: `manage_task(action="update", details="...")`. That is the
  surface the task's board item shows.
- **Context** (global, project, branch or task tier): `manage_context`. It carries the background a later
  reader needs; a task-level note written through `manage_context add_progress` does NOT reach the board
  item's Details (measured, hub task `4138904d-b8e6-43a1-8c84-55e84e44b9b0`), so progress goes through
  `manage_task`.

## Acceptance criteria: what the judge can settle

`4genteam complete` runs a gate whose judge is shown the evidence's COUNTS and the criteria text, and nothing
else: whether a test command ran, its exit code, how many tests failed, `files_changed`, `lines_changed`, the
added/deleted split (`lines_added`, `lines_deleted`), the per-path rows with every path name removed, and the
base and head SHAs (`agenthub_client/internal/clientjev/countsonly.go`, `countsState`). Paths, test names and
which path carries which counts do not reach the judge: every string in the judge's request, the criteria
included, goes through `RedactForWire`, which turns each path into `<path>` and each
`Test*`/`Benchmark*`/`Example*` name into `<test>` (`countsonly.go`; it runs at the transport, `jev.go`'s
`call`). There is no field for a file's contents and none for a command's output either
(`agenthub_client/internal/clientevidence/evidence.go`; `evidence_test.go`'s `assertKeys` fails on an extra
field) - and the request shape is pinned too (`clientjev/jev_test.go`,
`TestTheCriteriaRequestCarriesTheEvidenceAndNothingElse`). So a criterion that asks for content can only be
answered low: the wording is the instrument, not the evidence.

The gate refuses before the judge is asked. A criterion is admitted only when it names one of the facts the
local register carries - the acceptance command, the run's exit code, a base/head sha prefix of at least 7
hex characters, or a count key (`files_changed`, `lines_changed`, `lines_added`, `lines_deleted`) stated with
THIS bundle's value in the same clause; a criterion whose only fact is a path the numstat lists is refused as
well, because the wire would show the judge `<path>` in place of the one fact it resolved. Anything else makes
the whole task `unjudgeable` with no judge call (`agenthub_client/internal/clientcomplete/gate.go`,
`register.names`). The count branch is literal: the first number after the key, before the next count key,
must equal the bundle's value. "files_changed is 2" settles nothing on a bundle of 3, and "the numstat names 2
files" names no key at all.

The two rules meet, and that is the trap: a path the numstat lists RESOLVES, and a criterion that is about
that path and nothing else is still refused before the judge, because the request would carry `the numstat
names <path>` and the answer could only be an opinion; a path it does not list is refused as naming no fact at
all. What is both admitted and visible is the command, its exit code, a sha prefix and the counts. A
well-formed criterion names the command it is settled by, NARROW enough that the command line
itself names what it proves, and settles the rest with a sha and the counts - the totals, and the split when
added and deleted lines matter separately.

A count criterion is about the change, not a file: the per-path rows reach the judge with no names, so "one
path adds 34 lines" cannot be stated - only "lines_added 34" can. A criterion that needs a particular path's
count is not settleable; state the count, or run a command whose line names that proof.

Two edges, both measured on the gate itself. The exit-code branch matches the run's own integer whatever
command the criterion names it for, so "`tsc` exits 0" is settled by a bundle whose command was
`npx vitest run` - name the command the bundle actually ran. And a claim no fact can carry has no admissible
wording: a screenshot, a rendered page, "reachable by tap" - either a command that produces the proof runs as
the acceptance command, or the claim belongs in the task's details, not in its criteria.

A THIRD HAZARD, measured the same way: a command that exits 0 without doing the work passes, so name one that
cannot no-op - and the frontend had one that could. At the repository root `npx tsc` is NOT TypeScript: the
root carries no compiler, so npx resolves a global package named `tsc`, which prints a notice and exits 0 in
0.93 s without reading a file (measured 2026-10-21; the real compiler takes 11.8 s on the same tree, hub task
`951d97e3`). The frontend's acceptance command from the root is `sh scripts/typecheck-frontend.sh`
(equivalently `npm run typecheck`): it names `agenthub-frontend/node_modules/.bin/tsc` by path and exits 127
when that binary is absent, so a missing install is a failure and not a green. From inside
`agenthub-frontend`, `npx tsc --noEmit -p .` resolves that package's own compiler and is sound.

The `--base` is evidence, not a formality: it is REQUIRED, it is resolved to a full 40-hex sha, and the numstat
is a two-dot `git diff --numstat <base>..HEAD` between the resolved shas
(`agenthub_client/internal/clientcomplete/complete.go:50,:118`;
`agenthub_client/internal/clientevidence/evidence.go`, `Collect`, `:59`). The judge reads `base_sha`,
`head_sha`, `files_changed` and `lines_changed`, so a base one commit off settles the criterion on somebody
else's lines. The base is where YOUR line stood before this change: the tip's FIRST parent when the tip is
itself the landing merge, and otherwise the merge-base of `HEAD` and the line being landed on. Measured on the
landing merge `0a731846` (parents `ebc3da01`, the trunk tip, and `3fe14469`, the branch tip): base `^1` reads
3 files / 34 lines, base `^2` reads 0 files / 0 lines, and the parents' merge-base is `^1`. On a landing merge
the second parent is the branch side, so it measures the merge against its own branch and reads nothing. And
the trunk tip is only a base when no other work landed between your fork point and it: measuring the landing
merge `ebc3da01` from the pre-merge trunk `2c345157` reads 6 paths, the merge's pin side included, where the
branch tip `216a89d1` against the same base reads 3 files / 21 lines (task `6e84d62e`, its own Progress 6).

- GOOD: "the acceptance command `go test -count=1 ./internal/clientcomplete/` exits 0 and the change is
  measured from base 99cdc0ef to head 0c53c313, files_changed 2, lines_added 47, lines_deleted 6"
- GOOD: "the acceptance command `cargo test --test seat_guard a_seat_cannot_raise_its_own_budget` exits 0 and
  head 0c53c313 is reached from base 99cdc0ef with files_changed 1"
- GOOD: "between base 99cdc0ef and head 0c53c313, lines_added 18 and lines_deleted 3" - a count sentence
  settles without a command: the sha carries the admission, the keys carry the claim.
- BAD: "the numstat names rust/agenthub-runtime/tests/seat_guard.rs" - a path the numstat lists is the one fact
  the wire takes away, so a criterion that is only that path is refused as `unjudgeable`; a path it does not
  list is refused too, for naming no fact at all.
- BAD: "the change is under 120 lines" / "the numstat names 2 files" - no count key, so the register refuses
  the task as `unjudgeable` before any judge call; name the key and the value, as in the GOOD examples.
- BAD: "files_changed 3 and lines_changed 120" on a bundle of 3 files and 162 lines - the keys are right and
  the value is not: the count branch compares THIS bundle's value, and the judge is never asked about a count
  the change does not carry.
- BAD: "the response keys are shown" / "a test in agenthub_go pins the node" - each needs a file's contents.
- BAD: "a real closure is demonstrated from a seat" - a process claim, not a measurement: it belongs in the
  completion summary, not in a criterion.
- BAD: "at 375 and 320 the row actions are reachable by tap" - nothing the bundle carries shows a rendered
  page; run the browser check as the acceptance command, or record the walk in the task's details.

MEASURED, on one task's own evidence and its own command (hub task `8bd075eb`, 2026-10-16): the four
criteria as written answered .57/.42/.41/.49 -> uncertain, exit 6; the same claims re-worded into this
vocabulary answered .97/.96/.96 -> accept. Re-measured against the redacted wire (friction `e2056bf9`,
2026-10-18): criteria that name a listed path, which the register admits, answered .16-.34, and the same
claims with a sha and the totals answered .93-.97. The count keys are new (board `86e4d618`, 2026-10-18);
their band is not measured yet, so the count form is the fallback when a run has no sha to name, not the
primary form. The ruling, its measurements and the instrument that re-runs them:
`seats/architect/RULING-outcome2-proof-shape.md` (room 4genthub-min).

## Subtasks

Use subtasks for multi-step work. `progress_notes` is mandatory for update; `completion_summary`
and `progress_notes` are both mandatory for complete.

```python
subtask = mcp__agenthub_http__manage_subtask(
    action="create", task_id=parent_task_id,
    title="Design database schema", progress_notes="Starting schema design"
)

mcp__agenthub_http__manage_subtask(
    action="update", task_id=parent_task_id, subtask_id=subtask_id,
    progress_percentage=50, progress_notes="Schema designed, creating migrations"
)

mcp__agenthub_http__manage_subtask(
    action="complete", task_id=parent_task_id, subtask_id=subtask_id,
    completion_summary="Schema created with proper indexes",
    progress_notes="Final review done, all indexes verified"
)
```

**Verify every subtask is done before completing the parent task.**

## Precise context with line numbers

Reference code with `file:line`, not prose:

```python
# WRONG (vague):
details="Update the user validation logic"

# RIGHT (precise):
details="""
Update user validation logic in:
- <path>:<line>-<end> (validateEmail)
- <path>:<line>-<end> (registerUser)
- <path>:<line>-<end> (email-validation test)
Focus on lines 28-30 where the email regex changes.
"""
```

Format: `<path>:<line>` | `<path>:<line>-<end>` | `<path>:<line>-<end> (functionName)`.

## Receiving results

1. Verify completion against the objective (read the files, confirm the change).
2. Verify quality where needed.
3. Update the tracking task with a summary, or continue if more work is needed.

Never complete a parent task while any child is still pending or in progress.
