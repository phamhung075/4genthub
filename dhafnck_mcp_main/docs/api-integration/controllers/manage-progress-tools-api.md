# manage_progress_tools - Progress Tracking API Documentation

## Overview

The `manage_progress_tools` provides simple, AI-friendly progress reporting utilities for task management without requiring deep understanding of the context structure. This is part of the Vision System Phase 2: Progress Reporting Tools, designed to enable effortless progress tracking and workflow management.

## Base Information

- **Tool Name**: `manage_progress_tools`
- **Controller**: `ProgressToolsController`  
- **Module**: `fastmcp.task_management.interface.mcp_controllers.progress_tools_controller`
- **Architecture**: Modular implementation with Factory Pattern
- **Authentication**: Required (user context from JWT)
- **Vision System Integration**: ✅ Automatic context updates and workflow guidance

## Architecture Overview

The controller uses a modular architecture with specialized handlers:

- **ProgressOperationFactory**: Routes operations to appropriate handlers
- **ProgressReportingHandler**: Handles progress reporting and quick updates
- **WorkflowHandler**: Manages work checkpoints and state tracking
- **ContextHandler**: Updates structured work context information
- **StandardResponseFormatter**: Provides consistent response formatting

## Parameters Schema

> **📋 Parameter Handling**: Parameters are passed directly to controller methods without intermediate model classes. All parameter validation is handled at the controller level using the schema below.

```json
{
  "type": "object",
  "properties": {
    "action": {
      "type": "string",
      "required": true,
      "description": "Progress operation to perform",
      "enum": ["report_progress", "quick_task_update", "checkpoint_work", "update_work_context"]
    },
    "task_id": {
      "type": "string",
      "description": "Task identifier (UUID) - required for all operations"
    },
    "progress_type": {
      "type": "string",
      "description": "Type of progress being reported",
      "enum": ["analysis", "implementation", "testing", "debugging", "documentation", "review", "research", "planning", "integration", "deployment"]
    },
    "description": {
      "type": "string",
      "description": "Progress description or work summary"
    },
    "percentage": {
      "type": "integer",
      "description": "Progress percentage (0-100)",
      "minimum": 0,
      "maximum": 100
    },
    "files_affected": {
      "type": "array",
      "items": {"type": "string"},
      "description": "List of files affected by the work"
    },
    "next_steps": {
      "type": "array", 
      "items": {"type": "string"},
      "description": "Planned next steps"
    },
    "status": {
      "type": "string",
      "description": "Task status update",
      "enum": ["pending", "in_progress", "review", "testing", "completed", "cancelled"]
    },
    "notes": {
      "type": "string",
      "description": "Quick notes or updates"
    },
    "completed_work": {
      "type": "string",
      "description": "Description of completed work"
    },
    "current_state": {
      "type": "string",
      "description": "Current work state for checkpointing"
    },
    "files_read": {
      "type": "array",
      "items": {"type": "string"},
      "description": "Files that were read/analyzed"
    },
    "files_modified": {
      "type": "array",
      "items": {"type": "string"}, 
      "description": "Files that were modified/created"
    },
    "key_decisions": {
      "type": "array",
      "items": {"type": "string"},
      "description": "Key decisions made during work"
    },
    "discoveries": {
      "type": "array",
      "items": {"type": "string"},
      "description": "Important discoveries or insights"
    },
    "test_results": {
      "type": "object",
      "description": "Test execution results and metrics"
    }
  },
  "required": ["action"]
}
```

## Available Actions

### Progress Reporting Operations

#### `report_progress` - Report Task Progress

Reports progress on a task with structured information and automatic context updates.

**Required Parameters:**
- `action`: "report_progress"
- `task_id`: Task UUID
- `progress_type`: Type of progress (from valid types)
- `description`: Progress description

**Optional Parameters:**
- `percentage`: Progress percentage (0-100)
- `files_affected`: List of affected files
- `next_steps`: Planned next steps

**Valid Progress Types:**
- `analysis` - Code analysis, research, investigation
- `implementation` - Code writing, feature development
- `testing` - Test creation, test execution
- `debugging` - Bug investigation, problem solving
- `documentation` - Documentation writing, updates
- `review` - Code review, design review
- `research` - Technology research, requirements analysis
- `planning` - Task planning, architectural planning
- `integration` - System integration, component integration
- `deployment` - Deployment activities, CI/CD

**Example Request:**
```json
{
  "action": "report_progress",
  "task_id": "123e4567-e89b-12d3-a456-426614174000",
  "progress_type": "implementation",
  "description": "Completed JWT authentication logic and token validation",
  "percentage": 75,
  "files_affected": [
    "src/auth/jwt_handler.py",
    "src/auth/token_validator.py"
  ],
  "next_steps": [
    "Add refresh token functionality",
    "Write unit tests for authentication"
  ]
}
```

**Example Response:**
```json
{
  "success": true,
  "operation": "report_progress",
  "status": "success",
  "data": {
    "progress_type": "implementation",
    "percentage": 75,
    "next_reminder": "Progress will be tracked automatically",
    "hint": "Good progress! Remember to document key decisions."
  },
  "message": "Progress reported for task 123e4567-e89b-12d3-a456-426614174000",
  "metadata": {
    "task_id": "123e4567-e89b-12d3-a456-426614174000"
  },
  "timestamp": "2025-01-27T14:30:00Z"
}
```

#### `quick_task_update` - Quick Task Status Update

Provides a simple way to update task status and add notes without complex parameters.

**Required Parameters:**
- `action`: "quick_task_update"
- `task_id`: Task UUID

**Optional Parameters:**
- `status`: New task status
- `notes`: Quick notes or updates
- `completed_work`: Description of completed work

**Example Request:**
```json
{
  "action": "quick_task_update",
  "task_id": "123e4567-e89b-12d3-a456-426614174000",
  "status": "in_progress",
  "notes": "Started working on authentication module",
  "completed_work": "Set up project structure and dependencies"
}
```

**Example Response:**
```json
{
  "success": true,
  "operation": "quick_task_update",
  "status": "success",
  "data": {
    "updated_fields": ["status", "status_change", "quick_notes", "completed_work"],
    "status_updated": true,
    "context_updated": true
  },
  "message": "Task 123e4567-e89b-12d3-a456-426614174000 updated successfully",
  "metadata": {
    "task_id": "123e4567-e89b-12d3-a456-426614174000"
  },
  "timestamp": "2025-01-27T14:30:00Z"
}
```

### Workflow Management Operations

#### `checkpoint_work` - Create Work Checkpoint

Creates a checkpoint of current work state for easy resumption later.

**Required Parameters:**
- `action`: "checkpoint_work"
- `task_id`: Task UUID
- `current_state`: Description of current work state
- `next_steps`: List of planned next steps

**Optional Parameters:**
- `notes`: Additional checkpoint notes

**Example Request:**
```json
{
  "action": "checkpoint_work",
  "task_id": "123e4567-e89b-12d3-a456-426614174000",
  "current_state": "JWT authentication implemented, working on token refresh mechanism",
  "next_steps": [
    "Implement refresh token rotation",
    "Add token blacklisting for logout",
    "Create authentication middleware"
  ],
  "notes": "Need to review security best practices for token storage"
}
```

**Example Response:**
```json
{
  "success": true,
  "operation": "checkpoint_work", 
  "status": "success",
  "data": {
    "checkpoint_time": "2025-01-27T14:30:00Z",
    "next_steps_count": 3,
    "has_notes": true
  },
  "message": "Work checkpoint created",
  "metadata": {
    "task_id": "123e4567-e89b-12d3-a456-426614174000",
    "hint": "Checkpoint saved. You can resume from this state later."
  },
  "timestamp": "2025-01-27T14:30:00Z"
}
```

### Context Management Operations

#### `update_work_context` - Update Work Context

Updates structured work context with detailed information about files, decisions, and discoveries.

**Required Parameters:**
- `action`: "update_work_context"
- `task_id`: Task UUID

**Optional Parameters:**
- `files_read`: List of files that were read/analyzed
- `files_modified`: List of files that were modified/created
- `key_decisions`: List of important decisions made
- `discoveries`: List of discoveries or insights
- `test_results`: Test execution results and metrics

**Example Request:**
```json
{
  "action": "update_work_context",
  "task_id": "123e4567-e89b-12d3-a456-426614174000",
  "files_read": [
    "src/auth/models.py",
    "docs/authentication.md",
    "requirements.txt"
  ],
  "files_modified": [
    "src/auth/jwt_handler.py",
    "src/auth/token_validator.py",
    "tests/test_auth.py"
  ],
  "key_decisions": [
    "Used PyJWT library for token handling",
    "Implemented 15-minute access tokens with 7-day refresh tokens",
    "Added token blacklisting using Redis cache"
  ],
  "discoveries": [
    "Existing user model already has required fields",
    "Current Redis setup can handle token blacklisting efficiently"
  ],
  "test_results": {
    "tests_run": 12,
    "passed": 11,
    "failed": 1,
    "coverage": 85.5,
    "failing_test": "test_expired_token_refresh"
  }
}
```

**Example Response:**
```json
{
  "success": true,
  "operation": "update_work_context",
  "status": "success", 
  "data": {
    "files_count": 6,
    "decisions_count": 3,
    "discoveries_count": 2,
    "has_test_results": true,
    "context_updated": true
  },
  "message": "Work context updated with 6 files, 3 decisions, 2 discoveries, test results",
  "metadata": {
    "task_id": "123e4567-e89b-12d3-a456-426614174000",
    "hint": "Work context updated. Information will be available for future sessions."
  },
  "timestamp": "2025-01-27T14:30:00Z"
}
```

## Progress Percentage Calculations

The system uses intelligent progress percentage mapping:

- **0%**: Task not started
- **1-25%**: Initial analysis, planning, setup
- **26-50%**: Active implementation, core work
- **51-75%**: Implementation nearly complete, testing begins
- **76-90%**: Testing, refinements, documentation
- **91-99%**: Final testing, deployment preparation
- **100%**: Task complete

### Automatic Hints Based on Progress

- **≥90%**: "Task is nearly complete. Consider running tests and preparing completion summary."
- **≥50%**: "Good progress! Remember to document key decisions."
- **<50%**: General progress acknowledgment

## Integration with Task Management

### Automatic Context Updates

All progress operations automatically update the task's context with:
- Timestamped progress entries
- Status change tracking
- File modification history
- Decision and discovery logs
- Workflow checkpoint data

### Hierarchical Context Propagation

Progress updates propagate through the 4-tier context hierarchy:
```
GLOBAL ← PROJECT ← BRANCH ← TASK
```

Changes at the task level automatically update parent contexts when `propagate_changes=True`.

### Vision System Integration

The progress tools integrate with the Vision System to provide:
- Intelligent workflow hints
- Progress-based recommendations
- Automatic milestone detection
- Context-aware next action suggestions

## Error Handling

### Common Error Responses

#### Invalid Percentage
```json
{
  "success": false,
  "operation": "report_progress",
  "status": "error",
  "error": "Invalid percentage value",
  "error_code": "VALIDATION_ERROR",
  "metadata": {
    "field": "percentage",
    "expected": "Integer between 0 and 100",
    "hint": "Provide a percentage between 0 and 100"
  }
}
```

#### Unknown Operation
```json
{
  "success": false,
  "operation": "invalid_action",
  "status": "error", 
  "error": "Unknown operation: invalid_action",
  "error_code": "INVALID_OPERATION",
  "metadata": {
    "valid_operations": [
      "report_progress",
      "quick_task_update", 
      "checkpoint_work",
      "update_work_context"
    ]
  }
}
```

#### Task Not Found
```json
{
  "success": false,
  "operation": "report_progress",
  "status": "error",
  "error": "Failed to update progress: Task not found",
  "error_code": "OPERATION_FAILED",
  "metadata": {
    "task_id": "invalid-task-id"
  }
}
```

## JSON-RPC Integration

### MCP Tool Call Format

```json
{
  "jsonrpc": "2.0",
  "method": "tools/call",
  "params": {
    "name": "manage_progress_tools",
    "arguments": {
      "action": "report_progress",
      "task_id": "123e4567-e89b-12d3-a456-426614174000",
      "progress_type": "implementation", 
      "description": "Completed JWT authentication logic",
      "percentage": 75
    }
  },
  "id": "1"
}
```

### MCP Tool Response Format

```json
{
  "jsonrpc": "2.0",
  "result": {
    "content": [
      {
        "type": "text",
        "text": "{\n  \"success\": true,\n  \"operation\": \"report_progress\",\n  \"status\": \"success\",\n  \"data\": {\n    \"progress_type\": \"implementation\",\n    \"percentage\": 75,\n    \"next_reminder\": \"Progress will be tracked automatically\",\n    \"hint\": \"Good progress! Remember to document key decisions.\"\n  },\n  \"message\": \"Progress reported for task 123e4567-e89b-12d3-a456-426614174000\",\n  \"metadata\": {\n    \"task_id\": \"123e4567-e89b-12d3-a456-426614174000\"\n  },\n  \"timestamp\": \"2025-01-27T14:30:00Z\"\n}"
      }
    ],
    "isError": false
  },
  "id": "1"
}
```

## Usage Patterns

### 1. Simple Progress Reporting

For basic progress updates without complex context:

```json
{
  "action": "report_progress",
  "task_id": "task-uuid",
  "progress_type": "implementation",
  "description": "Added user registration endpoint",
  "percentage": 30
}
```

### 2. Quick Status Updates

For rapid status changes during active work:

```json
{
  "action": "quick_task_update", 
  "task_id": "task-uuid",
  "status": "in_progress",
  "notes": "Starting on authentication module"
}
```

### 3. Work Checkpointing

For creating resumable work states:

```json
{
  "action": "checkpoint_work",
  "task_id": "task-uuid", 
  "current_state": "API endpoints implemented, working on validation",
  "next_steps": ["Add input validation", "Write tests", "Update documentation"]
}
```

### 4. Detailed Context Updates

For comprehensive work documentation:

```json
{
  "action": "update_work_context",
  "task_id": "task-uuid",
  "files_modified": ["src/api.py", "tests/test_api.py"],
  "key_decisions": ["Used FastAPI for better async support"],
  "discoveries": ["Existing auth middleware can be reused"],
  "test_results": {"tests_run": 15, "passed": 14, "failed": 1}
}
```

## Best Practices

### 1. Progress Type Selection

Choose appropriate progress types:
- Use `analysis` for understanding existing code
- Use `implementation` for writing new code
- Use `testing` for test creation and execution
- Use `debugging` for problem investigation
- Use `documentation` for writing docs

### 2. Percentage Guidelines

- Report percentages in meaningful increments (25%, 50%, 75%)
- Use percentage hints to guide completion activities
- Consider task complexity when estimating percentages

### 3. Context Updates

- Update work context regularly to maintain session continuity
- Include key decisions for future reference
- Document discoveries for knowledge sharing
- Record test results for quality tracking

### 4. Checkpoint Strategy

- Create checkpoints at natural stopping points
- Include sufficient detail for easy resumption
- Use clear next steps for workflow continuity

## Performance Considerations

- All operations are atomic and handle failures gracefully
- Context updates propagate asynchronously to avoid blocking
- Failed context updates don't block the primary operation
- Response times are optimized for real-time progress reporting

## Security

- All operations require valid JWT authentication
- Task access is validated through the security layer
- User context is automatically injected from the authentication token
- All progress data is scoped to the authenticated user's context