# API Response DTO Types Documentation

## Overview

All API controllers in the agenthub system now use type-safe Data Transfer Objects (DTOs) for responses. This ensures consistency between backend and frontend, with TypeScript types matching Python Pydantic models.

**Location**: `agenthub_main/src/fastmcp/types/`
- **responses.py**: Response wrapper types
- **entities.py**: Core entity DTOs

## Response Type Hierarchy

```
ApiResponse (Base)
├── TaskResponse (single task)
├── TasksResponse (task list)
├── SubtaskResponse (single subtask)
├── SubtasksResponse (subtask list)
├── ProjectResponse (single project)
├── ProjectsResponse (project list)
├── BranchResponse (single branch)
├── BranchesResponse (branch list)
├── ContextResponse (context data)
├── DeleteResponse (deletion confirmation)
├── HealthResponse (health check)
├── AgentsResponse (agent list)
├── StatisticsResponse (metrics)
└── CountResponse (count queries)
```

## Core Response Types

### 1. TaskResponse

**Purpose**: Single task operation responses (create, get, update)

**Structure**:
```python
class TaskResponse(BaseModel):
    success: bool = True
    task: TaskDTO
    error: Optional[str] = None
    message: Optional[str] = None
    timestamp: Optional[str] = None
```

**TaskDTO Fields**:
```python
{
    "id": str,                          # UUID
    "title": str,                       # Task title
    "description": Optional[str],       # Detailed description
    "status": str,                      # todo, in_progress, blocked, review, testing, done, cancelled
    "priority": str,                    # low, medium, high, urgent, critical
    "assignees": Optional[List[str]],   # Agent identifiers
    "assignees_count": int,             # Number of assigned agents
    "subtask_count": int,               # Number of subtasks
    "has_dependencies": bool,           # Whether task has dependencies
    "dependency_count": Optional[int],  # Number of dependencies
    "dependencies": Optional[List[str]], # Dependency UUIDs
    "has_context": bool,                # Whether task has context data
    "context_id": Optional[str],        # Context UUID
    "context_data": Optional[Any],      # Context payload
    "git_branch_id": str,               # Branch UUID
    "project_id": str,                  # Project UUID
    "created_at": Optional[str],        # ISO 8601 timestamp
    "updated_at": Optional[str],        # ISO 8601 timestamp
    "due_date": Optional[str],          # ISO 8601 date
    "estimated_effort": Optional[str],  # e.g., "2 hours", "3 days"
    "labels": Optional[List[str]],      # Task tags
    "details": Optional[str],           # Implementation notes
    "progress_percentage": Optional[int], # 0-100
    "subtasks": Optional[List[SubtaskDTO]] # Nested subtasks
}
```

**Example Response**:
```json
{
    "success": true,
    "task": {
        "id": "550e8400-e29b-41d4-a716-446655440000",
        "title": "Implement JWT authentication",
        "description": "Add JWT-based auth with login, logout, and session management",
        "status": "in_progress",
        "priority": "high",
        "assignees": ["coding-agent", "security-auditor-agent"],
        "assignees_count": 2,
        "subtask_count": 3,
        "has_dependencies": false,
        "dependency_count": 0,
        "has_context": true,
        "context_id": "ctx-uuid",
        "git_branch_id": "branch-uuid",
        "project_id": "proj-uuid",
        "progress_percentage": 60,
        "created_at": "2025-09-30T10:00:00Z",
        "updated_at": "2025-09-30T10:30:00Z"
    },
    "message": "Task retrieved successfully",
    "timestamp": "2025-09-30T10:30:00Z"
}
```

### 2. TasksResponse

**Purpose**: List/search operations returning multiple tasks

**Structure**:
```python
class TasksResponse(BaseModel):
    success: bool = True
    tasks: List[TaskDTO]
    total: Optional[int] = None        # Total count (for pagination)
    page: Optional[int] = None         # Current page number
    limit: Optional[int] = None        # Items per page
    error: Optional[str] = None
    message: Optional[str] = None
    timestamp: Optional[str] = None
```

**Example Response**:
```json
{
    "success": true,
    "tasks": [
        { "id": "task-1", "title": "Task 1", ... },
        { "id": "task-2", "title": "Task 2", ... }
    ],
    "total": 25,
    "page": 1,
    "limit": 10,
    "message": "Found 25 tasks",
    "timestamp": "2025-09-30T10:30:00Z"
}
```

### 3. SubtaskResponse

**Purpose**: Single subtask operation responses

**Structure**:
```python
class SubtaskResponse(BaseModel):
    success: bool = True
    subtask: SubtaskDTO
    error: Optional[str] = None
    message: Optional[str] = None
    timestamp: Optional[str] = None
```

**SubtaskDTO Fields**:
```python
{
    "id": str,                          # UUID
    "task_id": str,                     # Parent task UUID (matches parent_task_id in frontend)
    "title": str,                       # Subtask title
    "description": Optional[str],       # Detailed description
    "status": str,                      # todo, in_progress, done
    "priority": str,                    # low, medium, high, urgent, critical
    "assignees": Optional[List[str]],   # Agent identifiers (inherits from parent if not set)
    "assignees_count": int,             # Number of assigned agents
    "progress_percentage": Optional[int], # 0-100
    "created_at": Optional[str],        # ISO 8601 timestamp
    "updated_at": Optional[str],        # ISO 8601 timestamp
    "progress_notes": Optional[str],    # Work progress notes
    "completion_summary": Optional[str] # Final summary when completed
}
```

### 4. SubtasksResponse

**Purpose**: List operations returning multiple subtasks

**Structure**:
```python
class SubtasksResponse(BaseModel):
    success: bool = True
    subtasks: List[SubtaskDTO]
    total: Optional[int] = None
    error: Optional[str] = None
    message: Optional[str] = None
    timestamp: Optional[str] = None
```

### 5. ProjectResponse

**Purpose**: Single project operation responses

**Structure**:
```python
class ProjectResponse(BaseModel):
    success: bool = True
    project: ProjectDTO
    error: Optional[str] = None
    message: Optional[str] = None
    timestamp: Optional[str] = None
```

**ProjectDTO Fields**:
```python
{
    "id": str,                          # UUID
    "name": str,                        # Project name
    "description": Optional[str],       # Project description
    "created_at": Optional[str],        # ISO 8601 timestamp
    "updated_at": Optional[str],        # ISO 8601 timestamp
    "owner_id": Optional[str],          # User UUID
    "status": Optional[str],            # Project status
    "branch_count": Optional[int],      # Number of branches
    "task_count": Optional[int],        # Number of tasks
    "git_branchs": Optional[Dict[str, BranchDTO]], # Branches as dictionary (API format)
    "branches": Optional[List[BranchDTO]] # Branches as list (legacy format)
}
```

### 6. ProjectsResponse

**Purpose**: List operations returning multiple projects

**Structure**:
```python
class ProjectsResponse(BaseModel):
    success: bool = True
    projects: List[ProjectDTO]
    total: Optional[int] = None
    error: Optional[str] = None
    message: Optional[str] = None
    timestamp: Optional[str] = None
```

### 7. BranchResponse

**Purpose**: Single branch operation responses

**Structure**:
```python
class BranchResponse(BaseModel):
    success: bool = True
    branch: BranchDTO
    error: Optional[str] = None
    message: Optional[str] = None
    timestamp: Optional[str] = None
```

**BranchDTO Fields**:
```python
{
    "id": str,                          # UUID
    "project_id": str,                  # Parent project UUID
    "name": str,                        # Display name
    "git_branch_name": str,             # Git branch name
    "description": Optional[str],       # Branch description
    "status": Optional[str],            # Branch status
    "is_active": Optional[bool],        # Active flag
    "created_at": Optional[str],        # ISO 8601 timestamp
    "updated_at": Optional[str],        # ISO 8601 timestamp
    "task_count": Optional[int],        # Number of tasks
    "completed_tasks": Optional[int]    # Number of completed tasks
}
```

### 8. BranchesResponse

**Purpose**: List operations returning multiple branches

**Structure**:
```python
class BranchesResponse(BaseModel):
    success: bool = True
    branches: List[BranchDTO]
    total: Optional[int] = None
    error: Optional[str] = None
    message: Optional[str] = None
    timestamp: Optional[str] = None
```

### 9. DeleteResponse

**Purpose**: Deletion operation confirmations

**Structure**:
```python
class DeleteResponse(BaseModel):
    success: bool = True
    deleted: Optional[bool] = None      # Confirmation flag
    id: Optional[str] = None            # Deleted entity UUID
    error: Optional[str] = None
    message: Optional[str] = None
    timestamp: Optional[str] = None
```

**Example Response**:
```json
{
    "success": true,
    "deleted": true,
    "id": "550e8400-e29b-41d4-a716-446655440000",
    "message": "Task deleted successfully",
    "timestamp": "2025-09-30T10:30:00Z"
}
```

### 10. StatisticsResponse

**Purpose**: Metrics and statistics queries

**Structure**:
```python
class StatisticsResponse(BaseModel):
    success: bool = True
    statistics: Optional[Any] = None    # Flexible statistics payload
    error: Optional[str] = None
    message: Optional[str] = None
    timestamp: Optional[str] = None
```

**Example Response**:
```json
{
    "success": true,
    "statistics": {
        "total_tasks": 100,
        "completed_tasks": 75,
        "in_progress_tasks": 20,
        "blocked_tasks": 5,
        "completion_rate": 0.75,
        "average_completion_time": "2.5 days"
    },
    "timestamp": "2025-09-30T10:30:00Z"
}
```

### 11. CountResponse

**Purpose**: Count queries with filters

**Structure**:
```python
class CountResponse(BaseModel):
    success: bool = True
    count: Optional[int] = None         # Result count
    filters: Optional[Any] = None       # Applied filters
    error: Optional[str] = None
    message: Optional[str] = None
    timestamp: Optional[str] = None
```

**Example Response**:
```json
{
    "success": true,
    "count": 42,
    "filters": {
        "status": "in_progress",
        "priority": "high"
    },
    "message": "Found 42 matching tasks",
    "timestamp": "2025-09-30T10:30:00Z"
}
```

## Utility Response Types

### 12. ContextResponse

**Purpose**: Context data retrieval

**Structure**:
```python
class ContextResponse(BaseModel):
    success: bool = True
    context: Any                        # Context data payload
    level: Optional[str] = None         # Context level (global, project, branch, task)
    inherited: Optional[Any] = None     # Inherited context from parent levels
    error: Optional[str] = None
    message: Optional[str] = None
    timestamp: Optional[str] = None
```

### 13. HealthResponse

**Purpose**: System health checks

**Structure**:
```python
class HealthResponse(BaseModel):
    success: bool = True
    status: str                         # "healthy", "degraded", "down"
    version: Optional[str] = None       # System version
    timestamp: str                      # ISO 8601 timestamp
    error: Optional[str] = None
    message: Optional[str] = None
```

### 14. AgentsResponse

**Purpose**: Agent listing operations

**Structure**:
```python
class AgentsResponse(BaseModel):
    success: bool = True
    agents: List[Any]                   # Agent data (flexible structure)
    total: Optional[int] = None
    error: Optional[str] = None
    message: Optional[str] = None
    timestamp: Optional[str] = None
```

### 15. ApiResponse (Base)

**Purpose**: Generic response wrapper (fallback)

**Structure**:
```python
class ApiResponse(BaseModel):
    success: bool
    data: Optional[Any] = None          # Generic data payload
    error: Optional[str] = None
    message: Optional[str] = None
    timestamp: Optional[str] = None
```

## Error Handling

All response types include error handling fields:

**Error Response Example**:
```json
{
    "success": false,
    "error": "Task not found",
    "message": "No task exists with ID: 550e8400-e29b-41d4-a716-446655440000",
    "timestamp": "2025-09-30T10:30:00Z"
}
```

**Common Error Messages**:
- `"Task not found"` - Entity does not exist
- `"Validation error: {details}"` - Invalid input data
- `"Unauthorized"` - Authentication required
- `"Forbidden"` - Insufficient permissions
- `"Internal server error"` - Unexpected server error

## Using DTOs in Controllers

### Converting Entities to DTOs

**Import Conversion Functions**:
```python
from fastmcp.types import (
    task_to_dto,
    task_summary_to_dto,
    subtask_to_dto,
    subtask_summary_to_dto,
    project_to_dto,
    branch_to_dto,
    TaskResponse,
    TasksResponse,
    SubtaskResponse,
    SubtasksResponse,
    ProjectResponse,
    ProjectsResponse,
    BranchResponse,
    BranchesResponse,
    DeleteResponse,
    StatisticsResponse,
    CountResponse
)
```

**Example Controller Method**:
```python
def get_task(self, task_id: str, user_id: str, session) -> TaskResponse:
    """
    Retrieve a task by ID.

    Args:
        task_id: Task UUID identifier
        user_id: Authenticated user ID
        session: Database session

    Returns:
        TaskResponse: Type-safe response with task data

    Raises:
        ValueError: If task_id is invalid
        PermissionError: If user lacks access
    """
    try:
        facade = self.facade_service.get_task_facade(
            project_id=None,
            git_branch_id=None,
            user_id=user_id
        )

        task_entity = facade.get_task(task_id)

        # Convert to DTO
        task_dto = task_to_dto(task_entity)

        # Return type-safe response
        return TaskResponse(
            success=True,
            task=task_dto,
            message="Task retrieved successfully",
            timestamp=datetime.now(timezone.utc).isoformat()
        )
    except Exception as e:
        return TaskResponse(
            success=False,
            error=str(e),
            message="Failed to retrieve task",
            timestamp=datetime.now(timezone.utc).isoformat()
        )
```

## Frontend Integration

### TypeScript Types

Frontend types are defined in `agenthub-frontend/src/types/api.types.ts` and match these DTOs exactly:

```typescript
// Matches TaskResponse
interface TaskResponse {
    success: boolean;
    task?: Task;
    error?: string;
    message?: string;
    timestamp?: string;
}

// Matches TaskDTO
interface Task {
    id: string;
    title: string;
    description?: string;
    status: TaskStatus;
    priority: TaskPriority;
    assignees?: string[];
    assignees_count: number;
    subtask_count: number;
    has_dependencies: boolean;
    dependency_count?: number;
    dependencies?: string[];
    has_context: boolean;
    context_id?: string;
    context_data?: any;
    git_branch_id: string;
    project_id: string;
    created_at?: string;
    updated_at?: string;
    due_date?: string;
    estimated_effort?: string;
    labels?: string[];
    details?: string;
    progress_percentage?: number;
    subtasks?: Subtask[];
}
```

### API Usage Examples

**Fetching a Task**:
```typescript
import { TaskResponse } from '@/types/api.types';

async function fetchTask(taskId: string): Promise<TaskResponse> {
    const response = await fetch(`/api/tasks/${taskId}`);
    return await response.json() as TaskResponse;
}

// Usage
const result = await fetchTask('task-uuid');
if (result.success && result.task) {
    console.log('Task:', result.task.title);
    console.log('Progress:', result.task.progress_percentage);
} else {
    console.error('Error:', result.error);
}
```

**Creating a Task**:
```typescript
async function createTask(data: CreateTaskRequest): Promise<TaskResponse> {
    const response = await fetch('/api/tasks', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(data)
    });
    return await response.json() as TaskResponse;
}
```

**Listing Tasks**:
```typescript
async function listTasks(branchId: string): Promise<TasksResponse> {
    const response = await fetch(`/api/branches/${branchId}/tasks`);
    return await response.json() as TasksResponse;
}

// Usage
const result = await listTasks('branch-uuid');
if (result.success && result.tasks) {
    console.log(`Found ${result.total} tasks`);
    result.tasks.forEach(task => {
        console.log(`- ${task.title} (${task.status})`);
    });
}
```

## Best Practices

### 1. Always Use Type-Safe Responses

**Good**:
```python
def get_task(self, task_id: str) -> TaskResponse:
    # ...
    return TaskResponse(success=True, task=task_dto)
```

**Bad**:
```python
def get_task(self, task_id: str) -> dict:
    # ...
    return {"success": True, "task": task_dict}  # Not type-safe
```

### 2. Include Timestamps

Always include timestamps in responses for debugging and caching:

```python
return TaskResponse(
    success=True,
    task=task_dto,
    timestamp=datetime.now(timezone.utc).isoformat()
)
```

### 3. Use Conversion Functions

Use the provided conversion functions instead of manual mapping:

```python
# Good
task_dto = task_to_dto(task_entity)

# Bad
task_dto = TaskDTO(
    id=str(task_entity.id),
    title=task_entity.title,
    # ... manual mapping is error-prone
)
```

### 4. Handle Errors Consistently

```python
try:
    # ... operation
    return TaskResponse(success=True, task=task_dto)
except ValueError as e:
    return TaskResponse(
        success=False,
        error="Validation error",
        message=str(e)
    )
except Exception as e:
    logger.error(f"Unexpected error: {e}")
    return TaskResponse(
        success=False,
        error="Internal server error",
        message="An unexpected error occurred"
    )
```

### 5. Document Response Structures

Always document the response structure in controller docstrings:

```python
def get_task(self, task_id: str) -> TaskResponse:
    """
    Retrieve a task by ID.

    Returns:
        TaskResponse: {
            "success": bool,
            "task": TaskDTO,
            "message": str,
            "timestamp": str (ISO 8601)
        }
    """
```

## Migration Notes

### For Developers

If you're migrating old controller code to use DTOs:

1. **Update Imports**:
   ```python
   from fastmcp.types import (
       TaskResponse, TasksResponse,
       task_to_dto, task_summary_to_dto
   )
   ```

2. **Change Return Types**:
   ```python
   # Old
   def get_task(self, task_id: str) -> dict:

   # New
   def get_task(self, task_id: str) -> TaskResponse:
   ```

3. **Use Conversion Functions**:
   ```python
   # Old
   return {"success": True, "task": entity.__dict__}

   # New
   return TaskResponse(success=True, task=task_to_dto(entity))
   ```

4. **Update Tests**:
   ```python
   # Old
   assert response["success"] == True

   # New
   assert response.success == True
   assert isinstance(response, TaskResponse)
   ```

## Related Documentation

- **DTO Definitions**: `agenthub_main/src/fastmcp/types/responses.py`
- **Entity DTOs**: `agenthub_main/src/fastmcp/types/entities.py`
- **Frontend Types**: `agenthub-frontend/src/types/api.types.ts`
- **Conversion Functions**: `agenthub_main/src/fastmcp/types/converters.py`
- **API Controllers**: `agenthub_main/src/fastmcp/task_management/interface/api_controllers/`

## Version History

- **2025-09-30**: Initial DTO response types documentation
  - Documented all 15 response types
  - Added conversion examples
  - Included frontend integration guide
  - Added migration notes