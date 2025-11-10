"""Task Workflow Operations Handler"""

import logging
from datetime import UTC, datetime

# DTO imports for response standardization
from fastmcp.types import TaskResponse, task_to_dto

logger = logging.getLogger(__name__)


class TaskWorkflowHandler:
    """Handler for task workflow operations"""

    def __init__(self, facade_service):
        """
        Initialize handler with facade service.

        Args:
            facade_service: Service for obtaining application facades
        """
        self.facade_service = facade_service

    def complete_task(
        self,
        task_id: str,
        completion_summary: str,
        testing_notes: str | None,
        user_id: str,
        session,
    ) -> TaskResponse:
        """
        Complete a task.

        Args:
            task_id: Task identifier
            completion_summary: Summary of completion
            testing_notes: Optional testing notes
            user_id: Authenticated user ID
            session: Database session

        Returns:
            TaskResponse: Type-safe completion result
        """
        try:
            # Get task facade with proper user context through service
            task_facade = self.facade_service.get_task_facade(
                project_id="default_project", git_branch_id=None, user_id=user_id
            )

            # Delegate to facade
            result = task_facade.complete_task(
                task_id=task_id,
                completion_summary=completion_summary,
                testing_notes=testing_notes,
                user_id=user_id,
            )

            # Check if the completion was successful
            if result.get("success"):
                task = result.get("task")
                logger.info(f"Task {task_id} completed successfully by user {user_id}")

                return TaskResponse(
                    success=True,
                    task=task_to_dto(task) if isinstance(task, dict) else task,
                    message="Task completed successfully",
                    timestamp=datetime.now(UTC).isoformat(),
                )
            else:
                # Handle validation or other errors from facade
                error_msg = result.get("error", "Failed to complete task")
                logger.warning(
                    f"Task {task_id} completion failed for user {user_id}: {error_msg}"
                )
                return TaskResponse(
                    success=False,
                    task=None,
                    error=error_msg,
                    message=error_msg,
                    timestamp=datetime.now(UTC).isoformat(),
                )

        except Exception as e:
            logger.error(f"Error completing task {task_id} for user {user_id}: {e}")
            return TaskResponse(
                success=False,
                task=None,
                error=str(e),
                message="Failed to complete task",
                timestamp=datetime.now(UTC).isoformat(),
            )
