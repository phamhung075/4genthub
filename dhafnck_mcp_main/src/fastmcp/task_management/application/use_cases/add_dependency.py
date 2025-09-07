"""Add Dependency Use Case"""

from typing import Union, Optional
import logging
from ...application.dtos.dependency import (
    AddDependencyRequest,
    DependencyResponse
)

from ...domain import TaskRepository, TaskId, TaskNotFoundError
from ...domain.entities.task import Task

logger = logging.getLogger(__name__)

class AddDependencyUseCase:
    def __init__(self, task_repository: TaskRepository):
        self._task_repository = task_repository

    def _convert_to_task_id(self, task_id: Union[str, int]) -> TaskId:
        if isinstance(task_id, int):
            return TaskId.from_int(task_id)
        else:
            return TaskId.from_string(str(task_id))

    def _find_dependency_task(self, dependency_id: TaskId) -> Optional[Task]:
        """
        Enhanced dependency lookup that searches across all task states.
        
        Args:
            dependency_id: The ID of the dependency task to find
            
        Returns:
            Task if found in any state, None if not found anywhere
        """
        logger.debug(f"Searching for dependency task {dependency_id} across all states")
        
        # First try the new find_by_id_all_states method that searches all states
        if hasattr(self._task_repository, 'find_by_id_all_states'):
            logger.debug(f"Using find_by_id_all_states for {dependency_id}")
            dependency_task = self._task_repository.find_by_id_all_states(dependency_id)
            if dependency_task:
                logger.debug(f"Found dependency task {dependency_id} with status {dependency_task.status}")
                return dependency_task
        
        # Fallback to the standard find_by_id (for backward compatibility)
        dependency_task = self._task_repository.find_by_id(dependency_id)
        
        if dependency_task:
            logger.debug(f"Found dependency task {dependency_id} with status {dependency_task.status}")
            return dependency_task
            
        # If we have an across_contexts method, try it
        if hasattr(self._task_repository, 'find_by_id_across_contexts'):
            logger.debug(f"Trying find_by_id_across_contexts for {dependency_id}")
            dependency_task = self._task_repository.find_by_id_across_contexts(dependency_id)
            if dependency_task:
                logger.debug(f"Found dependency task {dependency_id} across contexts")
                return dependency_task
        
        logger.warning(f"Dependency task {dependency_id} not found in any context or state")
        return None

    def execute(self, request: AddDependencyRequest) -> DependencyResponse:
        task_id = self._convert_to_task_id(request.task_id)
        dependency_id = self._convert_to_task_id(request.depends_on_task_id)
        task = self._task_repository.find_by_id(task_id)
        if not task:
            raise TaskNotFoundError(f"Task {request.task_id} not found")
        # Enhanced dependency lookup: check multiple sources
        dependency_task = self._find_dependency_task(dependency_id)
        if not dependency_task:
            raise TaskNotFoundError(f"Dependency task {request.depends_on_task_id} not found in active, completed, or archived tasks")
        if task.has_dependency(dependency_id):
            return DependencyResponse(
                success=False,
                message=f"Dependency {request.depends_on_task_id} already exists",
                task_id=str(request.task_id),
                depends_on_task_id=str(request.depends_on_task_id)
            )
        if task.has_circular_dependency(dependency_id):
            return DependencyResponse(
                success=False,
                message="Cannot add dependency: would create circular reference",
                task_id=str(request.task_id),
                depends_on_task_id=str(request.depends_on_task_id)
            )
        
        # Add dependency with enhanced status information
        task.add_dependency(dependency_id)
        self._task_repository.save(task)
        
        # Generate informative success message based on dependency status
        dependency_status = dependency_task.status.value if hasattr(dependency_task.status, 'value') else str(dependency_task.status)
        status_info = ""
        
        if dependency_task.status.is_done():
            status_info = " (dependency is completed - task can proceed immediately)"
        elif dependency_status in ['todo', 'in_progress']:
            status_info = f" (dependency is {dependency_status} - task will wait for completion)"
        elif dependency_status == 'blocked':
            status_info = " (warning: dependency is currently blocked)"
        elif dependency_status == 'cancelled':
            status_info = " (warning: dependency was cancelled - please review)"
        
        return DependencyResponse(
            success=True,
            message=f"Dependency {request.depends_on_task_id} added successfully{status_info}",
            task_id=str(request.task_id),
            depends_on_task_id=str(request.depends_on_task_id),
            dependency_type=getattr(request, 'dependency_type', 'blocks')
        ) 