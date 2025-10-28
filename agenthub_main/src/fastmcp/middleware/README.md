# Runtime Response Validation Middleware

This package provides runtime validation and logging for HTTP responses and WebSocket messages to catch property issues that unit tests miss.

## Components

### 1. ResponseValidatorMiddleware

Validates all HTTP responses against expected schemas to detect:
- Missing required fields
- Null values in required fields
- Wrong data types
- Incorrect values (e.g., completed_subtasks > subtask_count)

### 2. WebSocketMessageLogger

Logs and validates WebSocket messages to detect:
- Missing fields in event payloads
- Incorrect message structure
- Invalid data in cascade updates

## Quick Start

### Enable Response Validation

Add to `http_server.py`:

```python
from fastmcp.middleware import ResponseValidatorMiddleware

# In create_base_app function, add middleware:
final_middleware.append(Middleware(ResponseValidatorMiddleware))
```

### Enable WebSocket Logging

Integrate into WebSocket notification service:

```python
from fastmcp.middleware import log_websocket_message

# In broadcast method:
async def broadcast_task_event(self, event_type, task_data, user_id):
    # Validate before broadcasting
    errors = log_websocket_message(
        event=f"task.{event_type}",
        data=task_data,
        user_id=user_id,
        validate=True
    )

    if errors:
        logger.error(f"WebSocket message validation failed: {errors}")

    # Proceed with broadcast
    await websocket_manager.broadcast(...)
```

## Configuration

### Environment Variables

```bash
# Response Validation
VALIDATE_RESPONSES=true           # Enable/disable (default: true)
VALIDATION_LOG_LEVEL=warning      # error|warning|info|debug (default: warning)
VALIDATION_SAMPLE_RATE=100        # Percentage to validate (default: 100)

# WebSocket Logging
LOG_WEBSOCKET_MESSAGES=true       # Enable/disable (default: true)
WS_LOG_LEVEL=info                 # error|warning|info|debug (default: info)
WS_VALIDATION_ENABLED=true        # Enable schema validation (default: true)
```

### Development Setup

```bash
# Enable full validation and logging in development
export VALIDATE_RESPONSES=true
export VALIDATION_LOG_LEVEL=debug
export LOG_WEBSOCKET_MESSAGES=true
export WS_LOG_LEVEL=debug
```

### Production Setup

```bash
# Sample validation to reduce overhead
export VALIDATE_RESPONSES=true
export VALIDATION_LOG_LEVEL=error
export VALIDATION_SAMPLE_RATE=10    # Only validate 10% of requests
export LOG_WEBSOCKET_MESSAGES=true
export WS_LOG_LEVEL=error
```

## Usage Examples

### 1. HTTP Response Validation

The middleware automatically validates responses for these endpoints:
- `/mcp/*` - MCP tool responses
- `/api/tasks/*` - Task endpoints
- `/api/subtasks/*` - Subtask endpoints
- `/api/projects/*` - Project endpoints
- `/api/branches/*` - Branch endpoints
- `/api/context/*` - Context endpoints

No code changes needed - validation happens automatically!

### 2. WebSocket Message Validation

```python
from fastmcp.middleware import log_websocket_message, get_websocket_stats

# Log a task update event
errors = log_websocket_message(
    event="task.updated",
    data={
        "id": "task-123",
        "title": "Fix bug",
        "status": "in_progress",
        "subtask_count": 5,
        "completed_subtasks": 2,
        # ... other fields
    },
    user_id="user-456"
)

if errors:
    print(f"Validation errors: {errors}")

# Get statistics
stats = get_websocket_stats()
print(f"Total messages: {stats['total_messages']}")
print(f"Validation errors: {stats['validation_errors']}")
```

### 3. Custom Validation

```python
from fastmcp.middleware import ResponseValidator

# Validate a task object
task_data = {
    "id": "task-123",
    "title": "My Task",
    # ...
}

issues = ResponseValidator.validate_task_response(task_data)

for issue in issues:
    print(f"{issue.severity}: {issue.message}")
    print(f"  Field: {issue.field_path}")
    print(f"  Expected: {issue.expected}")
    print(f"  Actual: {issue.actual}")
```

## Validation Schemas

### Task Schema

Required fields:
- `id` (str)
- `title` (str)
- `status` (str)
- `priority` (str)
- `assignees` (list)
- `subtask_count` (int)
- `completed_subtasks` (int)
- `progress_percentage` (int)
- `created_at` (str)
- `updated_at` (str)

Optional fields:
- `project_id` (str)
- `git_branch_id` (str)
- `description` (str)
- `details` (str)
- `labels` (list)
- `context_data` (dict)

### Subtask Schema

Required fields:
- `id` (str)
- `title` (str)
- `status` (str)
- `priority` (str)
- `parent_task_id` (str)
- `assignees` (list)
- `progress_percentage` (int)
- `created_at` (str)
- `updated_at` (str)

## Validation Severity Levels

- **ERROR**: Critical issues that will cause frontend bugs
  - Missing required fields
  - Wrong data types
  - Invalid values (e.g., completed > total)

- **WARNING**: Potential issues that might cause problems
  - Null values with defaults
  - Missing optional fields that are usually present

- **INFO**: Non-critical observations
  - Unexpected fields (possible schema drift)
  - Deprecated fields still present

## Monitoring and Debugging

### View Validation Statistics

```python
from fastmcp.middleware import ResponseValidatorMiddleware

# Get stats from middleware instance
stats = middleware_instance.get_stats()
print(f"Validated {stats['validated_requests']} of {stats['total_requests']} requests")
print(f"Found {stats['issues_found']} issues ({stats['errors']} errors, {stats['warnings']} warnings)")
```

### Check WebSocket Logs

```bash
# Filter validation errors in logs
grep "VALIDATION ERRORS" logs/app.log

# Filter WebSocket validation failures
grep "WebSocket Message Validation FAILED" logs/app.log
```

### Common Issues Found

1. **Missing `subtask_count`**
   ```
   ERROR: Required field 'task.subtask_count' is missing or null
   ```

2. **Wrong type for `assignees`**
   ```
   ERROR: Field 'task.assignees' has wrong type: expected list, got str
   ```

3. **Invalid subtask count**
   ```
   ERROR: completed_subtasks (10) exceeds subtask_count (5)
   ```

## Integration Checklist

- [ ] Add `ResponseValidatorMiddleware` to HTTP server
- [ ] Integrate `log_websocket_message` in WebSocket broadcasts
- [ ] Set environment variables for development
- [ ] Run application and check logs for validation errors
- [ ] Create fix tasks for discovered issues
- [ ] Document patterns in investigation report

## Performance Impact

- **HTTP Validation**: ~1-2ms per request (only for JSON responses)
- **WebSocket Validation**: ~0.5ms per message
- **Sampling**: Use `VALIDATION_SAMPLE_RATE` to reduce overhead in production

## Next Steps

1. Enable middleware in development environment
2. Run typical user workflows (create task, add subtasks, update, complete)
3. Review logs for validation errors
4. Document all discovered issues
5. Create reproduction tests
6. Create fix tasks for each issue

## Files

- `response_validator_middleware.py` - HTTP response validation
- `websocket_message_logger.py` - WebSocket message logging
- `__init__.py` - Package exports
- `README.md` - This file
