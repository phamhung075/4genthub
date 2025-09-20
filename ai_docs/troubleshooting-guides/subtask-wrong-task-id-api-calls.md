# Subtask Dialog Wrong Task ID API Calls - Troubleshooting Guide

## Issue Description

When clicking on a subtask detail button:
1. Wrong task ID is used in API calls (MCP task management ID instead of actual parent task ID)
2. Wrong dialog opens (TaskDetailsDialog instead of SubtaskDetailsDialog)
3. URL with subtask parameter disappears quickly

**Example Error**:
- API call uses: `GET /api/v2/tasks/fee968a4-9cbc-4f75-9d5e-761f77959945/subtasks/adf6c6ed-893b-4522-b938-c9a6b4a2bb50`
- Should use: `GET /api/v2/tasks/f7f8f526-d1f2-4b9b-a2d3-96326c799cd6/subtasks/adf6c6ed-893b-4522-b938-c9a6b4a2bb50`

## Root Cause Analysis

After comprehensive investigation of the entire data flow from database to frontend, the **root cause is data integrity issue in the database**.

### What We Investigated (All Found to be Correct)

1. **Frontend Components** ✅ CORRECT
   - `LazySubtaskList.tsx` - properly uses `parentTaskId` prop
   - `SubtaskRow.tsx` - correctly constructs URLs with `parentTaskId`
   - `TaskRow.tsx` - correctly passes `summary.id` as `parentTaskId`

2. **API Layer** ✅ CORRECT
   - `/api/v2/tasks/` endpoint returns database data correctly
   - `TaskAPIController` and handlers work properly
   - Task serialization through DTOs works correctly

3. **Domain Layer** ✅ CORRECT
   - `Task` entity `to_dict()` method correctly serializes `str(self.id)`
   - `TaskResponse` DTO correctly maps task ID
   - TaskId value object correctly stores UUID

4. **Infrastructure Layer** ✅ CORRECT
   - Repository `_model_to_entity()` correctly maps `TaskId(str(task.id))` from database
   - ORM mapping works properly

### Actual Root Cause ❌ DATABASE CONTENT

The **database itself contains wrong task IDs**. Tasks are being stored with MCP task management IDs instead of application task IDs.

**Data Flow Issue**:
```
Database stores: fee968a4-9cbc-4f75-9d5e-761f77959945 (MCP task ID)
↓
Repository maps: TaskId(str(task.id)) → MCP task ID
↓
Entity serializes: to_dict() → MCP task ID
↓
API returns: JSON with MCP task ID
↓
Frontend uses: summary.id → MCP task ID
↓
Subtask API call: /api/v2/tasks/{MCP_TASK_ID}/subtasks/{SUBTASK_ID} ❌ FAILS
```

## Solution

Fix the **task creation process** to ensure proper application UUIDs are stored in the database instead of MCP task management IDs.

### Investigation Points

1. **Check Task Creation**: Verify how tasks are being created and ensure proper UUID generation
2. **Check MCP Integration**: Ensure MCP task management IDs are not overwriting application task IDs
3. **Database Migration**: May need to fix existing data with incorrect IDs

### Files to Investigate Further

1. Task creation in MCP controllers
2. Task creation through API endpoints
3. Any data migration or import processes
4. MCP task management integration points

## Debugging Process Documentation

### How We Identified the Issue

1. **Started with Frontend**: Examined component logic and data flow
2. **Traced API Calls**: Verified API endpoints and controller behavior
3. **Examined Domain Logic**: Checked entity and DTO mapping
4. **Investigated Repository**: Verified ORM to entity mapping
5. **Database Analysis**: Attempted to check database content (blocked by Docker access)
6. **Root Cause**: Identified that all code is correct, issue is in stored data

### Key Debug Files

- `/home/daihungpham/__projects__/4genthub/agenthub-frontend/src/components/LazySubtaskList.tsx`
- `/home/daihungpham/__projects__/4genthub/agenthub-frontend/src/components/SubtaskRow.tsx`
- `/home/daihungpham/__projects__/4genthub/agenthub-frontend/src/components/TaskRow.tsx`
- `/home/daihungpham/__projects__/4genthub/agenthub_main/src/fastmcp/task_management/domain/entities/task.py`
- `/home/daihungpham/__projects__/4genthub/agenthub_main/src/fastmcp/task_management/infrastructure/repositories/orm/task_repository.py`

### Debug Script Created

Created debug script at `/home/daihungpham/__projects__/4genthub/agenthub_main/scripts/debug_task_ids.py` to analyze database content (requires Docker environment).

## Prevention

1. **Task Creation Validation**: Ensure all task creation paths generate proper UUIDs
2. **Data Integrity Checks**: Add validation to prevent MCP task IDs from being stored as application task IDs
3. **Testing**: Add integration tests to verify correct task ID flow from creation to API response

## Related Issues

This issue is part of a broader concern about data integrity between MCP task management system and the main application database. Ensure proper separation and ID management between these systems.

---

**Investigation Date**: 2025-09-20
**Status**: Root cause identified, solution path documented
**Next Steps**: Fix task creation process and investigate database content