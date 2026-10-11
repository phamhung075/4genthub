### Fixed

**`call_agent` returned "Agent not found" for every agent on the Go backend** (2026-10-02)

- Cause: nothing in the Go backend populated `agent_templates` (`YAMLAgentTemplateLoader.LoadAllAgents` had no callers). Fix: run `agenthub -seed-agents` against the database.

**Fixed Task Deletion Not Updating Branch & Project Counters - Preventing Project Deletion** (2025-11-22)

Fixed bug where deleting tasks didn't update parent branch/project task counts, causing project deletion to be blocked even after all tasks were deleted.

**Root Cause**:
- Task delete WebSocket payload (`TaskDeletePayload`) only included `id`, `title`, and `git_branch_id`
- Missing `project_id` field meant frontend couldn't invalidate project cache
- Branch counters updated but project counters stayed stale
- When trying to delete project, backend validation saw stale count and rejected deletion

**Solution**:
- **Backend**: Added `project_id` field to `TaskDeletePayload` (websocket_protocol.py:204-206)
- **Backend**: Updated `convert_task_delete_legacy()` to extract `project_id` from task snapshot (websocket_protocol.py:579)
- **Backend**: Updated fallback payload creation to include `project_id` from task context (task_application_facade.py:1322-1324)
- **Frontend**: Added `project_id?: string` to `TaskDeletePayload` interface (websocket-protocol.ts:103)
- **Frontend**: Added project cache invalidations in task delete handler (useRealtimeSync.ts:229-233)
  - Invalidates `['projectSummaries']` to refresh project list
  - Invalidates `['project', project_id]` to refresh project detail view
- **Frontend**: Also added branch detail cache invalidation (useRealtimeSync.ts:226) for consistency

**Impact**:
- ✅ Deleting task now updates branch task count immediately
- ✅ Deleting task now updates project task count immediately
- ✅ Project deletion works correctly when all tasks are deleted
- ✅ Prevents "project has tasks" error when tasks were already deleted

**Files Modified**:
- `agenthub_main/src/fastmcp/task_management/domain/websocket_protocol.py` - Added project_id to TaskDeletePayload + convert function
- `agenthub_main/src/fastmcp/task_management/application/facades/task_application_facade.py` - Added project_id to fallback payload
- `agenthub-frontend/src/types/websocket-protocol.ts` - Added project_id to TypeScript interface
- `agenthub-frontend/src/hooks/useRealtimeSync.ts` - Added project/branch detail cache invalidations

---

**Fixed Entity-Specific Animation Classes + Cache Update Conflicts + WebSocket DateTime Error + Missing Animation Triggers - Subtask Delete Animations Now Working** (2025-11-22)

Fixed bug where subtask delete animations weren't playing. Subtasks would disappear instantly instead of sliding out smoothly like tasks.

**Root Causes** (Five Issues Fixed):

**Issue #1 - Wrong CSS Class Names**: AnimationFactory was hardcoded with task-specific CSS class names:
- Used `taskRowDeleteAnimation` for ALL entity types (tasks, subtasks, branches, projects)
- Each entity has its own CSS classes: `subtaskRowDeleteAnimation`, `branchRowDeleteAnimation`, `projectRowDeleteAnimation`
- When AnimationFactory.animate() applied wrong class to subtask element, animation didn't play

**Issue #2 - Optimistic Update Killed Animation** (useSubtasks.ts:214-220):
- Delete mutation had optimistic update in `onMutate` that removed subtask from cache IMMEDIATELY
- Subtask component unmounted before animation could play (800ms needed)
- WebSocket handler (useRealtimeSync.ts:430-448) has 600ms delay for animation, but optimistic update bypassed it
- Flow was: Click delete → API call → Optimistic remove from cache → Component unmounts → Animation can't play → WebSocket arrives but too late

**Issue #3 - invalidateQueries Triggered Immediate Refetch** (useSubtasks.ts:230-232):
- Even after removing optimistic update, `onSuccess` handler called `invalidateQueries` immediately after API success
- These invalidations triggered React Query refetch that removed subtask from cache
- Component unmounted before 800ms animation could complete
- WebSocket handler's 600ms delay never got a chance to execute because onSuccess invalidations happened first

**Issue #4 - WebSocket Broadcast Failing with DateTime Error** (websocket_protocol.py:378):
- Backend WebSocket broadcast was silently failing with `type object 'datetime.datetime' has no attribute 'UTC'`
- Code used incorrect syntax: `datetime.now(datetime.UTC)` which doesn't exist in Python datetime module
- After fixing Issues #1-3, subtasks stayed visible forever because WebSocket never sent delete message
- Backend logs showed: `WARNING - Failed to broadcast subtask deletion: type object 'datetime.datetime' has no attribute 'UTC'`
- This prevented ANY WebSocket message from being sent, making frontend 100% dependent on removed cache update logic

**Issue #5 - WebSocket Delete Messages Never Triggered Animations** (useRealtimeSync.ts):
- After fixing datetime error, WebSocket messages were being sent and received successfully
- BUT no animation was triggered - subtasks/tasks just disappeared instantly after 600ms
- `useRealtimeSync` was ONLY delaying cache removal, never calling animation system
- `WebSocketAnimationService` exists but was never initialized or called
- `animationFactory.animate()` was never invoked for delete operations
- Result: Items stayed visible during 600ms timeout, then vanished without animation

**Solutions**:

**Fix #1 - Made AnimationFactory Entity-Aware**:

**1. Type System Updates (animationTypes.ts:12,28)**:
- Added `EntityType = 'task' | 'subtask' | 'branch' | 'project'` type
- Updated `ElementRegistration` interface to include `entityType: EntityType` field
- Each element registration now explicitly declares its entity type

**2. AnimationFactory Refactor (AnimationFactory.ts:20-157)**:
- **Removed hardcoded CSS classes** from `animationRegistry` (was `{create: {cssClass: 'taskRowCreateAnimation'}}`)
- Changed to entity-agnostic duration/description only: `{create: {duration: 800, description: '...'}}`
- **Added `buildCssClass(entityType, animationType)` method** to dynamically build CSS classes
  - Example: `buildCssClass('subtask', 'delete')` → `'subtaskRowDeleteAnimation'`
  - Example: `buildCssClass('task', 'create')` → `'taskRowCreateAnimation'`
- **Updated `registerElement()`** to accept `entityType` parameter (3rd argument)
- **Updated `applyAnimation()`** to use dynamic CSS class from `buildCssClass()`

**3. Animation Hook Updates - All 6 Hooks Fixed**:
- `useTaskAnimation.ts:99-111` - Pass `entityType: 'task'`
- `useSubtaskAnimation.ts:93-107` (SubtaskRow version) - Pass `entityType: 'subtask'`
- `useSubtaskAnimation.ts:96-108` (hooks version) - Pass `entityType: 'subtask'`
- `useBranchAnimation.ts:99-111` - Pass `entityType: 'branch'`
- `useProjectAnimation.ts:99-111` - Pass `entityType: 'project'`
- Updated fallback CSS class functions in branch/project hooks (was using task classes)

**Key Technical Details**:
- CSS classes follow pattern: `{entityType}Row{AnimationType}Animation`
- AnimationFactory logs applied class for debugging: `Applied animation {entityType: 'subtask', animationType: 'delete', cssClass: 'subtaskRowDeleteAnimation'}`
- Backward compatible - existing task animations continue working
- Future-proof - supports any new entity types (just add to EntityType union)

**Fix #2 - Removed Optimistic Update for Delete** (useSubtasks.ts:191-219):
- **Removed optimistic cache update** from delete mutation's `onMutate` handler
- Subtask now stays in list during API call, allowing animation to play
- WebSocket handler removes from cache AFTER 600ms animation delay
- New flow: Click delete → API call → Subtask stays → WebSocket arrives → Animation plays → After 600ms cache updates → Component unmounts gracefully

**Fix #3 - Removed invalidateQueries from onSuccess** (useSubtasks.ts:226-231):
- **Removed all `invalidateQueries` calls** from delete mutation's `onSuccess` handler
- Prevented immediate refetch that was removing subtask from cache before animation could play
- WebSocket handler now exclusively manages cache updates with proper 600ms animation delay
- Follows same pattern as create mutation (lines 119-122) which also relies on WebSocket for cache updates
- Final flow: Click delete → API call → Success → No invalidation → Subtask stays visible → WebSocket arrives → Animation plays (800ms) → Cache updated after delay → Component unmounts gracefully

**Fix #4 - Fixed DateTime Syntax Error** (websocket_protocol.py:35,378):
- **Added `timezone` import**: Changed `from datetime import datetime` to `from datetime import datetime, timezone`
- **Fixed datetime syntax**: Changed `datetime.now(datetime.UTC)` to `datetime.now(timezone.utc)`
- `datetime.UTC` doesn't exist in Python - should use `timezone.utc` from datetime module
- WebSocket broadcast now succeeds and sends delete messages to frontend
- Frontend can now receive WebSocket delete events

**Fix #5 - Added Animation Triggers to WebSocket Handlers** (useRealtimeSync.ts:16,180-187,431-438):
- **Added AnimationFactory import**: `import { animationFactory } from '../services/AnimationFactory'`
- **Added animation trigger for task deletion**: Calls `animationFactory.animate(taskId, 'delete', 'websocket')` IMMEDIATELY when delete message arrives
- **Added animation trigger for subtask deletion**: Calls `animationFactory.animate(subtaskId, 'delete', 'websocket')` IMMEDIATELY when delete message arrives
- Uses `requestAnimationFrame` + 150ms delay to ensure DOM is ready before animating
- Animation plays for 800ms while 600ms cache removal timeout counts down
- **Pattern**: Message arrives → Trigger animation (150ms) → Show toast → Wait 600ms → Remove from cache
- Now matches how task deletion was SUPPOSED to work (WebSocketAnimationService pattern)

**Impact**: Subtask & Task delete animations now work end-to-end:
1. ✅ Correct CSS classes applied (Fix #1)
2. ✅ Subtask stays visible during API call (Fix #2)
3. ✅ No premature cache invalidation (Fix #3)
4. ✅ WebSocket broadcasts successfully (Fix #4)
5. ✅ Animation is triggered immediately when delete message arrives (Fix #5)
6. ✅ Delete animation plays smoothly for 800ms with slide-out effect
7. ✅ Cache updates after 600ms delay (during animation)
8. ✅ Component unmounts gracefully after animation completes

**Complete Flow**:
- User clicks delete → API call → Backend deletes & broadcasts WebSocket
- WebSocket arrives → **Animation triggered immediately** → Toast shown
- Item slides out smoothly (800ms animation)
- After 600ms: Cache updated, component unmounts
- **Result**: Smooth visual feedback matching task behavior

**Files Modified**:
- `agenthub-frontend/src/types/animationTypes.ts` - Added EntityType, updated ElementRegistration
- `agenthub-frontend/src/services/AnimationFactory.ts` - Entity-aware class building
- `agenthub-frontend/src/components/TaskRow/hooks/useTaskAnimation.ts` - Pass 'task'
- `agenthub-frontend/src/components/SubtaskRow/hooks/useSubtaskAnimation.ts` - Pass 'subtask'
- `agenthub-frontend/src/hooks/useSubtaskAnimation.ts` - Pass 'subtask'
- `agenthub-frontend/src/hooks/useBranchAnimation.ts` - Pass 'branch', fixed fallback classes
- `agenthub-frontend/src/hooks/useProjectAnimation.ts` - Pass 'project', fixed fallback classes
- `agenthub-frontend/src/hooks/useSubtasks.ts` - Removed optimistic delete update + invalidateQueries
- `agenthub-frontend/src/hooks/useRealtimeSync.ts` - Added AnimationFactory import + animation triggers for task & subtask deletion + debug logging
- `agenthub_main/src/fastmcp/task_management/domain/websocket_protocol.py` - Fixed datetime.UTC → timezone.utc

---

**Fixed Partial Task Update KeyError (Two Locations)** (2025-11-22)

Fixed KeyError "'title'" when updating task with only some fields (e.g., description + progress notes without changing title/status). Error occurred in TWO places that both needed fixes.

**Root Causes**:

1. **WebSocket Payload Building (task_application_facade.py:720-734)**:
   - TaskUpdatePayload requires ALL fields (title, status, priority, git_branch_id are mandatory)
   - MinimalResponseSerializer INTENTIONALLY excludes input fields from UPDATE responses for token optimization
   - For UPDATE operations, minimal response only returns: id, created_at, updated_at, progress_percentage, subtask_count
   - It EXCLUDES: title, description, status, priority, git_branch_id, assignees, labels (~70-75% token savings)
   - Code tried to build WebSocket payload from minimal response → fields were None → KeyError

2. **API Response Conversion (crud_handler.py:200 & task_application_facade.py:811)**:
   - Facade returned minimal response `task_dict` to crud_handler
   - crud_handler passed it to `task_to_dto()` which uses dict syntax: `task["title"]`
   - task_to_dto REQUIRES: title, status, priority, git_branch_id (types/converters.py:47-50)
   - Minimal response doesn't have these fields → KeyError when converting to TaskDTO

**Changes Made**:

**Fix #1 - WebSocket Payload (task_application_facade.py:712-745)**:
- Used `current_task` (from DB) instead of minimal response for WebSocket payload
- `current_task` already fetched at line 687 via `_get_task_for_update_comparison(task_id)` - has ALL fields
- Changed from: `task_dict.get("title") or task_data.get("title")` (both minimal, returned None)
- Changed to: `full_task_data.get("title")` where `full_task_data = current_task.to_dict()` (complete DB data)
- All required payload fields now guaranteed present from database

**Fix #2 - API Response (task_application_facade.py:811-815)**:
- Changed facade return value from minimal `task_dict` to complete `task_response.task.to_dict()`
- Added comment: "MinimalResponseSerializer is for internal use/token optimization only"
- API responses need complete task for task_to_dto conversion
- Changed from: `return {"success": True, "action": "update", "task": task_dict}` (minimal)
- Changed to: `return {"success": True, "action": "update", "task": complete_task}` (complete)

**Before/After Example**:
```python
# ❌ BEFORE FIX #1: WebSocket payload using minimal response
task_dict = MinimalResponseSerializer.serialize_task_minimal(task_response.task, "update")
# Returns: {"id": "...", "updated_at": "...", "progress_percentage": 50}
# MISSING: title, description, status, priority, git_branch_id

payload = TaskUpdatePayload(
    title=task_dict.get("title"),  # ❌ Returns None → KeyError!
)

# ✅ AFTER FIX #1: WebSocket payload using complete database task
full_task_data = current_task.to_dict()  # Has ALL fields from DB
# Returns: {"id": "...", "title": "My Task", "status": "in_progress", "priority": "high", ...}

payload = TaskUpdatePayload(
    title=full_task_data.get("title"),  # ✅ Returns "My Task"
)

# ❌ BEFORE FIX #2: Facade returns minimal response
return {"success": True, "action": "update", "task": task_dict}
# crud_handler receives minimal → task_to_dto(task_dict) → KeyError on task["title"]

# ✅ AFTER FIX #2: Facade returns complete task
complete_task = task_response.task.to_dict()
return {"success": True, "action": "update", "task": complete_task}
# crud_handler receives complete → task_to_dto(complete_task) → Success!
```

**Impact**:
- ✅ **Users can now update ANY subset of task fields without errors**
- ✅ Updating only description works (title/status/priority come from DB)
- ✅ Updating only progress notes works (all required fields filled from current_task)
- ✅ Updating only labels/assignees works
- ✅ **WebSocket notifications work correctly** - payload has all required fields from database
- ✅ **API responses work correctly** - task_to_dto receives complete task data
- ✅ **No more KeyError 'title'** - both backend locations fixed
- ✅ MinimalResponseSerializer token optimization preserved for internal use
- ⚠️ **Note**: API responses now return complete task data (not minimal) for proper DTO conversion

**Fixed Subtask Update KeyError and Stale Cache (Same Pattern as Task)** (2025-11-22)

Applied the EXACT same fixes to Subtask that were applied to Task - same root causes, same solutions.

**Root Causes**:
1. **Backend Facade Return (subtask_application_facade.py:626-628)**:
   - Returned MinimalResponseSerializer result which excludes `priority` for UPDATE operations
   - subtask_to_dto requires `priority` with dict syntax (converters.py:136)
   - Caused KeyError 'priority' when subtask_api_controller calls subtask_to_dto (line 431)

2. **Frontend Cache (useRealtimeSync.ts:377-399)**:
   - Used `invalidateQueries` instead of `setQueryData` for updates
   - Caused stale data in component state after WebSocket notifications
   - Same pattern as Task - edit dialog showed old data after update

**Changes Made**:

**Fix #1 - Facade Return (subtask_application_facade.py:621-634)**:
- Changed from: `"subtask": MinimalResponseSerializer.serialize_subtask_minimal(response.subtask, "update")`
- Changed to: `"subtask": complete_subtask` where `complete_subtask = response.subtask.to_dict()`
- Now returns complete data for subtask_to_dto conversion
- Same fix pattern as task_application_facade.py:811-815

**Fix #2 - Frontend Cache (useRealtimeSync.ts:377-405)**:
- Changed from: `queryClient.invalidateQueries({ queryKey: ['subtasks', taskId] })`
- Changed to: `queryClient.setQueryData<Subtask[]>(['subtasks', taskId], (old) => old.map(...))`
- Direct cache update with WebSocket data instead of refetch
- Same fix pattern as task update (useRealtimeSync.ts:135-154)

**Impact**:
- ✅ Subtask updates now work without KeyError
- ✅ Edit dialog shows fresh data after subtask update
- ✅ Faster updates (direct cache vs invalidate + refetch)
- ✅ Consistent pattern across Task and Subtask entities

**Fixed Task Edit Dialog Showing Stale Data After Update** (2025-11-22)

Fixed issue where edit dialog showed old task data instead of updated data when reopening after update.

**Root Cause**:
- useRealtimeSync invalidated React Query cache on task update
- But fullTasksMap.current (ref cache) still had old data
- loadFullTask returned stale data from fullTasksMap WITHOUT checking React Query
- Edit dialog received stale task from fullTasksMap.current.get(taskId)

**Changes Made**:

**Fix #1 - Use setQueryData instead of invalidateQueries (useRealtimeSync.ts:141-154)**:
- Changed from: `queryClient.invalidateQueries()` (forces refetch)
- Changed to: `queryClient.setQueryData(['task', taskId], taskData)` (direct update)
- Backend now sends complete task data, so we can update cache immediately
- Faster and more reliable than invalidation + refetch

**Fix #2 - Remove stale cache early return (LazyTaskListRefactored.tsx:48-50)**:
- Removed: `if (fullTasksMap.current.has(taskId)) return fullTasksMap.current.get(taskId)`
- Now always fetches from React Query cache which has fresh WebSocket data
- fullTasksMap is still updated AFTER React Query fetch (line 65)

**Impact**:
- ✅ Edit dialog now shows fresh data after task update
- ✅ React Query cache updated immediately via WebSocket (no refetch delay)
- ✅ fullTasksMap synchronized with React Query cache
- ✅ Faster updates (direct cache update vs invalidate + refetch)

**Improved Validation Error Messages for Task Operations** (2025-11-22)

Fixed generic error messages that made debugging validation errors impossible. Now returns specific validation errors instead of "Failed to update task".

**Root Cause**:
- Backend exception handlers were returning generic error messages ("Failed to create/update/delete task")
- Specific validation errors (e.g., "Task description cannot be empty") were being logged but not returned to frontend
- Error messages were stored in `error` field but generic message used in `message` field
- Frontend displayed the generic `message`, making debugging impossible

**Changes Made**:
- `crud_handler.py:85-95`: Updated create_task exception handler to return specific error
- `crud_handler.py:151-161`: Updated get_task exception handler to return specific error
- `crud_handler.py:214-224`: Updated update_task exception handler to return specific error
- `crud_handler.py:278-288`: Updated delete_task exception handler to return specific error
- `crud_handler.py:341-351`: Updated list_tasks exception handler to return specific error
- All handlers now use: `error_message = str(e) if str(e) else "Failed to [operation] task"`
- Both `error` and `message` fields now contain the specific validation error

**Impact**:
- ✅ Frontend now displays actual validation errors (e.g., "Task description cannot be empty")
- ✅ Debugging is much easier - users see WHY the operation failed
- ✅ Validation errors are clear and actionable
- ✅ No more generic "Failed to update task: Failed to update task" messages

**Example Error Messages Now Shown**:
- Before: "Failed to update task: Failed to update task"
- After: "Failed to update task: Task description cannot be empty"
- After: "Failed to create task: Task title is required"
- After: "Failed to update task: Cannot transition from done to todo"

**Task Update Duplicate Toast Notifications** (2025-11-22)

Fixed duplicate toast notifications when updating task: both success toast (from WebSocket) and error toast (from API mutation) appeared simultaneously.

**Root Cause**:
- Backend requires `details` field (minimum 10 characters) when updating `status` or `progress_percentage`
- Frontend marked progress notes as optional for all updates
- User changed task status without providing progress notes
- Backend validation failed → returned error response
- But WebSocket notification was already sent → showed success toast
- API mutation error reached frontend → showed error toast
- Result: Both success and error toasts appeared

**Changes Made**:
- `TaskEditDialog.tsx:115-127`: Added `isSaveDisabled()` validation function that checks if status changed and progress notes provided
- `TaskEditDialog.tsx:293-328`: Updated progress notes field UI to dynamically show requirement based on status change
  - Shows "Required when changing status - minimum 10 characters" when status changed
  - Shows "Optional - add notes about work done" when status unchanged
  - Red border on textarea when validation fails
  - Real-time character count with "Need X more" indicator
  - Clear error message below field
- `TaskEditDialog.tsx:406`: Updated Save button to use `isSaveDisabled()` validation
- Disabled Save button when status changed but progress notes < 10 characters

**Impact**:
- ✅ Users cannot save status changes without providing progress notes (10+ characters)
- ✅ Clear visual feedback shows when progress notes are required
- ✅ No more duplicate toasts (validation prevents API error)
- ✅ Frontend validation matches backend requirements
- ✅ WebSocket remains the single source of truth for success notifications

**Task Update Empty Date Field Validation Error** (2025-11-22)

Fixed error when updating task with empty due_date field: "Invalid due date format: . Expected ISO 8601 format".

**Root Cause**:
- Date input field sends empty string `''` when cleared by user
- Backend validation rejects empty strings for date fields (expects null or valid ISO 8601)
- Form was sending empty strings directly without cleaning

**Changes Made**:
- `TaskEditDialog.tsx:98-112`: Added data cleaning in `handleSave()` function
- Empty strings converted to `undefined` for optional fields: `due_date`, `estimated_effort`, `description`, `progress_notes`
- Backend now receives `undefined` (omitted from request) instead of empty string

**Impact**:
- ✅ Users can clear date fields without validation errors
- ✅ Empty optional fields handled correctly (not sent to backend)
- ✅ Valid dates still sent as ISO 8601 strings
