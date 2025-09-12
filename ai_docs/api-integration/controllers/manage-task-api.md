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

### Complete Parameter Reference (30+ Parameters)

The manage_task API supports 30+ parameters for comprehensive task management. Only `action` is required at schema level, with action-specific parameters validated at business logic level.

```json
{
  "type": "object",
  "properties": {
    "action": {
      "type": "string",
      "required": true,
      "description": "Task operation to perform"
    },
    "task_id": {
      "type": "string", 
      "description": "[OPTIONAL] Unique task identifier (UUID)"
    },
    "git_branch_id": {
      "type": "string",
      "description": "[OPTIONAL] Git branch UUID for task context"
    },
    "title": {
      "type": "string",
      "description": "[OPTIONAL] Task title - be specific and action-oriented"
    },
    "description": {
      "type": "string",
      "description": "[OPTIONAL] Detailed task description with acceptance criteria"
    },
    "status": {
      "type": "string",
      "description": "[OPTIONAL] Task status: 'todo', 'in_progress', 'blocked', 'review', 'testing', 'done', 'cancelled'"
    },
    "priority": {
      "type": "string",
      "description": "[OPTIONAL] Task priority: 'low', 'medium', 'high', 'urgent', 'critical'"
    },
    "details": {
      "type": "string",
      "description": "[OPTIONAL] Additional implementation notes and technical details"
    },
    "estimated_effort": {
      "type": "string",
      "description": "[OPTIONAL] Time estimate (e.g., '2 hours', '3 days', '1 week')"
    },
    "assignees": {
      "type": "string",
      "description": "[REQUIRED for create] Agent identifiers (@agent-name format, comma-separated)"
    },
    "labels": {
      "type": "string",
      "description": "[OPTIONAL] Categories/tags (comma-separated or single string)"
    },
    "due_date": {
      "type": "string",
      "description": "[OPTIONAL] Target completion date (ISO 8601 format)"
    },
    "dependencies": {
      "type": "string",
      "description": "[OPTIONAL] Task IDs this task depends on (comma-separated)"
    },
    "dependency_id": {
      "type": "string",
      "description": "[OPTIONAL] Single dependency task UUID for add/remove operations"
    },
    "context_id": {
      "type": "string",
      "description": "[OPTIONAL] Context identifier (usually same as task_id)"
    },
    "completion_summary": {
      "type": "string",
      "description": "[OPTIONAL] Detailed summary of accomplished work"
    },
    "testing_notes": {
      "type": "string",
      "description": "[OPTIONAL] Description of testing performed"
    },
    "query": {
      "type": "string",
      "description": "[OPTIONAL] Search terms for finding tasks"
    },
    "limit": {
      "type": "integer",
      "description": "[OPTIONAL] Maximum number of results (1-100, default: 50)"
    },
    "offset": {
      "type": "integer",
      "description": "[OPTIONAL] Result offset for pagination (default: 0)"
    },
    "sort_by": {
      "type": "string",
      "description": "[OPTIONAL] Field to sort by ('created_at', 'updated_at', 'priority', 'status')"
    },
    "sort_order": {
      "type": "string",
      "description": "[OPTIONAL] Sort order ('asc', 'desc', default: 'desc')"
    },
    "include_context": {
      "type": "boolean",
      "description": "[OPTIONAL] Include vision insights and recommendations (default: true)"
    },
    "force_full_generation": {
      "type": "boolean",
      "description": "[OPTIONAL] Force vision system regeneration (default: false)"
    },
    "assignee": {
      "type": "string",
      "description": "[OPTIONAL] Filter tasks by specific assignee"
    },
    "tag": {
      "type": "string",
      "description": "[OPTIONAL] Filter tasks by specific tag/label"
    },
    "user_id": {
      "type": "string",
      "description": "[OPTIONAL] User identifier (auto-populated from auth context)"
    }
  },
  "required": ["action"]
}
```

## Available Actions

### Two-Stage Validation Pattern

⚠️ **Important**: The API uses a two-stage validation pattern:
1. **Schema Level**: Only `action` is required in JSON schema
2. **Business Logic Level**: Action-specific parameters are validated based on the action value

This provides:
- ✅ Flexibility for different parameter requirements per action
- ✅ Better error messages with context-specific validation
- ✅ MCP compatibility with single required parameter
- ✅ Clear feedback about missing parameters for each action

### Core CRUD Operations

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

Intelligently selects the next task to work on based on priority, dependencies, and AI recommendations.

**Required Parameters:**
- `action`: "next"
- `git_branch_id`: Branch context

**Optional Parameters:**
- `include_context`: Include vision insights (default: true)

**Example Request:**
```json
{
  "action": "next",
  "git_branch_id": "550e8400-e29b-41d4-a716-446655440000",
  "include_context": true
}
```

**Example Response:**
```json
{
  "success": true,
  "operation": "next",
  "task": {
    "next_item": {
      "task": {
        "id": "task-uuid",
        "title": "Implement JWT authentication",
        "priority": "high",
        "status": "todo"
      },
      "recommendation_reason": "High priority task with no blocking dependencies",
      "estimated_impact": "Critical for user authentication flow"
    }
  },
  "workflow_hints": {
    "next_actions": ["Start with JWT service implementation", "Set up authentication middleware"],
    "suggested_approach": "Begin with backend JWT service, then frontend integration"
  }
}
```

### Advanced Query Operations

#### `count` - Count Tasks

Returns the total count of tasks matching specified criteria.

**Required Parameters:**
- `action`: "count"

**Optional Parameters:**
- `git_branch_id`: Filter by branch
- `status`: Filter by status
- `priority`: Filter by priority
- `assignee`: Filter by assignee
- `tag`: Filter by label/tag

**Example Request:**
```json
{
  "action": "count",
  "git_branch_id": "550e8400-e29b-41d4-a716-446655440000",
  "status": "in_progress"
}
```

### Dependency Management Operations

#### `add_dependency` - Add Task Dependency

Adds a dependency relationship between tasks to enforce completion order.

**Required Parameters:**
- `action`: "add_dependency"
- `task_id`: Target task UUID
- `dependency_id`: Task that must be completed first

**Example Request:**
```json
{
  "action": "add_dependency",
  "task_id": "550e8400-e29b-41d4-a716-446655440007",
  "dependency_id": "550e8400-e29b-41d4-a716-446655440008"
}
```

**Example Response:**
```json
{
  "success": true,
  "operation": "add_dependency",
  "message": "Dependency added successfully",
  "task_id": "550e8400-e29b-41d4-a716-446655440007",
  "dependency_id": "550e8400-e29b-41d4-a716-446655440008",
  "workflow_impact": "Task will be blocked until dependency is completed"
}
```

#### `remove_dependency` - Remove Task Dependency

Removes a dependency relationship between tasks.

**Required Parameters:**
- `action`: "remove_dependency"
- `task_id`: Target task UUID
- `dependency_id`: Dependency to remove

**Example Request:**
```json
{
  "action": "remove_dependency",
  "task_id": "550e8400-e29b-41d4-a716-446655440007",
  "dependency_id": "550e8400-e29b-41d4-a716-446655440009"
}
```

### Vision System Operations

#### `enrich` - Enrich Task Response

Applies Vision System enrichment to existing task data with AI insights.

**Required Parameters:**
- `action`: "enrich"
- `response`: Existing response to enrich
- `task_data`: Task data for enrichment

**Optional Parameters:**
- `action`: Operation context for enrichment

#### `context` - Create Task Context

Creates enriched context entry for a task with Vision System integration.

**Required Parameters:**
- `action`: "context"
- `task_id`: Task UUID
- `task_data`: Task data for context creation
- `git_branch_id`: Branch context

#### `workflow` - Get Workflow Guidance

Provides intelligent workflow guidance and next action suggestions.

**Required Parameters:**
- `action`: "workflow"
- `task_id`: Task UUID (optional for general guidance)

**Example Response:**
```json
{
  "success": true,
  "operation": "workflow",
  "workflow_guidance": {
    "current_phase": "implementation",
    "next_actions": ["Write unit tests", "Update documentation"],
    "quality_gates": ["Code review required", "Integration tests must pass"],
    "risk_factors": ["Database migration needed"],
    "recommendations": ["Consider adding error handling", "Implement logging"]
  }
}
```

## Vision System Features

### Automatic AI Enrichment

The Vision System automatically enriches all task operations with AI-generated insights and recommendations.

#### Task Enhancement Features
- **AI-Enhanced Descriptions**: Automatically expands task descriptions with context, technical details, and best practices
- **Subtask Suggestions**: Proposes logical task breakdown with implementation steps
- **Blocker Detection**: Identifies potential obstacles before they impact progress
- **Impact Analysis**: Assesses task importance, dependencies, and effect on project goals
- **Progress Tracking**: Monitors milestone completion and workflow advancement
- **Context Propagation**: Automatically updates related tasks and project context

#### Intelligent Workflow Guidance
- **Progress Hints**: Suggests specific next actions based on current task state
- **Quality Checkpoints**: Recommends review points and validation steps
- **Testing Suggestions**: Proposes appropriate testing strategies for task type
- **Documentation Reminders**: Highlights documentation needs and compliance requirements
- **Code Review Recommendations**: Suggests review criteria and focus areas
- **Performance Considerations**: Identifies optimization opportunities

#### Strategic Project Orchestration
- **Dependency Analysis**: Maps comprehensive task relationships and completion order
- **Resource Planning**: Estimates effort, resources, and optimal agent assignments
- **Timeline Predictions**: Provides realistic completion estimates with confidence intervals
- **Risk Assessment**: Identifies project risks with mitigation strategies
- **Workflow Optimization**: Recommends process improvements and parallel work opportunities
- **Knowledge Transfer**: Captures and shares lessons learned across tasks

### Enhanced Response Fields

Vision System integration adds the following fields to responses:

```json
{
  "vision_insights": {
    "enriched_description": "AI-enhanced task description with technical details",
    "suggested_subtasks": ["Specific implementation steps"],
    "potential_blockers": ["Identified obstacles and dependencies"],
    "impact_analysis": "Assessment of task importance and project impact",
    "technical_considerations": ["Architecture decisions", "Technology choices"],
    "testing_strategy": ["Unit tests", "Integration tests", "E2E scenarios"]
  },
  "workflow_hints": {
    "next_actions": ["Immediate next steps to take"],
    "quality_gates": ["Review checkpoints and validation criteria"],
    "suggested_approach": "Recommended implementation methodology",
    "parallel_opportunities": ["Tasks that can be done simultaneously"],
    "collaboration_points": ["When to involve other team members"]
  },
  "progress_indicators": {
    "milestone_tracking": "Current progress against milestones",
    "completion_signals": ["Indicators that task is ready for completion"],
    "risk_level": "Current risk assessment (low/medium/high)"
  },
  "related_tasks": {
    "dependencies": ["Tasks this depends on"],
    "dependents": ["Tasks that depend on this"],
    "related_work": ["Similar or complementary tasks"]
  }
}
```

### Context Integration

Vision System automatically integrates with the 4-tier context hierarchy:

- **Global Context**: Learns patterns across all user projects
- **Project Context**: Maintains project-specific knowledge and standards
- **Branch Context**: Tracks branch-specific workflow and progress
- **Task Context**: Stores task-specific insights and lessons learned

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

#### Comprehensive Task Creation with Dependencies
```json
{
  "action": "create",
  "git_branch_id": "550e8400-e29b-41d4-a716-446655440002",
  "title": "Implement user authentication with JWT",
  "description": "Add comprehensive JWT authentication with refresh tokens, password reset, and 2FA support",
  "assignees": "coding-agent,@security-auditor-agent",
  "priority": "high",
  "estimated_effort": "5 days",
  "labels": "authentication,security,backend",
  "dependencies": ["550e8400-e29b-41d4-a716-446655440001", "550e8400-e29b-41d4-a716-446655440003"],
  "due_date": "2025-02-15T23:59:59Z"
}
```

#### Advanced Task Updates with Progress Tracking
```json
{
  "action": "update",
  "task_id": "550e8400-e29b-41d4-a716-446655440005",
  "status": "in_progress",
  "details": "Completed JWT service implementation, working on refresh token mechanism",
  "completion_summary": "JWT core functionality complete, 60% done",
  "labels": "authentication,security,backend,in-progress"
}
```

#### Intelligent Task Completion with Knowledge Capture
```json
{
  "action": "complete",
  "task_id": "550e8400-e29b-41d4-a716-446655440006",
  "completion_summary": "Implemented comprehensive JWT authentication with refresh tokens, password reset flow, and 2FA integration. Added comprehensive error handling and security middleware.",
  "testing_notes": "Added 45 unit tests covering all auth flows, integration tests for login/logout, security tests for token validation, load tests for 1000+ concurrent users",
  "context_id": "550e8400-e29b-41d4-a716-446655440006"
}
```

#### Smart Task Search and Filtering
```json
{
  "action": "search",
  "query": "authentication jwt security",
  "git_branch_id": "550e8400-e29b-41d4-a716-446655440000",
  "status": "in_progress",
  "priority": "high",
  "limit": 20,
  "sort_by": "priority",
  "sort_order": "desc"
}
```

#### Dependency Chain Management
```json
// Create sequential task dependencies
{
  "action": "add_dependency",
  "task_id": "task-login-ui",
  "dependency_id": "task-jwt-backend"
}
{
  "action": "add_dependency", 
  "task_id": "task-integration-tests",
  "dependency_id": "task-login-ui"
}
```

#### With Subtask Integration
```json
// First create parent task
{"action": "create", "title": "Implement Authentication System", "assignees": "coding-agent,@security-auditor-agent"}
// Vision System suggests subtask breakdown
// Use manage_subtask to create specific implementation tasks
// Parent task automatically tracks subtask progress
```

#### With Context Management Integration
```json
// Tasks automatically create context entries
// Context includes Vision System insights and progress tracking
// Use manage_context to:
// - Share insights between sessions
// - Delegate knowledge to different hierarchy levels
// - Maintain cross-project learning patterns
```

#### With Agent Assignment Integration
```json
// Specialized agent assignment based on task requirements
{
  "action": "create",
  "title": "Security audit for authentication system",
  "assignees": "@security-auditor-agent,@security-penetration-tester-agent"
}
// Agents automatically receive:
// - Task context and requirements
// - Related task information
// - Project-specific security guidelines
// - Vision System recommendations
```

### Workflow Orchestration Patterns

#### AI-Recommended Task Flow
```json
// Get AI-recommended next task
{"action": "next", "git_branch_id": "branch-uuid", "include_context": true}
// Response includes workflow guidance and next actions
// Automatically considers dependencies, priority, and project state
```

#### Progress Monitoring and Insights
```json
// List tasks with enriched progress information
{"action": "list", "git_branch_id": "branch-uuid", "include_context": true}
// Response includes Vision System insights for each task
// Workflow hints for project advancement
// Risk analysis and mitigation suggestions
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