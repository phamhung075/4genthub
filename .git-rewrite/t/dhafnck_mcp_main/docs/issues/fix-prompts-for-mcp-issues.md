# Fix Prompts for MCP Tool Issues
**Date**: 2025-08-21
**Purpose**: Individual prompts to fix each identified issue in dhafnck_mcp_http tools

---

## Issue 1: Git Branch Management Authentication

### Prompt for New Chat:
```
Fix the git branch management authentication issue in dhafnck_mcp_http server.

**Error**: "Project repository creation requires user authentication. No user ID was provided."

**Affected Tool**: mcp__dhafnck_mcp_http__manage_git_branch
**Actions Failing**: create, list, update, assign_agent

**Current Behavior**: 
All git branch operations fail with authentication error even though other operations (project, task) work without user authentication.

**Expected Behavior**: 
Git branch operations should work through MCP without requiring explicit user authentication, similar to how project and task operations currently work.

**Test Case to Verify Fix**:
```python
# This should work after fix:
mcp__dhafnck_mcp_http__manage_git_branch(
    action="create",
    project_id="valid-project-id",
    git_branch_name="feature/test",
    git_branch_description="Test branch"
)
```

**Files to Check**:
- Git branch application facade
- Authentication middleware for MCP operations
- User context resolution in MCP server

Please implement a fix that allows git branch operations through MCP without requiring explicit user authentication.
```

---

## Issue 2: Task Get Operation TypeError

### Prompt for New Chat:
```
Fix the TypeError in task get operation for dhafnck_mcp_http server.

**Error**: "The task retrieval could not be completed." with "error_type": "TypeError"

**Affected Tool**: mcp__dhafnck_mcp_http__manage_task
**Action Failing**: get

**Current Behavior**:
When calling manage_task with action="get" and a valid task_id, the operation fails with a TypeError.

**Test That Fails**:
```python
mcp__dhafnck_mcp_http__manage_task(
    action="get",
    task_id="56239d42-94e9-4ba6-9dc5-644181b7e44a"
)
```

**Expected Behavior**:
Should return the task details successfully, similar to how the list action works.

**Working Example for Reference**:
The list action works correctly:
```python
mcp__dhafnck_mcp_http__manage_task(
    action="list",
    git_branch_id="e74330da-d1d9-49c2-91e1-d91c53ee74bb"
)
```

**Likely Issues**:
- Missing or incorrect parameter handling in get action
- Type conversion issue with task_id parameter
- Missing include_context parameter handling

Please debug and fix the TypeError in the task get operation.
```

---

## Issue 3: Subtask Creation Authentication

### Prompt for New Chat:
```
Fix the subtask creation authentication requirement in dhafnck_mcp_http server.

**Error**: "Subtask context derivation requires user authentication. No user ID was provided."

**Affected Tool**: mcp__dhafnck_mcp_http__manage_subtask
**Action Failing**: create

**Current Behavior**:
Subtask creation fails requiring user authentication, while parent task creation works without it.

**Test That Fails**:
```python
mcp__dhafnck_mcp_http__manage_subtask(
    action="create",
    task_id="56239d42-94e9-4ba6-9dc5-644181b7e44a",
    title="Write failing tests",
    description="TDD red phase"
)
```

**Expected Behavior**:
Subtask creation should work without explicit user authentication, inheriting context from parent task.

**Context**:
- Parent task creation works fine
- This seems to be related to context derivation for subtasks
- The error mentions "context derivation" specifically

Please modify the subtask creation to work without requiring explicit user authentication, similar to task creation.
```

---

## Issue 4: Task Completion Database Schema

### Prompt for New Chat:
```
Fix the database schema issue preventing task completion in dhafnck_mcp_http.

**Error**: "column task_contexts.user_id does not exist"

**SQL Error**:
```sql
psycopg2.errors.UndefinedColumn: column task_contexts.user_id does not exist
```

**Affected Tool**: mcp__dhafnck_mcp_http__manage_task
**Action Failing**: complete

**Current Behavior**:
Task completion fails because the ORM expects a user_id column in task_contexts table that doesn't exist in the database.

**Test That Fails**:
```python
mcp__dhafnck_mcp_http__manage_task(
    action="complete",
    task_id="56239d42-94e9-4ba6-9dc5-644181b7e44a",
    completion_summary="Task completed successfully",
    testing_notes="All tests passing"
)
```

**Required Fix**:
Either:
1. Add user_id column to task_contexts table (migration needed)
2. Make user_id optional in the ORM model
3. Remove user_id from the query

**Database Table**: task_contexts
**ORM Model Location**: Check SQLAlchemy models for TaskContext

Please fix this schema mismatch to allow task completion through MCP.
```

---

## Issue 5: Branch Context Creation Schema

### Prompt for New Chat:
```
Fix the database schema issue preventing branch context creation in dhafnck_mcp_http.

**Error**: "column branch_contexts.user_id does not exist"

**SQL Error**:
```sql
psycopg2.errors.UndefinedColumn: column branch_contexts.user_id does not exist
```

**Affected Tool**: mcp__dhafnck_mcp_http__manage_context
**Action Failing**: create (for branch level)

**Current Behavior**:
Branch context creation fails because the ORM expects a user_id column in branch_contexts table.

**Test That Fails**:
```python
mcp__dhafnck_mcp_http__manage_context(
    action="create",
    level="branch",
    context_id="e74330da-d1d9-49c2-91e1-d91c53ee74bb",
    project_id="9b2f301c-1dd4-48bd-afd9-e49052ec6cb2",
    data={
        "branch_name": "main",
        "branch_purpose": "Main development branch"
    }
)
```

**Working Operations**:
- Global context get ✅
- Project context get/update ✅

**Database Table**: branch_contexts
**Related Tables Working**: global_contexts, project_contexts

Please fix the schema mismatch for branch_contexts table to match the working context tables.
```

---

## Master Fix Prompt (All Issues)

### Prompt for Comprehensive Fix:
```
Fix all authentication and database schema issues in dhafnck_mcp_http MCP server.

**Critical Issues Found**:

1. **Git Branch Management** - Requires user authentication (shouldn't need it)
2. **Task Get Operation** - TypeError when retrieving task
3. **Subtask Creation** - Requires user authentication (shouldn't need it) 
4. **Task Completion** - Missing user_id column in task_contexts table
5. **Branch Context Creation** - Missing user_id column in branch_contexts table

**Pattern Observed**:
- Authentication issues: Operations requiring user_id when MCP operations should work without explicit authentication
- Schema issues: user_id columns missing from task_contexts and branch_contexts tables

**Suggested Solution Approach**:
1. Implement MCP service account or bypass authentication for MCP operations
2. Add migration to add user_id columns to affected tables OR make them optional
3. Fix the TypeError in task get operation
4. Ensure consistency across all MCP operations

**Test Coverage Needed**:
- All CRUD operations for: projects, git_branches, tasks, subtasks, contexts
- Operations should work without explicit user authentication through MCP

Please implement a comprehensive fix addressing all these issues systematically.
```

---

**Usage Instructions**:
1. Copy the relevant prompt for the specific issue you want to fix
2. Start a new chat with the AI agent
3. Paste the prompt
4. The AI will analyze and fix the specific issue
5. Test the fix using the provided test cases
6. Move to the next issue if needed

**Priority Order**:
1. Fix database schema issues (Issues 4 & 5) - CRITICAL
2. Fix authentication requirements (Issues 1 & 3) - HIGH
3. Fix task get operation (Issue 2) - MEDIUM