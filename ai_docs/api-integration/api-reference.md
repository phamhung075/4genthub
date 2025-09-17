# API Reference

## Overview

This document provides comprehensive reference for all MCP tools available in the 4genthub system. Each tool is documented with its parameters, return values, and usage examples.

## Tool Categories

### Task Management
- [manage_task](#manage_task) - Complete task lifecycle operations
- [manage_subtask](#manage_subtask) - Hierarchical task decomposition

### Project & Branch Management  
- [manage_project](#manage_project) - Project lifecycle and coordination
- [manage_git_branch](#manage_git_branch) - Branch operations and task trees

### Context Management
- [manage_context](#manage_context) - Unified 4-tier hierarchical context system with inheritance and delegation

> **⚠️ IMPORTANT UPDATE (January 2025)**: The context management system has been significantly improved with critical bug fixes:
> - Fixed TaskId import scoping issues in repositories
> - Implemented async repository patterns for better performance
> - Resolved database schema mismatches
> - Updated all import paths to use unified context services
> - All context operations now work reliably with proper error handling

### Agent Orchestration
- [manage_agent](#manage_agent) - Agent registration and assignment
- [call_agent](#call_agent) - Dynamic agent loading and execution

### System Operations
- [manage_rule](#manage_rule) - Rule lifecycle with hierarchy analysis
- [manage_compliance](#manage_compliance) - Operation validation and audit
- [manage_connection](#manage_connection) - Health monitoring and diagnostics

---

## Task Management Tools

### manage_task

Complete task lifecycle operations with Vision System integration.

#### Parameters

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| action | string | Yes | Task operation: 'create', 'update', 'get', 'delete', 'complete', 'list', 'search', 'next', 'add_dependency', 'remove_dependency' |
| git_branch_id | string | Conditional | Git branch UUID (required for 'create', optional when task_id provided) |
| task_id | string | Conditional | Task UUID (required for update, get, delete, complete, dependencies) |
| title | string | Conditional | Task title (required for 'create') |
| description | string | Optional | Detailed task description |
| status | string | Optional | Task status: 'todo', 'in_progress', 'blocked', 'review', 'testing', 'done', 'cancelled' |
| priority | string | Optional | Priority: 'low', 'medium', 'high', 'urgent', 'critical' |
| assignees | string\|array | Optional | User identifiers |
| labels | string\|array | Optional | Categories/tags |
| estimated_effort | string | Optional | Time estimate (e.g., "2 hours", "3 days") |
| due_date | string | Optional | Target date (ISO 8601 format) |
| dependencies | string\|array | Optional | Task IDs this task depends on |
| completion_summary | string | Conditional | Summary for 'complete' action |
| testing_notes | string | Optional | Testing details for 'complete' action |

#### Examples

```bash
# Create new task
mcp__4genthub_http__manage_task(
    action="create",
    git_branch_id="branch-uuid-123",
    title="Implement user authentication",
    description="Add JWT-based authentication with login/logout",
    priority="high",
    estimated_effort="3 days"
)

# Update task status
mcp__4genthub_http__manage_task(
    action="update",
    task_id="task-uuid-456",
    status="in_progress",
    details="Started implementation"
)

# Complete task
mcp__4genthub_http__manage_task(
    action="complete",
    task_id="task-uuid-456",
    completion_summary="Implemented JWT auth with refresh tokens, added tests",
    testing_notes="Unit tests for auth service, integration tests for login flow"
)

# Get next priority task
mcp__4genthub_http__manage_task(
    action="next",
    git_branch_id="branch-uuid-123",
    include_context=true
)
```

#### Response Format

```json
{
  "success": true,
  "task": {
    "id": "task-uuid",
    "title": "Task title",
    "status": "in_progress",
    "priority": "high",
    "created_at": "2024-01-01T00:00:00Z"
  },
  "workflow_guidance": {
    "recommended_agent": "coding-agent",
    "next_actions": ["Start implementation", "Write tests"],
    "hints": ["Use existing auth utilities"]
  }
}
```

---

### manage_subtask

Hierarchical task decomposition with automatic context updates.

#### Parameters

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| action | string | Yes | Subtask operation: 'create', 'update', 'delete', 'list', 'get', 'complete' |
| task_id | string | Yes | Parent task UUID |
| subtask_id | string | Conditional | Subtask UUID (required for update, delete, get, complete) |
| title | string | Conditional | Subtask title (required for 'create') |
| description | string | Optional | Detailed subtask description |
| progress_percentage | integer | Optional | Completion percentage (0-100) |
| progress_notes | string | Optional | Brief work description |
| completion_summary | string | Conditional | Summary for 'complete' action |
| blockers | string | Optional | Any blocking issues |
| insights_found | array | Optional | Discoveries during work |

#### Examples

```bash
# Create subtask
mcp__4genthub_http__manage_subtask(
    action="create",
    task_id="task-uuid-123",
    title="Implement JWT token generation",
    description="Create secure JWT tokens with proper expiration"
)

# Update progress
mcp__4genthub_http__manage_subtask(
    action="update",
    task_id="task-uuid-123",
    subtask_id="subtask-uuid-456",
    progress_percentage=75,
    progress_notes="Token generation complete, working on validation"
)

# Complete subtask
mcp__4genthub_http__manage_subtask(
    action="complete",
    task_id="task-uuid-123",
    subtask_id="subtask-uuid-456",
    completion_summary="JWT implementation complete with refresh token support",
    insights_found=["Found existing crypto utility", "Redis integration needed"]
)
```

---

## Project & Branch Management Tools

### manage_project

Complete project lifecycle and multi-project orchestration.

#### Parameters

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| action | string | Yes | Project operation: 'create', 'get', 'list', 'update', 'delete', 'project_health_check', 'cleanup_obsolete', 'validate_integrity', 'rebalance_agents' |
| project_id | string | Conditional | Project UUID (required for most actions except create/list) |
| name | string | Conditional | Project name (required for 'create', can substitute project_id for 'get') |
| description | string | Optional | Project description |
| force | boolean | Optional | Force operations bypassing safety checks - applies to 'delete' and maintenance operations (default: false) |

#### Examples

```bash
# Create new project
mcp__4genthub_http__manage_project(
    action="create",
    name="user-authentication-system",
    description="JWT-based authentication with role management"
)

# Check project health
mcp__4genthub_http__manage_project(
    action="project_health_check",
    project_id="project-uuid-123"
)

# List all projects
mcp__4genthub_http__manage_project(action="list")

# Delete project with all related data (with safety checks)
mcp__4genthub_http__manage_project(
    action="delete",
    project_id="project-uuid-123",
    force=false  # Will fail if active tasks exist
)

# Force delete project (bypasses safety checks)
mcp__4genthub_http__manage_project(
    action="delete",
    project_id="project-uuid-123",
    force=true  # Deletes even with active tasks
)
```

**Delete Operation Details:**
- Performs cascade deletion of all related data
- Deletes in order: contexts → tasks/subtasks → git branches → project
- With `force=false`: Prevents deletion if active/in-progress tasks exist
- With `force=true`: Bypasses all safety checks for immediate deletion
- Returns detailed statistics of deleted entities
- Continues deletion even if some operations fail (error recovery)

---

### manage_git_branch

Branch operations and task tree organization.

#### Parameters

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| action | string | Yes | Branch operation: 'create', 'get', 'list', 'update', 'delete', 'assign_agent', 'unassign_agent', 'get_statistics', 'archive', 'restore' |
| project_id | string | Yes | Project UUID |
| git_branch_id | string | Conditional | Branch UUID (required for most operations) |
| git_branch_name | string | Legacy | DEPRECATED: Use git_branch_id (UUID) instead. Branch name (required for 'create', can substitute git_branch_id for assignments) |
| agent_id | string | Conditional | Agent identifier - supports UUID, @agent_name, or agent_name formats (required for assign/unassign operations) |

#### Examples

```bash
# Create new branch - use git_branch_name for creation, get git_branch_id (UUID) in response
mcp__4genthub_http__manage_git_branch(
    action="create",
    project_id="project-uuid-123",
    git_branch_name="feature/user-auth",
    git_branch_description="User authentication feature development"
)
# Response will contain: git_branch_id (UUID) for subsequent operations

# Assign agent to branch (multiple format examples)
# Format 1: @agent_name (recommended)
mcp__4genthub_http__manage_git_branch(
    action="assign_agent",
    project_id="project-uuid-123",
    git_branch_id="branch-uuid-456",
    agent_id="coding-agent"
)

# Format 2: agent_name (without @)
mcp__4genthub_http__manage_git_branch(
    action="assign_agent",
    project_id="project-uuid-123", 
    git_branch_id="branch-uuid-456",
    agent_id="coding-agent"
)

# Format 3: UUID (existing format)
mcp__4genthub_http__manage_git_branch(
    action="assign_agent",
    project_id="project-uuid-123",
    git_branch_id="branch-uuid-456", 
    agent_id="2d3727cf-6915-4b54-be8d-4a5a0311ca03"
)
```

---

## Context Management Tools

> **📋 Status Update (January 2025)**: All context management tools have been fixed and are fully operational. Recent critical fixes include:
>
> 1. **Repository Fixes**: Resolved TaskId import scoping issues that caused UnboundLocalError
> 2. **Async Pattern Updates**: All repositories now use proper async/await patterns
> 3. **Database Schema**: Updated TaskContext table structure with correct foreign key references
> 4. **Import Path Resolution**: Fixed all import conflicts between hierarchical and unified services
> 5. **Test Infrastructure**: Corrected mock configurations for proper context manager testing
>
> **Result**: All context operations now work reliably without errors. Task completion functionality fully restored.

### manage_context

Unified context management system providing a single interface for all context operations across the 4-tier hierarchy (Global → Project → Branch → Task).

> **🚀 NEW in v9.1**: The `data` parameter now accepts JSON strings in addition to dictionary objects! JSON strings are automatically parsed, making it easier to work with serialized data.
> 
> **📋 January 2025 Updates**:
> - All context operations now use the unified manage_context interface
> - Fixed boolean parameter validation - accepts "true", "false", "yes", "no", etc.
> - Enhanced array parameter handling for assignees, labels, dependencies
> - Automatic context synchronization on task updates
> - Context auto-creation when creating projects, branches, and tasks

#### Parameters

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| action | string | Yes | Context operation: 'create', 'get', 'update', 'delete', 'resolve', 'delegate', 'add_insight', 'add_progress', 'list' |
| level | string | Optional | Context hierarchy level: 'global', 'project', 'branch', 'task' (default: 'task') |
| context_id | string | Conditional | Context identifier appropriate for the level (e.g., task_id for task level) |
| data | dict\|string | Optional | Context data - accepts dictionary object OR JSON string (automatically parsed) |
| user_id | string | Optional | User identifier (default: system default) |
| project_id | string | Optional | Project identifier (auto-detected from task/branch if not provided) |
| git_branch_id | string | Optional | Git branch UUID (auto-detected from task if not provided) |
| force_refresh | boolean | Optional | Bypass cache for fresh data (default: false) |
| include_inherited | boolean | Optional | Include inherited data from parent levels (default: false) |
| propagate_changes | boolean | Optional | Cascade updates to dependent contexts (default: true) |
| delegate_to | string | Optional | Target level for delegation: 'global', 'project', 'branch' |
| delegate_data | dict | Optional | Data to delegate to higher level |
| delegation_reason | string | Optional | Explanation for delegation |
| content | string | Conditional | Content for insights/progress (required for add_insight, add_progress) |
| category | string | Optional | Category for insights: 'technical', 'business', 'performance', 'risk', 'discovery' |
| importance | string | Optional | Importance level: 'low', 'medium', 'high', 'critical' (default: 'medium') |
| agent | string | Optional | Agent identifier performing the operation |
| filters | dict | Optional | Filter criteria for list operation |
| task_id | string | Legacy | Deprecated - use context_id with level='task' |
| data_title | string | Legacy | Deprecated - use data.title or data='{"title": "..."}' |
| data_description | string | Legacy | Deprecated - use data.description |
| data_status | string | Legacy | Deprecated - use data.status |
| data_priority | string | Legacy | Deprecated - use data.priority |

#### Data Parameter Format Examples

```python
# Method 1: Dictionary object (standard)
manage_context(
    action="create",
    level="task",
    context_id="task-123",
    data={
        "title": "Implement Authentication",
        "description": "Add JWT-based authentication",
        "priority": "high"
    }
)

# Method 2: JSON string (NEW! - automatically parsed)
manage_context(
    action="create",
    level="task", 
    context_id="task-123",
    data='{"title": "Implement Authentication", "description": "Add JWT-based authentication", "priority": "high"}'
)

# Method 3: Legacy parameters (backward compatible)
manage_context(
    action="create",
    task_id="task-123",  # legacy parameter
    data_title="Implement Authentication",
    data_description="Add JWT-based authentication",
    data_priority="high"
)

# Add insight to context
mcp__4genthub_http__manage_context(
    action="add_insight",
    task_id="task-uuid-123",
    content="Found existing validation utility that can be reused",
    category="technical",
    importance="medium"
)

# Update context with progress
mcp__4genthub_http__manage_context(
    action="add_progress",
    task_id="task-uuid-123",
    content="Completed login UI, starting JWT integration"
)

# Update next steps
mcp__4genthub_http__manage_context(
    action="update_next_steps",
    task_id="task-uuid-123",
    next_steps=["Create auth service", "Add middleware", "Write tests"]
)
```

#### Response Format

```json
{
  "success": true,
  "context": {
    "id": "task-uuid-123",
    "level": "task",
    "data": {
      "title": "Implement Authentication",
      "description": "Add JWT-based authentication system",
      "priority": "high",
      "status": "in_progress"
    },
    "insights": [
      {
        "content": "Found existing validation utility that can be reused",
        "category": "technical",
        "importance": "medium",
        "timestamp": "2025-01-19T10:30:00Z"
      }
    ],
    "progress": [
      {
        "content": "Completed login UI, starting JWT integration",
        "timestamp": "2025-01-19T10:35:00Z"
      }
    ],
    "next_steps": ["Create auth service", "Add middleware", "Write tests"]
  }
}
```

---

### manage_context

> **⚠️ DEPRECATED**: This tool is deprecated as of January 2025. Use [manage_context](#manage_context) instead, which provides the same functionality with a simpler interface and better performance.

Legacy 4-tier context system with inheritance and delegation. All functionality has been integrated into `manage_context`.

#### Parameters

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| action | string | Yes | Context operation: 'resolve', 'update', 'create', 'delegate', 'propagate', 'get_health', 'cleanup_cache' |
| level | string | Conditional | Context level: 'global', 'project', 'branch', 'task' |
| context_id | string | Conditional | Context identifier |
| data | object | Optional | Context data to create/update |
| delegate_to | string | Optional | Target level for delegation |
| force_refresh | boolean | Optional | Force cache refresh (default: false) |
| propagate_changes | boolean | Optional | Propagate changes to dependents (default: true) |

#### Examples

```bash
# DEPRECATED - Use manage_context instead
# OLD: mcp__4genthub_http__manage_context(...)
# NEW: mcp__4genthub_http__manage_context(...)

# Example - Resolve context with inheritance
mcp__4genthub_http__manage_context(
    action="resolve",
    level="task",
    context_id="task-uuid-123",
    force_refresh=false
)

# Example - Delegate pattern to project level
mcp__4genthub_http__manage_context(
    action="delegate",
    level="task",
    context_id="task-uuid-123",
    delegate_to="project",
    delegate_data={
        "authentication_pattern": {
            "implementation": "JWT with refresh tokens",
            "best_practices": ["Secure storage", "Token rotation"]
        }
    },
    delegation_reason="Reusable auth pattern for team"
)
```

---

---

## Agent Orchestration Tools

### call_agent

Dynamic agent loading and execution.

#### Parameters

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| name_agent | string | Yes | Agent name with @ prefix |

#### Available Agents

- `master-orchestrator-agent` - Complex multi-step workflows
- `coding-agent` - Implementation and development
- `debugger-agent` - Bug fixing and troubleshooting
- `test-orchestrator-agent` - Testing and validation
- `task-planning-agent` - Task breakdown and planning
- `@ui_designer_agent` - UI/UX design and frontend
- `security-auditor-agent` - Security analysis and auditing
- `documentation-agent` - Documentation creation
- `deep-research-agent` - Research and investigation

#### Examples

```bash
# Switch to coding agent
mcp__4genthub_http__call_agent(name_agent="coding-agent")

# Switch to security auditor for security review
mcp__4genthub_http__call_agent(name_agent="security-auditor-agent")
```

---

### manage_agent

Agent registration and assignment.

#### Parameters

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| action | string | Yes | Agent operation: 'register', 'assign', 'get', 'list', 'update', 'unassign', 'unregister', 'rebalance' |
| project_id | string | Yes | Project identifier |
| agent_id | string | Conditional | Agent identifier (required for most operations) |
| git_branch_id | string | Conditional | Branch UUID (required for assign/unassign) |
| name | string | Conditional | Agent name (required for register) |

---

## System Operations Tools

### manage_compliance

Operation validation and audit trails.

#### Parameters

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| action | string | Yes | Compliance operation: 'validate_compliance', 'get_compliance_dashboard', 'execute_with_compliance', 'get_audit_trail' |
| operation | string | Conditional | Operation to validate (required for validate_compliance) |
| command | string | Conditional | Command to execute (required for execute_with_compliance) |
| file_path | string | Optional | File path for file operations |
| security_level | string | Optional | Security level: 'public', 'internal', 'restricted', 'confidential', 'secret' |
| user_id | string | Optional | User identifier (default: 'system') |

#### Examples

```bash
# Validate file operation
mcp__4genthub_http__manage_compliance(
    action="validate_compliance",
    operation="edit_file",
    file_path="/secure/config.yaml",
    security_level="restricted"
)

# Execute command with compliance
mcp__4genthub_http__manage_compliance(
    action="execute_with_compliance",
    command="npm test",
    timeout=300
)
```

---

### manage_connection

Health monitoring and diagnostics.

#### Parameters

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| action | string | Yes | Connection operation: 'health_check', 'server_capabilities', 'connection_health', 'status', 'register_updates' |
| include_details | boolean | Optional | Include detailed information (default: true) |
| session_id | string | Conditional | Session ID (required for register_updates) |
| connection_id | string | Optional | Specific connection to analyze |

#### Examples

```bash
# Basic health check
mcp__4genthub_http__manage_connection(action="health_check")

# Get server capabilities
mcp__4genthub_http__manage_connection(
    action="server_capabilities",
    include_details=true
)
```

---

## Error Handling

### Common Error Responses

#### Validation Errors
```json
{
  "success": false,
  "error": "Validation failed",
  "details": {
    "field": "git_branch_id",
    "message": "git_branch_id is required for task creation"
  }
}
```

#### Business Logic Errors
```json
{
  "success": false,
  "error": "Task completion requires context to be created first",
  "suggestions": [
    "Update context using manage_context",
    "Then retry task completion"
  ]
}
```

#### System Errors
```json
{
  "success": false,
  "error": "Internal server error",
  "correlation_id": "uuid-for-debugging"
}
```

## Rate Limiting

### Default Limits
- **Standard Operations**: 100 requests per minute
- **Heavy Operations** (health checks, statistics): 10 requests per minute
- **Bulk Operations**: 5 requests per minute

### Rate Limit Headers
```
X-RateLimit-Limit: 100
X-RateLimit-Remaining: 95
X-RateLimit-Reset: 1640995200
```

## Authentication

### Bearer Token Authentication
```bash
# Include token in requests
Authorization: Bearer your-token-here
```

### Token Management
- Tokens are project-scoped
- Default expiration: 30 days
- Refresh tokens available for long-running operations

## Best Practices

### 1. Error Handling
- Always check `success` field in responses
- Use `suggestions` field for recovery guidance
- Log `correlation_id` for debugging

### 2. Performance
- Use `include_details=false` for faster responses when details not needed
- Cache frequently accessed data
- Use batch operations when available

### 3. Context Management
- Always resolve context before modifications
- Use `force_refresh=false` for better performance
- Delegate patterns appropriately to avoid over-sharing

### 4. Agent Usage
- Switch to appropriate agent before work
- Use `master-orchestrator-agent` as fallback
- Monitor agent assignments for optimal distribution

## Versioning

### API Version
Current version: `v1.0`

### Backward Compatibility
- MCP protocol version: `1.0`
- Maintain compatibility for deprecated parameters
- Migration guides provided for breaking changes

## Support

### Debug Information
Include in support requests:
- Tool name and parameters used
- Complete error response
- System health check results
- Correlation ID (if available)

### Common Issues
See [Comprehensive Troubleshooting Guide](COMPREHENSIVE_TROUBLESHOOTING_GUIDE.md) for detailed solutions to common problems.