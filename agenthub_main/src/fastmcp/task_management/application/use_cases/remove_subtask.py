"""Remove Subtask Use Case"""

from __future__ import annotations

from typing import Any

from ...domain import TaskId, TaskRepository
from ...domain.repositories.subtask_repository import SubtaskRepository


class RemoveSubtaskUseCase:
    def __init__(self, task_repository: TaskRepository, subtask_repository: SubtaskRepository = None):
        self._task_repository = task_repository
        self._subtask_repository = subtask_repository

    def execute(self, task_id: str | int, id: str | int, user_id: str = None) -> dict[str, Any]:
        subtask = self._subtask_repository.find_by_id(id)
        if not subtask:
            raise ValueError(f"Subtask {id} not found in task {task_id}")

        # Get branch ID, status, and title before deletion for event and WebSocket payload
        parent_task_obj = self._task_repository.find_by_id(self._convert_to_task_id(task_id))
        branch_id = parent_task_obj.git_branch_id if parent_task_obj and hasattr(parent_task_obj, 'git_branch_id') else None
        subtask_status = 'done' if subtask.is_completed else 'todo'
        is_subtask_completed = subtask.is_completed
        subtask_title = subtask.title  # ✅ FIX: Capture title before deletion for WebSocket payload

        # Remove the subtask
        success = self._subtask_repository.remove_subtask(task_id, id)

        # Update parent task progress and subtask_count
        if success:
            # Remove subtask ID from parent task's subtasks list and decrement count
            # This calls the domain method which does both operations atomically
            parent_task_obj.remove_subtask(str(id))

            # If the deleted subtask was completed, decrement the completed counter
            if is_subtask_completed:
                parent_task_obj.decrement_completed_subtasks()

            self._task_repository.save(parent_task_obj)
            import logging
            logging.info(f"Removed subtask {id} from parent task {task_id}, subtask_count now {parent_task_obj.subtask_count}")

            self._update_parent_task_progress(str(task_id))

            # NOTE: WebSocket notification is sent by the facade layer (subtask_application_facade.py)
            # to maintain consistency with task deletion pattern

            # Dispatch domain event for subtask deletion
            # This will trigger branch statistics update
            try:
                from ...domain.events.task_lifecycle_events import TaskDeletedEvent
                from ...domain.services.event_dispatcher import dispatch_domain_event

                if branch_id:
                    event = TaskDeletedEvent.create(
                        task_id=str(id),
                        branch_id=branch_id,
                        status=subtask_status,
                        title=subtask.title
                    )

                    dispatch_domain_event("task_deleted", event)
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
        from dataclasses import asdict, dataclass

        @dataclass
        class RemoveSubtaskResponse:
            success: bool
            subtask: dict
            progress: dict

        response = RemoveSubtaskResponse(
            success=success,
            subtask={"id": str(id), "title": subtask_title},  # ✅ FIX: Include title for WebSocket notification
            progress=progress
        )
        return asdict(response)

    def _convert_to_task_id(self, task_id: str | int) -> TaskId:
        if isinstance(task_id, int):
            return TaskId.from_int(task_id)
        else:
            return TaskId.from_string(str(task_id))

    def _update_parent_task_progress(self, task_id: str) -> None:
        """Update parent task progress based on subtask completion."""
        try:
            from ..services.task_progress_service import TaskProgressService
            progress_service = TaskProgressService(self._task_repository, self._subtask_repository)
            progress_service.update_task_progress_from_subtasks(task_id)
        except Exception as e:
            import logging
            logging.warning(f"Failed to update parent task progress: {e}") 