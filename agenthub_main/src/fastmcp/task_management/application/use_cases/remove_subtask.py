"""Remove Subtask Use Case"""

from typing import Union, Any, Dict
from ...domain import TaskRepository, TaskId, TaskNotFoundError
from ...domain.repositories.subtask_repository import SubtaskRepository

class RemoveSubtaskUseCase:
    def __init__(self, task_repository: TaskRepository, subtask_repository: SubtaskRepository = None):
        self._task_repository = task_repository
        self._subtask_repository = subtask_repository

    def execute(self, task_id: Union[str, int], id: Union[str, int]) -> Dict[str, Any]:
        subtask = self._subtask_repository.find_by_id(id)
        if not subtask:
            raise ValueError(f"Subtask {id} not found in task {task_id}")

        # Get branch ID and status before deletion for event
        parent_task_obj = self._task_repository.find_by_id(self._convert_to_task_id(task_id))
        branch_id = parent_task_obj.git_branch_id if parent_task_obj and hasattr(parent_task_obj, 'git_branch_id') else None
        subtask_status = 'done' if subtask.is_completed else 'todo'

        # Remove the subtask
        success = self._subtask_repository.remove_subtask(task_id, id)

        # Update parent task progress and subtask_count
        if success:
            self._decrement_parent_subtask_count(str(task_id))
            self._update_parent_task_progress(str(task_id))

            # Dispatch domain event for subtask deletion
            # This will trigger branch statistics update
            try:
                from ...domain.services.event_dispatcher import dispatch_domain_event
                from ...domain.events.task_lifecycle_events import TaskDeletedEvent

                if branch_id:
                    event = TaskDeletedEvent.create(
                        task_id=str(id),
                        branch_id=branch_id,
                        status=subtask_status,
                        title=subtask.title
                    )

                    dispatch_domain_event("task_deleted", event)
                    import logging
                    logging.info(f"Dispatched task_deleted event for subtask {id}")
            except Exception as e:
                import logging
                logging.warning(f"Failed to dispatch subtask deletion event: {e}")
        
        # Calculate progress after deletion
        progress = {}
        if success and self._subtask_repository:
            try:
                task_id_obj = self._convert_to_task_id(task_id)
                progress = self._subtask_repository.get_subtask_progress(task_id_obj)
            except Exception:
                # If progress calculation fails, provide fallback
                progress = {
                    "total_subtasks": 0,
                    "completed_subtasks": 0,
                    "completion_percentage": 0
                }
        
        # Use dataclass for clean response structure
        from dataclasses import dataclass, asdict

        @dataclass
        class RemoveSubtaskResponse:
            success: bool
            subtask: dict
            progress: dict

        response = RemoveSubtaskResponse(
            success=success,
            subtask={"id": str(id)},
            progress=progress
        )
        return asdict(response)

    def _convert_to_task_id(self, task_id: Union[str, int]) -> TaskId:
        if isinstance(task_id, int):
            return TaskId.from_int(task_id)
        else:
            return TaskId.from_string(str(task_id))

    def _decrement_parent_subtask_count(self, task_id: str) -> None:
        """Decrement the parent task's subtask_count by 1."""
        try:
            task_id_obj = self._convert_to_task_id(task_id)
            task = self._task_repository.find_by_id(task_id_obj)
            if task:
                # The ORM model has subtask_count column - update it directly
                from ...infrastructure.database.models import Task as TaskModel
                from ...infrastructure.database.session_manager import SessionManager
                import logging

                session = SessionManager.get_session()
                task_orm = session.query(TaskModel).filter(TaskModel.id == str(task_id)).first()
                if task_orm and task_orm.subtask_count > 0:
                    task_orm.subtask_count = task_orm.subtask_count - 1
                    session.commit()
                    logging.info(f"Decremented subtask_count for task {task_id} to {task_orm.subtask_count}")
        except Exception as e:
            import logging
            logging.warning(f"Failed to decrement parent subtask_count: {e}")

    def _update_parent_task_progress(self, task_id: str) -> None:
        """Update parent task progress based on subtask completion."""
        try:
            from ..services.task_progress_service import TaskProgressService
            progress_service = TaskProgressService(self._task_repository, self._subtask_repository)
            progress_service.update_task_progress_from_subtasks(task_id)
        except Exception as e:
            import logging
            logging.warning(f"Failed to update parent task progress: {e}") 