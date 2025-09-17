"""Get Subtask Use Case"""

from typing import Union, Any, Dict, Optional
from ...domain import TaskRepository, TaskId, TaskNotFoundError
from ...domain.repositories.subtask_repository import SubtaskRepository

class GetSubtaskUseCase:
    def __init__(self, task_repository: TaskRepository, subtask_repository: SubtaskRepository = None):
        self._task_repository = task_repository
        self._subtask_repository = subtask_repository

    def execute(self, task_id: Union[str, int], id: Union[str, int]) -> Dict[str, Any]:
        task_id_obj = self._convert_to_task_id(task_id)
        task = self._task_repository.find_by_id(task_id_obj)
        if not task:
            raise TaskNotFoundError(f"Task {task_id} not found")
        
        # Use dedicated subtask repository if available
        if self._subtask_repository:
            subtask = self._subtask_repository.find_by_id(id)
            if not subtask:
                raise ValueError(f"Subtask {id} not found in task {task_id}")
            
            subtask_data = subtask.to_dict()
        else:
            # Fallback to existing task entity method for backward compatibility
            subtask_data = task.get_subtask(id)
            if not subtask_data:
                raise ValueError(f"Subtask {id} not found in task {task_id}")
        
        return {
            "task_id": str(task_id),
            "subtask": subtask_data,
            "progress": task.get_subtask_progress()
        }

    def _convert_to_task_id(self, task_id: Union[str, int]) -> TaskId:
        if isinstance(task_id, int):
            return TaskId.from_int(task_id)
        else:
            return TaskId.from_string(str(task_id)) 