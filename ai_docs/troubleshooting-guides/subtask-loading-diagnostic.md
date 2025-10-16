# Subtask Loading Diagnostic Guide

## Problem
When clicking to expand a task row, subtasks are not appearing even though they exist in the database.

## Complete Data Flow with Logging

### 1. Frontend Component (LazySubtaskList.tsx)
```
User Click → Task Expansion → LazySubtaskList Component Mounts
    ↓
Console Logs:
   [LazySubtaskList] 🏁 Component mount effect triggered
   [LazySubtaskList] 🚀 Starting API call
   [LazySubtaskList] 📡 Calling getSubtaskSummaries API...
```

### 2. Frontend API Layer (api-lazy.ts → apiV2.ts)
```
getSubtaskSummaries(task_id)
    ↓
subtaskApiV2.listSubtasksForTask(task_id)
    ↓
GET /api/v2/subtasks/task/{task_id}
   Headers: Authorization: Bearer <JWT token>
```

### 3. Backend Route (subtask_routes.py:170-208)
```
FastAPI Router receives request
    ↓
Backend Logs:
   🔵 [ROUTE] GET /api/v2/subtasks/task/{task_id} - Request received
   🔵 [ROUTE] User ID: {user_id}, User Email: {email}
   🔵 [ROUTE] Calling controller.list_subtasks
```

### 4. Backend Controller (subtask_api_controller.py:164-250)
```
SubtaskAPIController.list_subtasks()
    ↓
Backend Logs:
   🟢 [CONTROLLER] list_subtasks called: task_id={id}, user_id={id}
   🟢 [CONTROLLER] Getting task facade to lookup parent task
   🟢 [CONTROLLER] Looking up parent task
   🟢 [CONTROLLER] Parent task found, git_branch_id={id}
   🟢 [CONTROLLER] Getting subtask facade
   🟢 [CONTROLLER] Calling subtask_facade.handle_manage_subtask(action='list')
   🟢 [CONTROLLER] Facade returned {count} subtasks
   🟢 [CONTROLLER] Converting subtasks to DTOs
   🟢 [CONTROLLER] Returning SubtasksResponse with {count} DTOs
```

### 5. Backend Facade → Repository → Database
```
SubtaskFacade.handle_manage_subtask(action='list')
    ↓
SubtaskRepository.find_by_parent_task_id(task_id)
    ↓
SQL Query: SELECT * FROM subtasks WHERE task_id = {task_id} AND user_id = {user_id}
```

### 6. Response Path
```
Backend Controller → Route → HTTP Response
    ↓
Frontend API receives JSON response
    ↓
Frontend Logs:
   [LazySubtaskList] ✅ API response received: {subtask_count}
   [LazySubtaskList] ✅ Load complete, hasLoaded set to true
```

## How to Diagnose the Issue

### Step 1: Check Frontend Console
Open browser DevTools Console (F12) and look for:
```
[LazySubtaskList] 🏁 Component mount effect triggered
[LazySubtaskList] 🚀 Starting API call
[LazySubtaskList] 📡 Calling getSubtaskSummaries API...
```

**If you DON'T see these logs:**
- Component is not mounting or hasLoaded flag is preventing API call
- Check if the fix for resetting hasLoaded is applied

**If you DO see these logs but no response:**
- Check Network tab for the API request
- Look for HTTP errors (401, 404, 500)

### Step 2: Check Network Tab
In DevTools Network tab, filter for "subtasks":
```
Request: GET /api/v2/subtasks/task/{task_id}
Status: Should be 200 OK
Response: Check the JSON body for subtasks array
```

**Expected Response:**
```json
{
  "success": true,
  "subtasks": [
    {
      "id": "subtask-uuid",
      "title": "Subtask title",
      "status": "todo",
      "priority": "medium"
    }
  ],
  "total": 1,
  "message": "Retrieved 1 subtasks",
  "timestamp": "2025-10-16T..."
}
```

### Step 3: Check Backend Logs
Check Docker logs for the backend container:
```bash
docker logs agenthub-backend-1 --tail=100 -f
```

Look for the colored logs:
```
🔵 [ROUTE] GET /api/v2/subtasks/task/... - Request received
🟢 [CONTROLLER] list_subtasks called
🟢 [CONTROLLER] Facade returned X subtasks
```

### Step 4: Check Database
Connect to PostgreSQL and verify subtasks exist:
```sql
-- Check if subtasks exist for the task
SELECT id, title, task_id, status, user_id, created_at
FROM subtasks
WHERE task_id = 'your-task-id-here';

-- Verify user_id matches JWT token user
-- Compare the user_id in results with the user_id from backend logs
```

## Common Issues and Solutions

### Issue 1: hasLoaded Flag Not Resetting
**Symptom:** API call only happens once, subsequent expansions show no logs
**Solution:** The fix has been applied - useEffect now resets hasLoaded when parentTaskId changes
**Verify:** Check that you see "🔄 parentTaskId changed" log when expanding different tasks

### Issue 2: JWT Token User ID Mismatch
**Symptom:** Backend logs show "0 subtasks" but database has data
**Solution:** Check if user_id in database matches user_id from JWT token
**Debug:**
```bash
# In backend logs, find:
🔵 [ROUTE] User ID: f0de4c5d-...

# In database, check:
SELECT DISTINCT user_id FROM subtasks WHERE task_id = 'task-id';

# If they don't match, there's an authentication issue
```

### Issue 3: No API Call in Network Tab
**Symptom:** Console shows component mount but no network request
**Solution:** Check if hasLoaded is preventing the call
**Debug:** Look for "[LazySubtaskList] ⏭️ Skipping load - already loaded" in console

### Issue 4: 401 Unauthorized
**Symptom:** Network tab shows 401 error
**Solution:** JWT token expired or invalid
**Fix:** Refresh the page to get a new token

### Issue 5: Empty Response with 200 OK
**Symptom:** Network shows 200 OK but subtasks array is empty
**Solution:** Multi-tenancy filter is blocking access (user_id mismatch)
**Fix:** Verify user_id consistency between JWT and database

## Testing the Fix

### Test Scenario 1: Expand Same Task Multiple Times
1. Expand task A
2. Collapse task A
3. Expand task A again
4. **Expected:** Should NOT make new API call (already loaded)

### Test Scenario 2: Expand Different Tasks
1. Expand task A
2. See subtasks load
3. Collapse task A
4. Expand task B
5. **Expected:** Should see "🔄 parentTaskId changed" and new API call

### Test Scenario 3: Navigate Away and Back
1. Expand task A
2. Navigate to different page
3. Navigate back
4. Expand task A again
5. **Expected:** Component remounts, should make API call

## WebSocket Notifications (Future Check)

If subtasks are created via MCP tools, WebSocket should notify the frontend:
```
Backend: changePoolService.emitChange('subtask', 'created', subtask_id)
    ↓
WebSocket: Broadcast to all connected clients
    ↓
Frontend: useChangeSubscription receives notification
    ↓
LazySubtaskList: Refreshes subtask list
```

Check browser console for:
```
🔔 LazySubtaskList-{parentTaskId}: Received subtask notification
📡 LazySubtaskList-{parentTaskId}: Subtask changes detected, refreshing...
```

## Log Color Legend

- 🔵 **[ROUTE]** - FastAPI route handler (entry point)
- 🟢 **[CONTROLLER]** - API Controller layer
- 🔴 **[ERROR]** - Error occurred at this layer
- 🏁 **[Frontend]** - Component lifecycle
- 🚀 **[Frontend]** - API call initiated
- 📡 **[Frontend]** - Network operation
- ✅ **[Frontend]** - Success
- ❌ **[Frontend]** - Failure
- 🔄 **[Frontend]** - State change
- 🔔 **[Frontend]** - WebSocket notification

## Next Steps

1. **Restart backend to apply logging changes:**
   ```bash
   cd /home/daihungpham/__projects__/4genthub
   echo "R" | ./docker-system/docker-menu.sh
   ```

2. **Open browser with DevTools:**
   - Open Console tab
   - Open Network tab
   - Filter Network by "subtasks"

3. **Test subtask loading:**
   - Navigate to a task with subtasks
   - Click to expand the task row
   - Watch both Console and Network tabs

4. **Check backend logs:**
   ```bash
   docker logs agenthub-backend-1 --tail=50 -f
   ```

5. **Report findings:**
   - Share screenshots of Console logs
   - Share screenshots of Network tab
   - Share relevant backend log lines

## Expected Successful Flow

When everything works correctly, you should see:

**Frontend Console:**
```
[LazySubtaskList] 🏁 Component mount effect triggered
[LazySubtaskList] 🚀 Starting API call
[LazySubtaskList] 📡 Calling getSubtaskSummaries API...
[LazySubtaskList] ✅ API response received: {subtaskCount: 4}
[LazySubtaskList] ✅ Load complete, hasLoaded set to true
```

**Network Tab:**
```
GET /api/v2/subtasks/task/db50fea1-...
Status: 200 OK
Response: {success: true, subtasks: [...], total: 4}
```

**Backend Logs:**
```
🔵 [ROUTE] GET /api/v2/subtasks/task/db50fea1-... - Request received
🔵 [ROUTE] User ID: f0de4c5d-...
🟢 [CONTROLLER] list_subtasks called
🟢 [CONTROLLER] Parent task found
🟢 [CONTROLLER] Facade returned 4 subtasks
🟢 [CONTROLLER] Returning SubtasksResponse with 4 DTOs
🔵 [ROUTE] Returning response with 4 subtasks
```

**UI:**
```
Task row expands showing:
- Subtask 1: Test subtask for review 1 [todo]
- Subtask 2: Test subtask for review 2 [todo]
- Subtask 3: Test subtask for review 3 [todo]
- Subtask 4: Test subtask for review 4 [todo]
```
