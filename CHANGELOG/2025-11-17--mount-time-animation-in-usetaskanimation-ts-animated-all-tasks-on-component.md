### Fixed

**Task Animation Spillover Bug + Duplicate Row Race Condition** (2025-11-22)

Fixed two critical issues with task creation in the frontend:
1. Creating a task via frontend API triggered animations for ALL tasks in the list
2. Creating multiple tasks quickly caused duplicate rows (1 task → 4 rows visible)

**Root Cause - Animation Spillover**:
- Mount-time animation in `useTaskAnimation.ts` animated all tasks on component mount
- WebSocketAnimationService had create animations disabled (skip on line 68-70)
- Both API route and MCP route send WebSocket notifications, but only MCP trigger was enabled

**Root Cause - Duplicate Rows (Race Condition)**:
- **Step 1**: Optimistic update creates temp task: `[temp-123, ...old]`
- **Step 2**: WebSocket arrives → adds real task: `[real-id, temp-123, ...old]`
- **Step 3**: API onSuccess → removes temp, adds real AGAIN: `[real-id, real-id, ...old]` ← DUPLICATE!
- When creating multiple tasks quickly, this race happens multiple times → 4+ duplicate rows

**Changes Made**:
- `agenthub-frontend/src/services/WebSocketAnimationService.ts:67-68`: Enabled create animations for WebSocket events
- `agenthub-frontend/src/components/TaskRow/hooks/useTaskAnimation.ts:125-131`: Disabled mount-time animation completely
- `agenthub-frontend/src/hooks/useTasks.ts:112-136`:
  - Changed `invalidateQueries()` to `setQueryData()` to prevent component remounts
  - Added duplicate check before adding task (lines 123-129)
  - Updates existing task if WebSocket already added it (prevents duplicates)
- Removed duplicate unused file: `agenthub-frontend/src/hooks/useTaskAnimation.ts`

**Technical Details**:
- **MCP Trigger = Source of Truth**: Both API and MCP routes call same facade → send WebSocket 'created' event
- **Single Animation Source**: WebSocketAnimationService handles ALL create animations via WebSocket
- **No Mount Detection**: Removed timestamp-based mount animation to prevent spillover
- **Direct Cache Update**: Prevents React Query from refetching and remounting all components
- **Race-Safe Deduplication**: Checks if task exists before adding (matches useRealtimeSync pattern)

**Task Insertion Order** (2025-11-22):
- WebSocket handler was adding new tasks to END of list (last row)
- Fixed to add to BEGINNING (first row) for newest-first order
- `useRealtimeSync.ts:105`: Changed `[...old, taskData]` → `[taskData, ...old]`
- `useRealtimeSync.ts:121`: Changed `[...old, taskData]` → `[taskData, ...old]`

**Task Create Animation** (2025-11-22):
- Task appeared visible before animation started (flash effect)
- Animation triggered TWICE very fast (duplicate event listeners)
- Fixed to start hidden and slide in from RIGHT to LEFT once
- `task-animations.css:46-51`: Added initial hidden state `transform: translateX(100%); opacity: 0;`
- `useTaskAnimation.ts:182-194`: Added `taskRowNew` class for newly created tasks (< 2 seconds old)
- `WebSocketAnimationService.ts:24-29`: Added initialization guard to prevent duplicate event listeners
- New tasks now start with `taskRowNew` class (hidden) until WebSocket animation replaces it
- Animation duration reduced from 0.8s to 0.5s for snappier feel
- Animation triggers only ONCE per task creation (no duplicates)

**Impact**:
- ✅ Only newly created task animates (single task animation)
- ✅ Existing tasks do NOT animate on list updates
- ✅ No duplicate rows when creating multiple tasks quickly
- ✅ New tasks always appear at TOP (first row) for better visibility
- ✅ Works identically for both MCP tools (AI agents) and API route (human create button)
- ✅ No component remounts = smoother UX and better performance
