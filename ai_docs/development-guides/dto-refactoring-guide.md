# DTO Refactoring Guide
**Converting API Responses to Use fastmcp/types DTOs**

## Overview

This guide explains how to refactor existing API controllers to use the new `fastmcp/types` DTOs for type-safe frontend communication.

## Current State

**Problem**: Controllers return raw dictionaries with no type safety
```python
# ❌ BEFORE: No type safety
def get_task(task_id: str) -> Dict[str, Any]:
    task = task_service.get(task_id)
    return {
        "success": True,
        "task": {
            "id": str(task.id),
            "title": task.title,
            # ... manually building dict
        }
    }
```

## Target State

**Solution**: Controllers return Pydantic DTOs matching frontend types
```python
# ✅ AFTER: Type-safe with Pydantic validation
from fastmcp.types import TaskResponse, task_to_dto

def get_task(task_id: str) -> TaskResponse:
    task = task_service.get(task_id)
    return TaskResponse(
        success=True,
        task=task_to_dto(task)  # Guaranteed to match frontend
    )
```

## Refactoring Process

### Step 1: Identify Return Points

Find all places where controller methods return data to frontend:
- ✅ GET endpoints (single object, list)
- ✅ POST endpoints (create response)
- ✅ PUT/PATCH endpoints (update response)
- ✅ DELETE endpoints (delete confirmation)

### Step 2: Map Domain → DTO

| Domain Entity | DTO Type | Conversion Helper |
|--------------|----------|-------------------|
| Task (full) | `TaskDTO` | `task_to_dto()` |
| Task (summary) | `TaskSummaryDTO` | `task_summary_to_dto()` |
| Subtask (full) | `SubtaskDTO` | `subtask_to_dto()` |
| Subtask (summary) | `SubtaskSummaryDTO` | `subtask_summary_to_dto()` |
| Project | `ProjectDTO` | Manual creation |
| Branch | `BranchDTO` | Manual creation |

### Step 3: Update Response Wrappers

Use appropriate response wrapper based on operation:

| Operation | Response Type |
|-----------|--------------|
| Get single task | `TaskResponse` |
| List tasks | `TasksResponse` |
| Get single subtask | `SubtaskResponse` |
| List subtasks | `SubtasksResponse` |
| Delete | `DeleteResponse` |
| Health check | `HealthResponse` |

## Example Refactoring

### Example 1: Get Single Task

```python
# ❌ BEFORE
from typing import Dict, Any

def get_task(self, task_id: str, user_id: str, session) -> Dict[str, Any]:
    """Get a specific task"""
    try:
        facade = self.facade_service.get_facade(user_id, session)
        task = facade.task_facade.get_task_by_id(task_id)

        return {
            "success": True,
            "task": {
                "id": str(task.id),
                "title": task.title,
                "description": task.description,
                "status": str(task.status),
                "priority": str(task.priority),
                "assignees": task.assignees or [],
                "assignees_count": len(task.assignees or []),
                "subtask_count": getattr(task, 'subtask_count', 0),
                # ... many more fields manually mapped
            }
        }
    except Exception as e:
        return {"success": False, "error": str(e)}
```

```python
# ✅ AFTER
from fastmcp.types import TaskResponse, task_to_dto
from datetime import datetime

def get_task(self, task_id: str, user_id: str, session) -> TaskResponse:
    """Get a specific task"""
    try:
        facade = self.facade_service.get_facade(user_id, session)
        task = facade.task_facade.get_task_by_id(task_id)

        return TaskResponse(
            success=True,
            task=task_to_dto(task, include_subtasks=False),
            timestamp=datetime.now(timezone.utc).isoformat()
        )
    except Exception as e:
        return TaskResponse(
            success=False,
            error=str(e),
            message="Failed to get task",
            timestamp=datetime.now(timezone.utc).isoformat()
        )
```

**Benefits**:
- ✅ **25 lines → 15 lines**: Conversion helper eliminates manual mapping
- ✅ **Type Safety**: Pydantic validates all fields match frontend
- ✅ **No Field Omissions**: Guaranteed all required fields present
- ✅ **Consistent Structure**: Standard response format

### Example 2: List Tasks

```python
# ❌ BEFORE
def list_tasks(self, filters: Dict, offset: int, limit: int,
               user_id: str, session) -> Dict[str, Any]:
    """List tasks with pagination"""
    try:
        facade = self.facade_service.get_facade(user_id, session)
        tasks = facade.task_facade.list_tasks(filters, offset, limit)

        return {
            "success": True,
            "tasks": [
                {
                    "id": str(t.id),
                    "title": t.title,
                    "status": str(t.status),
                    # ... manual mapping for each task
                }
                for t in tasks
            ],
            "total": len(tasks)
        }
    except Exception as e:
        return {"success": False, "error": str(e)}
```

```python
# ✅ AFTER
from fastmcp.types import TasksResponse, task_summary_to_dto
from datetime import datetime

def list_tasks(self, filters: Dict, offset: int, limit: int,
               user_id: str, session) -> TasksResponse:
    """List tasks with pagination"""
    try:
        facade = self.facade_service.get_facade(user_id, session)
        tasks = facade.task_facade.list_tasks(filters, offset, limit)

        return TasksResponse(
            success=True,
            tasks=[task_summary_to_dto(t) for t in tasks],
            total=len(tasks),
            page=offset // limit if limit > 0 else 0,
            limit=limit,
            timestamp=datetime.now(timezone.utc).isoformat()
        )
    except Exception as e:
        return TasksResponse(
            success=False,
            tasks=[],
            error=str(e),
            message="Failed to list tasks",
            timestamp=datetime.now(timezone.utc).isoformat()
        )
```

**Benefits**:
- ✅ Uses `task_summary_to_dto()` for lightweight list views
- ✅ Includes pagination metadata (page, limit)
- ✅ Returns empty array on error (frontend safe)

### Example 3: Create Task

```python
# ❌ BEFORE
def create_task(self, request: CreateTaskRequest,
                user_id: str, session) -> Dict[str, Any]:
    """Create a new task"""
    try:
        facade = self.facade_service.get_facade(user_id, session)
        task = facade.task_facade.create_task(
            title=request.title,
            description=request.description,
            # ... all parameters
        )

        return {
            "success": True,
            "task": {
                "id": str(task.id),
                # ... manual mapping
            },
            "message": "Task created successfully"
        }
    except Exception as e:
        return {"success": False, "error": str(e)}
```

```python
# ✅ AFTER
from fastmcp.types import TaskResponse, task_to_dto
from datetime import datetime

def create_task(self, request: CreateTaskRequest,
                user_id: str, session) -> TaskResponse:
    """Create a new task"""
    try:
        facade = self.facade_service.get_facade(user_id, session)
        task = facade.task_facade.create_task(
            title=request.title,
            description=request.description,
            # ... all parameters
        )

        return TaskResponse(
            success=True,
            task=task_to_dto(task),
            message="Task created successfully",
            timestamp=datetime.now(timezone.utc).isoformat()
        )
    except Exception as e:
        return TaskResponse(
            success=False,
            error=str(e),
            message="Failed to create task",
            timestamp=datetime.now(timezone.utc).isoformat()
        )
```

### Example 4: Delete Task

```python
# ❌ BEFORE
def delete_task(self, task_id: str, user_id: str, session) -> Dict[str, Any]:
    """Delete a task"""
    try:
        facade = self.facade_service.get_facade(user_id, session)
        facade.task_facade.delete_task(task_id)

        return {
            "success": True,
            "deleted": True,
            "id": task_id,
            "message": "Task deleted successfully"
        }
    except Exception as e:
        return {"success": False, "error": str(e)}
```

```python
# ✅ AFTER
from fastmcp.types import DeleteResponse
from datetime import datetime

def delete_task(self, task_id: str, user_id: str, session) -> DeleteResponse:
    """Delete a task"""
    try:
        facade = self.facade_service.get_facade(user_id, session)
        facade.task_facade.delete_task(task_id)

        return DeleteResponse(
            success=True,
            deleted=True,
            id=task_id,
            message="Task deleted successfully",
            timestamp=datetime.now(timezone.utc).isoformat()
        )
    except Exception as e:
        return DeleteResponse(
            success=False,
            deleted=False,
            error=str(e),
            message="Failed to delete task",
            timestamp=datetime.now(timezone.utc).isoformat()
        )
```

## Files to Refactor (Priority Order)

### High Priority (User-Facing)
1. ✅ **task_api_controller.py** - Task CRUD operations
2. ✅ **subtask_api_controller.py** - Subtask operations
3. ✅ **project_api_controller.py** - Project management
4. ✅ **branch_api_controller.py** - Branch operations

### Medium Priority
5. **agent_api_controller.py** - Agent management
6. **context_api_controller.py** - Context operations

### Low Priority (Internal)
7. **token_api_controller.py** - Token management
8. **auth_api_controller.py** - Authentication

## Refactoring Checklist

For each controller method:

- [ ] Import appropriate DTO types from `fastmcp.types`
- [ ] Import conversion helpers (`task_to_dto`, etc.)
- [ ] Change return type from `Dict[str, Any]` to specific DTO
- [ ] Replace manual dict building with conversion helper
- [ ] Wrap in appropriate response type (`TaskResponse`, etc.)
- [ ] Add timestamp to responses
- [ ] Handle error cases with same response type
- [ ] Update type hints throughout
- [ ] Test API endpoint returns correct structure
- [ ] Verify frontend can parse response

## Common Patterns

### Pattern 1: Single Object Response
```python
from fastmcp.types import TaskResponse, task_to_dto

return TaskResponse(
    success=True,
    task=task_to_dto(domain_object)
)
```

### Pattern 2: List Response
```python
from fastmcp.types import TasksResponse, task_summary_to_dto

return TasksResponse(
    success=True,
    tasks=[task_summary_to_dto(t) for t in tasks],
    total=len(tasks)
)
```

### Pattern 3: Error Response
```python
return TaskResponse(
    success=False,
    error=str(e),
    message="Operation failed"
)
```

### Pattern 4: Delete Response
```python
from fastmcp.types import DeleteResponse

return DeleteResponse(
    success=True,
    deleted=True,
    id=object_id
)
```

## Testing Strategy

### 1. Unit Test Updates
```python
def test_get_task_returns_dto():
    response = controller.get_task(task_id, user_id, session)

    # Verify response is TaskResponse type
    assert isinstance(response, TaskResponse)
    assert response.success is True
    assert isinstance(response.task, TaskDTO)
    assert response.task.id == task_id
```

### 2. Integration Test Updates
```python
def test_api_endpoint_returns_correct_json():
    response = client.get(f"/api/tasks/{task_id}")
    data = response.json()

    # Verify structure matches frontend expectations
    assert "success" in data
    assert "task" in data
    assert "timestamp" in data
    assert data["task"]["id"] == task_id
```

### 3. Contract Test (Frontend/Backend)
```typescript
// Frontend test verifying backend contract
it('should match TaskResponse interface', () => {
  const response = await taskService.getTask(taskId);

  // TypeScript compiler ensures response matches interface
  expect(response.success).toBe(true);
  expect(response.task.id).toBe(taskId);
});
```

## Migration Strategy

### Phase 1: Non-Breaking Addition
1. Add DTO imports alongside existing code
2. Keep existing dict returns temporarily
3. Test new DTO code path

### Phase 2: Gradual Replacement
1. Replace one method at a time
2. Test each method individually
3. Verify frontend compatibility

### Phase 3: Cleanup
1. Remove old dict-building code
2. Update all type hints
3. Remove unused imports

## Benefits Summary

✅ **Type Safety**: Pydantic validates all fields
✅ **Less Code**: Conversion helpers eliminate manual mapping
✅ **Consistency**: All responses follow same structure
✅ **Frontend Safety**: Guaranteed to match TypeScript interfaces
✅ **Early Errors**: Catch issues at development time
✅ **Maintainability**: Single source of truth for API structure
✅ **Documentation**: DTOs serve as API documentation

## See Also

- [API Models Guide](../types/API_MODELS_GUIDE.md)
- [Frontend Types](../../agenthub-frontend/src/types/api.types.ts)
- [Conversion Helpers](../../agenthub_main/src/fastmcp/types/converters.py)