# manage_dependency - Task Dependency Management API Documentation

## Overview

The `manage_dependency` tool provides comprehensive task dependency management operations for workflow sequencing and project orchestration. This controller handles adding, removing, listing, and clearing task dependencies with automatic circular dependency detection and comprehensive error handling.

## Base Information

- **Tool Name**: `manage_dependency`
- **Controller**: `DependencyMCPController`
- **Module**: `fastmcp.task_management.interface.mcp_controllers.dependency_mcp_controller`
- **Authentication**: Required (user context from JWT)
- **Circular Dependency Protection**: ✅ Automatic detection and prevention

## Parameters Schema

```json
{
  "type": "object",
  "properties": {
    "action": {
      "type": "string",
      "required": true,
      "description": "Dependency management action to perform"
    },
    "task_id": {
      "type": "string",
      "description": "[OPTIONAL] Unique identifier for the target task"
    },
    "project_id": {
      "type": "string",
      "description": "[OPTIONAL] Project identifier for context"
    },
    "git_branch_id": {
      "type": "string",
      "description": "[OPTIONAL] Branch UUID identifier for hierarchical context"
    },
    "git_branch_name": {
      "type": "string",
      "description": "[DEPRECATED] Use git_branch_id (UUID) instead. Task tree identifier for hierarchical context"
    },
    "user_id": {
      "type": "string",
      "description": "[OPTIONAL] User identifier for auditing and access control"
    },
    "dependency_data": {
      "type": "string",
      "description": "[OPTIONAL] JSON string containing dependency information"
    }
  },
  "required": ["action"]
}
```

## Available Actions

### Core Operations

#### `add_dependency` - Add Task Dependency

Adds a dependency relationship between two tasks, establishing workflow sequencing.

**Required Parameters:**
- `action`: "add_dependency"
- `task_id`: Target task UUID
- `dependency_data`: JSON string with `dependency_id` field

**Optional Parameters:**
- `project_id`: Project context (derived from task if not provided)
- `git_branch_id`: Branch UUID (for branch context)
- `user_id`: User identifier for audit trails

**Example Request:**
```json
{
  "action": "add_dependency",
  "task_id": "123e4567-e89b-12d3-a456-426614174000",
  "dependency_data": "{\"dependency_id\": \"456e7890-e89b-12d3-a456-426614174001\"}"
}
```

**Example Response:**
```json
{
  "success": true,
  "message": "Dependency 456e7890-e89b-12d3-a456-426614174001 added to task 123e4567-e89b-12d3-a456-426614174000",
  "task": {
    "id": "123e4567-e89b-12d3-a456-426614174000",
    "title": "Implement user authentication",
    "status": "pending",
    "dependencies": [
      {
        "id": "456e7890-e89b-12d3-a456-426614174001",
        "title": "Setup database schema",
        "status": "completed"
      }
    ],
    "updated_at": "2025-01-27T10:30:00Z"
  }
}
```

#### `remove_dependency` - Remove Task Dependency

Removes an existing dependency relationship between tasks.

**Required Parameters:**
- `action`: "remove_dependency"
- `task_id`: Target task UUID
- `dependency_data`: JSON string with `dependency_id` field

**Optional Parameters:**
- `project_id`: Project context
- `git_branch_id`: Branch UUID
- `user_id`: User identifier

**Example Request:**
```json
{
  "action": "remove_dependency",
  "task_id": "123e4567-e89b-12d3-a456-426614174000",
  "dependency_data": "{\"dependency_id\": \"456e7890-e89b-12d3-a456-426614174001\"}"
}
```

**Example Response:**
```json
{
  "success": true,
  "message": "Dependency 456e7890-e89b-12d3-a456-426614174001 removed from task 123e4567-e89b-12d3-a456-426614174000",
  "task": {
    "id": "123e4567-e89b-12d3-a456-426614174000",
    "title": "Implement user authentication",
    "status": "pending",
    "dependencies": [],
    "updated_at": "2025-01-27T10:30:00Z"
  }
}
```

### Query Operations

#### `get_dependencies` - List Task Dependencies

Retrieves all dependencies for a specific task with detailed dependency information.

> **⚠️ Implementation Status**: This action is currently in development. Core dependency management (add/remove) is fully operational, but some query operations may have limited functionality.

**Required Parameters:**
- `action`: "get_dependencies"
- `task_id`: Target task UUID

**Optional Parameters:**
- `project_id`: Project context
- `git_branch_id`: Branch UUID
- `user_id`: User identifier

**Example Request:**
```json
{
  "action": "get_dependencies",
  "task_id": "123e4567-e89b-12d3-a456-426614174000"
}
```

**Example Response:**
```json
{
  "success": true,
  "task_id": "123e4567-e89b-12d3-a456-426614174000",
  "dependencies": [
    {
      "id": "456e7890-e89b-12d3-a456-426614174001",
      "title": "Setup database schema",
      "status": "completed",
      "priority": "high",
      "completion_percentage": 100,
      "is_blocking": false,
      "estimated_effort": "2 days",
      "assignees": ["@database-agent"],
      "updated_at": "2025-01-26T14:20:00Z"
    },
    {
      "id": "789e0123-e89b-12d3-a456-426614174002", 
      "title": "Design authentication flow",
      "status": "in_progress",
      "priority": "medium",
      "completion_percentage": 75,
      "is_blocking": true,
      "estimated_effort": "1 day",
      "assignees": ["@security-auditor-agent"],
      "updated_at": "2025-01-27T09:15:00Z"
    }
  ],
  "dependency_count": 2,
  "blocking_dependencies": 1,
  "completed_dependencies": 1
}
```

#### `clear_dependencies` - Remove All Dependencies

Removes all dependency relationships from a task.

> **⚠️ Implementation Status**: This action is currently in development. Implementation may be incomplete and requires verification.

**Required Parameters:**
- `action`: "clear_dependencies"
- `task_id`: Target task UUID

**Optional Parameters:**
- `project_id`: Project context
- `git_branch_id`: Branch UUID  
- `user_id`: User identifier

**Example Request:**
```json
{
  "action": "clear_dependencies",
  "task_id": "123e4567-e89b-12d3-a456-426614174000"
}
```

**Example Response:**
```json
{
  "success": true,
  "message": "All dependencies cleared from task 123e4567-e89b-12d3-a456-426614174000",
  "task": {
    "id": "123e4567-e89b-12d3-a456-426614174000",
    "title": "Implement user authentication",
    "status": "pending",
    "dependencies": [],
    "cleared_dependencies_count": 3,
    "updated_at": "2025-01-27T10:30:00Z"
  }
}
```

#### `get_blocking_tasks` - List Blocking Tasks

Retrieves all tasks that are currently blocking the specified task from proceeding.

> **⚠️ Implementation Status**: This action is currently in development. Implementation may be incomplete and requires verification.

**Required Parameters:**
- `action`: "get_blocking_tasks"
- `task_id`: Target task UUID

**Optional Parameters:**
- `project_id`: Project context
- `git_branch_id`: Branch UUID
- `user_id`: User identifier

**Example Request:**
```json
{
  "action": "get_blocking_tasks",
  "task_id": "123e4567-e89b-12d3-a456-426614174000"
}
```

**Example Response:**
```json
{
  "success": true,
  "task_id": "123e4567-e89b-12d3-a456-426614174000",
  "blocking_tasks": [
    {
      "id": "789e0123-e89b-12d3-a456-426614174002",
      "title": "Design authentication flow", 
      "status": "in_progress",
      "priority": "medium",
      "completion_percentage": 75,
      "estimated_completion": "2025-01-28T16:00:00Z",
      "assignees": ["@security-auditor-agent"],
      "blocking_reason": "Authentication design must be complete before implementation"
    }
  ],
  "total_blocking_tasks": 1,
  "estimated_unblock_date": "2025-01-28T16:00:00Z",
  "can_proceed": false
}
```

## Dependency Chain and Graph Documentation

### Dependency Relationships

The dependency system supports complex workflow patterns:

#### Linear Dependencies
```
Task A → Task B → Task C
```
Task C depends on Task B, which depends on Task A.

#### Parallel Dependencies  
```
Task A → Task C
Task B → Task C
```
Task C depends on both Task A and Task B completing.

#### Complex Graph
```
Task A → Task C → Task E
Task B → Task D → Task E
Task A → Task D
```
Multiple dependency paths with shared prerequisites.

### Circular Dependency Prevention

The system automatically detects and prevents circular dependencies:

**Prohibited Pattern:**
```
Task A → Task B → Task C → Task A  // Circular dependency
```

**Error Response for Circular Dependency:**
```json
{
  "success": false,
  "error": "Circular dependency detected: Task cannot depend on itself directly or indirectly",
  "error_code": "CIRCULAR_DEPENDENCY",
  "dependency_chain": ["task-a-id", "task-b-id", "task-c-id", "task-a-id"],
  "hint": "Remove one of the dependencies in the chain to break the cycle"
}
```

### Dependency Status Impact

Dependencies affect task workflow:

- **Blocked**: Task cannot start if dependencies are incomplete
- **Ready**: All dependencies completed, task can proceed
- **In Progress**: Task can continue while non-critical dependencies complete
- **Partial Block**: Some dependencies complete, others pending

## JSON-RPC Format Examples

### Add Dependency (JSON-RPC)
```json
{
  "jsonrpc": "2.0",
  "id": 1,
  "method": "manage_dependency",
  "params": {
    "action": "add_dependency",
    "task_id": "123e4567-e89b-12d3-a456-426614174000",
    "dependency_data": "{\"dependency_id\": \"456e7890-e89b-12d3-a456-426614174001\"}"
  }
}
```

### List Dependencies (JSON-RPC)
```json
{
  "jsonrpc": "2.0", 
  "id": 2,
  "method": "manage_dependency",
  "params": {
    "action": "get_dependencies",
    "task_id": "123e4567-e89b-12d3-a456-426614174000"
  }
}
```

### Remove All Dependencies (JSON-RPC)
```json
{
  "jsonrpc": "2.0",
  "id": 3,
  "method": "manage_dependency", 
  "params": {
    "action": "clear_dependencies",
    "task_id": "123e4567-e89b-12d3-a456-426614174000"
  }
}
```

## Error Handling

### Common Error Codes

- `MISSING_FIELD`: Required parameter missing
- `TASK_NOT_FOUND`: Task ID doesn't exist or is inaccessible
- `DEPENDENCY_NOT_FOUND`: Dependency task doesn't exist
- `CIRCULAR_DEPENDENCY`: Circular dependency detected
- `INVALID_JSON`: Malformed dependency_data parameter
- `UNKNOWN_ACTION`: Invalid action parameter
- `PERMISSION_DENIED`: User lacks access rights
- `VALIDATION_ERROR`: Parameter validation failed
- `INTERNAL_ERROR`: System error during operation

### Error Response Examples

#### Missing Required Field
```json
{
  "success": false,
  "error": "Missing required field: task_id",
  "error_code": "MISSING_FIELD",
  "field": "task_id",
  "expected": "A valid task_id string",
  "hint": "Include 'task_id' in your request body"
}
```

#### Missing Dependency ID
```json
{
  "success": false,
  "error": "Missing required field: dependency_id in dependency_data",
  "error_code": "MISSING_FIELD", 
  "field": "dependency_data.dependency_id",
  "expected": "A valid dependency_id string inside dependency_data",
  "hint": "Include 'dependency_data': {'dependency_id': ...} in your request body"
}
```

#### Task Not Found
```json
{
  "success": false,
  "error": "Task with ID 123e4567-e89b-12d3-a456-426614174000 not found",
  "error_code": "TASK_NOT_FOUND",
  "task_id": "123e4567-e89b-12d3-a456-426614174000",
  "hint": "Verify the task ID exists and you have access"
}
```

#### Self-Dependency Error
```json
{
  "success": false,
  "error": "Task cannot depend on itself",
  "error_code": "CIRCULAR_DEPENDENCY",
  "task_id": "123e4567-e89b-12d3-a456-426614174000",
  "dependency_id": "123e4567-e89b-12d3-a456-426614174000"
}
```

#### Invalid JSON in dependency_data
```json
{
  "success": false,
  "error": "Invalid JSON in dependency_data parameter: Expecting property name enclosed in double quotes",
  "error_code": "INVALID_JSON",
  "field": "dependency_data",
  "hint": "Ensure dependency_data parameter contains valid JSON"
}
```

#### Unknown Action
```json
{
  "success": false,
  "error": "Unknown dependency action: invalid_action",
  "error_code": "UNKNOWN_ACTION",
  "field": "action", 
  "expected": "One of: add_dependency, remove_dependency, get_dependencies, clear_dependencies, get_blocking_tasks",
  "hint": "Check the 'action' parameter for typos"
}
```

## Usage Guidelines

### Best Practices

1. **Validate Dependencies**: Always verify dependent tasks exist before adding dependencies
2. **Check for Cycles**: The system prevents cycles, but plan dependencies thoughtfully
3. **Use Descriptive Naming**: Clear task titles help understand dependency relationships
4. **Monitor Blocking Tasks**: Regular checks prevent workflow bottlenecks
5. **Clean Up Dependencies**: Remove obsolete dependencies to maintain clean workflows

### Workflow Patterns

#### Sequential Task Implementation
```json
// Step 1: Add foundational dependency
{"action": "add_dependency", "task_id": "implement-feature", "dependency_data": "{\"dependency_id\": \"design-feature\"}"}

// Step 2: Add testing dependency  
{"action": "add_dependency", "task_id": "deploy-feature", "dependency_data": "{\"dependency_id\": \"test-feature\"}"}

// Step 3: Chain implementation to testing
{"action": "add_dependency", "task_id": "test-feature", "dependency_data": "{\"dependency_id\": \"implement-feature\"}"}
```

#### Parallel Development with Merge Point
```json
// Frontend and backend can work in parallel
{"action": "add_dependency", "task_id": "integration-testing", "dependency_data": "{\"dependency_id\": \"frontend-implementation\"}"}
{"action": "add_dependency", "task_id": "integration-testing", "dependency_data": "{\"dependency_id\": \"backend-implementation\"}"}
```

#### Dependency Cleanup During Refactoring
```json
// Remove all old dependencies
{"action": "clear_dependencies", "task_id": "refactored-task"}

// Add new streamlined dependencies
{"action": "add_dependency", "task_id": "refactored-task", "dependency_data": "{\"dependency_id\": \"new-prerequisite\"}"}
```

## Integration Patterns

### With Task Management
```json
// Create task with immediate dependency setup
// 1. Create tasks using manage_task
// 2. Establish dependencies using manage_dependency 
// 3. Monitor progress with get_blocking_tasks
```

### With Project Workflow
```json
// Project-level dependency coordination
// 1. Use project_id to scope dependencies within projects
// 2. Coordinate cross-branch dependencies via git_branch_id (UUID)
// 3. Maintain audit trails with user_id tracking
```

### With Agent Assignment
```json
// Dependency-aware agent coordination
// 1. Check blocking tasks before assigning work
// 2. Coordinate agent handoffs at dependency boundaries  
// 3. Update dependencies when agents complete work
```

## Related Tools

- **manage_task**: Core task lifecycle management and creation
- **manage_subtask**: Task decomposition with automatic dependency inheritance
- **manage_project**: Project-level coordination and resource management
- **manage_git_branch**: Branch-based task organization and workflow management
- **manage_context**: Cross-session dependency context sharing

## Technical Notes

### Authentication & Security
- JWT-based authentication with request context middleware
- User ID extracted from authentication header or provided explicitly
- All operations are user-scoped for multi-tenant isolation
- Dependency modifications logged for audit trails

### Database Integration
- SQLAlchemy ORM with UUID foreign key relationships
- Optimized dependency queries with eager loading
- Constraint-based circular dependency prevention
- Atomic operations for consistency during dependency changes

### Performance Considerations
- Indexed dependency lookups for fast relationship queries
- Cached dependency graphs for complex workflows
- Batch operations support for bulk dependency management
- Async operation support for heavy dependency resolution

### Validation Rules
- Task existence validation before dependency creation
- Cross-context task lookup for dependencies in different branches
- Automatic cleanup of orphaned dependencies
- Comprehensive error messaging for debugging workflow issues