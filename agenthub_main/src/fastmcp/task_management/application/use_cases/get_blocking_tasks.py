"""Get Blocking Tasks Use Case"""

from typing import Union, Any, Dict
from ...domain import TaskRepository, TaskId, TaskNotFoundError

class GetBlockingTasksUseCase:
    def __init__(self, task_repository: TaskRepository):
        self._task_repository = task_repository

    def _convert_to_task_id(self, task_id: Union[str, int]) -> TaskId:
        if isinstance(task_id, int):
            return TaskId.from_int(task_id)
        else:
            return TaskId.from_string(str(task_id))

    def execute(self, task_id: Union[str, int]) -> Dict[str, Any]:
        task_id_obj = self._convert_to_task_id(task_id)
        task = self._task_repository.find_by_id(task_id_obj)
        if not task:
            raise TaskNotFoundError(f"Task {task_id} not found")
        all_tasks = self._task_repository.find_all()
        blocking_tasks = []
        for other_task in all_tasks:
            if other_task.has_dependency(task_id_obj):
                blocking_tasks.append({
                    "id": str(other_task.id),
                    "title": other_task.title,
                    "status": str(other_task.status),
                    "priority": str(other_task.priority)
                })
        return {
            "task_id": str(task_id),
            "blocking_tasks": blocking_tasks,
            "blocking_count": len(blocking_tasks)
        } 