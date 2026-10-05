# Development Workflow - Complete Guide

## Quick Reference

| Workflow Pattern | Use Case | Key Tools | Execution Model |
|-----------------|----------|-----------|----------------|
| **3-Phase Professional** | Complex features with multiple agents | MCP tasks, subtasks, agent assignment | Plan → Execute (parallel) → Review |
| **cclaude (async)** | Fire-and-forget parallel execution | cclaude command | Non-blocking, terminal visibility |
| **cclaude-wait (sync)** | Single task with result capture | cclaude-wait command | Blocking, returns JSON |
| **cclaude-wait-parallel** | Multiple subtasks in parallel | cclaude-wait-parallel command | Blocking, aggregated results, WebSocket monitoring |
| **Seat resolution (call_seat)** | Load a seat's runtime/context in one session | `call_seat` | In-session, no terminals |

---

## 3-Phase Professional Workflow

### Pattern: Plan → Execute → Review

**Benefits**:
- Complete visibility before execution
- Parallel agent execution
- Quality gates before deployment
- Full audit trail

### Phase 1: Create All Tasks and Assign Agents

**Step 1: Create Parent Task**:
```python
parent_task = manage_task(
    action="create",
    git_branch_id="branch-uuid",
    title="Build JWT authentication system",
    description="End-to-end auth with JWT tokens, password hashing, middleware, testing, docs",
    assignees="@master-orchestrator-agent",
    priority="critical",
    details="""
    REQUIREMENTS:
    - JWT token generation (RS256)
    - Bcrypt password hashing (12+ salt rounds)
    - Auth middleware for route protection
    - Endpoints: /api/auth/login, /api/auth/register, /api/auth/refresh, /api/auth/logout
    - Security audit (OWASP Top 10)
    - Test suite (95%+ coverage)
    - API documentation

    ACCEPTANCE CRITERIA:
    - All endpoints functional and tested
    - Security audit passed
    - Documentation complete
    - Code reviewed
    """
)

parent_task_id = parent_task["task"]["id"]
```

**Step 2: Create Specialized Subtasks**:
```python
# Subtask 1: JWT Service
subtask_jwt = manage_subtask(
    action="create",
    task_id=parent_task_id,
    title="Implement JWT token generation service",
    description="""
    FILES: src/services/jwt.service.py
    REQUIREMENTS:
    - Token generation with RS256
    - 1-hour access token expiry
    - 7-day refresh token expiry
    - Token validation and verification
    DEPENDENCIES: None (start immediately)
    """,
    assignees="@coding-agent",
    priority="critical"
)

# Subtask 2: Password Security
subtask_password = manage_subtask(
    action="create",
    task_id=parent_task_id,
    title="Implement password hashing service",
    description="""
    FILES: src/services/password.service.py
    REQUIREMENTS:
    - Bcrypt hashing with 12+ salt rounds
    - Password validation
    - Strength checking
    DEPENDENCIES: None
    """,
    assignees="@security-auditor-agent"
)

# Subtask 3: Auth Middleware
subtask_middleware = manage_subtask(
    action="create",
    task_id=parent_task_id,
    title="Implement auth middleware",
    description="""
    FILES: src/middleware/auth.middleware.py
    REQUIREMENTS:
    - JWT validation on protected routes
    - User context extraction
    - Error handling for invalid tokens
    DEPENDENCIES: JWT Service (subtask 1)
    """,
    assignees="@coding-agent"
)

# Subtask 4: Testing
subtask_tests = manage_subtask(
    action="create",
    task_id=parent_task_id,
    title="Comprehensive test suite",
    description="""
    FILES: tests/auth/*.py
    REQUIREMENTS:
    - Unit tests for JWT service
    - Unit tests for password service
    - Integration tests for auth flow
    - 95%+ code coverage
    DEPENDENCIES: All above subtasks
    """,
    assignees="@test-orchestrator-agent"
)
```

### Phase 2: Parallel Execution

**Option A: Fire-and-Forget (cclaude)**:
```bash
# Start all agents in parallel (non-blocking)
cclaude coding-agent "subtask_id: $subtask_jwt_id, task_id: $parent_task_id"
cclaude security-auditor-agent "subtask_id: $subtask_password_id, task_id: $parent_task_id"
# Each opens separate terminal, work continues in parallel
```

**Option B: Wait for Results (cclaude-wait-parallel)**:
```bash
# Execute multiple subtasks in parallel, wait for all, get aggregated results
result=$(cclaude-wait-parallel "$parent_task_id" \
    coding-agent "$subtask_jwt_id" --custom "6) Use RS256 signing 7) Add comprehensive error handling" \
    security-auditor-agent "$subtask_password_id" --custom "6) Test password strength 7) Validate bcrypt rounds")

# Parse results
echo "$result" | jq '.subtasks[0].completion_data.completion_summary'  # JWT subtask
echo "$result" | jq '.subtasks[1].completion_data.completion_summary'  # Password subtask
```

**Option C: Token-Efficient Sequential (Seat resolution)**:
```python
# Resolve the coding seat (returns runtime + rendered context files)
call_seat(room="<room>", seat="coding-agent")
# Do the work in-session, using the returned context/runtime
manage_subtask(action="update", task_id=parent_task_id, subtask_id=subtask_jwt_id,
    progress_percentage=100, progress_notes="JWT service implemented")

# Resolve the security-auditor seat
call_seat(room="<room>", seat="security-auditor-agent")

# Resolve the orchestrator seat
call_seat(room="<room>", seat="master-orchestrator-agent")
```

### Phase 3: Review and Complete

```python
# Get all subtasks
subtasks = manage_subtask(action="list", task_id=parent_task_id)

# Verify all complete
incomplete = [st for st in subtasks["subtasks"] if st["status"] != "done"]
if incomplete:
    print(f"Incomplete subtasks: {[st['title'] for st in incomplete]}")
else:
    # Complete parent task
    manage_task(
        action="complete",
        task_id=parent_task_id,
        completion_summary="JWT auth system complete: token generation, password hashing, middleware, comprehensive tests (97% coverage), security audit passed",
        testing_notes="All unit tests passed, integration tests verified login/logout/refresh flows, security scan showed no critical issues"
    )
```

---

## Delegation Models

### Model Comparison

| Model | Token Cost | Execution | Results | Visibility | Best For |
|-------|-----------|-----------|---------|------------|----------|
| **cclaude (async)** | ~20k per agent | Non-blocking, parallel | No | ✅ Separate terminals | Fire-and-forget, parallel work |
| **cclaude-wait (sync)** | ~20k per agent | Blocking, sequential | ✅ JSON | ✅ Separate terminal | Single task + results needed |
| **cclaude-wait-parallel** | ~20k total | Blocking, parallel | ✅ Aggregated JSON | ✅ Multi-terminal + WebSocket | Multiple subtasks + all results |
| **Seat resolution (call_seat)** | n/a | In-session | ✅ Yes | ❌ Same session | Load seat context, automation |

### cclaude (Asynchronous)

**Syntax**:
```bash
cclaude <agent-name> <description or task_id> [--custom "instructions"]
```

**Examples**:
```bash
# By description
cclaude coding-agent "Fix auth bug in src/auth/login.js:45-52"

# By task ID
cclaude coding-agent "task_id: 381291d6-fa7f-4e60-80c5-0d1b86664722"

# By subtask ID
cclaude coding-agent "subtask_id: xyz-456, task_id: abc-123"

# With custom instructions
cclaude coding-agent "task_id: abc-123" --custom "Use strict TypeScript types and add JSDoc comments"
```

**Behavior**:
- Opens new terminal for agent session
- Returns immediately (non-blocking)
- No result capture
- Monitor terminals manually

### cclaude-wait (Synchronous)

**Syntax**:
```bash
cclaude-wait <agent-name> <task_id or subtask_id> [--custom "instructions"]
```

**Examples**:
```bash
# Execute and capture results
result=$(cclaude-wait coding-agent "task_id: abc-123")
echo "$result" | jq '.completion_summary'

# With custom instructions
result=$(cclaude-wait coding-agent "task_id: abc-123" --custom "6) Use TypeScript strict mode 7) Add JSDoc comments")
```

**Returns**:
```json
{
  "success": true,
  "completion_data": {
    "completion_summary": "Implemented JWT service with RS256 signing",
    "testing_notes": "Unit tests added, all passing",
    "files_modified": ["src/services/jwt.service.py"]
  },
  "execution_time": 45.2
}
```

### cclaude-wait-parallel (Parallel + Synchronous)

**Syntax**:
```bash
# Basic (same agent for all subtasks)
cclaude-wait-parallel <task_id> <agent> <subtask1> <agent> <subtask2>

# Multi-agent (different agents per subtask)
cclaude-wait-parallel <task_id> <agent1> <subtask1> <agent2> <subtask2>

# With custom instructions per agent
cclaude-wait-parallel <task_id> \
    <agent1> <subtask1> --custom "6) Instruction1 7) Instruction2" \
    <agent2> <subtask2> --custom "6) Different instruction"
```

**Examples**:
```bash
# Execute 2 subtasks in parallel, wait for both
result=$(cclaude-wait-parallel "cd482b1b-..." \
    coding-agent "40a7581e-..." --custom "6) Use TypeScript strict mode" \
    test-orchestrator-agent "f2148066-..." --custom "6) Run pytest with coverage")

# Parse results
echo "$result" | jq '.subtasks[0].completion_data.completion_summary'
echo "$result" | jq '.subtasks[1].completion_data.testing_notes'
echo "$result" | jq '.overall_status'
```

**Returns**:
```json
{
  "success": true,
  "overall_status": "completed",
  "subtasks": [
    {
      "subtask_id": "40a7581e-...",
      "agent": "coding-agent",
      "status": "done",
      "completion_data": {
        "completion_summary": "JWT service implemented with strict types",
        "files_modified": ["src/services/jwt.service.ts"]
      }
    },
    {
      "subtask_id": "f2148066-...",
      "agent": "test-orchestrator-agent",
      "status": "done",
      "completion_data": {
        "completion_summary": "Test suite complete: 98% coverage",
        "testing_notes": "All 45 tests passing"
      }
    }
  ],
  "execution_time": 67.4,
  "websocket_updates": 12
}
```

**Features**:
- Executes subtasks in parallel
- Waits for all to complete
- WebSocket monitoring for real-time progress
- Aggregated results in single JSON response

### Seat Resolution (Token Efficient)

> **Status:** the `call_agent()` MCP tool described in earlier revisions of this guide was
> **retired**. Agent registration and assignment use the `manage_agent` tool, whose
> optional `call_agent` field (the agent's `@handle`) remains live. To load a seat's
> runtime and context in-session, resolve it with the separate `call_seat` tool.

**Syntax**:
```python
call_seat(room="<room>", seat="<seat-slug>")
```

**Workflow**:
```python
# 1. Resolve the orchestrator seat
call_seat(room="<room>", seat="master-orchestrator-agent")
# Returns: runtime, permission policy, resolved snapshot hash, rendered context files

# 2. Resolve a specialist seat
call_seat(room="<room>", seat="coding-agent")
# Use the returned context/runtime to do the work in-session
manage_task(action="update", task_id="...", status="in_progress")

# 3. Resolve another specialist seat
call_seat(room="<room>", seat="test-orchestrator-agent")

# 4. Resolve the orchestrator seat again to review and complete
call_seat(room="<room>", seat="master-orchestrator-agent")
```

---

## MCP Task Creation Guide

### Required vs Optional Parameters

**manage_task create action**:
```python
# REQUIRED
git_branch_id="uuid"  # Branch context
title="Clear action-oriented title"
assignees="@agent-name"  # Minimum 1 agent

# OPTIONAL (but recommended)
description="Detailed description with acceptance criteria"
priority="low|medium|high|urgent|critical"  # Default: medium
details="Additional implementation notes"
estimated_effort="2 hours|3 days|1 week"
labels="tag1,tag2,tag3"
dependencies="uuid1,uuid2"  # Other task UUIDs
due_date="2025-12-31T23:59:59Z"  # ISO 8601
```

### Task Title Best Practices

| Good ✅ | Bad ❌ | Why |
|---------|---------|-----|
| "Implement JWT token generation service" | "Auth" | Specific, action-oriented vs vague |
| "Fix circular dependency detection in task service" | "Bug fix" | Clear scope vs ambiguous |
| "Add unit tests for password hashing module" | "Tests" | Precise target vs general |

### Task Description Template

```python
description="""
REQUIREMENTS:
- [Specific requirement 1]
- [Specific requirement 2]
- [Specific requirement 3]

FILES TO MODIFY/CREATE:
- src/path/to/file.py:45-67 (specific function)
- src/path/to/new-file.py (create new)

DEPENDENCIES:
- [Task ID or description if dependency exists]
- None (if no dependencies)

ACCEPTANCE CRITERIA:
- [Testable criterion 1]
- [Testable criterion 2]
- [Testable criterion 3]

TECHNICAL NOTES:
- [Any specific technical considerations]
- [Constraints or limitations]
"""
```

### Progress Tracking

**Subtask Updates** (progress_notes MANDATORY):
```python
# Update at 25% intervals
manage_subtask(
    action="update",
    task_id="parent-uuid",
    subtask_id="subtask-uuid",
    progress_percentage=25,
    progress_notes="JWT signing key generated, token structure designed"
)

# Update at 50%
manage_subtask(
    action="update",
    task_id="parent-uuid",
    subtask_id="subtask-uuid",
    progress_percentage=50,
    progress_notes="Token generation implemented, working on validation logic"
)

# Complete at 100%
manage_subtask(
    action="complete",
    task_id="parent-uuid",
    subtask_id="subtask-uuid",
    completion_summary="JWT service complete with generation, validation, refresh logic",
    progress_notes="Final testing complete, all edge cases handled"
)
```

---

## Workflow Decision Tree

```
User Request
    │
    ▼
Is it complex (>3 steps)?
    │
    ├─ NO → Seat resolution (call_seat)
    │
    └─ YES → Need parallel execution?
            │
            ├─ NO → cclaude-wait (sequential + results)
            │
            └─ YES → Need results?
                    │
                    ├─ NO → cclaude (fire-and-forget)
                    │
                    └─ YES → cclaude-wait-parallel (parallel + all results)
```

### When to Use Each Model

**Use seat resolution (`call_seat`) when**:
- Token efficiency is priority
- Work is sequential (no parallelization needed)
- Production automation
- Simple workflows

**Use cclaude (async) when**:
- Multiple independent tasks
- Don't need results immediately
- Want terminal visibility
- Fire-and-forget acceptable

**Use cclaude-wait (sync) when**:
- Single task execution
- Need results for next step
- Terminal visibility + result capture
- Sequential dependencies

**Use cclaude-wait-parallel when**:
- Multiple subtasks that can run in parallel
- Need all results aggregated
- Real-time progress monitoring via WebSocket
- Complex multi-agent coordination

---

## Common Patterns

### Pattern: Task Decomposition

**Complex Feature** → Parent Task + Specialized Subtasks:
```
Parent: "Build JWT Authentication System"
├─ Subtask 1: "Implement JWT token service" (@coding-agent)
├─ Subtask 2: "Implement password hashing" (@security-auditor-agent)
├─ Subtask 3: "Create auth middleware" (@coding-agent)
├─ Subtask 4: "Write comprehensive tests" (@test-orchestrator-agent)
└─ Subtask 5: "Document API endpoints" (@documentation-agent)
```

### Pattern: Dependency Chain

**Sequential Dependencies**:
```python
# Create tasks with dependencies
task1 = manage_task(action="create", title="Design database schema", ...)
task2 = manage_task(action="create", title="Implement ORM models",
    dependencies=task1["task"]["id"], ...)
task3 = manage_task(action="create", title="Create repositories",
    dependencies=task2["task"]["id"], ...)
```

### Pattern: Parallel + Review

**Parallel Work with Quality Gate**:
```
Phase 1: Create structure (orchestrator)
Phase 2: Parallel execution (coding-agent, test-agent, security-agent)
Phase 3: Code review (code-reviewer-agent) - BLOCKS completion
Phase 4: Complete (orchestrator)
```

---

## Related Documentation
- [DDD Architecture Complete](./ddd-architecture-complete.md)
- [MCP Tools API Complete](../api-integration/mcp-tools-api-complete.md)
- [Complete Setup Guide](../setup-guides/complete-setup-guide.md)
