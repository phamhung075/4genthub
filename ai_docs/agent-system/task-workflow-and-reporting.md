# Task workflow and reporting

> This is guidance for the agenthub
> **MCP task surface** (`manage_task` / `manage_subtask`). A seat in a rig moves its own work
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

### Tier 3 — complex: RETIRED

The earlier Tier 3 spawned a sub-agent team (`TeamCreate`, `subagent_type`) and injected each
member's config with the "Proxy Pattern". That mechanism is retired: the `.claude/agents/` library
is gone and 4genteam seats replace sub-agent teams. Complex work is split across seats and routed
through `4genteam room queue`; see the seat model in
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
    Files: src/auth/login.js:23-45 (handleLogin), src/models/User.py:15-30 (validate)
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

`4genteam complete` runs a gate whose judge is shown the EVIDENCE and the criteria text, and nothing else:
the acceptance command line, its exit code, the failing test names, the `git diff --numstat` paths and line
counts, and the base and head SHAs. There is no field for a file's contents and none for a command's output
- that is the payload's own rule and it is pinned (`agenthub_client/internal/clientevidence/evidence.go`;
`evidence_test.go`'s `assertKeys` fails on an extra field) - and the client's request shape is pinned too
(`agenthub_client/internal/clientjev/jev_test.go`, `TestTheCriteriaRequestCarriesTheEvidenceAndNothingElse`).
So a criterion that asks for content can only be answered low: the wording is the instrument, not the
evidence.

A criterion is well-formed when (i) it names the acceptance command it is settled by, (ii) that command is
NARROW enough that the command line itself names what it proves, and (iii) everything else it asserts is a
path, a line count or a sha.

- GOOD: "the acceptance command `cargo test --test seat_guard a_seat_cannot_raise_its_own_budget` exits 0
  and the numstat names rust/agenthub-runtime/tests/seat_guard.rs"
- GOOD: "the change is measured from base 99cdc0ef to head 0c53c313, `go test -count=1 ./fastmcp/...` exits
  0, and the numstat names agenthub_go/fastmcp/types/entities.go and
  agenthub_go/fastmcp/types/converters.go"
- GOOD: "the acceptance command exits 0 and the numstat names exactly one path under CHANGELOG/"
- BAD: "the response keys are shown" / "a test in agenthub_go pins the node" - each needs a file's contents.
- BAD: "a real closure is demonstrated from a seat" - a process claim, not a measurement: it belongs in the
  completion summary, not in a criterion.

MEASURED, on one task's own evidence and its own command (hub task `8bd075eb`, 2026-10-16): the four
criteria as written answered .57/.42/.41/.49 -> uncertain, exit 6; the same claims re-worded into this
vocabulary answered .97/.96/.96 -> accept. A criterion naming a path the numstat does not carry is a
criterion the judge can only answer low. The ruling, its measurements and the instrument that re-runs them:
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
- src/models/User.js:23-35 (validateEmail)
- src/controllers/auth.js:67-89 (registerUser)
- tests/auth.test.js:12-25 (email-validation test)
Focus on lines 28-30 where the email regex changes.
"""
```

Format: `file.js:23` | `file.js:23-35` | `file.js:23-35 (functionName)`.

## Receiving results

1. Verify completion against the objective (read the files, confirm the change).
2. Verify quality where needed.
3. Update the tracking task with a summary, or continue if more work is needed.

Never complete a parent task while any child is still pending or in progress.
