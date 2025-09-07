# Task Dependency Visibility Fix

## Issue Description
When adding a dependency to a task using `manage_task(action="add_dependency")`, the success message confirms the dependency was added, but the returned task object shows an empty dependencies array.

## Root Cause
The issue was in the `TaskApplicationFacade.add_dependency()` method. It was checking for and using a non-existent `depends_on` attribute instead of the actual `dependencies` field that exists on the Task entity.

### Code Analysis
1. **Task Entity** (task.py): Has a `dependencies` field and proper `add_dependency()` method
2. **TaskApplicationFacade** (task_application_facade.py): Was incorrectly using `task.depends_on` instead of the Task entity's `add_dependency()` method

## Solution Implemented

### Fix Applied
Updated `TaskApplicationFacade.add_dependency()` to use the Task entity's built-in `add_dependency()` method:

```python
# Before (incorrect):
if not hasattr(task, 'depends_on'):
    task.depends_on = []
dependency_task_id = dependency_task.id
if dependency_task_id not in task.depends_on:
    task.depends_on.append(dependency_task_id)

# After (correct):
try:
    task.add_dependency(dependency_task.id)
    self._task_repository.save(task)
    message = f"Dependency {dependency_id} added to task {task_id}"
except ValueError as ve:
    # Handle validation errors
```

### Similar fix for remove_dependency:
```python
# Now uses:
task.remove_dependency(dependency_task_id)
```

## Testing
Created comprehensive unit tests in `test_dependency_visibility_fix.py` that verify:
1. Dependencies are visible immediately after adding
2. Multiple dependencies all show up correctly
3. Removing dependencies updates the response
4. Duplicate dependencies are handled properly

All tests pass successfully.

## Impact
- **Before**: Dependencies were not visible in the response after adding
- **After**: Dependencies are immediately visible in the task object returned by the MCP tool

## Files Modified
1. `/src/fastmcp/task_management/application/facades/task_application_facade.py` - Fixed add_dependency and remove_dependency methods
2. `/src/tests/unit/test_dependency_visibility_fix.py` - Added unit tests
3. `/src/tests/integration/test_dependency_visibility_mcp_integration.py` - Added integration tests

## Verification
The fix ensures that when you call:
```python
manage_task(action="add_dependency", task_id="X", dependency_id="Y")
```

The response now correctly includes:
```json
{
    "success": true,
    "message": "Dependency Y added to task X",
    "task": {
        "id": "X",
        "dependencies": ["Y"],
        // ... other task fields
    }
}
```