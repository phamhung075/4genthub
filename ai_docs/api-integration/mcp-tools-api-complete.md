# MCP Tools API - Complete Reference

## Quick Reference

| Tool | Primary Actions | Key Parameters | Use Case |
|------|----------------|----------------|----------|
| **manage_task** | create, update, complete, next | git_branch_id, title, assignees (required for create) | Task lifecycle management |
| **manage_subtask** | create, update, complete | task_id, progress_percentage, progress_notes | Hierarchical task decomposition |
| **manage_project** | create, list, project_health_check | name | Project coordination |
| **manage_git_branch** | create, assign_agent, get_statistics | project_id, git_branch_name | Branch operations |
| **manage_context** | create, get, resolve, delegate | level, context_id | Context records at four levels (global \| project \| branch \| task) |
| **manage_agent** | register, assign, get, list, update, unassign, unregister, rebalance | project_id, name, call_agent (field) | Agent registry orchestration |
| **manage_seat** | list, get, set_occupant | room, seat, runtime, model | Seat management (switch a seat's occupant) |
| **call_seat** | N/A (single action) | room, seat | Resolve one exact seat and its rendered context files |
| **submit_feedback** | N/A (single action) | room, seat, session, layer, text | Report friction from a seat: the layer it is in, the room and seat, and what happened |
| **manage_connection** | N/A (health check) | include_details | System health monitoring |

**Common Pattern**: All tools require `action` parameter except `call_seat`, `submit_feedback` and `manage_connection`.

The live registry publishes **ten** tools, the ten rows above. `manage_context` is published when the context controller is wired, which it is on a database-backed server. `manage_seat`, `call_seat`, `submit_feedback` and `manage_connection` are appended to the `tools/list` registry by `App.MCPToolsList` (`mcp_routes.go:275`; the four appends at `:301`, `:310`, `:319`, `:328`) rather than carried in `ToolDefinitions()`; `tools/list` is not gated by any `TOOL_*` environment variable. **RE-RESOLVED 2026-10-09 at HEAD `36716e6e`: the builder was renamed — `getMCPToolsList` resolves nowhere in `agenthub_go`, its one-line alias having been deleted — and the five registry tests pass (`ok agenthub/fastmcp/server/httpapp 0.024s`), so the ten names above are unchanged.** **Measured at HEAD `763b8196` (2026-10-06): a booted server answers `tools/list` with exactly these ten names.** **RE-MEASURED 2026-10-08 at HEAD `88d27758`: the same TEN names are what a connected client receives — verified live from the client side (the ten routes this seat's own session exposes) rather than from the registry alone, and the set is unchanged since `763b8196`.**

---

## Task Management Tools

### manage_task

**Purpose**: Complete task lifecycle with Vision System integration

**Required Parameters by Action**:

| Action | Required Parameters |
|--------|-------------------|
| create | git_branch_id, title, assignees (min 1) |
| update | task_id |
| get | task_id |
| delete | task_id |
| complete | task_id, completion_summary |
| list | git_branch_id |
| search | query |
| next | git_branch_id |
| add_dependency | task_id, dependency_id |
| remove_dependency | task_id, dependency_id |

**Key Parameters** (30+ total):

| Parameter | Type | Description | Validation |
|-----------|------|-------------|------------|
| title | string | Action-oriented task name | Required for create |
| description | string | Detailed task description | Max 2000 chars |
| status | string | todo \| in_progress \| blocked \| review \| testing \| done \| cancelled | Auto-set on create/complete |
| priority | string | low \| medium \| high \| urgent \| critical | Default: medium |
| assignees | string\|array | @agent-name format, comma-separated | Min 1 for create |
| labels | string\|array | Categories/tags | Optional |
| estimated_effort | string | "2 hours", "3 days", "1 week" | Human-readable |
| dependencies | string\|array | Task IDs (comma-separated) | UUIDs |
| completion_summary | string | Detailed work summary | Required for complete |
| testing_notes | string | Testing performed | Optional for complete |

**Examples**:
```python
# Create task
manage_task(
    action="create",
    git_branch_id="branch-uuid",
    title="Implement JWT authentication",
    description="Add token-based auth with refresh",
    priority="high",
    assignees="@coding-agent",
    estimated_effort="3 days"
)

# Update status
manage_task(
    action="update",
    task_id="task-uuid",
    status="in_progress",
    details="Started implementation of token generation"
)

# Complete task
manage_task(
    action="complete",
    task_id="task-uuid",
    completion_summary="JWT auth implemented with 1-hour access tokens, 7-day refresh tokens",
    testing_notes="Unit tests for token service, integration tests for login flow"
)

# Get next priority task (with AI guidance)
manage_task(
    action="next",
    git_branch_id="branch-uuid",
    include_context=true  # Returns workflow_guidance with recommended_agent, next_actions, hints
)
```

**Response Format**:
```json
{
  "success": true,
  "task": {
    "id": "task-uuid",
    "title": "Implement JWT authentication",
    "status": "in_progress",
    "priority": "high",
    "progress_percentage": 50,
    "assignees": ["@coding-agent"],
    "dependencies": [],
    "subtasks": [],
    "created_at": "2025-11-09T12:00:00Z"
  },
  "workflow_guidance": {
    "recommended_agent": "coding-agent",
    "next_actions": ["Implement token generation", "Add refresh logic"],
    "hints": ["Use existing crypto utilities", "Consider token expiry edge cases"]
  }
}
```

---

### manage_subtask

**Purpose**: Hierarchical task decomposition with automatic parent updates

**Required Parameters by Action**:

| Action | Required Parameters |
|--------|-------------------|
| create | task_id, title |
| update | task_id, subtask_id, progress_notes (MANDATORY) |
| get | task_id, subtask_id |
| list | task_id |
| delete | task_id, subtask_id |
| complete | task_id, subtask_id, completion_summary, progress_notes (MANDATORY) |

**Key Parameters**:

| Parameter | Type | Description | Validation |
|-----------|------|-------------|------------|
| task_id | string | Parent task UUID | Always required |
| subtask_id | string | Subtask UUID | Required for update/delete/get/complete |
| title | string | Subtask title | Required for create |
| description | string | Detailed subtask description | Optional |
| progress_percentage | integer | 0-100 completion | Auto-maps to status (0=todo, 1-99=in_progress, 100=done) |
| progress_notes | string | Brief work status | MANDATORY for update/complete (min 10 chars) |
| completion_summary | string | Detailed accomplishment summary | MANDATORY for complete |
| assignees | string\|array | Agent identifiers | Inherits from parent if not specified |
| blockers | string | Issues preventing progress | Comma-separated or JSON array |
| insights_found | string | Discoveries during work | Comma-separated or JSON array |

**Auto Features**:
- Progress history tracking (timestamped entries)
- Agent inheritance from parent
- Parent progress recalculation
- Status mapping (progress_percentage → status)
- Blocker escalation
- Insight propagation

**Examples**:
```python
# Create subtask
manage_subtask(
    action="create",
    task_id="task-uuid",
    title="Design JWT token structure",
    description="Define claims, expiry, signing algorithm"
)

# Update progress (progress_notes MANDATORY)
manage_subtask(
    action="update",
    task_id="task-uuid",
    subtask_id="subtask-uuid",
    progress_percentage=75,
    progress_notes="Token structure designed, working on validation logic"
)

# Complete subtask (both MANDATORY)
manage_subtask(
    action="complete",
    task_id="task-uuid",
    subtask_id="subtask-uuid",
    completion_summary="JWT structure complete: access (1hr expiry), refresh (7 days), user_id + roles claims",
    progress_notes="Final review completed, structure documented",
    insights_found="Found existing crypto utility for signing, Redis integration needed for token blacklist"
)
```

**Response**: Auto-updates parent task progress_percentage based on completed subtasks

---

## Project & Branch Management

### manage_project

**Purpose**: Project lifecycle and multi-project orchestration

**Actions**: create, get, list, update, delete, project_health_check, cleanup_obsolete, validate_integrity, rebalance_agents

**Key Parameters**:

| Parameter | Type | Description |
|-----------|------|-------------|
| project_id | string | Project UUID (required for most actions except create/list) |
| name | string | Project name (required for create, can substitute project_id for get) |
| description | string | Project description |
| force | boolean | Bypass safety checks for delete/maintenance (default: false) |

**Examples**:
```python
# Create project
manage_project(action="create", name="authentication-system", description="JWT-based auth")

# Health check
manage_project(action="project_health_check", project_id="project-uuid")

# Cleanup obsolete data
manage_project(action="cleanup_obsolete", project_id="project-uuid", force=true)
```

**Response**: Includes orchestration status, branch_count, task_count, health metrics

---

### manage_git_branch

**Purpose**: Branch operations and task tree management

**Actions**: create, get, list, update, delete, assign_agent, unassign_agent, get_statistics, archive, restore

**Key Parameters**:

| Parameter | Type | Description |
|-----------|------|-------------|
| project_id | string | Project UUID (REQUIRED for all actions) |
| git_branch_id | string | Branch UUID (required for most except create/list) |
| git_branch_name | string | Branch name (required for create) |
| git_branch_description | string | Branch description |
| agent_id | string | Agent UUID (required for assign/unassign) |

**Examples**:
```python
# Create branch
manage_git_branch(
    action="create",
    project_id="project-uuid",
    git_branch_name="feature/jwt-auth",
    git_branch_description="JWT authentication implementation"
)

# Assign agent
manage_git_branch(
    action="assign_agent",
    git_branch_id="branch-uuid",
    agent_id="agent-uuid"
)

# Get statistics
manage_git_branch(action="get_statistics", git_branch_id="branch-uuid")
# Returns: total_tasks, completed_tasks, progress_percentage
```

---

## Context Management

### manage_context

**Purpose**: Context records at four levels behind the mounted `/api/v2/contexts/{level}` routes (`global`, `project`, `branch`, `task`)

**Actions**: create, get, update, delete, resolve, delegate, add_insight, add_progress, list

**Context levels** (the `{level}` path segment):

| Level | Context ID | Inheritance | Use Case |
|-------|-----------|-------------|----------|
| **global** | user_id | N/A (top level) | User-scoped settings |
| **project** | project_id | Inherits from global | Project-wide config |
| **branch** | git_branch_id | Inherits from project | Branch-specific context |
| **task** | task_id | Inherits from branch | Task-level data |

**Key Parameters**:

| Parameter | Type | Description |
|-----------|------|-------------|
| action | string | Context operation |
| level | string | global \| project \| branch \| task (REQUIRED except for list) |
| context_id | string | ID appropriate for level (REQUIRED except for list) |
| data | string | Context data as JSON string |
| include_inherited | string | Include parent data ("true"/"false"/"1"/"0") |
| force_refresh | string | Bypass cache ("true"/"false") |
| delegate_to | string | Target level for delegation (required for delegate action) |
| content | string | Content for add_insight/add_progress |

**Examples**:
```python
# Create task context
manage_context(
    action="create",
    level="task",
    context_id="task-uuid",
    data='{"custom_field": "value"}'
)

# Resolve with full inheritance chain
manage_context(
    action="resolve",
    level="task",
    context_id="task-uuid",
    include_inherited="true"
)
# Returns: task data + branch data + project data + global data (merged)

# Delegate context to different level
manage_context(
    action="delegate",
    level="task",
    context_id="task-uuid",
    delegate_to="branch",
    delegation_reason="Promoting task-specific config to branch level"
)

# Add insight
manage_context(
    action="add_insight",
    level="task",
    context_id="task-uuid",
    content="Found performance bottleneck in query",
    category="performance",  # technical|business|performance|risk|discovery
    importance="high"
)
```

**Features**:
- One API across the four context levels
- Auto-inheritance from parent levels on resolve
- Smart caching with TTL
- Change propagation (cascading updates)
- Delegation queue for moving context between levels

---

## Agent Orchestration

### manage_agent

**Purpose**: Agent registration and assignment

**Actions**: register, assign, get, list, update, unassign, unregister, rebalance

**Key Parameters**:

| Parameter | Type | Description |
|-----------|------|-------------|
| project_id | string | Project UUID (REQUIRED for all actions) |
| name | string | Agent name (required for register) |
| agent_id | string | Agent UUID (required for most except register/list/rebalance) |
| git_branch_id | string | Branch UUID (required for assign/unassign) |

**Examples**:
```python
# Register agent
manage_agent(
    action="register",
    project_id="project-uuid",
    name="coding-agent",
    description="Primary coding agent"
)
# Returns: agent_id (auto-generated if not provided)

# Assign to branch
manage_agent(
    action="assign",
    git_branch_id="branch-uuid",
    agent_id="agent-uuid"
)

# List all agents
manage_agent(action="list", project_id="project-uuid")

# Rebalance workload
manage_agent(action="rebalance", project_id="project-uuid")
```

---

### manage_seat

**Purpose**: Seat management over the seat model: list seats, get one seat, or switch the occupant (runtime + model) of a seat

**Actions**: list, get, set_occupant

**Key Parameters**:

| Parameter | Type | Description |
|-----------|------|-------------|
| action | string | `list` \| `get` \| `set_occupant` (REQUIRED) |
| room | string | Room slug (optional for list, REQUIRED for get/set_occupant) |
| seat | string | Seat key (REQUIRED for get/set_occupant) |
| runtime | string | `claude-code`, `codex`, `agy` or `omp` (REQUIRED for set_occupant) |
| model | string | Model id; empty uses the runtime default (optional for set_occupant) |

**Examples**:
```python
# List seats in a room
manage_seat(action="list", room="4genthub-dev")

# Get one seat
manage_seat(action="get", room="4genthub-dev", seat="lead")

# Switch the occupant of a seat
manage_seat(action="set_occupant", room="4genthub-dev", seat="lead",
            runtime="omp", model="deepseek/deepseek-flash")
```

**Response**: `{"success": true, "seats": [...]}` for list, `{"success": true, "seat": {...}}` for get/set_occupant; failures are `{"success": false, "error": "..."}`.

Go-only tool, appended to `tools/list` by `ManageSeatInputSchema()` (`fastmcp/seat_management/interface/mcp_controllers/manage_seat_controller.go`; appended at `fastmcp/server/httpapp/mcp_routes.go:301`, the `ManageSeatToolName` entry at `:302`).

---

### call_seat

**Purpose**: Resolve one exact seat by room and seat key. Returns the seat's runtime, permission policy, resolved snapshot hash and its rendered context files. When the hash is new, the call writes a `resolved_seats` row.

**Parameters**:

| Parameter | Type | Description |
|-----------|------|-------------|
| room | string | Room slug (REQUIRED) |
| seat | string | Seat key (REQUIRED) |

**Example**:
```python
call_seat(room="4genthub-dev", seat="lead")
```

**Response**: `{"success": true, "room": ..., "seat": ..., "hash": ..., "runtime": ..., "policy": ..., "files": [{"path": ..., "content": ...}]}`; failures are `{"success": false, "error": "..."}`.

Go-only tool, appended to `tools/list` by `CallSeatInputSchema()` (`fastmcp/seat_management/interface/mcp_controllers/call_seat_controller.go`; appended at `fastmcp/server/httpapp/mcp_routes.go:310`, the `CallSeatToolName` entry at `:311`).

---

### call_agent — retired

The `call_agent` **tool** ("load agent instructions") no longer exists: it was removed together with the Python agent library (`agenthub_main/agent-library`), which is retired. It is gone from `tools/list`, from `tools_golden.json` and from the tests, and calling it now returns `{"error":"Unknown tool: call_agent"}` from `dispatchMCPTool`. `call_agent` survives only as an optional **field/parameter of the `manage_agent` tool** (register/update) — that field is live and deliberate, and is not a tool.

---

## System Operations

### manage_connection

**Purpose**: Health monitoring and diagnostics

**Parameters**:

| Parameter | Type | Description |
|-----------|------|-------------|
| include_details | boolean | Include detailed health info (default: true) |
| user_id | string | User identifier (optional) |

**Examples**:
```python
# Basic health check
manage_connection()

# Detailed health check
manage_connection(include_details=true)
```

**Response**:
```json
{
  "status": "healthy",
  "timestamp": "2025-11-09T12:00:00Z",
  "details": {
    "database": "connected",
    "cache": "operational",
    "version": "1.0.0"
  }
}
```

---

## Common Patterns

### Parameter Type Handling

**Boolean Parameters**: Accept "true", "1", "yes", "on" (case-insensitive)
```python
include_context="true"  # ✅
include_context="1"     # ✅
include_context=true    # ✅
```

**Array Parameters**: Accept JSON string, comma-separated, or native array
```python
assignees="@agent1,@agent2"           # ✅ Comma-separated
assignees='["@agent1", "@agent2"]'    # ✅ JSON string
assignees=["@agent1", "@agent2"]      # ✅ Native array
```

**JSON Parameters**: Auto-parsed from strings
```python
data='{"key": "value"}'  # ✅ Parsed automatically
```

### Error Handling

All tools return consistent error format:
```json
{
  "success": false,
  "error": {
    "message": "Specific error description",
    "code": "ERROR_CODE",
    "operation": "action_name",
    "timestamp": "2025-11-09T12:00:00Z"
  }
}
```

### Validation Rules

**Two-Stage Validation**:
1. Schema validation (action parameter only at tool level)
2. Business logic validation (action-specific required parameters)

**Common Errors**:
- Missing required fields → Specific error with field name
- Invalid UUID → Clear error with example format
- Unknown action → List of valid actions
- Duplicate data → Rejection with existing record details

---

## Advanced Features

### Vision System Integration (manage_task)

**Automatic AI Enrichment**:
- Recommended agent selection
- Next action suggestions
- Implementation hints
- Complexity analysis
- Risk identification

**Enable**: Set `include_context=true` on get/next actions

### Progress Tracking (manage_subtask)

**Automatic Features**:
- Timestamped progress history
- Parent task progress recalculation
- Status auto-mapping from progress_percentage
- Blocker escalation to parent

**Requirement**: `progress_notes` MANDATORY for update/complete (min 10 chars)

### Context Inheritance (manage_context)

**Inheritance Chain** (what `resolve` folds): Task → Branch → Project → Global

**Resolution**: Set `include_inherited=true` to get merged data from all parent levels

**Delegation**: Move context data between levels with `delegate` action

---

## Related Documentation
- [Go server surface inventory (authoritative)](./surface-inventory.md)
- [Complete Setup Guide](../setup-guides/complete-setup-guide.md)
- [Complete Authentication Guide](../authentication/complete-authentication-guide.md)
