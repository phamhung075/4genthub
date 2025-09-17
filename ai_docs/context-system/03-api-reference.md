# Context System API Reference

## MCP Tool: manage_context

The unified tool for all context management operations.

### Basic Syntax
```python
mcp__agenthub_http__manage_context(
    action: str,                    # Required: Operation to perform
    level: str = "task",           # Context level: global, project, branch, task
    context_id: str = None,        # Context identifier (required for most actions)
    data: Dict|str = None,         # Context data (dict or JSON string)
    # ... additional parameters
)
```

### Actions

#### create
Create a new context at specified level.

```python
# Example: Create task context
result = manage_context(
    action="create",
    level="task",
    context_id="task-123",
    data={
        "title": "Implement authentication",
        "description": "Add JWT-based auth system",
        "priority": "high",
        "status": "in_progress"
    }
)
```

#### get
Retrieve context with optional inheritance.

```python
# Example: Get context with inheritance
result = manage_context(
    action="get",
    level="task",
    context_id="task-123",
    include_inherited=True  # Include parent context data
)
```

#### update
Update existing context data.

```python
# Example: Update progress
result = manage_context(
    action="update",
    level="task",
    context_id="task-123",
    data={
        "progress": 75,
        "status": "in_progress",
        "last_activity": "Implemented token generation"
    },
    propagate_changes=True  # Update dependent contexts
)
```

#### delete
Remove context from specified level.

```python
result = manage_context(
    action="delete",
    level="task",
    context_id="task-123"
)
```

#### resolve
Get fully resolved context with complete inheritance chain.

```python
result = manage_context(
    action="resolve",
    level="task",
    context_id="task-123",
    force_refresh=False  # Use cache if available
)
```

#### delegate
Move reusable patterns to higher levels.

```python
result = manage_context(
    action="delegate",
    level="task",
    context_id="task-123",
    delegate_to="project",  # Target: global, project, branch
    delegate_data={
        "auth_pattern": {
            "implementation": "jwt_auth_code",
            "usage": "Standard JWT authentication",
            "best_practices": ["Use secure cookies", "Implement refresh"]
        }
    },
    delegation_reason="Reusable authentication pattern for all features"
)
```

#### add_insight
Add insights to context.

```python
result = manage_context(
    action="add_insight",
    level="task",
    context_id="task-123",
    content="Redis caching improved response time by 40%",
    category="performance",  # technical, business, performance, discovery
    importance="high",       # low, medium, high, critical
    agent="coding-agent"
)
```

#### add_progress
Track progress updates.

```python
result = manage_context(
    action="add_progress",
    level="task",
    context_id="task-123",
    content="Completed JWT token generation logic",
    agent="coding-agent"
)
```

#### list
List contexts at specified level.

```python
result = manage_context(
    action="list",
    level="task",
    filters={
        "status": "in_progress",
        "priority": "high"
    }
)
```

### Parameters

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| action | str | required | Operation to perform |
| level | str | "task" | Context hierarchy level |
| context_id | str | None | Context identifier |
| data | Dict/str | None | Context data (supports JSON strings) |
| force_refresh | bool | False | Bypass cache |
| include_inherited | bool | False | Include parent data |
| propagate_changes | bool | True | Update dependents |
| delegate_to | str | None | Target delegation level |
| delegate_data | Dict | None | Data to delegate |
| delegation_reason | str | None | Reason for delegation |
| content | str | None | Content for insights/progress |
| category | str | None | Insight category |
| importance | str | "medium" | Insight importance |
| agent | str | None | Agent identifier |
| filters | Dict | None | List filtering criteria |

### Data Parameter Formats

The `data` parameter accepts multiple formats:

```python
# Dictionary format
data={"title": "My Task", "status": "active"}

# JSON string format
data='{"title": "My Task", "status": "active"}'

# Legacy format (backward compatible)
data_title="My Task"
data_status="active"
```

## Response Format

### Standard Response Structure
```json
{
  "status": "success|partial_success|failure",
  "success": true|false,
  "operation": "manage_context.{action}",
  "operation_id": "uuid-string",
  "timestamp": "2025-01-19T10:30:00.000Z",
  "data": {
    // Operation-specific data
  },
  "metadata": {
    "context_operation": {
      "level": "task",
      "context_id": "task-123",
      // Additional metadata
    }
  },
  "confirmation": {
    "operation_completed": true,
    "data_persisted": true,
    "partial_failures": []
  }
}
```

### Response Data by Action

#### Single Context (create, get, update)
```json
{
  "data": {
    "context_data": {
      "id": "task-123",
      "level": "task",
      "data": {
        "title": "Task Title",
        "status": "in_progress",
        // ... other fields
      },
      "created_at": "2025-01-19T10:30:00.000Z",
      "updated_at": "2025-01-19T10:30:00.000Z"
    }
  }
}
```

#### List Operation
```json
{
  "data": {
    "contexts": [
      {
        "id": "task-123",
        "level": "task",
        "data": { /* context data */ }
      },
      // ... more contexts
    ]
  },
  "metadata": {
    "context_operation": {
      "count": 10
    }
  }
}
```

#### Resolve Operation
```json
{
  "data": {
    "resolved_context": {
      "id": "task-123",
      "level": "task",
      "data": { /* merged data */ },
      "inheritance_chain": [
        {"level": "global", "data": {}},
        {"level": "project", "data": {}},
        {"level": "branch", "data": {}},
        {"level": "task", "data": {}}
      ]
    }
  }
}
```

#### Delegation Operation
```json
{
  "data": {
    "delegation_result": {
      "source_context_id": "task-123",
      "target_context_id": "project-456",
      "delegated_data": { /* delegated data */ },
      "delegation_reason": "Reusable pattern"
    }
  }
}
```

### Error Response
```json
{
  "status": "failure",
  "success": false,
  "operation": "manage_context.{action}",
  "error": {
    "message": "Context not found: task-123",
    "code": "NOT_FOUND",
    "operation": "manage_context.get",
    "timestamp": "2025-01-19T10:30:00.000Z"
  }
}
```

## Common Usage Patterns

### Task Workflow with Context
```python
# 1. Create task context
manage_context(
    action="create",
    level="task",
    context_id="task-123",
    data={"title": "Implement feature", "status": "todo"}
)

# 2. Update progress during work
manage_context(
    action="add_progress",
    level="task",
    context_id="task-123",
    content="Started implementation"
)

# 3. Add insights discovered
manage_context(
    action="add_insight",
    level="task",
    context_id="task-123",
    content="Found existing utility function",
    category="discovery"
)

# 4. Complete with final update
manage_context(
    action="update",
    level="task",
    context_id="task-123",
    data={"status": "completed", "progress": 100}
)
```

### Pattern Delegation
```python
# After implementing reusable pattern
manage_context(
    action="delegate",
    level="task",
    context_id="task-123",
    delegate_to="project",
    delegate_data={
        "error_handler": {
            "code": error_handler_code,
            "usage": "Standard error handling"
        }
    },
    delegation_reason="Reusable across all features"
)
```

### Context Resolution
```python
# Get complete context with inheritance
context = manage_context(
    action="resolve",
    level="task",
    context_id="task-123"
)

# Access different levels of data
task_data = context["data"]["resolved_context"]["data"]
inherited_standards = context["data"]["resolved_context"]["inheritance_chain"]
```

## Best Practices

1. **Use Appropriate Levels**: Create contexts at the right hierarchy level
2. **Leverage Inheritance**: Don't duplicate data that can be inherited
3. **Delegate Patterns**: Share reusable discoveries with higher levels
4. **Track Progress**: Use add_progress for visibility
5. **Document Insights**: Capture learnings with add_insight
6. **Handle Errors**: Check response["success"] before using data