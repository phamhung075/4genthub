"""Task Progress Service

Handles automatic progress calculation and updates for tasks based on subtask completion.
"""

import logging
from typing import Optional, Any
from ...domain.repositories.task_repository import TaskRepository
from ...domain.repositories.subtask_repository import SubtaskRepository
from ...domain.value_objects.task_id import TaskId

logger = logging.getLogger(__name__)


class TaskProgressService:
    """Service for managing task progress based on subtask completion."""
    
    def __init__(self, task_repository: TaskRepository, subtask_repository: SubtaskRepository, user_id: Optional[str] = None):
        """Initialize with repositories."""
        self._task_repository = task_repository
        self._subtask_repository = subtask_repository
        self._user_id = user_id  # Store user context

    def _get_user_scoped_repository(self, repository: Any) -> Any:
        """Get a user-scoped version of the repository if it supports user context."""
        if not repository:
            return repository
        if hasattr(repository, 'with_user') and self._user_id:
            return repository.with_user(self._user_id)
        elif hasattr(repository, 'user_id'):
            if self._user_id and repository.user_id != self._user_id:
                repo_class = type(repository)
                if hasattr(repository, 'session'):
                    return repo_class(repository.session, user_id=self._user_id)
        return repository

    def with_user(self, user_id: str) -> 'TaskProgressService':
        """Create a new service instance scoped to a specific user."""
        return TaskProgressService(self._task_repository, self._subtask_repository, user_id)
    
    def update_task_progress_from_subtasks(self, task_id: str) -> Optional[float]:
        """
        Calculate and update task progress based on subtask completion.
        
        Args:
            task_id: The parent task ID
            
        Returns:
            The calculated progress percentage (0-100) or None if task not found
        """
        try:
            # Get the task using user-scoped repository
            domain_task_id = TaskId(task_id)
            task_repo = self._get_user_scoped_repository(self._task_repository)
            task = task_repo.find_by_id(domain_task_id)
            
            if not task:
                logger.warning(f"Task {task_id} not found for progress update")
                return None
            
            # Get all subtasks for this task using user-scoped repository
            subtask_repo = self._get_user_scoped_repository(self._subtask_repository)
            subtasks = subtask_repo.find_by_parent_task_id(domain_task_id)
            
            if not subtasks:
                # No subtasks, progress remains at current value or 0
                logger.debug(f"Task {task_id} has no subtasks, keeping progress at current value")
                return getattr(task, 'progress_percentage', 0)
            
            # Calculate progress based on subtask completion
            total_subtasks = len(subtasks)
            completed_subtasks = 0
            total_progress = 0
            
            logger.debug(f"Processing {total_subtasks} subtasks for task {task_id}")
            
            for subtask in subtasks:
                # Check if subtask is completed (status == 'done')
                if hasattr(subtask, 'status') and str(subtask.status) == 'done':
                    completed_subtasks += 1
                    total_progress += 100
                elif hasattr(subtask, 'progress_percentage'):
                    # Use subtask's progress percentage if available
                    progress_value = subtask.progress_percentage
                    total_progress += progress_value
                elif hasattr(subtask, 'status') and str(subtask.status) == 'in_progress':
                    # If in progress but no percentage, assume 50%
                    total_progress += 50
                # else: todo or blocked subtasks contribute 0%
            
            # Calculate average progress
            progress_percentage = total_progress / total_subtasks if total_subtasks > 0 else 0
            progress_percentage = round(progress_percentage)  # Round to nearest integer
            
            # Update the task progress in the database
            # We need to update the task through the repository or directly via SQLAlchemy
            from ...infrastructure.database.database_config import get_session
            from ...infrastructure.database.models import Task as TaskModel
            
            with get_session() as session:
                task_model = session.get(TaskModel, task_id)
                if task_model:
                    task_model.progress_percentage = progress_percentage
                    session.commit()
                    logger.info(f"Updated task {task_id} progress to {progress_percentage}%")
                else:
                    logger.error(f"Task model {task_id} not found in database")
            
            return progress_percentage
            
        except Exception as e:
            logger.error(f"Error updating task progress: {e}")
            return None
    
    def get_task_progress(self, task_id: str) -> Optional[float]:
        """
        Get the current progress percentage for a task.
        
        Args:
            task_id: The task ID
            
        Returns:
            The progress percentage (0-100) or None if task not found
        """
        try:
            # Get the task from database
            from ...infrastructure.database.database_config import get_session
            from ...infrastructure.database.models import Task as TaskModel
            
            with get_session() as session:
                task_model = session.get(TaskModel, task_id)
                if task_model and hasattr(task_model, 'progress_percentage'):
                    return task_model.progress_percentage
                else:
                    return 0
        except Exception as e:
            logger.error(f"Error getting task progress: {e}")
            return None