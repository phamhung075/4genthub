# Fix Prompts for MCP Tools Issues - 2025-08-24

## Critical Issue: Task Data Persistence Problem

### Prompt for Fix
```
CRITICAL: Tasks are being created successfully with valid UUIDs but cannot be retrieved afterward. 

Evidence:
- Created 7 tasks across 2 branches
- All creation responses showed success with valid task IDs
- manage_task(action="list") returns 0 tasks for all branches
- Project statistics show task_count: 0 for all branches
- Subtasks remain accessible even though parent tasks cannot be retrieved

Debug and fix the task persistence/retrieval issue:
1. Check if tasks are being committed to database properly
2. Verify the git_branch_id is being stored and queried correctly
3. Check if there's a visibility/permission filter preventing retrieval
4. Ensure database transactions are being committed
5. Check if tasks are being created in wrong schema or context

Files to investigate:
- TaskRepository.create() - check commit logic
- TaskRepository.list() - check filter/query logic
- TaskApplicationFacade - check transaction handling
- Database models - verify git_branch_id field mapping

Add detailed logging:
- Log task creation with all fields
- Log database commit status
- Log retrieval queries with filters
- Log raw database results before filtering
```

---

## Issue 1: Improve Context Creation Error Messages

### Prompt for Fix
```
Please improve the error handling in the manage_context tool when a context already exists. Instead of returning an error, return an informative status that indicates the context was auto-created and provide guidance on next steps.

Current behavior:
- Returns error: "Project context already exists"

Desired behavior:
- Return status: "info" or "success" 
- Message: "Project context already exists (auto-created)"
- Include the existing context_id
- Add hint: "Use 'get' or 'update' actions to work with existing context"

Files to modify:
- Context management facade or service
- Error handling for duplicate context creation
```

---

## Issue 2: Document Required Parameters for Context Management

### Prompt for Fix
```
Please update the documentation for the manage_context tool to clearly specify required parameters for each hierarchy level.

Add a section called "Required Parameters by Level" with:
- Global: context_id="global_singleton"  
- Project: context_id=project_id
- Branch: context_id=branch_id, project_id=required
- Task: context_id=task_id, git_branch_id=required

Also add examples for each level showing the correct parameter usage.

Files to update:
- manage_context tool documentation
- API documentation
- README or user guide
```

---

## Issue 3: Enhance UUID Validation Error Messages

### Prompt for Fix
```
Please improve the UUID validation error message in the manage_agent tool to be more helpful.

Current message:
"Agent ID 'test-agent-1-id' is not a valid UUID"

Improved message should include:
- UUID format example: "xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx"
- Auto-generated suggestion that can be copied
- Example of a valid UUID

Files to modify:
- Agent management validation
- UUID validation utility
```

---

## Issue 4: Add Parameter Validation Hints

### Prompt for Fix
```
Please add validation hints to the workflow_guidance response when required parameters are missing.

For each action that fails due to missing parameters:
1. List the missing required parameters
2. Provide examples of valid values
3. Show where to get these values (e.g., "Get project_id from manage_project(action='list')")

This should be added to the workflow_guidance.warnings or a new field like parameter_errors.

Files to modify:
- Workflow guidance generator
- Parameter validation logic
```

---

## Issue 5: Improve Task Completion Error Message

### Prompt for Fix
```
The error message when trying to complete a task with incomplete subtasks is correct but could be more helpful.

Current: "Cannot complete task: 3 of 4 subtasks are incomplete"

Enhance to include:
- List of specific incomplete subtask IDs and titles
- Suggestion: "Complete all subtasks first or remove unnecessary subtasks"
- Option to force complete with a warning (if business logic allows)

Files to modify:
- Task completion validation
- Subtask checking logic
```

---

## Issue 6: Add Context Auto-Creation Documentation

### Prompt for Fix
```
Document the auto-creation behavior for contexts at each level.

Create a new section in documentation explaining:
1. Which contexts are auto-created:
   - Project context (on project creation)
   - Branch context (on branch creation)
   - Task context (NOT auto-created currently)

2. When they are created
3. What default data they contain
4. How to modify auto-created contexts

Files to create/update:
- Context management documentation
- Architecture documentation about auto-creation patterns
```

---

## Issue 7: Create Comprehensive MCP Tools Testing Suite

### Prompt for Fix
```
Create an automated test suite that covers all the scenarios tested manually today:

Test categories needed:
1. Project Management Tests
   - Create, get, list, update, health_check
   - Context auto-creation validation

2. Git Branch Management Tests
   - Create, get, list, update, assign_agent
   - Context auto-creation validation

3. Task Management Tests
   - CRUD operations
   - Dependency management
   - Status transitions
   - Next task logic

4. Subtask Management Tests
   - CRUD operations
   - Progress tracking
   - Parent task progress calculation
   - Completion validation

5. Context Hierarchy Tests
   - Inheritance chain validation
   - Level-specific operations
   - Auto-creation behavior

Files to create:
- tests/integration/test_mcp_tools_comprehensive.py
- tests/fixtures/mcp_test_data.py
```

---

## Issue 8: Add MCP Tools Health Dashboard

### Prompt for Fix
```
Create a health dashboard endpoint that shows the status of all MCP tools in one place:

Should include:
- Number of projects, branches, tasks, subtasks
- Context hierarchy health
- Recent errors and warnings
- Performance metrics
- Auto-creation statistics

Endpoint: GET /api/mcp/health-dashboard

Response should include:
{
  "projects": { "total": 8, "active": 5 },
  "branches": { "total": 15, "with_tasks": 10 },
  "tasks": { "total": 50, "completed": 10, "in_progress": 5 },
  "contexts": { "global": 1, "project": 8, "branch": 15, "task": 20 },
  "health_score": 97,
  "recent_issues": []
}

Files to create:
- New dashboard route
- Dashboard service/facade
- Health calculation logic
```

---

## Issue 9: Implement Batch Operations

### Prompt for Fix
```
Add batch operation support for common repetitive tasks:

New batch operations needed:
1. batch_create_subtasks - Create multiple subtasks at once
2. batch_update_tasks - Update multiple tasks with same changes
3. batch_add_dependencies - Add dependencies between multiple tasks
4. batch_complete_subtasks - Complete multiple subtasks

Example API:
manage_task(
    action="batch_update",
    task_ids=["id1", "id2", "id3"],
    updates={"status": "in_progress", "priority": "high"}
)

Files to modify:
- Task management facade
- Subtask management facade
- Add new batch operation handlers
```

---

## Issue 10: Add Undo/Rollback Capability

### Prompt for Fix
```
Implement undo/rollback functionality for critical operations:

Operations that should support undo:
1. Task deletion (soft delete with restore)
2. Bulk status changes
3. Context updates
4. Dependency changes

Implementation approach:
- Create audit log of changes
- Store previous state before modifications
- Provide undo action that restores previous state
- Time limit for undo (e.g., 5 minutes)

Files to create/modify:
- Audit log service
- Undo manager
- State storage for rollback
```

---

## General Testing Improvements

### Prompt for Fix
```
Based on today's testing, implement these improvements:

1. Add verbose mode to all operations that shows:
   - What was auto-created
   - What validations were performed
   - What side effects occurred

2. Create a test mode that:
   - Uses a separate test database
   - Provides detailed logging
   - Can reset to clean state

3. Add operation replay capability:
   - Record all operations in a session
   - Allow replay for debugging
   - Export/import operation sequences

Files to modify:
- Logging configuration
- Database configuration for test mode
- Operation recorder service
```

---

## Priority Order for Fixes

1. **High Priority** (Blocking issues)
   - Document required parameters (Issue 2)
   - Improve error messages (Issues 1, 3)

2. **Medium Priority** (Usability improvements)
   - Add validation hints (Issue 4)
   - Enhance completion messages (Issue 5)
   - Document auto-creation (Issue 6)

3. **Low Priority** (Nice to have)
   - Create test suite (Issue 7)
   - Add health dashboard (Issue 8)
   - Implement batch operations (Issue 9)
   - Add undo capability (Issue 10)

## Testing After Fixes

After implementing each fix, test with:
```python
# Test improved error messages
result = manage_context(action="create", level="project", context_id=existing_id)
assert result["status"] == "info"
assert "auto-created" in result["message"]

# Test parameter documentation
help_result = manage_context(action="help")
assert "Required Parameters by Level" in help_result

# Test UUID validation message
agent_result = manage_agent(action="register", agent_id="invalid")
assert "xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx" in agent_result["error"]
```