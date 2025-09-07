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
        
        # Remove the subtask
        success = self._subtask_repository.remove_subtask(task_id, id)
        
        # Update parent task progress
        if success:
            self._update_parent_task_progress(str(task_id))
        
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
        
        return {
            "success": success,
            "subtask": {"id": str(id)},
            "progress": progress
        }

    def _convert_to_task_id(self, task_id: Union[str, int]) -> TaskId:
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