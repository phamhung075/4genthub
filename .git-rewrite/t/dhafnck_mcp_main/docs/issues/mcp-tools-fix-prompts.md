# MCP Tools Fix Prompts
**Date**: 2025-08-16
**Purpose**: Detailed prompts for fixing identified issues from MCP tools testing

## Fix Prompt 1: Global Context Singleton Support

### Issue
Global context operations fail when using "global_singleton" as context_id because the system expects a UUID.

### Fix Requirements
1. Add support for "global_singleton" as a special identifier for global context
2. Maintain backward compatibility with existing UUID-based global contexts
3. Auto-create global context if it doesn't exist when using singleton pattern

### Implementation Prompt
```
Fix the global context management to support "global_singleton" as a special identifier.

Context:
- Location: dhafnck_mcp_main/src/fastmcp/task_management/application/facades/context_application_facade.py
- Current behavior: Expects UUID for all context_ids
- Desired behavior: Accept "global_singleton" as alias for global context

Requirements:
1. In the manage_context method, check if level=="global" and context_id=="global_singleton"
2. If true, either:
   - Get the existing global context UUID from database
   - Create a new global context with a generated UUID if none exists
   - Map "global_singleton" to this UUID for all operations
3. Store this mapping in a class variable or configuration
4. Ensure all global context operations (create, update, get, resolve) work with "global_singleton"

Test cases to verify:
- manage_context(action="update", level="global", context_id="global_singleton", data={...})
- manage_context(action="get", level="global", context_id="global_singleton")
- manage_context(action="resolve", level="project", context_id="project-uuid") should inherit from global

Error seen:
invalid input syntax for type uuid: "global_singleton"
```

## Fix Prompt 2: Task Context Visibility

### Issue
Tasks show `context_available: false` and `context_data: null` even when context exists.

### Fix Requirements
1. Ensure task context is properly linked when created
2. Make context data visible in task responses
3. Fix the context_available flag logic

### Implementation Prompt
```
Fix task context visibility in API responses.

Context:
- Location: dhafnck_mcp_main/src/fastmcp/task_management/application/facades/task_application_facade.py
- Current behavior: Tasks have context_id set but show context_available: false
- Desired behavior: Show context_data and set context_available: true when context exists

Requirements:
1. In create_task method:
   - After task creation, ensure context is created
   - Link context properly with task
   - Set context_available flag correctly

2. In get_task and list_tasks methods:
   - Check if context exists for each task
   - If exists, set context_available: true
   - Optionally include context_data in response

3. Fix the context checking logic:
   - Current: Checks context_id field only
   - Needed: Actually verify context exists in database

Code areas to check:
- Task creation logic where context is auto-created
- Task retrieval logic where context_available is set
- Context repository methods for checking existence

Test verification:
1. Create a task
2. Get the task - should show context_available: true
3. Resolve context for the task - should return context data
```

## Fix Prompt 3: Agent Registration Documentation

### Issue
Agent registration fails with non-UUID agent_id but documentation doesn't clarify this.

### Fix Requirements
1. Update parameter documentation
2. Add validation with clear error message
3. Consider allowing custom string IDs with UUID generation

### Implementation Prompt
```
Improve agent registration to handle custom IDs better.

Context:
- Location: dhafnck_mcp_main/src/fastmcp/task_management/interface/ddd_compliant_mcp_tools.py
- Current behavior: Fails with database error for non-UUID agent_id
- Desired behavior: Either accept custom strings or provide clear validation error

Option 1 - Clear Validation:
1. In manage_agent method, validate agent_id parameter
2. If provided and not UUID format, return clear error:
   "agent_id must be a valid UUID or omitted for auto-generation"
3. Update parameter documentation to clarify UUID requirement

Option 2 - Support Custom IDs:
1. Accept any string as agent_id
2. Store a mapping of custom_id -> UUID
3. Generate UUID internally but allow referencing by custom ID
4. Update database schema if needed to support this

Recommended: Option 1 (simpler, maintains data integrity)

Test cases:
- manage_agent(action="register", name="test", agent_id="custom-string") -> Clear error
- manage_agent(action="register", name="test") -> Success with auto-generated UUID
- manage_agent(action="register", name="test", agent_id="valid-uuid") -> Success
```

## Fix Prompt 4: Enhanced Context Data in Task Responses

### Issue
Task responses don't include context data even when it exists, making frontend display incomplete.

### Fix Requirements
1. Include context data in task responses when requested
2. Add parameter to control context inclusion
3. Maintain performance by making it optional

### Implementation Prompt
```
Add context data inclusion option to task operations.

Context:
- Location: dhafnck_mcp_main/src/fastmcp/task_management/application/facades/task_application_facade.py
- Current: Tasks return minimal context info
- Desired: Option to include full context data

Requirements:
1. Add include_context parameter to task operations:
   - get_task(task_id, include_context=False)
   - list_tasks(filters, include_context=False)
   - next_task(git_branch_id, include_context=False)

2. When include_context=True:
   - Fetch context data for each task
   - Include in response under context_data field
   - Use batch fetching for list operations

3. Performance considerations:
   - Default to False to maintain current performance
   - Cache context data when possible
   - Use joins instead of N+1 queries for lists

Implementation steps:
1. Update method signatures to accept include_context
2. Add context fetching logic conditionally
3. Update response builders to include context when available
4. Add tests for both modes

Test verification:
- get_task(id, include_context=True) returns context_data
- list_tasks(include_context=True) includes context for all tasks
- Performance test: list with 100 tasks should complete < 2 seconds
```

## Testing After Fixes

### Test Script
```python
# Test 1: Global context singleton
result = manage_context(
    action="update",
    level="global",
    context_id="global_singleton",
    data={"test": "value"}
)
assert result["success"] == True

# Test 2: Task context visibility
task = manage_task(
    action="create",
    git_branch_id="branch-uuid",
    title="Test task"
)
task_get = manage_task(
    action="get",
    task_id=task["task"]["id"],
    include_context=True
)
assert task_get["task"]["context_available"] == True
assert task_get["task"]["context_data"] is not None

# Test 3: Agent registration validation
result = manage_agent(
    action="register",
    name="test-agent",
    agent_id="not-a-uuid"
)
assert "UUID" in result.get("error", {}).get("message", "")

# Test 4: Context inclusion in list
tasks = manage_task(
    action="list",
    git_branch_id="branch-uuid",
    include_context=True
)
assert all(t.get("context_data") is not None for t in tasks["tasks"])
```

## Priority Order

1. **High Priority**: Fix #2 (Task Context Visibility) - Affects frontend functionality
2. **Medium Priority**: Fix #1 (Global Context Singleton) - Improves usability
3. **Low Priority**: Fix #3 (Agent Registration) - Has workaround
4. **Enhancement**: Fix #4 (Context Data Inclusion) - Performance optimization

## Estimated Effort

- Fix #1: 2 hours (includes testing)
- Fix #2: 3 hours (requires debugging current logic)
- Fix #3: 1 hour (simple validation addition)
- Fix #4: 4 hours (performance considerations)

**Total**: ~10 hours for all fixes

## Success Criteria

All fixes are complete when:
1. Global context works with "global_singleton" identifier
2. Tasks show correct context_available status
3. Agent registration provides clear validation errors
4. Context data can be optionally included in responses
5. All existing tests continue to pass
6. New tests for fixed functionality pass
7. Performance remains within acceptable limits (<2s for operations)