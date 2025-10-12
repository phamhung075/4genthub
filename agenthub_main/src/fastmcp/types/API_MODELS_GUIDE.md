# API Models Guide - Type-Safe Frontend Communication

This guide explains how to use Pydantic models that match frontend TypeScript interfaces for type-safe API responses.

## Purpose

The API models in `api_models.py` ensure **exact type matching** between:
- **Backend** (Python/Pydantic) → **Frontend** (TypeScript)
- Prevents type mismatches and API contract violations
- Makes errors visible at development time, not runtime

## Key Concept: DTOs (Data Transfer Objects)

```
┌─────────────────┐     ┌──────────────┐     ┌─────────────────┐
│ Domain Entity   │────▶│ DTO Model    │────▶│ Frontend Type   │
│ (Task)          │     │ (TaskDTO)    │     │ (Task)          │
└─────────────────┘     └──────────────┘     └─────────────────┘
  Business Logic        API Contract          UI Component
```

## Complete Type Mapping

### Entity Models

| Backend (Python)  | Frontend (TypeScript)     | Purpose                    |
|------------------|---------------------------|----------------------------|
| `TaskDTO`        | `Task`                    | Full task with all fields  |
| `SubtaskDTO`     | `Subtask`                 | Full subtask with all fields |
| `ProjectDTO`     | `Project`                 | Project with branches      |
| `BranchDTO`      | `Branch`                  | Git branch/task tree       |
| `RuleDTO`        | `Rule`                    | Cursor rules               |

### Summary Models (Lightweight)

| Backend (Python)       | Frontend (TypeScript)  | Purpose                    |
|-----------------------|------------------------|----------------------------|
| `TaskSummaryDTO`      | `TaskSummary`          | Task list display          |
| `SubtaskSummaryDTO`   | `SubtaskSummary`       | Subtask list display       |
| `BranchSummaryDTO`    | `BranchSummary`        | Branch with statistics     |
| `ProjectSummaryDTO`   | `ProjectSummary`       | Project overview           |

### Response Wrappers

| Backend (Python)       | Frontend (TypeScript)  | Usage                      |
|-----------------------|------------------------|----------------------------|
| `TaskResponse`        | `TaskResponse`         | Single task response       |
| `TasksResponse`       | `TasksResponse`        | Task list with pagination  |
| `SubtaskResponse`     | `SubtaskResponse`      | Single subtask response    |
| `SubtasksResponse`    | `SubtasksResponse`     | Subtask list               |
| `ProjectResponse`     | `ProjectResponse`      | Single project response    |
| `BranchResponse`      | `BranchResponse`       | Single branch response     |
| `DeleteResponse`      | `DeleteResponse`       | Deletion confirmation      |
| `HealthResponse`      | `HealthResponse`       | System health check        |

## Usage Patterns

### Pattern 1: Converting Domain Entity to DTO

```python
from fastmcp.types import task_to_dto, TaskResponse

# In your API endpoint
def get_task(task_id: str) -> TaskResponse:
    # Get domain entity from repository
    task_entity = task_repository.get_by_id(task_id)

    # Convert to DTO (matches frontend type)
    task_dto = task_to_dto(task_entity)

    # Return wrapped response
    return TaskResponse(
        success=True,
        task=task_dto,
        timestamp=datetime.now().isoformat()
    )
```

### Pattern 2: Using Summary Models for Lists

```python
from fastmcp.types import task_summary_to_dto, TasksResponse

def list_tasks(branch_id: str) -> TasksResponse:
    # Get domain entities
    tasks = task_repository.list_by_branch(branch_id)

    # Convert to lightweight summaries
    task_summaries = [task_summary_to_dto(t) for t in tasks]

    # Return list response
    return TasksResponse(
        success=True,
        tasks=task_summaries,
        total=len(task_summaries),
        timestamp=datetime.now().isoformat()
    )
```

### Pattern 3: Error Responses

```python
from fastmcp.types import TaskResponse

def get_task_with_error_handling(task_id: str) -> TaskResponse:
    try:
        task = task_repository.get_by_id(task_id)
        return TaskResponse(
            success=True,
            task=task_to_dto(task)
        )
    except TaskNotFoundError as e:
        return TaskResponse(
            success=False,
            error=str(e),
            message="Task not found"
        )
```

### Pattern 4: Pydantic Validation

```python
from fastmcp.types import SubtasksResponse, SubtaskSummaryDTO

def get_subtasks(parent_task_id: str) -> SubtasksResponse:
    subtasks = subtask_repository.list_by_parent(parent_task_id)

    # Pydantic validates each field matches the schema
    subtask_dtos = [
        SubtaskSummaryDTO(
            id=str(s.id),
            title=s.title,
            status=str(s.status),
            priority=str(s.priority),
            assignees_count=len(s.assignees),
            # ... Pydantic validates all required fields exist
        )
        for s in subtasks
    ]

    return SubtasksResponse(
        success=True,
        subtasks=subtask_dtos,
        total=len(subtask_dtos)
    )
```

## Type Safety Benefits

### 1. Compile-Time Validation

```python
# ✅ CORRECT: All required fields provided
task_dto = TaskDTO(
    id="123",
    title="Implement auth",
    status="in_progress",
    priority="high",
    assignees_count=2,
    subtask_count=3,
    has_dependencies=False,
    has_context=True,
    git_branch_id="branch-123",
    project_id="proj-456"
)

# ❌ ERROR: Pydantic validation fails - missing required fields
task_dto = TaskDTO(
    id="123",
    title="Implement auth"
    # Missing: status, priority, assignees_count, etc.
)
# ValidationError: 8 validation errors for TaskDTO
```

### 2. Field Name Matching

```python
# Backend field names match frontend exactly
subtask_dto = SubtaskDTO(
    id="sub-123",
    task_id="task-456",  # ← Frontend expects "task_id", not "parent_task_id"
    title="Add tests",
    status="todo",
    priority="medium",
    assignees_count=1
)

# Conversion helper handles field name mapping
def subtask_to_dto(subtask: Subtask) -> SubtaskDTO:
    return SubtaskDTO(
        task_id=str(subtask.parent_task_id),  # Maps parent_task_id → task_id
        # ...
    )
```

### 3. Optional Fields Handling

```python
# Optional fields default to None
task_dto = TaskDTO(
    # ... required fields ...
    description=None,  # Optional
    labels=None,       # Optional
    due_date=None,     # Optional
)

# Or omit them entirely
task_dto = TaskDTO(
    # ... required fields only ...
)
```

## Common Patterns by Endpoint

### GET /api/tasks/{task_id}

```python
@router.get("/tasks/{task_id}")
def get_task(task_id: str) -> TaskResponse:
    from fastmcp.types import task_to_dto, TaskResponse

    task = task_service.get(task_id)
    return TaskResponse(
        success=True,
        task=task_to_dto(task, include_subtasks=True)
    )
```

### GET /api/tasks?branch_id={branch_id}

```python
@router.get("/tasks")
def list_tasks(branch_id: str) -> TasksResponse:
    from fastmcp.types import task_summary_to_dto, TasksResponse

    tasks = task_service.list(branch_id)
    return TasksResponse(
        success=True,
        tasks=[task_summary_to_dto(t) for t in tasks],
        total=len(tasks)
    )
```

### GET /api/subtasks?parent_task_id={task_id}

```python
@router.get("/subtasks")
def list_subtasks(parent_task_id: str) -> SubtasksResponse:
    from fastmcp.types import subtask_summary_to_dto, SubtasksResponse

    subtasks = subtask_service.list(parent_task_id)
    return SubtasksResponse(
        success=True,
        subtasks=[subtask_summary_to_dto(s) for s in subtasks],
        total=len(subtasks)
    )
```

### DELETE /api/tasks/{task_id}

```python
@router.delete("/tasks/{task_id}")
def delete_task(task_id: str) -> DeleteResponse:
    from fastmcp.types import DeleteResponse

    task_service.delete(task_id)
    return DeleteResponse(
        success=True,
        deleted=True,
        id=task_id,
        message="Task deleted successfully"
    )
```

## Bulk Operations

```python
from fastmcp.types import BulkSummaryResponse, BranchSummaryDTO

def get_bulk_summaries(project_ids: List[str]) -> BulkSummaryResponse:
    summaries = {}
    for project_id in project_ids:
        branches = branch_service.list_with_stats(project_id)
        for branch in branches:
            summaries[branch.id] = BranchSummaryDTO(
                id=branch.id,
                project_id=project_id,
                name=branch.name,
                task_count=branch.task_count,
                completed_tasks=branch.completed_tasks,
                # ...
            )

    return BulkSummaryResponse(
        success=True,
        summaries=summaries,
        projects={},
        metadata=BulkSummaryMetadata(
            count=len(summaries),
            queryTimeMs=100,
            fromCache=False
        ),
        timestamp=datetime.now().isoformat()
    )
```

## Testing API Contracts

```python
def test_task_dto_matches_frontend():
    """Verify TaskDTO structure matches frontend Task interface"""
    from fastmcp.types import TaskDTO

    # Create DTO with all frontend-expected fields
    dto = TaskDTO(
        id="123",
        title="Test",
        status="todo",
        priority="medium",
        assignees_count=0,
        subtask_count=0,
        has_dependencies=False,
        has_context=False,
        git_branch_id="branch-123",
        project_id="proj-456"
    )

    # Verify serialization matches frontend expectations
    json_data = dto.model_dump()
    assert "id" in json_data
    assert "title" in json_data
    assert "assignees_count" in json_data  # Not assigneesCount
```

## Migration Guide

### Before (No Type Safety)

```python
# ❌ No validation, field names might be wrong
def get_task(task_id: str) -> dict:
    task = task_service.get(task_id)
    return {
        "id": str(task.id),
        "title": task.title,
        "assigneeCount": len(task.assignees),  # ❌ Wrong field name!
        # Missing required fields...
    }
```

### After (Type Safe with DTOs)

```python
# ✅ Pydantic validation, guaranteed correct structure
def get_task(task_id: str) -> TaskResponse:
    from fastmcp.types import task_to_dto, TaskResponse

    task = task_service.get(task_id)
    return TaskResponse(
        success=True,
        task=task_to_dto(task)  # ✅ All fields validated
    )
```

## Debugging Type Mismatches

### 1. Check Pydantic Validation Errors

```python
try:
    dto = TaskDTO(**data)
except ValidationError as e:
    print(e.json())
    # Shows exactly which fields are missing or incorrect
```

### 2. Compare with Frontend Type

```typescript
// Frontend expects (api.types.ts):
interface Task {
    id: string;
    assignees_count: number;  // ← snake_case
    // ...
}
```

```python
# Backend provides (api_models.py):
class TaskDTO(BaseModel):
    id: str
    assignees_count: int  # ← Must match exactly
    # ...
```

### 3. Use Helper Functions

```python
# Helper functions handle all field mapping
from fastmcp.types import task_to_dto

# Don't manually create DTOs
task_dto = task_to_dto(task_entity)  # ✅ Guaranteed correct
```

## Best Practices

1. **Always use DTOs for API responses** - Never return domain entities directly
2. **Use helper functions** - `task_to_dto()`, `subtask_to_dto()` handle field mapping
3. **Validate early** - Let Pydantic catch errors before sending to frontend
4. **Match frontend names exactly** - Use `snake_case` to match TypeScript interfaces
5. **Test API contracts** - Write tests verifying DTO structure matches frontend
6. **Document mismatches** - If field names differ, document the mapping

## See Also

- Frontend types: `agenthub-frontend/src/types/api.types.ts`
- Domain entities: `fastmcp/task_management/domain/entities/`
- API endpoints: `fastmcp/task_management/interface/controllers/`