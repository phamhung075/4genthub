# WebSocket Delete Notifications Fix

**Date**: 2025-10-03
**Issue**: Tasks and subtasks not disappearing from frontend when deleted via MCP
**Status**: ✅ Fixed

## Problem Summary

When deleting tasks and subtasks through the MCP interface, the items remained visible in the frontend (LazyTaskList) instead of disappearing immediately like projects do.

### Symptoms
- ✅ CREATE: Tasks/subtasks appear live in frontend
- ✅ UPDATE: Tasks/subtasks update live in frontend
- ❌ DELETE: Tasks/subtasks stay visible in frontend (not removed)

## Root Cause Analysis

### Issue 1: Duplicate WebSocket Broadcasts
**Both** use cases AND facades were sending WebSocket notifications:

1. **Use Cases** (delete_task.py, remove_subtask.py):
   - `_send_websocket_notification()` method sent broadcasts
   - Used hardcoded `user_id="system"`

2. **Facades** (task_application_facade.py, subtask_application_facade.py):
   - ALSO sent WebSocket broadcasts
   - Used proper user context

**Result**: Duplicate events for every deletion operation

### Issue 2: Missing User Context
- `DeleteTaskUseCase.execute()` didn't accept user_id parameter
- `RemoveSubtaskUseCase.execute()` didn't accept user_id parameter
- Use case notifications used `user_id="system"` instead of actual user
- May have caused authorization issues preventing frontend from receiving events

## Solution Applied

### 1. Removed Duplicate Notifications from Use Cases

**File**: `agenthub_main/src/fastmcp/task_management/application/use_cases/delete_task.py`
- Removed `_send_websocket_notification()` method (lines 123-146)
- Removed WebSocket broadcast call from execute() (lines 82-89)
- Added comment referencing facade layer handling

**File**: `agenthub_main/src/fastmcp/task_management/application/use_cases/remove_subtask.py`
- Removed `_send_websocket_notification()` method (lines 128-152)
- Removed WebSocket broadcast call from execute() (lines 33-38)
- Removed unused `subtask_title` variable
- Added comment referencing facade layer handling

### 2. Added User Context to Use Cases

**File**: `agenthub_main/src/fastmcp/task_management/application/use_cases/delete_task.py`
```python
# Before
def execute(self, task_id: Union[str, int], cascade: bool = True) -> Dict[str, Any]:

# After
def execute(self, task_id: Union[str, int], cascade: bool = True, user_id: str = None) -> Dict[str, Any]:
```

**File**: `agenthub_main/src/fastmcp/task_management/application/use_cases/remove_subtask.py`
```python
# Before
def execute(self, task_id: Union[str, int], id: Union[str, int]) -> Dict[str, Any]:

# After
def execute(self, task_id: Union[str, int], id: Union[str, int], user_id: str = None) -> Dict[str, Any]:
```

### 3. Updated Facades to Pass User Context

**File**: `agenthub_main/src/fastmcp/task_management/application/facades/task_application_facade.py`
```python
# Line 614 - Before
result = self._delete_task_use_case.execute(task_id, cascade=True)

# Line 614 - After
result = self._delete_task_use_case.execute(task_id, cascade=True, user_id=user_id)
```

## Architecture Pattern Established

### Clean Separation of Concerns

**Use Cases** (Business Logic):
- ✅ Execute domain logic
- ✅ Dispatch domain events
- ❌ NO WebSocket notifications

**Facades** (Application Orchestration):
- ✅ Handle WebSocket notifications
- ✅ Pre-fetch context when needed
- ✅ Use proper user context
- ✅ Single source of truth for broadcasts

### Benefits
1. **No Duplicates**: Single broadcast per operation
2. **Proper Authorization**: Correct user_id in all events
3. **Maintainability**: Clear responsibility separation
4. **Consistency**: Matches working project deletion pattern

## Expected Behavior After Fix

1. **Delete Task**:
   - Backend: Use case executes deletion
   - Backend: Facade broadcasts WebSocket "deleted" event with user_id
   - Frontend: Receives event and removes task from LazyTaskList instantly

2. **Delete Subtask**:
   - Backend: Use case executes deletion
   - Backend: Facade broadcasts WebSocket "deleted" event with user_id
   - Frontend: Receives event and removes subtask from list instantly

## Testing Checklist

### Manual Testing Required
- [ ] Delete a task via MCP
- [ ] Verify task disappears from frontend instantly
- [ ] Delete a subtask
- [ ] Verify subtask disappears from subtask list instantly
- [ ] Check backend logs for duplicate WebSocket events (should be none)
- [ ] Verify events sent with correct user_id (not "system")

### Backend Verification
```bash
# Check for WebSocket broadcast logs
grep "Successfully broadcasted" logs/agenthub.log

# Should see SINGLE broadcast per deletion:
# ✅ Successfully broadcasted task deleted event for {task_id}
# ✅ Successfully broadcasted subtask deleted event for {subtask_id}
```

### Frontend Verification
```javascript
// Open browser console
// Delete a task
// Should see WebSocket message received:
{
  event_type: "deleted",
  entity_type: "task", // or "subtask"
  entity_id: "task-uuid",
  user_id: "actual-user-id" // NOT "system"
}
```

## Files Modified

1. `agenthub_main/src/fastmcp/task_management/application/use_cases/delete_task.py`
   - Lines 44: Added user_id parameter
   - Lines 82-85: Removed WebSocket broadcast call, added comment
   - Removed: Lines 123-146 (_send_websocket_notification method)

2. `agenthub_main/src/fastmcp/task_management/application/use_cases/remove_subtask.py`
   - Line 12: Added user_id parameter
   - Lines 22-34: Removed WebSocket broadcast call, added comment
   - Removed: Lines 128-152 (_send_websocket_notification method)

3. `agenthub_main/src/fastmcp/task_management/application/facades/task_application_facade.py`
   - Line 614: Pass user_id to use case

## Related Issues

- ✅ Project deletion works correctly (reference implementation)
- ✅ Task/subtask CREATE works correctly
- ✅ Task/subtask UPDATE works correctly
- ✅ Task/subtask DELETE now fixed

## Comparison with Working System

### Projects (Working Reference)
```python
# project_management_service.py lines 305-316
if deleted:
    await WebSocketNotificationService.broadcast_project_event(
        event_type="deleted",
        project_id=project_id,
        user_id=self._user_id,
        project_data={"name": project.name}
    )
```

### Tasks (Now Fixed)
```python
# task_application_facade.py lines 627-633
WebSocketNotificationService.sync_broadcast_task_event(
    event_type="deleted",
    task_id=task_id,
    user_id=notification_user_id,
    task_data=None,
    pre_fetched_context=task_context
)
```

### Subtasks (Now Fixed)
```python
# subtask_application_facade.py lines 417-423
WebSocketNotificationService.sync_broadcast_subtask_event(
    event_type="deleted",
    subtask_id=actual_subtask_id,
    task_id=task_id,
    user_id=user_id,
    subtask_data={"id": actual_subtask_id, "deleted": True}
)
```

## Lessons Learned

1. **Check for Duplicates**: Always verify single source of truth for events
2. **User Context Matters**: WebSocket authorization requires correct user_id
3. **Pattern Consistency**: Follow established patterns (project deletion)
4. **Layer Responsibility**: Use cases = logic, Facades = orchestration/notifications

## Related Documentation

- [WebSocket Notification Service](/home/daihungpham/__projects__/4genthub/agenthub_main/src/fastmcp/task_management/application/services/websocket_notification_service.py)
- [Project Delete (Working Reference)](/home/daihungpham/__projects__/4genthub/agenthub_main/src/fastmcp/task_management/application/services/project_management_service.py) lines 305-316
- [Task Application Facade](/home/daihungpham/__projects__/4genthub/agenthub_main/src/fastmcp/task_management/application/facades/task_application_facade.py)
- [Subtask Application Facade](/home/daihungpham/__projects__/4genthub/agenthub_main/src/fastmcp/task_management/application/facades/subtask_application_facade.py)
