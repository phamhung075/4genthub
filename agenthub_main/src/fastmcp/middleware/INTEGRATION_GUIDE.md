# Integration Guide: Runtime Response Validation

This guide shows how to integrate the response validation middleware into the agenthub system.

## Step 1: Enable Response Validation Middleware

### File: `agenthub_main/src/fastmcp/server/http_server.py`

Add the middleware to the middleware stack:

```python
# At the top, add import
from fastmcp.middleware import ResponseValidatorMiddleware

# In create_base_app function, after line 277 (after RequestContextMiddleware):
def create_base_app(
    routes: list[BaseRoute],
    middleware: list[Middleware],
    debug: bool = False,
    lifespan: Callable | None = None,
    cors_origins: list[str] | None = None,
) -> StarletteWithLifespan:
    # ... existing code ...

    # 4. RequestContextMiddleware (if not already in middleware list)
    if not has_request_context:
        final_middleware.append(Middleware(RequestContextMiddleware))

    # 5. Response Validation Middleware (NEW)
    # Add this block:
    import os
    if os.getenv("VALIDATE_RESPONSES", "false").lower() in ("true", "1", "yes"):
        final_middleware.append(Middleware(ResponseValidatorMiddleware))
        logger.info("Response validation middleware enabled")

    # 6. Add any custom middleware passed in (renumber from 5)
    final_middleware.extend(middleware)

    # ... rest of function ...
```

## Step 2: Enable WebSocket Message Logging

### File: `agenthub_main/src/fastmcp/task_management/application/services/websocket_notification_service.py`

Add logging to broadcast methods:

```python
# At the top, add import
from fastmcp.middleware import log_websocket_message

# In broadcast_task_event method, around line 300:
@staticmethod
async def broadcast_task_event(
    event_type: str,
    task: Any,
    task_response=None,
    user_id: str = None
):
    """Broadcast a task event to connected WebSocket clients."""
    try:
        # Build complete payload
        from .websocket_payload_builder import WebSocketPayloadBuilder
        payload = WebSocketPayloadBuilder.build_task_payload(task, task_response)

        # Log and validate the message (NEW)
        event_name = f"task.{event_type}"
        validation_errors = log_websocket_message(
            event=event_name,
            data=payload,
            user_id=user_id,
            validate=True
        )

        if validation_errors:
            logger.error(
                f"🚨 WebSocket payload validation failed for {event_name}:\n" +
                "\n".join([f"  - {error}" for error in validation_errors])
            )

        # Broadcast to WebSocket clients
        from ....websocket.connection_manager import get_connection_manager
        manager = get_connection_manager()

        if manager and user_id:
            await manager.broadcast_user_update(
                user_id=user_id,
                entity_type="task",
                action_type=event_type,
                entity_data=payload
            )

    except Exception as e:
        logger.error(f"Failed to broadcast task event: {e}", exc_info=True)
```

Similar changes for `broadcast_subtask_event` around line 433:

```python
@staticmethod
async def broadcast_subtask_event(
    event_type: str,
    subtask: Any,
    task_id: str,
    user_id: str = None
):
    """Broadcast a subtask event to connected WebSocket clients."""
    try:
        # Build payload
        payload = {
            "id": str(subtask.id),
            "title": subtask.title,
            "status": str(subtask.status),
            "priority": str(subtask.priority),
            "parent_task_id": task_id,
            "assignees": subtask.assignees or [],
            "progress_percentage": subtask.progress_percentage or 0,
            "created_at": subtask.created_at.isoformat() if subtask.created_at else None,
            "updated_at": subtask.updated_at.isoformat() if subtask.updated_at else None,
        }

        # Log and validate the message (NEW)
        event_name = f"subtask.{event_type}"
        validation_errors = log_websocket_message(
            event=event_name,
            data=payload,
            user_id=user_id,
            validate=True
        )

        if validation_errors:
            logger.error(
                f"🚨 WebSocket payload validation failed for {event_name}:\n" +
                "\n".join([f"  - {error}" for error in validation_errors])
            )

        # Broadcast
        from ....websocket.connection_manager import get_connection_manager
        manager = get_connection_manager()

        if manager and user_id:
            await manager.broadcast_user_update(
                user_id=user_id,
                entity_type="subtask",
                action_type=event_type,
                entity_data=payload
            )

    except Exception as e:
        logger.error(f"Failed to broadcast subtask event: {e}", exc_info=True)
```

## Step 3: Configure Environment Variables

### File: `.env.dev` or `.env`

Add these variables:

```bash
# Response Validation (Development)
VALIDATE_RESPONSES=true
VALIDATION_LOG_LEVEL=debug
VALIDATION_SAMPLE_RATE=100

# WebSocket Logging (Development)
LOG_WEBSOCKET_MESSAGES=true
WS_LOG_LEVEL=debug
WS_VALIDATION_ENABLED=true
```

## Step 4: Test the Integration

### 1. Restart the Server

```bash
# If using Docker
echo "R" | ./docker-system/docker-menu.sh

# If running locally
export VALIDATE_RESPONSES=true
export LOG_WEBSOCKET_MESSAGES=true
python -m fastmcp.server.mcp_entry_point
```

### 2. Perform Test Workflows

Open the application and perform these actions:

1. **Create a task**
   - Check logs for: "📡 WS Message: task.created"
   - Check for validation errors

2. **Add subtasks**
   - Check logs for: "📡 WS Message: subtask.created"
   - Verify subtask_count updates in parent task

3. **Update a subtask**
   - Check logs for cascade updates
   - Verify parent task receives update

4. **Complete a task**
   - Check all required fields are present
   - Verify no null values in required fields

### 3. Review Logs

```bash
# Check for validation errors
grep "VALIDATION ERRORS" logs/app.log

# Check WebSocket validation
grep "WebSocket Message Validation FAILED" logs/app.log

# View all validation activity
grep -E "VALIDATION|WS Message" logs/app.log
```

## Step 5: Document Findings

Create a report in `ai_docs/testing-qa/runtime-validation-findings.md`:

```markdown
# Runtime Validation Findings

## Test Date: YYYY-MM-DD

### Validation Errors Found

#### 1. Missing subtask_count in task.updated events
- **Severity**: ERROR
- **Frequency**: 15/20 task update events
- **Impact**: Frontend badge flicker
- **Location**: WebSocket broadcast in update_task use case
- **Reproduction**: Update task status via MCP tool

#### 2. assignees is null instead of empty array
- **Severity**: ERROR
- **Frequency**: 3/10 task creation events
- **Impact**: TypeError in frontend
- **Location**: Task entity initialization
- **Reproduction**: Create task without assignees parameter

... (document all findings) ...
```

## Expected Log Output

### Successful Validation

```
INFO - 📡 WS Message #1: task.created (user: user-123)
INFO - ✅ Response validation passed for POST /api/tasks
```

### Validation Errors

```
ERROR - 🚨 VALIDATION ERRORS in POST /api/tasks
  - Required field 'task.subtask_count' is missing or null
  - Field 'task.assignees' has wrong type: expected list, got str

ERROR - 🚨 WebSocket payload validation failed for task.created:
  - Task event 'task.created': Missing required field 'subtask_count'
  - Task event 'task.created': assignees must be a list, got str
```

## Troubleshooting

### Middleware Not Running

Check that:
1. Environment variable is set: `echo $VALIDATE_RESPONSES`
2. Middleware is in the middleware list
3. Server was restarted after changes

### No Logs Appearing

Check:
1. Log level: `VALIDATION_LOG_LEVEL=debug`
2. Logging configuration in `logging.conf`
3. Correct logger name: `__name__` in middleware

### Performance Issues

Reduce sampling rate:
```bash
export VALIDATION_SAMPLE_RATE=10  # Only 10% of requests
```

## Next Steps After Integration

1. Run application for 30 minutes of normal usage
2. Collect all validation errors from logs
3. Categorize errors by severity and frequency
4. Create reproduction tests for each error type
5. Create fix tasks prioritized by impact
6. Update investigation report with findings

## Rollback Instructions

If validation causes issues:

1. Disable via environment variable:
   ```bash
   export VALIDATE_RESPONSES=false
   export LOG_WEBSOCKET_MESSAGES=false
   ```

2. Or remove middleware from `http_server.py`:
   ```python
   # Comment out or remove:
   # final_middleware.append(Middleware(ResponseValidatorMiddleware))
   ```

3. Restart server

## Success Criteria

✅ Middleware successfully integrated
✅ No application crashes or errors
✅ Validation logs appearing in output
✅ At least 5 distinct validation errors discovered
✅ All findings documented in report
✅ Reproduction tests created for each issue
