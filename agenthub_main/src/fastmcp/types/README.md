# API Response Models (DTOs)

## Purpose

This module contains **Pydantic models** that exactly match the frontend TypeScript interfaces, ensuring type-safe API communication between backend (Python) and frontend (TypeScript).

## Structure

```
fastmcp/types/
├── __init__.py          # Barrel exports for all DTOs
├── entities.py          # Core domain objects (Task, Subtask, Project, Branch, Rule)
├── summaries.py         # Lightweight objects for list views (summaries)
├── responses.py         # API response wrappers (TaskResponse, etc.)
├── bulk.py              # Bulk operation models
├── converters.py        # Domain entity to DTO conversion helpers
├── README.md            # This file
└── API_MODELS_GUIDE.md  # Comprehensive usage guide
```

## Quick Start

```python
from fastmcp.types import TaskDTO, TaskResponse, task_to_dto

# Convert domain entity to DTO
task_dto = task_to_dto(domain_task)

# Create API response
response = TaskResponse(
    success=True,
    task=task_dto
)

# Response JSON matches frontend TypeScript interface exactly
```

## Available Models

### Response Wrappers
- `ApiResponse` - Base response wrapper
- `TaskResponse`, `TasksResponse` - Task responses
- `SubtaskResponse`, `SubtasksResponse` - Subtask responses
- `ProjectResponse`, `ProjectsResponse` - Project responses
- `BranchResponse`, `BranchesResponse` - Branch responses
- `ContextResponse`, `DeleteResponse`, `HealthResponse`, `AgentsResponse`

### Entity DTOs (Full Objects)
- `TaskDTO` - Complete task with all fields
- `SubtaskDTO` - Complete subtask with all fields
- `ProjectDTO` - Project with branches
- `BranchDTO` - Git branch/task tree
- `RuleDTO` - Cursor rules

### Summary DTOs (Lightweight)
- `TaskSummaryDTO` - Task for list display
- `SubtaskSummaryDTO` - Subtask for list display
- `BranchSummaryDTO` - Branch with statistics
- `ProjectSummaryDTO` - Project overview

### Bulk Operations
- `BulkSummaryRequest` - Bulk query request
- `BulkSummaryResponse` - Bulk query response
- `BulkSummaryMetadata` - Query metadata

### Conversion Helpers
- `task_to_dto()` - Domain Task → TaskDTO
- `subtask_to_dto()` - Domain Subtask → SubtaskDTO
- `task_summary_to_dto()` - Domain Task → TaskSummaryDTO
- `subtask_summary_to_dto()` - Domain Subtask → SubtaskSummaryDTO

## Type Safety Benefits

1. **Exact Field Matching**: Pydantic validates all fields match frontend expectations
2. **Early Error Detection**: Type mismatches caught at development time, not runtime
3. **Field Name Consistency**: Ensures `snake_case` matches frontend TypeScript
4. **Required Field Validation**: Guarantees all required fields are present
5. **Type Conversion**: Automatic conversion from domain entities to API contracts

## Frontend Type Mapping

| Backend (Python)       | Frontend (TypeScript)  | File                    |
|-----------------------|------------------------|-------------------------|
| `TaskDTO`             | `Task`                 | `api.types.ts`          |
| `SubtaskDTO`          | `Subtask`              | `api.types.ts`          |
| `TaskSummaryDTO`      | `TaskSummary`          | `taskTypes.ts`          |
| `SubtaskSummaryDTO`   | `SubtaskSummary`       | `taskTypes.ts`          |
| `TaskResponse`        | `TaskResponse`         | `api.types.ts`          |
| `SubtasksResponse`    | `SubtasksResponse`     | `api.types.ts`          |

## Usage Example

```python
from fastmcp.types import (
    TaskDTO,
    TaskResponse,
    TasksResponse,
    task_to_dto,
    task_summary_to_dto
)

# API endpoint returning single task
def get_task(task_id: str) -> TaskResponse:
    task = task_repository.get_by_id(task_id)
    return TaskResponse(
        success=True,
        task=task_to_dto(task, include_subtasks=True)
    )

# API endpoint returning task list
def list_tasks(branch_id: str) -> TasksResponse:
    tasks = task_repository.list_by_branch(branch_id)
    return TasksResponse(
        success=True,
        tasks=[task_summary_to_dto(t) for t in tasks],
        total=len(tasks)
    )
```

## Documentation

See `API_MODELS_GUIDE.md` for:
- Complete usage patterns
- Field mapping details
- Error handling examples
- Testing API contracts
- Migration guide from dict responses

## Key Concepts

### DTOs (Data Transfer Objects)
DTOs are the **API contract** between backend and frontend. They:
- Define exact structure of API responses
- Match frontend TypeScript interfaces exactly
- Validate all fields at runtime
- Convert domain entities to API format

### Domain Entities vs DTOs
- **Domain Entities**: Business logic and validation (e.g., `Task`, `Subtask`)
- **DTOs**: API representation only (e.g., `TaskDTO`, `SubtaskDTO`)
- **Conversion**: Use helper functions to convert between them

## See Also

- Frontend types: `/agenthub-frontend/src/types/api.types.ts`
- Domain entities: `/fastmcp/task_management/domain/entities/`
- API endpoints: `/fastmcp/task_management/interface/controllers/`
