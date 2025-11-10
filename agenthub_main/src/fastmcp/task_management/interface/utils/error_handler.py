"""Centralized error handler for user-friendly error messages and recovery instructions."""

import inspect
import sqlite3
from enum import Enum
from typing import Any

from sqlalchemy.exc import SQLAlchemyError

from ...infrastructure.logging import TaskManagementLogger

logger = TaskManagementLogger.get_logger(__name__)


class ErrorCode(Enum):
    """Standardized error codes for client-side handling."""

    # Task-related errors
    TASK_NOT_FOUND = "TASK_NOT_FOUND"
    TASK_ALREADY_EXISTS = "TASK_ALREADY_EXISTS"
    TASK_COMPLETION_BLOCKED = "TASK_COMPLETION_BLOCKED"
    INVALID_TASK_STATUS = "INVALID_TASK_STATUS"

    # Context-related errors
    CONTEXT_REQUIRED = "CONTEXT_REQUIRED"
    CONTEXT_NOT_FOUND = "CONTEXT_NOT_FOUND"
    CONTEXT_ALREADY_EXISTS = "CONTEXT_ALREADY_EXISTS"

    # Validation errors
    VALIDATION_ERROR = "VALIDATION_ERROR"
    MISSING_REQUIRED_PARAMETER = "MISSING_REQUIRED_PARAMETER"
    INVALID_PARAMETER_FORMAT = "INVALID_PARAMETER_FORMAT"

    # Database errors
    DATABASE_ERROR = "DATABASE_ERROR"
    CONSTRAINT_VIOLATION = "CONSTRAINT_VIOLATION"

    # System errors
    INTERNAL_ERROR = "INTERNAL_ERROR"
    OPERATION_NOT_SUPPORTED = "OPERATION_NOT_SUPPORTED"


class UserFriendlyErrorHandler:
    """Centralized error handler that converts internal exceptions to user-friendly messages."""

    @staticmethod
    def handle_error(
        exception: Exception,
        operation: str = "operation",
        context: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        """
        Convert any exception to a user-friendly error response.

        Args:
            exception: The exception that occurred
            operation: Description of the operation that failed
            context: Additional context for error handling

        Returns:
            Standardized error response with user-friendly message and recovery instructions
        """
        context = context or {}

        # Handle specific exception types
        if isinstance(exception, (sqlite3.Error, SQLAlchemyError)):
            return UserFriendlyErrorHandler._handle_database_error(
                exception, operation, context
            )

        if isinstance(exception, ValueError):
            # Check if this is a context-related error that should be routed specially
            error_msg = str(exception).lower()
            if "context must be updated" in error_msg:
                # Skip special handling for task completion - let the use case handle it
                context.get("action", "").lower()
                operation.lower()

                # DISABLED: Let CompleteTaskUseCase handle context validation errors internally
                # if action == "complete" or "complet" in operation_lower:
                #     return UserFriendlyErrorHandler._handle_context_required_error(exception, context)
                pass  # Fall through to generic validation error

            return UserFriendlyErrorHandler._handle_validation_error(
                exception, operation, context
            )

        if isinstance(exception, KeyError):
            return UserFriendlyErrorHandler._handle_missing_parameter_error(
                exception, operation, context
            )

        # Handle business logic exceptions by message content
        error_message = str(exception).lower()

        if "task not found" in error_message:
            return UserFriendlyErrorHandler._handle_task_not_found_error(
                exception, context
            )

        if "incomplete subtasks" in error_message:
            return UserFriendlyErrorHandler._handle_incomplete_subtasks_error(
                exception, context
            )

        if "validation error" in error_message or "invalid" in error_message:
            return UserFriendlyErrorHandler._handle_validation_error(
                exception, operation, context
            )

        # Generic fallback for unknown errors
        logger.error(f"Unhandled exception in {operation}: {exception}", exc_info=True)
        return UserFriendlyErrorHandler._handle_generic_error(
            exception, operation, context
        )

    @staticmethod
    def _handle_database_error(
        exception: sqlite3.Error | SQLAlchemyError,
        operation: str,
        context: dict[str, Any],
    ) -> dict[str, Any]:
        """Handle SQLite and SQLAlchemy database errors with user-friendly messages."""

        error_str = str(exception).lower()

        # Enhanced label-specific error handling
        if "label" in error_str and ("timestamp" in error_str or "created_at" in error_str or "updated_at" in error_str):
            return {
                "success": False,
                "error": "Label creation failed: Timestamp constraint violation.",
                "error_code": ErrorCode.CONSTRAINT_VIOLATION.value,
                "explanation": "Labels require UTC-aware timestamps. This is a system error, not a user error.",
                "recovery_instructions": [
                    "This error indicates a bug in the system code",
                    "The system should automatically use UTC timestamps",
                    "You can create the task without labels for now",
                ],
                "technical_details": {
                    "issue": "Timestamps must be timezone-aware UTC datetime objects",
                    "fix": "Use datetime.now(UTC) instead of datetime.now()",
                    "location": "Label repository or service layer",
                },
                "workaround": "Create task without labels parameter, add labels later after fix",
                "examples": {
                    "create_without_labels": "manage_task(action='create', title='Task', git_branch_id='...', assignees=['coding-agent'])",
                },
            }

        if "unique constraint failed" in error_str:
            # Check if this is a label duplicate
            if "label" in error_str:
                return {
                    "success": False,
                    "error": "A label with this name already exists.",
                    "error_code": ErrorCode.CONSTRAINT_VIOLATION.value,
                    "recovery_instructions": [
                        "Use a different label name",
                        "The existing label will be automatically reused for the task",
                        "Labels are shared across tasks to maintain consistency",
                    ],
                    "examples": {
                        "alternative_names": "Try 'backend-api', 'api-backend', or 'backend-service'",
                    },
                }
            return {
                "success": False,
                "error": "A record with this information already exists.",
                "error_code": ErrorCode.CONSTRAINT_VIOLATION.value,
                "recovery_instructions": [
                    "Check if you're trying to create a duplicate record",
                    "Use 'update' action instead of 'create' if the record exists",
                    "Verify the unique identifier is correct",
                ],
                "examples": {
                    "check_existing": "Use action='get' to check if the record already exists",
                    "update_instead": "Use action='update' with the existing record ID",
                },
            }

        if "foreign key constraint failed" in error_str:
            return {
                "success": False,
                "error": "Referenced record does not exist.",
                "error_code": ErrorCode.CONSTRAINT_VIOLATION.value,
                "recovery_instructions": [
                    "Verify the referenced ID exists (e.g., task_id, project_id)",
                    "Create the referenced record first",
                    "Check for typos in the ID parameter",
                ],
                "examples": {
                    "verify_id": "Use action='get' to verify the referenced record exists",
                    "create_parent": "Create the parent record before creating dependent records",
                },
            }

        if "readonly database" in error_str:
            return {
                "success": False,
                "error": "Database is temporarily read-only.",
                "error_code": ErrorCode.DATABASE_ERROR.value,
                "recovery_instructions": [
                    "Try the operation again in a few seconds",
                    "Check if there's ongoing maintenance",
                    "Contact support if the problem persists",
                ],
            }

        if "database is locked" in error_str:
            return {
                "success": False,
                "error": "Database is temporarily busy.",
                "error_code": ErrorCode.DATABASE_ERROR.value,
                "recovery_instructions": [
                    "Wait a moment and try again",
                    "The system may be processing other requests",
                ],
            }

        # Generic database error
        return {
            "success": False,
            "error": "Database operation failed.",
            "error_code": ErrorCode.DATABASE_ERROR.value,
            "recovery_instructions": [
                "Try the operation again",
                "Check your parameters are correct",
                "Contact support if the problem persists",
            ],
        }

    @staticmethod
    def _handle_context_required_error(
        exception: Exception, context: dict[str, Any]
    ) -> dict[str, Any]:
        """Handle context requirement errors with specific recovery steps."""

        task_id = context.get("task_id", "your-task-id")
        context.get("project_id", "agenthub")

        return {
            "success": False,
            "error": "Task completion requires context to be created first.",
            "error_code": ErrorCode.CONTEXT_REQUIRED.value,
            "explanation": "Context stores task progress with inheritance from project and global contexts. This ensures work history is preserved with proper organizational structure.",
            "recovery_instructions": [
                "Create context for this task first",
                "Update the context with your progress",
                "Then try completing the task again",
            ],
            "step_by_step_fix": [
                {
                    "step": 1,
                    "action": "Create context",
                    "command": f"manage_context(action='create', level='task', context_id='{task_id}', data={{'title': 'Task Title', 'description': 'Task context'}})",
                },
                {
                    "step": 2,
                    "action": "Update context status",
                    "command": f"manage_context(action='update', level='task', context_id='{task_id}', data={{'status': 'done'}})",
                },
                {
                    "step": 3,
                    "action": "Complete task",
                    "command": f"manage_task(action='complete', task_id='{task_id}', completion_summary='Your summary here')",
                },
            ],
            "examples": {
                "minimal_fix": f"manage_context(action='create', level='task', context_id='{task_id}', data={{'title': 'Task Title'}}); manage_task(action='complete', task_id='{task_id}', completion_summary='Work completed')"
            },
        }

    @staticmethod
    def _handle_task_not_found_error(
        exception: Exception, context: dict[str, Any]
    ) -> dict[str, Any]:
        """Handle task not found errors."""

        task_id = context.get("task_id", "the specified task")

        return {
            "success": False,
            "error": f"Task '{task_id}' was not found.",
            "error_code": ErrorCode.TASK_NOT_FOUND.value,
            "recovery_instructions": [
                "Verify the task ID is correct",
                "Check if the task was deleted",
                "Use action='list' to see available tasks",
                "Use action='search' to find tasks by title",
            ],
            "examples": {
                "list_tasks": "manage_task(action='list', git_branch_id='your-branch-id')",
                "search_tasks": "manage_task(action='search', query='task title keywords')",
            },
        }

    @staticmethod
    def _handle_incomplete_subtasks_error(
        exception: Exception, context: dict[str, Any]
    ) -> dict[str, Any]:
        """Handle incomplete subtasks blocking task completion."""

        task_id = context.get("task_id", "your-task-id")

        return {
            "success": False,
            "error": "Cannot complete task while subtasks remain incomplete.",
            "error_code": ErrorCode.TASK_COMPLETION_BLOCKED.value,
            "explanation": "All subtasks must be completed before the parent task can be marked as done.",
            "recovery_instructions": [
                "List all subtasks to see which are incomplete",
                "Complete each remaining subtask",
                "Then try completing the parent task again",
            ],
            "step_by_step_fix": [
                {
                    "step": 1,
                    "action": "List subtasks",
                    "command": f"manage_subtask(action='list', task_id='{task_id}')",
                },
                {
                    "step": 2,
                    "action": "Complete each incomplete subtask",
                    "command": f"manage_subtask(action='complete', task_id='{task_id}', subtask_id='subtask-id', completion_summary='Subtask completed')",
                },
                {
                    "step": 3,
                    "action": "Complete parent task",
                    "command": f"manage_task(action='complete', task_id='{task_id}', completion_summary='All subtasks completed')",
                },
            ],
        }

    @staticmethod
    def _handle_validation_error(
        exception: Exception, operation: str, context: dict[str, Any]
    ) -> dict[str, Any]:
        """Handle validation errors with specific format guidance."""

        error_message = str(exception)

        # Common validation patterns
        if "labels" in error_message.lower() or "label" in error_message.lower():
            # Check for specific label error types
            if "timestamp" in error_message.lower() or "utc" in error_message.lower():
                return {
                    "success": False,
                    "error": "Label creation failed: System timestamp error.",
                    "error_code": ErrorCode.CONSTRAINT_VIOLATION.value,
                    "explanation": "The system failed to create UTC-aware timestamps for labels. This is a bug in the system code.",
                    "recovery_instructions": [
                        "This is not your fault - it's a system bug",
                        "You can create the task without labels as a workaround",
                        "Report this error to the development team",
                    ],
                    "technical_details": {
                        "issue": "Label timestamps must be UTC-aware",
                        "expected": "datetime.now(UTC)",
                        "actual": "datetime.now() (naive datetime)",
                        "fix_location": "Label repository or service layer needs to add UTC",
                    },
                    "workaround": {
                        "description": "Create task without labels, add labels later",
                        "command": "manage_task(action='create', title='Task', git_branch_id='...', assignees=['coding-agent'])",
                    },
                }
            if "format" in error_message.lower() or "invalid" in error_message.lower():
                return {
                    "success": False,
                    "error": "Invalid labels format. Labels must be an array of strings or comma-separated string.",
                    "error_code": ErrorCode.INVALID_PARAMETER_FORMAT.value,
                    "recovery_instructions": [
                        "Use array format: labels=['tag1', 'tag2', 'tag3']",
                        "Or comma-separated string: labels='tag1,tag2,tag3'",
                        "Each label should be a short, descriptive keyword",
                        "Labels can contain letters, numbers, hyphens, and underscores",
                    ],
                    "examples": {
                        "correct_array": "labels=['bug', 'urgent', 'frontend']",
                        "correct_string": "labels='bug,urgent,frontend'",
                        "with_hyphens": "labels='api-integration,backend-service,high-priority'",
                        "incorrect_spaces": "labels='bug urgent frontend' (needs commas!)",
                        "incorrect_special_chars": "labels=['bug!', 'urgent@'] (special chars not allowed)",
                    },
                    "label_naming_tips": [
                        "Use lowercase for consistency",
                        "Use hyphens to separate words: 'api-integration' not 'apiintegration'",
                        "Be specific but concise: 'frontend-bug' not 'frontend'",
                        "Common labels: bug, feature, urgent, backend, frontend, api, database, security",
                    ],
                }
            # Generic label validation error
            return {
                "success": False,
                "error": f"Label validation error: {error_message}",
                "error_code": ErrorCode.VALIDATION_ERROR.value,
                "recovery_instructions": [
                    "Check your label format and names",
                    "Labels must be alphanumeric with hyphens/underscores",
                    "Use descriptive, concise names",
                ],
                "examples": {
                    "good_labels": "labels=['bug', 'urgent', 'api-integration', 'backend-service']",
                    "bad_labels": "labels=['bug!', 'urgent@work', 'fix it now'] (special chars, spaces)",
                },
            }

        if "progress_percentage" in error_message.lower():
            return {
                "success": False,
                "error": "Invalid progress percentage format. Must be an integer between 0-100.",
                "error_code": ErrorCode.INVALID_PARAMETER_FORMAT.value,
                "recovery_instructions": [
                    "Use integer values only: progress_percentage=50",
                    "Range must be 0-100",
                    "Don't include % symbol or quotes",
                ],
                "examples": {
                    "correct": "progress_percentage=75",
                    "incorrect_string": "progress_percentage='75'",
                    "incorrect_symbol": "progress_percentage='75%'",
                },
            }

        if "assignees" in error_message.lower():
            return {
                "success": False,
                "error": "Invalid assignees format. Assignees must be an array of user identifiers.",
                "error_code": ErrorCode.INVALID_PARAMETER_FORMAT.value,
                "recovery_instructions": [
                    "Use array format: assignees=['user1', 'user2']",
                    "Each assignee should be a valid user identifier",
                ],
                "examples": {
                    "correct": "assignees=['alice', 'bob']",
                    "single_user": "assignees=['alice']",
                    "empty": "assignees=[]",
                },
            }

        # Generic validation error
        return {
            "success": False,
            "error": f"Invalid parameter format: {error_message}",
            "error_code": ErrorCode.VALIDATION_ERROR.value,
            "recovery_instructions": [
                "Check the parameter format matches the expected type",
                "Refer to documentation for correct parameter formats",
                "Use workflow guidance examples for reference",
            ],
        }

    @staticmethod
    def _handle_missing_parameter_error(
        exception: Exception, operation: str, context: dict[str, Any]
    ) -> dict[str, Any]:
        """Handle missing required parameter errors."""

        missing_param = str(exception).strip("'\"")

        return {
            "success": False,
            "error": f"Required parameter '{missing_param}' is missing.",
            "error_code": ErrorCode.MISSING_REQUIRED_PARAMETER.value,
            "recovery_instructions": [
                f"Add the required parameter: {missing_param}",
                "Check the function signature for all required parameters",
                "Use workflow guidance examples for complete parameter lists",
            ],
            "examples": {
                "with_parameter": f"Include {missing_param} in your function call"
            },
        }

    @staticmethod
    def _handle_generic_error(
        exception: Exception, operation: str, context: dict[str, Any]
    ) -> dict[str, Any]:
        """Handle unknown errors with generic recovery advice."""

        return {
            "success": False,
            "error": f"The {operation} could not be completed.",
            "error_code": ErrorCode.INTERNAL_ERROR.value,
            "recovery_instructions": [
                "Try the operation again",
                "Check that all required parameters are provided",
                "Verify your parameters are in the correct format",
                "Contact support if the problem persists",
            ],
            "technical_details": {
                "operation": operation,
                "error_type": type(exception).__name__,
            },
        }


def handle_operation_error(operation: str):
    """
    Decorator to automatically handle errors in MCP operations.

    Usage:
        @handle_operation_error("task creation")
        def create_task(self, ...):
            # Implementation
    """

    def decorator(func):
        import functools

        async def async_wrapper(*args, **kwargs):
            try:
                # Log operation start
                logger.debug(f"Starting {operation}", extra={"operation": operation})
                result = await func(*args, **kwargs)
                logger.debug(
                    f"Completed {operation} successfully",
                    extra={"operation": operation},
                )
                return result
            except Exception as e:
                # Extract context from function arguments if available
                context = {}
                if len(args) > 1 and hasattr(args[1], "__dict__"):
                    context = {
                        k: v
                        for k, v in args[1].__dict__.items()
                        if isinstance(v, (str, int, float, bool))
                    }

                # Log the error with full context
                logger.error(
                    f"Error in {operation}: {str(e)}",
                    exc_info=True,
                    extra={
                        "operation": operation,
                        "error_type": type(e).__name__,
                        "context": context,
                    },
                )

                return UserFriendlyErrorHandler.handle_error(e, operation, context)

        @functools.wraps(func)
        def sync_wrapper(*args, **kwargs):
            try:
                # Log operation start
                logger.debug(f"Starting {operation}", extra={"operation": operation})
                result = func(*args, **kwargs)
                logger.debug(
                    f"Completed {operation} successfully",
                    extra={"operation": operation},
                )
                return result
            except Exception as e:
                # Extract context from function arguments if available
                context = {}
                if len(args) > 1 and hasattr(args[1], "__dict__"):
                    context = {
                        k: v
                        for k, v in args[1].__dict__.items()
                        if isinstance(v, (str, int, float, bool))
                    }

                # Log the error with full context
                logger.error(
                    f"Error in {operation}: {str(e)}",
                    exc_info=True,
                    extra={
                        "operation": operation,
                        "error_type": type(e).__name__,
                        "context": context,
                    },
                )

                return UserFriendlyErrorHandler.handle_error(e, operation, context)

        # Return appropriate wrapper based on function type
        if inspect.iscoroutinefunction(func):
            return async_wrapper
        else:
            return sync_wrapper

    return decorator
