"""Task CRUD Operations Handler"""

import logging
from datetime import UTC, datetime

# No direct factory imports - handlers receive facades from controller
# DTO imports for response standardization
from fastmcp.types import (
    DeleteResponse,
    TaskResponse,
    TasksResponse,
    task_to_dto,
)

from .....application.dtos.task.create_task_request import CreateTaskRequest
from .....application.dtos.task.list_tasks_request import ListTasksRequest
from .....application.dtos.task.update_task_request import UpdateTaskRequest

logger = logging.getLogger(__name__)


class TaskCrudHandler:
    """Handler for task CRUD operations"""

    def __init__(self, facade_service):
        """
        Initialize handler with facade service.

        Args:
            facade_service: Service for obtaining application facades
        """
        self.facade_service = facade_service

    def create_task(
        self, request: CreateTaskRequest, user_id: str, session
    ) -> TaskResponse:
        """
        Create a new task.

        Args:
            request: Task creation request data
            user_id: Authenticated user ID
            session: Database session

        Returns:
            TaskResponse: Type-safe task creation result
        """
        try:
            # Get task facade with proper user context through service
            # Project ID should come from git_branch_id context or be None
            task_facade = self.facade_service.get_task_facade(
                project_id=None,  # Derived from git_branch_id context
                git_branch_id=request.git_branch_id,
                user_id=user_id,
            )

            # Delegate to facade
            result = task_facade.create_task(request)

            # Check if the creation was successful
            if result.get("success"):
                task = result.get("task")
                logger.info(
                    f"Task created successfully for user {user_id}: {task.get('id') if isinstance(task, dict) else task.id}"
                )

                return TaskResponse(
                    success=True,
                    task=task_to_dto(task) if isinstance(task, dict) else task,
                    message="Task created successfully",
                    timestamp=datetime.now(UTC).isoformat(),
                )
            else:
                # Handle validation or other errors from facade
                error_msg = result.get("error", "Failed to create task")
                logger.warning(f"Task creation failed for user {user_id}: {error_msg}")
                return TaskResponse(
                    success=False,
                    task=None,
                    error=error_msg,
                    message=error_msg,
                    timestamp=datetime.now(UTC).isoformat(),
                )

        except Exception as e:
            logger.error(f"Error creating task for user {user_id}: {e}")
            return TaskResponse(
                success=False,
                task=None,
                error=str(e),
                message="Failed to create task",
                timestamp=datetime.now(UTC).isoformat(),
            )

    def get_task(self, task_id: str, user_id: str, session) -> TaskResponse:
        """
        Get a specific task.

        Args:
            task_id: Task identifier
            user_id: Authenticated user ID
            session: Database session

        Returns:
            TaskResponse with task details
        """
        try:
            # Get task facade with proper user context through service
            # Project ID derived from task context, not hardcoded
            task_facade = self.facade_service.get_task_facade(
                project_id=None,  # Derived from task context
                git_branch_id=None,  # Will be determined by task
                user_id=user_id,
            )

            # Delegate to facade - returns {"success": bool, "action": str, "task": dict}
            result = task_facade.get_task(task_id)

            # Check if the facade call was successful
            if not result.get("success"):
                error_msg = result.get("error", "Task not found")
                return TaskResponse(
                    success=False,
                    task=None,
                    error=error_msg,
                    message=error_msg,
                    timestamp=datetime.now(UTC).isoformat(),
                )

            # Extract the actual task data from the result
            task = result.get("task")
            if not task:
                return TaskResponse(
                    success=False,
                    task=None,
                    error="Task not found",
                    message="Task not found or access denied",
                    timestamp=datetime.now(UTC).isoformat(),
                )

            logger.info(f"Retrieved task {task_id} for user {user_id}")

            return TaskResponse(
                success=True,
                task=task_to_dto(task, include_subtasks=False),
                timestamp=datetime.now(UTC).isoformat(),
            )

        except Exception as e:
            logger.error(f"Error getting task {task_id} for user {user_id}: {e}")
            return TaskResponse(
                success=False,
                task=None,
                error=str(e),
                message="Failed to get task",
                timestamp=datetime.now(UTC).isoformat(),
            )

    def update_task(
        self, task_id: str, request: UpdateTaskRequest, user_id: str, session
    ) -> TaskResponse:
        """
        Update a task.

        Args:
            task_id: Task identifier
            request: Task update request
            user_id: Authenticated user ID
            session: Database session

        Returns:
            TaskResponse: Type-safe updated task details
        """
        try:
            # Get task facade with proper user context through service
            # Project ID derived from task context, not hardcoded
            task_facade = self.facade_service.get_task_facade(
                project_id=None,  # Derived from task context
                git_branch_id=None,
                user_id=user_id,
            )

            # Set task_id in request
            request.task_id = task_id

            # Delegate to facade - pass request (task_id is already in request)
            result = task_facade.update_task(request)

            # Check if the update was successful
            if result.get("success"):
                task = result.get("task")
                logger.info(f"Task {task_id} updated successfully for user {user_id}")

                return TaskResponse(
                    success=True,
                    task=task_to_dto(task) if isinstance(task, dict) else task,
                    message="Task updated successfully",
                    timestamp=datetime.now(UTC).isoformat(),
                )
            else:
                # Handle validation or other errors from facade
                error_msg = result.get("error", "Failed to update task")
                logger.warning(
                    f"Task {task_id} update failed for user {user_id}: {error_msg}"
                )
                return TaskResponse(
                    success=False,
                    task=None,
                    error=error_msg,
                    message=error_msg,
                    timestamp=datetime.now(UTC).isoformat(),
                )

        except Exception as e:
            logger.error(f"Error updating task {task_id} for user {user_id}: {e}")
            return TaskResponse(
                success=False,
                task=None,
                error=str(e),
                message="Failed to update task",
                timestamp=datetime.now(UTC).isoformat(),
            )

    def delete_task(self, task_id: str, user_id: str, session) -> DeleteResponse:
        """
        Delete a task.

        Args:
            task_id: Task identifier
            user_id: Authenticated user ID
            session: Database session

        Returns:
            DeleteResponse: Type-safe deletion result
        """
        try:
            # Get task facade with proper user context through service
            # Project ID derived from task context, not hardcoded
            task_facade = self.facade_service.get_task_facade(
                project_id=None,  # Derived from task context
                git_branch_id=None,
                user_id=user_id,
            )

            # Delegate to facade with user_id for proper WebSocket notification
            result = task_facade.delete_task(task_id, user_id)

            # Check if the deletion was successful
            if result.get("success"):
                logger.info(f"Task {task_id} deleted successfully for user {user_id}")
                return DeleteResponse(
                    success=True,
                    deleted=True,
                    id=task_id,
                    message="Task deleted successfully",
                    timestamp=datetime.now(UTC).isoformat(),
                )
            else:
                # Handle validation or other errors from facade
                error_msg = result.get("error", "Failed to delete task")
                logger.warning(
                    f"Task {task_id} deletion failed for user {user_id}: {error_msg}"
                )
                return DeleteResponse(
                    success=False,
                    deleted=False,
                    error=error_msg,
                    message=error_msg,
                    timestamp=datetime.now(UTC).isoformat(),
                )

        except Exception as e:
            logger.error(f"Error deleting task {task_id} for user {user_id}: {e}")
            return DeleteResponse(
                success=False,
                deleted=False,
                error=str(e),
                message="Failed to delete task",
                timestamp=datetime.now(UTC).isoformat(),
            )

    def list_tasks(
        self, request: ListTasksRequest, user_id: str, session
    ) -> TasksResponse:
        """
        List tasks for a user.

        Args:
            request: Task listing request
            user_id: Authenticated user ID
            session: Database session

        Returns:
            TasksResponse with list of tasks
        """
        try:
            # Get task facade with proper user context through service
            # Project ID should be derived from git_branch_id context, not hardcoded
            task_facade = self.facade_service.get_task_facade(
                project_id=None,  # Derived from git_branch_id context
                git_branch_id=request.git_branch_id,
                user_id=user_id,
            )

            # Delegate to facade - include dependencies for proper display
            result = task_facade.list_tasks(
                request, include_dependencies=True, minimal=False
            )

            # Check if the listing was successful
            if result.get("success"):
                tasks = result.get("tasks", [])
                logger.info(f"Listed {len(tasks)} tasks for user {user_id}")

                return TasksResponse(
                    success=True,
                    tasks=[task_to_dto(t, include_subtasks=False) for t in tasks],
                    total=len(tasks),
                    timestamp=datetime.now(UTC).isoformat(),
                )
            else:
                # Handle validation or other errors from facade
                error_msg = result.get("error", "Failed to list tasks")
                logger.warning(f"Task listing failed for user {user_id}: {error_msg}")
                return TasksResponse(
                    success=False,
                    tasks=[],
                    error=error_msg,
                    message=error_msg,
                    timestamp=datetime.now(UTC).isoformat(),
                )

        except Exception as e:
            logger.error(f"Error listing tasks for user {user_id}: {e}", exc_info=True)
            return TasksResponse(
                success=False,
                tasks=[],
                error=str(e),
                message="Failed to list tasks",
                timestamp=datetime.now(UTC).isoformat(),
            )
