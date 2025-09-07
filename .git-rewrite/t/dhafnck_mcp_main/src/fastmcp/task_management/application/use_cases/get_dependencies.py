"""Get Dependencies Use Case"""

from typing import Union, Any, Dict
from ...domain import TaskRepository, TaskId, TaskNotFoundError

class GetDependenciesUseCase:
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
        dependency_details = []
        for dep_id in task.get_dependency_ids():
            dep_task = self._task_repository.find_by_id(self._convert_to_task_id(str(dep_id)))
            if dep_task:
                dependency_details.append({
                    "id": str(dep_id),
                    "title": dep_task.title,
                    "status": str(dep_task.status),
                    "priority": str(dep_task.priority)
                })
        return {
            "task_id": str(task_id),
            "dependency_ids": task.get_dependency_ids(),
            "dependencies": dependency_details,
            "can_start": task.can_be_started()
        } 