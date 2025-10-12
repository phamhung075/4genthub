"""Delete Task Use Case"""

from typing import Union, Optional, Dict, Any
import logging
import asyncio

from ...domain.repositories.task_repository import TaskRepository
from ...domain.repositories.subtask_repository import SubtaskRepository
from ...domain.value_objects.task_id import TaskId
from ...domain.events import TaskDeleted
from ...domain.interfaces.database_session import IDatabaseSessionFactory
from ...domain.interfaces.logging_service import ILoggingService
from ...domain.services.cascade_deletion_service import CascadeDeletionService, DeleteScope


class DeleteTaskUseCase:
    """Use case for deleting a task with cascade deletion"""

    def __init__(self,
                 task_repository: TaskRepository,
                 subtask_repository: Optional[SubtaskRepository] = None,
                 branch_repository=None,
                 project_repository=None,
                 context_repository=None,
                 db_session_factory: Optional[IDatabaseSessionFactory] = None,
                 logging_service: Optional[ILoggingService] = None):
        self._task_repository = task_repository
        self._subtask_repository = subtask_repository
        self._branch_repository = branch_repository
        self._project_repository = project_repository
        self._context_repository = context_repository
        self._db_session_factory = db_session_factory
        self._logger = logging.getLogger(__name__) if not logging_service else logging_service.get_logger(__name__)

        # Initialize cascade deletion service
        self._cascade_service = CascadeDeletionService(
            task_repository=task_repository,
            subtask_repository=subtask_repository,
            branch_repository=branch_repository,
            project_repository=project_repository,
            context_repository=context_repository
        )

    def execute(self, task_id: Union[str, int], cascade: bool = True, user_id: str = None) -> Dict[str, Any]:
        """
        Execute the delete task use case with cascade deletion.

        Args:
            task_id: ID of the task to delete
            cascade: Whether to cascade delete subtasks and contexts
            user_id: User performing the deletion (for WebSocket notifications)

        Returns:
            Dictionary with deletion statistics and success status
        """
        # Convert to string for cascade service
        task_id_str = str(task_id)

        # Convert to domain value object for checking
        if isinstance(task_id, int):
            domain_task_id = TaskId.from_int(task_id)
        else:
            domain_task_id = TaskId.from_string(str(task_id))

        # Find the task to get info for WebSocket notification
        task = self._task_repository.find_by_id(domain_task_id)
        if not task:
            return {
                "success": False,
                "task_deleted": False,
                "message": f"Task {task_id} not found"
            }

        # Store task info for WebSocket notification
        git_branch_id = task.git_branch_id if hasattr(task, 'git_branch_id') else None
        task_title = task.title

        # Use cascade deletion service
        scope = DeleteScope.TASK_FULL if cascade else DeleteScope.TASK_ONLY
        stats = self._cascade_service.delete_task_cascade(task_id_str, scope)

        # NOTE: WebSocket notification is sent by the facade layer (task_application_facade.py)
        # to use pre-fetched context and avoid querying deleted tasks
        # Dispatch TaskDeletedEvent to update branch task counts
        if stats["task_deleted"]:
            try:
                from ...domain.services.event_dispatcher import dispatch_domain_event
                from ...domain.events.task_lifecycle_events import TaskDeletedEvent

                if git_branch_id:
                    event = TaskDeletedEvent.create(
                        task_id=task_id_str,
                        branch_id=git_branch_id,
                        status="deleted",
                        metadata={
                            "title": task_title,
                            "cascade_stats": stats
                        }
                    )
                    dispatch_domain_event(event)
                    self._logger.info(f"Dispatched TaskDeletedEvent for task {task_id_str}")
            except Exception as e:
                self._logger.warning(f"Failed to dispatch TaskDeletedEvent: {e}")

            self._logger.info(
                f"Successfully deleted task {task_id} with cascade: "
                f"{stats['subtasks_deleted']} subtasks, "
                f"{stats['contexts_deleted']} contexts"
            )

        return {
            "success": stats["task_deleted"],
            **stats
        } 