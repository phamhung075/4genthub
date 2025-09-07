# Next Task TypeError Fix

## Issue Description
The `manage_task` action with `action="next"` was failing with a TypeError due to a parameter name mismatch between the controller and facade layers.

## Root Cause
The `TaskMCPController._handle_next_task` method was passing `git_branch_name` to the facade's `get_next_task` method, but the facade expected `git_branch_id` as the parameter name.

### Controller Code (Before Fix)
```python
# In task_mcp_controller.py
async def _run_async():
    return await facade.get_next_task(
        include_context=include_context,
        user_id=user_id,
        project_id=project_id,
        git_branch_name=git_branch_name,  # WRONG PARAMETER NAME
        assignee=None,
        labels=None
    )
```

### Facade Signature
```python
# In task_application_facade.py
async def get_next_task(self, include_context: bool = True, user_id: str = "default_id", 
                       project_id: str = "", git_branch_id: str = "main",  # EXPECTS git_branch_id
                       assignee: Optional[str] = None, labels: Optional[List[str]] = None)
```

## Solution
Changed the parameter name in the controller from `git_branch_name` to `git_branch_id` to match the facade's expected parameter.

### Fixed Code
```python
# In task_mcp_controller.py line 1181
async def _run_async():
    return await facade.get_next_task(
        include_context=include_context,
        user_id=user_id,
        project_id=project_id,
        git_branch_id=git_branch_id,  # Fixed: Pass git_branch_id instead of git_branch_name
        assignee=None,
        labels=None
    )
```

## Files Modified
- `/home/daihungpham/agentic-project/dhafnck_mcp_main/src/fastmcp/task_management/interface/controllers/task_mcp_controller.py` (line 1181)

## Test Verification
Created tests to verify the fix:
- `test_next_task_parameter_mismatch.py` - Demonstrates the parameter mismatch
- `test_next_task_controller_fix.py` - Verifies the fix works

## Impact
- The `manage_task(action="next")` operation now works without TypeError
- The controller correctly passes `git_branch_id` to the facade
- Next task retrieval functionality is restored

## Related Issues
After fixing this TypeError, there may be other issues with the next task logic (e.g., handling None values in filters), but the parameter mismatch TypeError is resolved.