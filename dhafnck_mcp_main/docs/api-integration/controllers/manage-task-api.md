# manage_task - Task Management API Documentation

## Overview

The `manage_task` tool provides comprehensive task lifecycle management with Vision System integration, automatic progress tracking, and intelligent workflow guidance. This is the core task management interface for the DhafnckMCP system.

## Base Information

- **Tool Name**: `manage_task`
- **Controller**: `TaskMCPController`
- **Module**: `fastmcp.task_management.interface.mcp_controllers.task_mcp_controller`
- **Authentication**: Required (user context from JWT)
- **Vision System Integration**: ✅ Full AI enrichment and guidance

## Parameters Schema

```json
{
  "type": "object",
  "properties": {
    "action": {
      "type": "string",
      "required": true,
      "description": "Task operation to perform"
    },
    "git_branch_id": {
      "type": "string",
      "description": "[OPTIONAL] Git branch UUID for task context"
    },
    "task_id": {
      "type": "string", 
      "description": "[OPTIONAL] Unique task identifier"
    },
    "title": {
      "type": "string",
      "description": "[OPTIONAL] Task title"
    },
    "description": {
      "type": "string",
      "description": "[OPTIONAL] Detailed task description"
    },
    "priority": {
      "type": "string",
      "description": "[OPTIONAL] Task priority: 'low', 'medium', 'high', 'critical'"
    },
    "status": {
      "type": "string",
      "description": "[OPTIONAL] Task status: 'pending', 'in_progress', 'completed', 'cancelled'"
    },
    "user_id": {
      "type": "string",
      "description": "[OPTIONAL] User identifier for authentication"
    }
  },
  "required": ["action"]
}
```

## Available Actions

### Core Operations

#### `create` - Create New Task

Creates a new task with Vision System enrichment and automatic context setup.

**Required Parameters:**
- `action`: "create"
- `git_branch_id`: Git branch UUID
- `title`: Task title

**Optional Parameters:**
- `description`: Task description
- `priority`: Priority level (default: "medium")
- `status`: Initial status (default: "pending")

**Example Request:**
```json
{
  "action": "create",
  "git_branch_id": "550e8400-e29b-41d4-a716-446655440000",
  "title": "Implement user authentication",
  "description": "Add JWT-based authentication system with refresh tokens",
  "priority": "high"
}
```

**Example Response:**
```json
{
  "success": true,
  "operation": "create",
  "task": {
    "id": "123e4567-e89b-12d3-a456-426614174000",
    "title": "Implement user authentication",
    "description": "Add JWT-based authentication system with refresh tokens",
    "status": "pending",
    "priority": "high",
    "git_branch_id": "550e8400-e29b-41d4-a716-446655440000",
    "created_at": "2025-01-27T10:30:00Z"
  },
  "vision_insights": {
    "enriched_description": "Comprehensive JWT authentication with security best practices...",
    "suggested_subtasks": ["Design auth flow", "Implement JWT service", "Add refresh tokens"],
    "potential_blockers": ["Database schema updates required"],
    "impact_analysis": "High impact on system security and user experience"
  }
}
```

#### `get` - Retrieve Task Details

Retrieves complete task information with inherited context.

**Required Parameters:**
- `action`: "get" 
- `task_id`: Task UUID

**Example Request:**
```json
{
  "action": "get",
  "task_id": "123e4567-e89b-12d3-a456-426614174000"
}
```

#### `update` - Update Task

Updates task properties with automatic progress tracking.

**Required Parameters:**
- `action`: "update"
- `task_id`: Task UUID

**Optional Parameters:**
- `title`: Updated title
- `description`: Updated description  
- `status`: New status
- `priority`: Updated priority

**Example Request:**
```json
{
  "action": "update", 
  "task_id": "123e4567-e89b-12d3-a456-426614174000",
  "status": "in_progress",
  "description": "Updated: JWT implementation in progress with OAuth2 integration"
}
```

#### `complete` - Complete Task

Marks task as complete with comprehensive completion analysis.

**Required Parameters:**
- `action`: "complete"
- `task_id`: Task UUID

**Optional Parameters:**
- `completion_notes`: Summary of completion
- `testing_notes`: Testing performed
- `deliverables`: What was delivered

**Example Request:**
```json
{
  "action": "complete",
  "task_id": "123e4567-e89b-12d3-a456-426614174000", 
  "completion_notes": "JWT authentication fully implemented with refresh token support",
  "testing_notes": "Unit tests added, integration tests pass",
  "deliverables": "AuthService, JWT middleware, refresh token endpoint"
}
```

### Query Operations

#### `list` - List Tasks

Lists tasks with filtering and pagination.

**Required Parameters:**
- `action`: "list"
- `git_branch_id`: Branch context

**Optional Parameters:**
- `status`: Filter by status
- `priority`: Filter by priority
- `limit`: Max results (default: 50)
- `offset`: Pagination offset

#### `search` - Search Tasks

Searches tasks by title, description, or content.

**Required Parameters:**
- `action`: "search"
- `git_branch_id`: Branch context
- `query`: Search query

#### `next` - Get Next Task

Intelligently selects the next task to work on based on priority and dependencies.

**Required Parameters:**
- `action`: "next"
- `git_branch_id`: Branch context

## Vision System Features

### Automatic Enrichment
- **AI-Enhanced Descriptions**: Automatically expands task descriptions with context and details
- **Subtask Suggestions**: Proposes logical task breakdown
- **Blocker Detection**: Identifies potential obstacles
- **Impact Analysis**: Assesses task importance and dependencies

### Workflow Guidance
- **Progress Hints**: Suggests next actions
- **Quality Checkpoints**: Recommends review points
- **Testing Suggestions**: Proposes appropriate testing strategies
- **Documentation Reminders**: Highlights documentation needs

### Strategic Orchestration
- **Dependency Analysis**: Maps task relationships
- **Resource Planning**: Estimates effort and resources
- **Timeline Predictions**: Provides completion estimates
- **Risk Assessment**: Identifies project risks

## Error Handling

### Common Error Codes
- `TASK_NOT_FOUND`: Task ID doesn't exist
- `INVALID_BRANCH`: Git branch ID invalid or inaccessible
- `VALIDATION_ERROR`: Parameter validation failed
- `PERMISSION_DENIED`: User lacks access rights
- `OPERATION_FAILED`: Internal operation failure

### Example Error Response
```json
{
  "success": false,
  "error": "Task not found",
  "error_code": "TASK_NOT_FOUND", 
  "operation": "get",
  "metadata": {
    "task_id": "invalid-uuid",
    "hint": "Verify the task ID exists and you have access"
  }
}
```

## Usage Guidelines

### Best Practices
1. **Always specify git_branch_id** for task context
2. **Use descriptive titles** for better AI enrichment
3. **Leverage Vision System insights** for planning
4. **Update status regularly** for progress tracking
5. **Complete with comprehensive notes** for knowledge retention

### Integration Patterns

#### With Subtasks
```json
// First create parent task
{"action": "create", "title": "Implement Authentication"}
// Then use manage_subtask to break it down
```

#### With Context Management
```json
// Tasks automatically create context entries
// Use manage_context to share insights between sessions
```

#### With Agent Assignment
```json
// Use manage_agent to assign specialized agents to tasks
// Agents receive task context automatically
```

## Related Tools
- **manage_subtask**: Task decomposition and progress tracking
- **manage_context**: Cross-session information sharing
- **manage_git_branch**: Branch-level task organization
- **manage_agent**: Agent assignment and coordination

## Technical Notes

### Authentication
- Uses JWT-based authentication with request context middleware
- User ID extracted from authentication header or provided explicitly
- All operations are user-scoped for multi-tenant isolation

### Database Integration
- SQLAlchemy ORM with UUID primary keys
- Automatic timestamp management
- Foreign key relationships with branches and users
- Optimized queries with eager loading

### Performance Considerations
- Pagination support for large result sets
- Indexed searches on title and description
- Cached Vision System results
- Async operation support for heavy processing