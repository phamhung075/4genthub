# Task Count Display Fix

## Problem
The ShimmerBadge was showing 0 for task counts on all branches in the ProjectList component.

## Root Cause
**Field Name Mismatch**: The backend API was returning `total_tasks` but the frontend was expecting `task_count`.

### Data Flow:
1. Backend query: `COALESCE(b.task_count, 0) as task_count` (from database)
2. Backend API response: Transformed to `'total_tasks': row[5]`
3. Frontend type: Expected `task_count: number`
4. Result: Frontend received undefined for `branch.task_count`, defaulting to 0

## Solution
**Unified field naming across the stack**:
1. Backend now consistently returns `task_count` instead of `total_tasks`
2. Frontend uses `task_count` everywhere
3. Removed unnecessary field mapping and conversions

### Files Changed:
1. **Backend**: `branch_api_controller.py`
   - Changed `'total_tasks': row[5]` to `'task_count': row[5]`
   - Ensures consistency with database field names

2. **Frontend**: `branchService.ts`
   - Updated logging to use `task_count` instead of `total_tasks`
   - Removed field mapping logic

3. **Frontend**: `ProjectList.tsx`
   - Simplified taskCounts calculation
   - Removed unnecessary compatibility mapping
   - Cleaned up debug logging

## Benefits:
- ✅ Single source of truth for field names
- ✅ No field mapping needed
- ✅ Works the same in local and cloud environments
- ✅ Cleaner, simpler code
- ✅ Task counts now display correctly

## Testing:
After restart, the task counts should display correctly in the ShimmerBadge components for each branch.