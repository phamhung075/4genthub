"""Complete Subtask Use Case"""

from typing import Union, Any, Dict
from ...domain import TaskRepository, TaskId, TaskNotFoundError
from ...domain.repositories.subtask_repository import SubtaskRepository

class CompleteSubtaskUseCase:
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
            
            subtask.complete()
            self._subtask_repository.save(subtask)
            success = True
        else:
            # Fallback to existing task entity method for backward compatibility
            success = task.complete_subtask(id)
            if success:
                self._task_repository.save(task)
        
        # Calculate parent progress after subtask completion
        parent_progress = task.get_subtask_progress()
        
        # Trigger parent task progress update
        try:
            self._update_parent_task_progress(task, parent_progress)
        except Exception as e:
            import logging
            logging.warning(f"Failed to update parent task progress: {e}")
        
        return {
            "success": success,
            "task_id": str(task_id),
            "subtask_id": str(id),
            "progress": parent_progress,
            "parent_progress": parent_progress  # Include explicit parent progress
        }

    def _update_parent_task_progress(self, task, progress: float) -> None:
        """Update parent task with aggregated progress from subtasks."""
        try:
            # Update the task's overall progress if it has subtasks
            if hasattr(task, 'subtasks') and task.subtasks:
                # Set overall progress based on subtask completion
                task.update_overall_progress(progress)
                
                # Save the updated task
                self._task_repository.save(task)
                
                import logging
                logging.info(f"Updated parent task {task.id} progress to {progress}%")
        except Exception as e:
            import logging
            logging.error(f"Failed to update parent task progress: {e}")
    
    def _convert_to_task_id(self, task_id: Union[str, int]) -> TaskId:
        if isinstance(task_id, int):
            return TaskId.from_int(task_id)
        else:
            return TaskId.from_string(str(task_id)) 