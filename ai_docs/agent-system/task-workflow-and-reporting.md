# Task workflow and reporting

> Moved out of the root `AGENTS.md` on 2026-10-05 (see
> [`agents-md-migration-map.md`](./agents-md-migration-map.md)). This is guidance for the agenthub
> **MCP task surface** (`manage_task` / `manage_subtask`). A seat in a rig moves its own work
> through the queue (`rig queue`), not through MCP tasks; the MCP surface is the product the user
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
is gone and OpenRig seats replace sub-agent teams. Complex work is split across seats and routed
through `rig queue`; see the seat model in
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
