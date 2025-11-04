# Token Usage Tracking Guide

## Overview

This guide explains how to implement detailed token usage tracking in MCP controllers to monitor how API tokens are being used across different operations.

## Architecture

### Database Schema

Tokens now include a `usage_stats` JSON field that stores operation-level counters:

```python
usage_stats = {
    "task_create": 45,
    "task_update": 23,
    "subtask_create": 12,
    "agent_call": 67,
    ...
}
```

### Components

1. **Database Model**: `ApiToken` model with `usage_stats` JSON field
2. **Repository Method**: `TokenRepository.update_token_usage(token_id, operation)`
3. **Tracking Service**: `token_usage_tracking_service.py` utility functions
4. **Frontend Display**: Token cards show operation breakdown

## How to Add Tracking

### Step 1: Import the Tracking Service

```python
from fastmcp.task_management.application.services.token_usage_tracking_service import (
    track_token_operation,
    OperationNames
)
```

### Step 2: Extract Token ID from Auth Context

```python
from fastmcp.auth.middleware.request_context_middleware import get_current_token_id

# In your controller/handler method:
token_id = get_current_token_id()  # Returns None if no token auth
```

### Step 3: Track the Operation

```python
# After successful operation execution:
await track_token_operation(
    token_id=token_id,
    operation=OperationNames.TASK_CREATE,  # Use standard operation names
    session=session
)
```

## Complete Example

### Task Creation Handler

```python
from sqlalchemy.orm import Session
from fastmcp.auth.middleware.request_context_middleware import get_current_token_id
from fastmcp.task_management.application.services.token_usage_tracking_service import (
    track_token_operation,
    OperationNames
)

async def create_task(
    task_data: dict,
    user_id: str,
    session: Session
) -> dict:
    """Create a new task and track token usage."""

    try:
        # 1. Execute the main operation
        task = await task_repository.create_task(task_data)

        # 2. Track token usage (non-blocking)
        token_id = get_current_token_id()
        await track_token_operation(
            token_id=token_id,
            operation=OperationNames.TASK_CREATE,
            session=session
        )

        return {"success": True, "task": task}

    except Exception as e:
        logger.error(f"Error creating task: {e}")
        return {"success": False, "error": str(e)}
```

## Standard Operation Names

Use the `OperationNames` class for consistency:

### Task Operations
- `TASK_CREATE` - Creating tasks
- `TASK_UPDATE` - Updating tasks
- `TASK_DELETE` - Deleting tasks
- `TASK_COMPLETE` - Completing tasks
- `TASK_LIST` - Listing tasks
- `TASK_GET` - Getting task details

### Subtask Operations
- `SUBTASK_CREATE` - Creating subtasks
- `SUBTASK_UPDATE` - Updating subtasks
- `SUBTASK_DELETE` - Deleting subtasks
- `SUBTASK_COMPLETE` - Completing subtasks
- `SUBTASK_LIST` - Listing subtasks
- `SUBTASK_GET` - Getting subtask details

### Project Operations
- `PROJECT_CREATE` - Creating projects
- `PROJECT_UPDATE` - Updating projects
- `PROJECT_DELETE` - Deleting projects
- `PROJECT_GET` - Getting project details
- `PROJECT_LIST` - Listing projects

### Branch Operations
- `BRANCH_CREATE` - Creating branches
- `BRANCH_UPDATE` - Updating branches
- `BRANCH_DELETE` - Deleting branches
- `BRANCH_GET` - Getting branch details
- `BRANCH_LIST` - Listing branches

### Agent Operations
- `AGENT_REGISTER` - Registering agents
- `AGENT_UPDATE` - Updating agents
- `AGENT_DELETE` - Deleting agents
- `AGENT_ASSIGN` - Assigning agents
- `AGENT_UNASSIGN` - Unassigning agents
- `AGENT_CALL` - Calling agent operations

### Context Operations
- `CONTEXT_CREATE` - Creating contexts
- `CONTEXT_UPDATE` - Updating contexts
- `CONTEXT_DELETE` - Deleting contexts
- `CONTEXT_GET` - Getting context details

## Custom Operation Names

For operations not in the standard list:

```python
from fastmcp.task_management.application.services.token_usage_tracking_service import (
    track_token_operation,
    get_operation_name
)

# Generate custom operation name:
operation = get_operation_name('webhook', 'trigger')  # Returns 'webhook_trigger'

await track_token_operation(
    token_id=token_id,
    operation=operation,
    session=session
)
```

## Best Practices

### 1. Track After Success

Only track operations that successfully complete:

```python
# ✅ CORRECT - Track after success
task = await create_task(data)
await track_token_operation(token_id, OperationNames.TASK_CREATE, session)

# ❌ WRONG - Tracking before operation completes
await track_token_operation(token_id, OperationNames.TASK_CREATE, session)
task = await create_task(data)  # Might fail!
```

### 2. Handle Tracking Failures Gracefully

Tracking failures shouldn't break the main operation:

```python
try:
    task = await create_task(data)

    # Tracking is best-effort - don't fail the request if it errors
    try:
        await track_token_operation(token_id, OperationNames.TASK_CREATE, session)
    except Exception as e:
        logger.warning(f"Failed to track token usage: {e}")

    return {"success": True, "task": task}
except Exception as e:
    return {"success": False, "error": str(e)}
```

### 3. Use Consistent Naming

Always use `OperationNames` constants for standard operations:

```python
# ✅ CORRECT - Using standard names
await track_token_operation(token_id, OperationNames.TASK_CREATE, session)

# ❌ WRONG - Using arbitrary strings
await track_token_operation(token_id, "create_task", session)
await track_token_operation(token_id, "task-create", session)
await track_token_operation(token_id, "taskCreate", session)
```

## Frontend Display

Token cards automatically display operation breakdown when `usage_stats` contains data:

```typescript
// Frontend displays:
// Operation Breakdown
// Task Create: 45
// Agent Call: 67
// Subtask Update: 23
```

## Migration Path

### Phase 1: Core Operations (Done)
- ✅ Database schema with `usage_stats` field
- ✅ Repository method `update_token_usage(token_id, operation)`
- ✅ Tracking utility service
- ✅ Frontend display component

### Phase 2: Add Tracking to Controllers (In Progress)
Add tracking calls to:
1. Task operations (create, update, delete)
2. Subtask operations (create, update, delete)
3. Project operations (create, update, delete)
4. Agent operations (call, register, assign)
5. Context operations (create, update)

### Phase 3: Analytics & Reporting (Future)
- Top operations per token
- Usage trends over time
- Operation performance metrics

## Troubleshooting

### Token ID Not Available

If `get_current_token_id()` returns `None`:

1. Check that the request is authenticated with an API token
2. Verify request context middleware is running
3. Keycloak authentication doesn't provide token_id (only user_id)

### Operation Not Showing in Frontend

1. Verify the operation was tracked successfully (check logs)
2. Ensure the token was refreshed in the frontend
3. Check that `usage_stats` is included in the API response
4. Verify the token belongs to the authenticated user

### Database Migration

If using PostgreSQL, the `usage_stats` column should use JSONB:

```sql
ALTER TABLE api_tokens ADD COLUMN usage_stats JSONB DEFAULT '{}';
```

For SQLite, use JSON:

```sql
ALTER TABLE api_tokens ADD COLUMN usage_stats TEXT DEFAULT '{}';
```

## Summary

1. **Import** the tracking service and operation names
2. **Extract** token_id from request context
3. **Track** after successful operation completion
4. **Use** standard operation names for consistency
5. **Handle** tracking failures gracefully

The frontend will automatically display the operation breakdown in token cards!
