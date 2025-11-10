"""Task Search and Statistics Handler"""

import logging
from datetime import UTC, datetime

# DTO imports for response standardization
from fastmcp.types import (
    CountResponse,
    StatisticsResponse,
    TaskResponse,
    TaskSummariesResponse,
    task_summary_to_dto,
    task_to_dto,
)

logger = logging.getLogger(__name__)


class TaskSearchHandler:
    """Handler for task search and statistics operations"""

    def __init__(self, facade_service):
        """
        Initialize handler with facade service.

        Args:
            facade_service: Service for obtaining application facades
        """
        self.facade_service = facade_service

    def get_task_statistics(self, user_id: str, session) -> StatisticsResponse:
        """
        Get task statistics for a user.

        Args:
            user_id: Authenticated user ID
            session: Database session

        Returns:
            StatisticsResponse with task statistics
        """
        try:
            # Get task facade with proper user context through service
            task_facade = self.facade_service.get_task_facade(
                project_id="default_project", git_branch_id=None, user_id=user_id
            )

            # Get statistics through facade
            result = task_facade.get_task_statistics(user_id)

            # Check if getting statistics was successful
            if isinstance(result, dict) and result.get("success"):
                logger.info(f"Retrieved task statistics for user {user_id}")
                return StatisticsResponse(
                    success=True,
                    statistics=result.get("statistics", result),
                    timestamp=datetime.now(UTC).isoformat(),
                )
            elif isinstance(result, dict) and not result.get("success"):
                # Handle errors from facade
                error_msg = result.get("error", "Failed to get task statistics")
                logger.warning(
                    f"Getting task statistics failed for user {user_id}: {error_msg}"
                )
                return StatisticsResponse(
                    success=False,
                    error=error_msg,
                    message=error_msg,
                    timestamp=datetime.now(UTC).isoformat(),
                )
            else:
                # Legacy format - return as-is for backward compatibility
                logger.info(f"Retrieved task statistics for user {user_id}")
                return StatisticsResponse(
                    success=True,
                    statistics=result,
                    timestamp=datetime.now(UTC).isoformat(),
                )

        except Exception as e:
            logger.error(f"Error getting task statistics for user {user_id}: {e}")
            return StatisticsResponse(
                success=False,
                error=str(e),
                message="Failed to get task statistics",
                timestamp=datetime.now(UTC).isoformat(),
            )

    def count_tasks(self, filters: dict, user_id: str, session) -> CountResponse:
        """
        Count tasks matching filters.

        Args:
            filters: Task filters
            user_id: Authenticated user ID
            session: Database session

        Returns:
            CountResponse with task count
        """
        try:
            # Get task facade through service
            task_facade = self.facade_service.get_task_facade(
                project_id="default_project", git_branch_id=None, user_id=user_id
            )

            # Add user_id to filters for security
            filters["user_id"] = user_id

            # Get count through facade
            result = task_facade.count_tasks(filters)

            # Check if counting was successful
            if isinstance(result, dict) and "success" in result:
                if result.get("success"):
                    count = result.get("count", 0)
                    logger.info(
                        f"Counted {count} tasks for user {user_id} with filters {filters}"
                    )
                    return CountResponse(
                        success=True,
                        count=count,
                        filters=filters,
                        timestamp=datetime.now(UTC).isoformat(),
                    )
                else:
                    # Handle errors from facade
                    error_msg = result.get("error", "Failed to count tasks")
                    logger.warning(
                        f"Counting tasks failed for user {user_id}: {error_msg}"
                    )
                    return CountResponse(
                        success=False,
                        error=error_msg,
                        message=error_msg,
                        timestamp=datetime.now(UTC).isoformat(),
                    )
            else:
                # Legacy format - result is just the count
                logger.info(
                    f"Counted {result} tasks for user {user_id} with filters {filters}"
                )
                return CountResponse(
                    success=True,
                    count=result,
                    filters=filters,
                    timestamp=datetime.now(UTC).isoformat(),
                )

        except Exception as e:
            logger.error(f"Error counting tasks for user {user_id}: {e}")
            return CountResponse(
                success=False,
                error=str(e),
                message="Failed to count tasks",
                timestamp=datetime.now(UTC).isoformat(),
            )

    def list_tasks_summary(
        self, filters: dict, offset: int, limit: int, user_id: str, session
    ) -> TaskSummariesResponse:
        """
        List task summaries with pagination.

        Args:
            filters: Task filters
            offset: Pagination offset
            limit: Pagination limit
            user_id: Authenticated user ID
            session: Database session

        Returns:
            TasksResponse with task summaries
        """
        try:
            # Get task facade through service
            task_facade = self.facade_service.get_task_facade(
                project_id="default_project", git_branch_id=None, user_id=user_id
            )

            # Add user_id to filters for security
            filters["user_id"] = user_id

            # Get tasks through facade
            result = task_facade.list_tasks_summary(filters, offset, limit)

            # Check if listing was successful
            if result.get("success"):
                tasks = result.get("tasks", [])
                total = result.get("total", 0)
                logger.info(f"📊 CONTROLLER: Listed {len(tasks)} task summaries for user {user_id}")

                # Log first task for debugging
                if tasks:
                    first_task = tasks[0]
                    logger.info(f"🔍 CONTROLLER: First task subtask_count = {first_task.get('subtask_count', 'MISSING')}")

                # Convert to DTOs
                dtos = [task_summary_to_dto(t) for t in tasks]
                logger.info(f"✅ CONTROLLER: Converted {len(dtos)} tasks to DTOs")
                if dtos:
                    logger.info(f"  - First DTO subtask_count: {dtos[0].subtask_count}")

                return TaskSummariesResponse(
                    success=True,
                    tasks=dtos,
                    total=total,
                    page=offset // limit if limit > 0 else 0,
                    limit=limit,
                    timestamp=datetime.now(UTC).isoformat(),
                )
            else:
                # Handle validation or other errors from facade
                error_msg = result.get("error", "Failed to list task summaries")
                logger.warning(
                    f"Task summary listing failed for user {user_id}: {error_msg}"
                )
                return TaskSummariesResponse(
                    success=False,
                    tasks=[],
                    error=error_msg,
                    message=error_msg,
                    timestamp=datetime.now(UTC).isoformat(),
                )

        except Exception as e:
            logger.error(f"Error listing task summaries for user {user_id}: {e}")
            return TaskSummariesResponse(
                success=False,
                tasks=[],
                error=str(e),
                message="Failed to list task summaries",
                timestamp=datetime.now(UTC).isoformat(),
            )

    def get_full_task(self, task_id: str, user_id: str, session) -> TaskResponse:
        """
        Get full task details including subtasks and dependencies.

        Args:
            task_id: Task identifier
            user_id: Authenticated user ID
            session: Database session

        Returns:
            TaskResponse with full task details
        """
        try:
            # Get task facade with proper user context through service
            task_facade = self.facade_service.get_task_facade(
                project_id="default_project", git_branch_id=None, user_id=user_id
            )

            # Get task with all relations through facade
            task = task_facade.get_task_with_relations(task_id)

            if not task:
                return TaskResponse(
                    success=False,
                    task=None,
                    error="Task not found",
                    message="Task not found or access denied",
                    timestamp=datetime.now(UTC).isoformat(),
                )

            logger.info(f"Retrieved full task details for task {task_id}")

            return TaskResponse(
                success=True,
                task=task_to_dto(task, include_subtasks=True),
                timestamp=datetime.now(UTC).isoformat(),
            )

        except Exception as e:
            logger.error(f"Error getting full task {task_id} for user {user_id}: {e}")
            return TaskResponse(
                success=False,
                task=None,
                error=str(e),
                message="Failed to get task details",
                timestamp=datetime.now(UTC).isoformat(),
            )
