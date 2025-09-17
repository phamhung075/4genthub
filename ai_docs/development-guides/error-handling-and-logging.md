# Error Handling and Logging Guide

## Overview

The 4genthub system implements comprehensive error handling and logging to ensure reliable operation and easy debugging. This guide covers the error handling patterns, logging configuration, and best practices.

## Error Handling Architecture

### Exception Hierarchy

The system uses a hierarchical exception structure for consistent error handling:

```
TaskManagementException (Base)
├── ValidationException
├── ResourceNotFoundException
├── ResourceAlreadyExistsException
├── OperationNotPermittedException
├── DatabaseException
│   ├── DatabaseConnectionException
│   └── DatabaseIntegrityException
├── ConcurrencyException
├── ExternalServiceException
└── ConfigurationException

TaskDomainError (Base)
├── TaskNotFoundError
├── InvalidTaskStateError
├── InvalidTaskTransitionError
├── TaskCompletionBlockedException
└── AutoRuleGenerationError
```

### Error Severity Levels

Each error has an associated severity level:

- **LOW**: Can be retried or ignored (e.g., validation errors)
- **MEDIUM**: Should be logged and monitored (e.g., not found errors)
- **HIGH**: Requires immediate attention (e.g., database errors)
- **CRITICAL**: System-breaking, requires immediate action (e.g., configuration errors)

### Error Response Format

All errors return a consistent JSON response:

```json
{
  "success": false,
  "error": "User-friendly error message",
  "error_code": "STANDARDIZED_ERROR_CODE",
  "severity": "medium",
  "details": {
    "field": "affected_field",
    "resource_id": "resource_identifier"
  },
  "request_id": "unique-request-id",
  "recoverable": true
}
```

## Logging System

### Configuration

The logging system is configured through environment variables:

```bash
# Log level (DEBUG, INFO, WARNING, ERROR, CRITICAL)
LOG_LEVEL=INFO

# Log directory
LOG_DIR=logs

# Log format (text or json)
LOG_FORMAT=json
```

### Logger Initialization

```python
from fastmcp.task_management.infrastructure.logging import TaskManagementLogger, init_logging

# Initialize logging system
init_logging()

# Get a logger for your module
logger = TaskManagementLogger.get_logger(__name__)
```

### Structured Logging

The system supports structured logging with contextual information:

```python
# Add context to logger
ctx_logger = TaskManagementLogger.add_context(
    logger,
    user_id="user123",
    task_id="task456",
    project_id="project789",
    operation="create_task"
)

# Log with context
ctx_logger.info("Task created successfully")
```

### Log Files

The system creates multiple log files:

1. **4genthub.log** - Main application log with all levels
2. **4genthub_errors.log** - Error-only log for quick issue identification

Both files support automatic rotation when they reach 10MB, keeping 5 backup copies.

## Error Handling Patterns

### Using the Error Handler Decorator

```python
from fastmcp.task_management.interface.utils.error_handler import handle_operation_error

@handle_operation_error("task creation")
async def create_task(self, request: CreateTaskRequest):
    # Your code here
    pass
```

### Using the Log Operation Decorator

```python
from fastmcp.task_management.infrastructure.logging import log_operation

@log_operation("create_task")
async def create_task(self, task_id: str, **kwargs):
    # Automatically logs start, completion, and errors
    pass
```

### Manual Error Handling

```python
try:
    result = await task_service.create_task(request)
except ValidationException as e:
    logger.warning(f"Validation failed: {e}")
    return {
        "success": False,
        "error": e.user_message,
        "error_code": e.error_code
    }
except TaskDomainError as e:
    logger.error(f"Domain error: {e}", exc_info=True)
    raise
```

## HTTP Error Middleware

The system includes global error handling middleware that:

1. Catches all exceptions
2. Logs errors with full context
3. Returns consistent error responses
4. Maps domain errors to appropriate HTTP status codes
5. Tracks request duration and adds request IDs

### Status Code Mapping

- **400 Bad Request**: Validation errors, low severity domain errors
- **404 Not Found**: Resource not found errors
- **409 Conflict**: Medium severity domain errors, state conflicts
- **422 Unprocessable Entity**: Input validation failures
- **500 Internal Server Error**: Unexpected errors, high severity issues
- **503 Service Unavailable**: Database errors, critical system issues

## Best Practices

### 1. Use Specific Exceptions

```python
# Good
raise TaskNotFoundException(task_id="task123")

# Avoid
raise Exception("Task not found")
```

### 2. Include Context

```python
raise ValidationException(
    message="Invalid priority value",
    field="priority",
    value=priority,
    context={"valid_values": ["high", "medium", "low"]}
)
```

### 3. Log at Appropriate Levels

```python
# Debug - Detailed diagnostic information
logger.debug(f"Checking cache for task {task_id}")

# Info - General informational messages
logger.info(f"Task {task_id} created successfully")

# Warning - Something unexpected but recoverable
logger.warning(f"Cache miss for task {task_id}, fetching from database")

# Error - Error events but application continues
logger.error(f"Failed to send notification for task {task_id}", exc_info=True)

# Critical - System might not recover
logger.critical(f"Database connection lost", exc_info=True)
```

### 4. Use Structured Logging

```python
# Good - Structured data
logger.info(
    "Task status updated",
    extra={
        "task_id": task_id,
        "old_status": old_status,
        "new_status": new_status,
        "updated_by": user_id
    }
)

# Avoid - Unstructured strings
logger.info(f"Task {task_id} status changed from {old_status} to {new_status}")
```

### 5. Handle Errors Gracefully

```python
async def get_task_with_fallback(task_id: str):
    try:
        # Try cache first
        return await cache_service.get_task(task_id)
    except CacheException as e:
        logger.warning(f"Cache error, falling back to database: {e}")
        # Fall back to database
        return await task_repository.get_task(task_id)
```

## Monitoring and Debugging

### Log Analysis

To analyze logs for specific patterns:

```bash
# Find all errors for a specific task
grep -i "task_id.*task123" logs/4genthub.log | grep ERROR

# Get all database errors
grep "DATABASE_ERROR" logs/4genthub_errors.log

# View logs in real-time
tail -f logs/4genthub.log | jq '.'  # For JSON format
```

### Recent Improvements (January 2025)

### Critical Error Handling Fixes

> **📋 Status**: All critical infrastructure errors have been resolved. Error handling has been significantly improved with better patterns and clearer error messages.

#### Fixed Error Categories

**1. Import Scoping Errors (RESOLVED)**
- **Previous Issue**: `UnboundLocalError: cannot access local variable 'TaskId'`
- **Root Cause**: Import statements inside loops causing variable scoping conflicts
- **Fix Applied**: Moved all imports to module level, eliminated scoping issues
- **Prevention**: Added validation patterns in testing guide

**2. Async/Sync Pattern Mismatches (RESOLVED)**
- **Previous Issue**: `TypeError: object is not awaitable` and `RuntimeWarning: coroutine was never awaited`
- **Root Cause**: Inconsistent async patterns between tests and repository implementations
- **Fix Applied**: Converted all repository methods to proper async patterns
- **Prevention**: Added async consistency validation in testing framework

**3. Database Schema Constraint Errors (RESOLVED)**
- **Previous Issue**: `FOREIGN KEY constraint failed` and `no such column` errors
- **Root Cause**: Outdated database schema not matching model definitions
- **Fix Applied**: Updated schema with correct foreign key references
- **Prevention**: Added schema validation tests and migration procedures

**4. Context Management Errors (RESOLVED)**
- **Previous Issue**: "Task completion requires context to be created first"
- **Enhanced**: More descriptive error messages with clear resolution steps
- **Improvement**: Better error handling with specific suggestions for context operations

### Enhanced Error Messages

The system now provides more helpful error messages with actionable suggestions:

```json
{
  "success": false,
  "error": "Task completion requires context to be created first",
  "suggestions": [
    "Update context using manage_context",
    "Ensure context exists before completing task",
    "Check context inheritance chain is complete"
  ],
  "suggested_actions": [
    {
      "action": "manage_context",
      "parameters": {
        "action": "update",
        "level": "task",
        "context_id": "your-task-id",
        "data": {"progress": "completed"}
      }
    }
  ]
}
```

## Common Error Patterns

### 1. Task Management Errors

**Task Not Found**
- Check if task ID is correct
- Verify task hasn't been deleted
- Ensure correct project/branch context

**Task Completion Errors**
- ✅ **NEW**: Clear guidance on context requirements
- Update context before completion using `manage_context`
- Verify all subtasks are completed
- Check task status allows completion

### 2. Infrastructure Errors

**Database Connection Errors**
- Check database service is running
- Verify connection string in environment
- Check for connection pool exhaustion
- ✅ **NEW**: Validate database schema matches models

**Import and Module Errors**
- ✅ **NEW**: All import path conflicts resolved
- Use unified context service imports only
- Avoid imports inside loops or conditional blocks
- Ensure all async methods are properly awaited

### 3. Context System Errors

**Context Resolution Errors**
- ✅ **NEW**: Enhanced error messages with specific guidance
- Use `validate_context_inheritance` to debug issues
- Ensure parent contexts exist before creating child contexts
- Check inheritance chain is not broken

**Schema Validation Errors**
- ✅ **NEW**: Database schema automatically validated
- Foreign key constraints properly enforced
- Column names match current model definitions
- Migration procedures available for schema updates

### 4. Development Errors

**Testing Errors**
- ✅ **NEW**: Proper mock configuration patterns documented
- Use correct context manager mocking
- Ensure async test patterns match repository implementation
- Validate test database schema matches production

### Debugging January 2025 Fixes

For detailed information about the fixes and how to validate they're working:

```bash
# Quick validation commands
# 1. Test TaskId scoping (should work without UnboundLocalError)
mcp__4genthub_http__manage_task(
    action="create",
    git_branch_id="test-branch-uuid",
    title="Validation test",
    dependencies=["dep1", "dep2"]
)

# 2. Test async repository patterns (should complete without warnings)
mcp__4genthub_http__manage_context(
    action="create",
    task_id="test-task-uuid",
    data_title="Test context"
)

# 3. Test database schema (should not show constraint errors)
# Any valid task creation should work without foreign key errors

# 4. Test import resolution (should not show ModuleNotFoundError)
# Any context operation should work without import errors
```

**Complete Fix Documentation**: See [Unified Context System Fixes - January 19, 2025](fixes/unified_context_system_fixes_2025_01_19.md) for comprehensive technical details.

**Regression Testing**: See [Testing Guide - Recent Fixes and Validation Testing](testing.md#recent-fixes-and-validation-testing-january-2025) for test patterns to validate fixes.

### Performance Monitoring

The logging system tracks operation duration:

```json
{
  "timestamp": "2024-01-15T10:30:45.123Z",
  "level": "INFO",
  "message": "Completed create_task in 0.145s",
  "operation": "create_task",
  "duration_ms": 145
}
```

## Error Recovery Strategies

### 1. Automatic Retry

For transient errors:

```python
from tenacity import retry, stop_after_attempt, wait_exponential

@retry(
    stop=stop_after_attempt(3),
    wait=wait_exponential(multiplier=1, min=1, max=10)
)
async def create_task_with_retry(request):
    return await task_service.create_task(request)
```

### 2. Circuit Breaker

For external service calls:

```python
from circuitbreaker import circuit

@circuit(failure_threshold=5, recovery_timeout=60)
async def call_external_service():
    # Service call that might fail
    pass
```

### 3. Graceful Degradation

```python
async def get_task_details(task_id: str):
    task = await get_task(task_id)
    
    # Try to enrich with additional data
    try:
        task["analytics"] = await get_task_analytics(task_id)
    except ExternalServiceException:
        logger.warning(f"Analytics service unavailable for task {task_id}")
        task["analytics"] = None
    
    return task
```

## Testing Error Scenarios

### Unit Testing

```python
import pytest
from fastmcp.task_management.domain.exceptions import TaskNotFoundException

async def test_task_not_found():
    with pytest.raises(TaskNotFoundException) as exc_info:
        await task_service.get_task("non-existent-id")
    
    assert exc_info.value.task_id == "non-existent-id"
    assert exc_info.value.error_code == "TASK_NOT_FOUND"
```

### Integration Testing

```python
async def test_error_response_format(client):
    response = await client.get("/api/tasks/invalid-id")
    
    assert response.status_code == 404
    data = response.json()
    assert data["success"] is False
    assert "error_code" in data
    assert "request_id" in data
```

## Troubleshooting

### Enable Debug Logging

For detailed troubleshooting:

```bash
export LOG_LEVEL=DEBUG
export LOG_FORMAT=text  # Easier to read for debugging
```

### Common Issues

1. **"Logger not initialized"**
   - Ensure `init_logging()` is called at startup
   - Check import paths are correct

2. **"Permission denied" on log files**
   - Verify write permissions on log directory
   - Check user running the application

3. **"Log rotation not working"**
   - Ensure sufficient disk space
   - Check file permissions for creating new files

4. **✅ "UnboundLocalError: TaskId" (RESOLVED)**
   - This error has been permanently fixed in January 2025
   - All TaskId imports are now at module level
   - If you encounter this, check for regression in import patterns

5. **✅ "ModuleNotFoundError: hierarchical_context_service" (RESOLVED)**
   - All import paths have been updated to use unified context services
   - Old hierarchical import paths have been eliminated
   - If you encounter this, check for outdated import statements

6. **✅ "Foreign key constraint failed" (RESOLVED)**
   - Database schema has been updated to match current model definitions
   - All foreign key references are now correct
   - If you encounter this, verify database schema is up to date

7. **✅ "TypeError: object is not awaitable" (RESOLVED)**
   - All repository methods have been converted to proper async patterns
   - Async/sync consistency is now maintained across the codebase
   - If you encounter this, check for regression in async patterns

### Getting Help

When reporting issues, include:

1. Error message and stack trace
2. Request ID from error response
3. Relevant log entries (sanitized)
4. Steps to reproduce
5. Environment details (OS, Python version, etc.)

**Important**: If you encounter any of the resolved errors (UnboundLocalError, ModuleNotFoundError, foreign key constraints, async/await issues), these may indicate regressions that need immediate attention. Please reference the [January 2025 fixes documentation](fixes/unified_context_system_fixes_2025_01_19.md) for context.

---

**Document Version**: 2.0  
**Last Updated**: January 19, 2025  
**Major Updates**: Added January 2025 error handling improvements, enhanced error messages, validation procedures, and cross-references to fix documentation