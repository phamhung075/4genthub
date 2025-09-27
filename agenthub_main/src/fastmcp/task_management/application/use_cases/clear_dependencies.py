"""Clear Dependencies Use Case"""

from typing import Union
from ...application.dtos.dependency import DependencyResponse

from ...domain import TaskRepository, TaskId, TaskNotFoundError

class ClearDependenciesUseCase:
    def __init__(self, task_repository: TaskRepository):
        self._task_repository = task_repository

    def _convert_to_task_id(self, task_id: Union[str, int]) -> TaskId:
        if isinstance(task_id, int):
            return TaskId.from_int(task_id)
        else:
            return TaskId.from_string(str(task_id))

    def execute(self, task_id: Union[str, int]) -> DependencyResponse:
        task_id_obj = self._convert_to_task_id(task_id)
        task = self._task_repository.find_by_id(task_id_obj)
        if not task:
            raise TaskNotFoundError(f"Task {task_id} not found")
        dependency_count = len(task.dependencies)
        task.clear_dependencies()
        self._task_repository.save(task)
        return DependencyResponse(
            task_id=str(task_id),
            dependencies=[],
            success=True,
            message=f"Cleared {dependency_count} dependencies"
        ) 