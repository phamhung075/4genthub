# API Endpoints Reference - Type-Safe DTOs

## Overview

All API endpoints in the agenthub system now return type-safe DTOs. This document provides a comprehensive reference for all endpoints, their request/response formats, and usage examples.

**Base URL**: `http://localhost:8000/api`

## Authentication

All endpoints require authentication via JWT token in the Authorization header:

```http
Authorization: Bearer <jwt_token>
```

## Task Management Endpoints

### Create Task

**Endpoint**: `POST /api/tasks`

**Request Body**:
```json
{
    "git_branch_id": "550e8400-e29b-41d4-a716-446655440000",
    "title": "Implement user authentication",
    "description": "Add JWT-based authentication system",
    "assignees": ["coding-agent", "security-auditor-agent"],
    "priority": "high",
    "estimated_effort": "3 days",
    "labels": ["authentication", "security"],
    "due_date": "2025-10-15"
}
```

**Response**: `TaskResponse`
```json
{
    "success": true,
    "task": {
        "id": "task-uuid",
        "title": "Implement user authentication",
        "status": "todo",
        "priority": "high",
        "assignees": ["coding-agent", "security-auditor-agent"],
        "assignees_count": 2,
        "subtask_count": 0,
        "has_dependencies": false,
        "dependency_count": 0,
        "has_context": true,
        "context_id": "ctx-uuid",
        "git_branch_id": "550e8400-e29b-41d4-a716-446655440000",
        "project_id": "proj-uuid",
        "created_at": "2025-09-30T10:00:00Z",
        "updated_at": "2025-09-30T10:00:00Z"
    },
    "message": "Task created successfully",
    "timestamp": "2025-09-30T10:00:00Z"
}
```

### Get Task

**Endpoint**: `GET /api/tasks/{task_id}`

**Response**: `TaskResponse`

### Update Task

**Endpoint**: `PUT /api/tasks/{task_id}`

**Request Body**:
```json
{
    "title": "Updated title",
    "status": "in_progress",
    "progress_percentage": 50,
    "details": "Implementation progress notes"
}
```

**Response**: `TaskResponse`

### Delete Task

**Endpoint**: `DELETE /api/tasks/{task_id}`

**Response**: `DeleteResponse`
```json
{
    "success": true,
    "deleted": true,
    "id": "task-uuid",
    "message": "Task deleted successfully",
    "timestamp": "2025-09-30T10:00:00Z"
}
```

### List Tasks

**Endpoint**: `GET /api/branches/{branch_id}/tasks`

**Query Parameters**:
- `status` (optional): Filter by status
- `priority` (optional): Filter by priority
- `assignee` (optional): Filter by assignee
- `page` (optional): Page number (default: 1)
- `limit` (optional): Items per page (default: 50)

**Response**: `TasksResponse`
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
    "timestamp": "2025-09-30T10:00:00Z"
}
```

### Complete Task

**Endpoint**: `POST /api/tasks/{task_id}/complete`

**Request Body**:
```json
{
    "completion_summary": "JWT authentication implemented with refresh tokens and secure storage",
    "testing_notes": "Unit tests passing, integration tests added for login flow"
}
```

**Response**: `TaskResponse`

### Get Task Statistics

**Endpoint**: `GET /api/tasks/statistics`

**Response**: `StatisticsResponse`
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
    "timestamp": "2025-09-30T10:00:00Z"
}
```

### Count Tasks

**Endpoint**: `GET /api/tasks/count`

**Query Parameters**:
- `status` (optional): Filter by status
- `priority` (optional): Filter by priority

**Response**: `CountResponse`
```json
{
    "success": true,
    "count": 42,
    "filters": {
        "status": "in_progress",
        "priority": "high"
    },
    "message": "Found 42 matching tasks",
    "timestamp": "2025-09-30T10:00:00Z"
}
```

## Subtask Management Endpoints

### Create Subtask

**Endpoint**: `POST /api/tasks/{task_id}/subtasks`

**Request Body**:
```json
{
    "title": "Design database schema",
    "description": "Create user and session tables",
    "assignees": ["coding-agent"]
}
```

**Response**: `SubtaskResponse`
```json
{
    "success": true,
    "subtask": {
        "id": "subtask-uuid",
        "task_id": "task-uuid",
        "title": "Design database schema",
        "status": "todo",
        "priority": "medium",
        "assignees": ["coding-agent"],
        "assignees_count": 1,
        "progress_percentage": 0,
        "created_at": "2025-09-30T10:00:00Z",
        "updated_at": "2025-09-30T10:00:00Z"
    },
    "message": "Subtask created successfully",
    "timestamp": "2025-09-30T10:00:00Z"
}
```

### Get Subtask

**Endpoint**: `GET /api/tasks/{task_id}/subtasks/{subtask_id}`

**Response**: `SubtaskResponse`

### Update Subtask

**Endpoint**: `PUT /api/tasks/{task_id}/subtasks/{subtask_id}`

**Request Body**:
```json
{
    "status": "in_progress",
    "progress_percentage": 75,
    "progress_notes": "Schema designed, creating migrations"
}
```

**Response**: `SubtaskResponse`

### Delete Subtask

**Endpoint**: `DELETE /api/tasks/{task_id}/subtasks/{subtask_id}`

**Response**: `DeleteResponse`

### List Subtasks

**Endpoint**: `GET /api/tasks/{task_id}/subtasks`

**Response**: `SubtasksResponse`
```json
{
    "success": true,
    "subtasks": [
        { "id": "subtask-1", "title": "Subtask 1", ... },
        { "id": "subtask-2", "title": "Subtask 2", ... }
    ],
    "total": 3,
    "message": "Found 3 subtasks",
    "timestamp": "2025-09-30T10:00:00Z"
}
```

### Complete Subtask

**Endpoint**: `POST /api/tasks/{task_id}/subtasks/{subtask_id}/complete`

**Request Body**:
```json
{
    "completion_summary": "Database schema created with proper indexes and relationships",
    "impact_on_parent": "Database layer ready for authentication implementation",
    "insights_found": ["Used compound index for email+status for better query performance"]
}
```

**Response**: `SubtaskResponse`

## Project Management Endpoints

### Create Project

**Endpoint**: `POST /api/projects`

**Request Body**:
```json
{
    "name": "E-commerce Platform",
    "description": "Full-featured e-commerce platform with payment integration"
}
```

**Response**: `ProjectResponse`
```json
{
    "success": true,
    "project": {
        "id": "proj-uuid",
        "name": "E-commerce Platform",
        "description": "Full-featured e-commerce platform with payment integration",
        "owner_id": "user-uuid",
        "status": "active",
        "branch_count": 0,
        "task_count": 0,
        "created_at": "2025-09-30T10:00:00Z",
        "updated_at": "2025-09-30T10:00:00Z"
    },
    "message": "Project created successfully",
    "timestamp": "2025-09-30T10:00:00Z"
}
```

### Get Project

**Endpoint**: `GET /api/projects/{project_id}`

**Response**: `ProjectResponse`

### Update Project

**Endpoint**: `PUT /api/projects/{project_id}`

**Request Body**:
```json
{
    "name": "Updated Project Name",
    "description": "Updated description"
}
```

**Response**: `ProjectResponse`

### Delete Project

**Endpoint**: `DELETE /api/projects/{project_id}`

**Response**: `DeleteResponse`

### List Projects

**Endpoint**: `GET /api/projects`

**Response**: `ProjectsResponse`
```json
{
    "success": true,
    "projects": [
        { "id": "proj-1", "name": "Project 1", ... },
        { "id": "proj-2", "name": "Project 2", ... }
    ],
    "total": 5,
    "message": "Found 5 projects",
    "timestamp": "2025-09-30T10:00:00Z"
}
```

### Get Project Health

**Endpoint**: `GET /api/projects/{project_id}/health`

**Response**: `StatisticsResponse`
```json
{
    "success": true,
    "statistics": {
        "project_id": "proj-uuid",
        "health_score": 85,
        "total_tasks": 100,
        "completed_tasks": 75,
        "blocked_tasks": 5,
        "overdue_tasks": 3,
        "active_branches": 5,
        "test_coverage": 82.5
    },
    "message": "Project health analyzed successfully",
    "timestamp": "2025-09-30T10:00:00Z"
}
```

## Branch Management Endpoints

### Create Branch

**Endpoint**: `POST /api/projects/{project_id}/branches`

**Request Body**:
```json
{
    "name": "feature/user-authentication",
    "git_branch_name": "feature/user-authentication",
    "description": "Implement JWT authentication system"
}
```

**Response**: `BranchResponse`
```json
{
    "success": true,
    "branch": {
        "id": "branch-uuid",
        "project_id": "proj-uuid",
        "name": "feature/user-authentication",
        "git_branch_name": "feature/user-authentication",
        "description": "Implement JWT authentication system",
        "status": "active",
        "is_active": true,
        "task_count": 0,
        "completed_tasks": 0,
        "created_at": "2025-09-30T10:00:00Z",
        "updated_at": "2025-09-30T10:00:00Z"
    },
    "message": "Branch created successfully",
    "timestamp": "2025-09-30T10:00:00Z"
}
```

### Get Branch

**Endpoint**: `GET /api/branches/{branch_id}`

**Response**: `BranchResponse`

### Update Branch

**Endpoint**: `PUT /api/branches/{branch_id}`

**Request Body**:
```json
{
    "name": "Updated branch name",
    "description": "Updated description",
    "status": "completed"
}
```

**Response**: `BranchResponse`

### Delete Branch

**Endpoint**: `DELETE /api/branches/{branch_id}`

**Response**: `DeleteResponse`

### List Branches

**Endpoint**: `GET /api/projects/{project_id}/branches`

**Response**: `BranchesResponse`
```json
{
    "success": true,
    "branches": [
        {
            "id": "branch-1",
            "name": "main",
            "task_count": 50,
            "completed_tasks": 45,
            ...
        },
        {
            "id": "branch-2",
            "name": "feature/auth",
            "task_count": 10,
            "completed_tasks": 3,
            ...
        }
    ],
    "total": 5,
    "message": "Found 5 branches",
    "timestamp": "2025-09-30T10:00:00Z"
}
```

### Get Branch Statistics

**Endpoint**: `GET /api/branches/{branch_id}/statistics`

**Response**: `StatisticsResponse`
```json
{
    "success": true,
    "statistics": {
        "branch_id": "branch-uuid",
        "total_tasks": 25,
        "completed_tasks": 15,
        "in_progress_tasks": 8,
        "blocked_tasks": 2,
        "completion_percentage": 60.0,
        "average_task_duration": "1.5 days"
    },
    "message": "Branch statistics retrieved successfully",
    "timestamp": "2025-09-30T10:00:00Z"
}
```

## Context Management Endpoints

### Get Context

**Endpoint**: `GET /api/contexts/{level}/{context_id}`

**Path Parameters**:
- `level`: Context level (global, project, branch, task)
- `context_id`: Context identifier (user_id for global, project_id, branch_id, or task_id)

**Query Parameters**:
- `include_inherited` (optional): Include inherited context from parent levels (default: false)

**Response**: `ContextResponse`
```json
{
    "success": true,
    "context": {
        "id": "ctx-uuid",
        "level": "task",
        "data": {
            "notes": "Implementation notes",
            "insights": ["Performance optimization applied"],
            "blockers": []
        }
    },
    "level": "task",
    "inherited": {
        "project": { ... },
        "branch": { ... }
    },
    "message": "Context retrieved successfully",
    "timestamp": "2025-09-30T10:00:00Z"
}
```

### Update Context

**Endpoint**: `PUT /api/contexts/{level}/{context_id}`

**Request Body**:
```json
{
    "data": {
        "notes": "Updated implementation notes",
        "insights": ["New insight added"],
        "blockers": ["Waiting for API approval"]
    }
}
```

**Response**: `ContextResponse`

## Agent Management Endpoints

### List Agents

**Endpoint**: `GET /api/projects/{project_id}/agents`

**Response**: `AgentsResponse`
```json
{
    "success": true,
    "agents": [
        {
            "id": "agent-1",
            "name": "coding-agent",
            "type": "coding",
            "status": "active",
            "assigned_tasks": 5
        },
        {
            "id": "agent-2",
            "name": "test-orchestrator-agent",
            "type": "testing",
            "status": "active",
            "assigned_tasks": 3
        }
    ],
    "total": 2,
    "message": "Found 2 agents",
    "timestamp": "2025-09-30T10:00:00Z"
}
```

## System Endpoints

### Health Check

**Endpoint**: `GET /api/health`

**Response**: `HealthResponse`
```json
{
    "success": true,
    "status": "healthy",
    "version": "1.0.0",
    "timestamp": "2025-09-30T10:00:00Z",
    "message": "System is operational"
}
```

## Error Responses

All endpoints return consistent error responses:

### Validation Error (400)

```json
{
    "success": false,
    "error": "Validation error",
    "message": "Title is required and must be at least 3 characters",
    "timestamp": "2025-09-30T10:00:00Z"
}
```

### Not Found (404)

```json
{
    "success": false,
    "error": "Task not found",
    "message": "No task exists with ID: 550e8400-e29b-41d4-a716-446655440000",
    "timestamp": "2025-09-30T10:00:00Z"
}
```

### Unauthorized (401)

```json
{
    "success": false,
    "error": "Unauthorized",
    "message": "Authentication required",
    "timestamp": "2025-09-30T10:00:00Z"
}
```

### Forbidden (403)

```json
{
    "success": false,
    "error": "Forbidden",
    "message": "You do not have permission to access this resource",
    "timestamp": "2025-09-30T10:00:00Z"
}
```

### Internal Server Error (500)

```json
{
    "success": false,
    "error": "Internal server error",
    "message": "An unexpected error occurred. Please try again later.",
    "timestamp": "2025-09-30T10:00:00Z"
}
```

## Usage Examples

### TypeScript/JavaScript (Frontend)

```typescript
import { TaskResponse, TasksResponse } from '@/types/api.types';

// Fetch a task
async function fetchTask(taskId: string): Promise<TaskResponse> {
    const response = await fetch(`/api/tasks/${taskId}`, {
        headers: {
            'Authorization': `Bearer ${token}`,
            'Content-Type': 'application/json'
        }
    });
    return await response.json() as TaskResponse;
}

// Create a task
async function createTask(data: CreateTaskRequest): Promise<TaskResponse> {
    const response = await fetch('/api/tasks', {
        method: 'POST',
        headers: {
            'Authorization': `Bearer ${token}`,
            'Content-Type': 'application/json'
        },
        body: JSON.stringify(data)
    });
    return await response.json() as TaskResponse;
}

// List tasks
async function listTasks(branchId: string): Promise<TasksResponse> {
    const response = await fetch(`/api/branches/${branchId}/tasks`, {
        headers: {
            'Authorization': `Bearer ${token}`,
            'Content-Type': 'application/json'
        }
    });
    return await response.json() as TasksResponse;
}
```

### Python (Backend)

```python
from fastmcp.types import TaskResponse, TasksResponse
from datetime import datetime, timezone

# In controller method
def get_task(self, task_id: str, user_id: str) -> TaskResponse:
    try:
        # Fetch task entity
        task_entity = self.task_repository.find_by_id(task_id)

        if not task_entity:
            return TaskResponse(
                success=False,
                error="Task not found",
                message=f"No task exists with ID: {task_id}",
                timestamp=datetime.now(timezone.utc).isoformat()
            )

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
        logger.error(f"Error retrieving task: {e}")
        return TaskResponse(
            success=False,
            error="Internal server error",
            message=str(e),
            timestamp=datetime.now(timezone.utc).isoformat()
        )
```

## Best Practices

1. **Always check the `success` field** before accessing data
2. **Handle errors gracefully** with proper error messages
3. **Use TypeScript types** for compile-time safety on frontend
4. **Include timestamps** for debugging and caching
5. **Log errors** with proper context for troubleshooting
6. **Validate input** before making API calls
7. **Use proper HTTP status codes** (200, 400, 401, 403, 404, 500)
8. **Include authentication tokens** in all requests
9. **Handle network errors** with retry logic
10. **Cache responses** when appropriate

## Related Documentation

- **DTO Types**: [dto-response-types.md](./dto-response-types.md)
- **Frontend Types**: `agenthub-frontend/src/types/api.types.ts`
- **API Controllers**: `agenthub_main/src/fastmcp/task_management/interface/api_controllers/`
- **Authentication**: [authentication documentation](../authentication/)

## Version History

- **2025-09-30**: Initial API endpoints reference with type-safe DTOs
  - Documented all major endpoints
  - Added request/response examples
  - Included error handling patterns
  - Added usage examples for frontend and backend