"""Token Usage Tracking Service

This service provides utilities for tracking detailed token usage statistics
per operation type (e.g., task_create, subtask_update, agent_call).

Usage Example:
    from fastmcp.task_management.application.services.token_usage_tracking_service import track_token_operation

    # In your controller/handler:
    await track_token_operation(token_id="tok_abc123", operation="task_create", session=db_session)
"""

import logging
from typing import Optional
from sqlalchemy.orm import Session

logger = logging.getLogger(__name__)


async def track_token_operation(
    token_id: Optional[str],
    operation: str,
    session: Session
) -> bool:
    """
    Track a specific operation for a token.

    This function updates the token's usage_stats JSON field to increment
    the counter for the specified operation type.

    Args:
        token_id: Token identifier (can be None if no token authentication)
        operation: Operation type (e.g., 'task_create', 'subtask_update', 'agent_call')
        session: Database session

    Returns:
        True if tracking was successful, False otherwise

    Example:
        await track_token_operation(
            token_id=payload.get("token_id"),
            operation="task_create",
            session=session
        )
    """
    if not token_id:
        logger.debug(f"No token_id provided for operation tracking: {operation}")
        return False

    try:
        from ...infrastructure.repositories.token_repository import TokenRepository

        repository = TokenRepository(session)
        success = await repository.update_token_usage(token_id, operation)

        if success:
            logger.debug(f"✅ Tracked token operation: {operation} for token {token_id}")
        else:
            logger.warning(f"⚠️ Failed to track operation: {operation} for token {token_id}")

        return success

    except Exception as e:
        logger.error(f"❌ Error tracking token operation {operation}: {e}")
        return False


def get_operation_name(entity: str, action: str) -> str:
    """
    Generate a standardized operation name from entity and action.

    Args:
        entity: Entity type (e.g., 'task', 'subtask', 'project')
        action: Action type (e.g., 'create', 'update', 'delete')

    Returns:
        Standardized operation name (e.g., 'task_create')

    Example:
        operation = get_operation_name('task', 'create')  # Returns 'task_create'
    """
    return f"{entity.lower()}_{action.lower()}"


# Standard operation names for consistency
class OperationNames:
    """Standard operation names for token usage tracking"""

    # Task operations
    TASK_CREATE = "task_create"
    TASK_UPDATE = "task_update"
    TASK_DELETE = "task_delete"
    TASK_COMPLETE = "task_complete"
    TASK_LIST = "task_list"
    TASK_GET = "task_get"

    # Subtask operations
    SUBTASK_CREATE = "subtask_create"
    SUBTASK_UPDATE = "subtask_update"
    SUBTASK_DELETE = "subtask_delete"
    SUBTASK_COMPLETE = "subtask_complete"
    SUBTASK_LIST = "subtask_list"
    SUBTASK_GET = "subtask_get"

    # Project operations
    PROJECT_CREATE = "project_create"
    PROJECT_UPDATE = "project_update"
    PROJECT_DELETE = "project_delete"
    PROJECT_GET = "project_get"
    PROJECT_LIST = "project_list"

    # Branch operations
    BRANCH_CREATE = "branch_create"
    BRANCH_UPDATE = "branch_update"
    BRANCH_DELETE = "branch_delete"
    BRANCH_GET = "branch_get"
    BRANCH_LIST = "branch_list"

    # Agent operations
    AGENT_REGISTER = "agent_register"
    AGENT_UPDATE = "agent_update"
    AGENT_DELETE = "agent_delete"
    AGENT_ASSIGN = "agent_assign"
    AGENT_UNASSIGN = "agent_unassign"
    AGENT_CALL = "agent_call"

    # Context operations
    CONTEXT_CREATE = "context_create"
    CONTEXT_UPDATE = "context_update"
    CONTEXT_DELETE = "context_delete"
    CONTEXT_GET = "context_get"
