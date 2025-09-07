"""Add Subtask Use Case"""

from typing import Union
from ...application.dtos.subtask.add_subtask_request import AddSubtaskRequest
from ...application.dtos.subtask.subtask_response import SubtaskResponse

from ...domain import TaskRepository, TaskId, TaskNotFoundError
from ...domain.repositories.subtask_repository import SubtaskRepository
from ...domain.entities.subtask import Subtask
from ...domain.value_objects.priority import Priority
import logging

class AddSubtaskUseCase:
    def __init__(self, task_repository: TaskRepository, subtask_repository: SubtaskRepository = None):
        self._task_repository = task_repository
        self._subtask_repository = subtask_repository

    def execute(self, request: AddSubtaskRequest) -> SubtaskResponse:
        logging.debug(f"[AddSubtask] Request received - priority: {request.priority}")
        task_id = self._convert_to_task_id(request.task_id)
        task = self._task_repository.find_by_id(task_id)
        if not task:
            raise TaskNotFoundError(f"Task {request.task_id} not found")
        
        # Create subtask using the new domain entity
        if self._subtask_repository:
            # Use dedicated subtask repository if available
            logging.debug("[AddSubtask] Using subtask repository path")
            subtask_id = self._subtask_repository.get_next_id(task_id)
            
            # Convert string priority to Priority value object
            priority = None
            if request.priority:
                priority = Priority.from_string(request.priority)
                logging.debug(f"[AddSubtask] Creating subtask with priority: {request.priority} -> {priority}")
            
            subtask = Subtask.create(
                id=subtask_id,
                title=request.title,
                description=request.description,
                parent_task_id=task_id,
                assignees=request.assignees,
                priority=priority
            )
            self._subtask_repository.save(subtask)
            added_subtask = subtask.to_dict()
            
            # Update parent task progress
            self._update_parent_task_progress(str(task_id))
        else:
            # Fallback to existing task entity method for backward compatibility
            logging.debug("[AddSubtask] Using legacy task entity path")
            subtask = {
                "title": request.title,
                "description": request.description,
                "completed": False,
                "assignees": request.assignees
            }
            added_subtask = task.add_subtask(subtask)
            self._task_repository.save(task)
        
        logging.debug(f"[AddSubtask] Creating subtask for task_id={task_id} (following clean relationship chain)")
        
        # Handle potential async/sync method issue
        try:
            progress = task.get_subtask_progress()
            # Check if it's a coroutine (async method result)
            if hasattr(progress, '__await__'):
                # If it's a coroutine, we can't await it in sync context
                # Fall back to a basic progress calculation
                logging.warning("[AddSubtask] get_subtask_progress returned coroutine, using fallback")
                progress = {"total": len(task.subtasks) if task.subtasks else 0, "completed": 0, "percentage": 0}
        except Exception as e:
            logging.error(f"[AddSubtask] Error getting subtask progress: {e}, using fallback")
            progress = {"total": len(task.subtasks) if task.subtasks else 0, "completed": 0, "percentage": 0}
        
        return SubtaskResponse(
            task_id=str(request.task_id),
            subtask=added_subtask,
            progress=progress
        )

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
            logging.warning(f"Failed to update parent task progress: {e}") 