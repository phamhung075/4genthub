"""Delete Task Use Case"""

from typing import Union, Optional
import logging

from ...domain.repositories.task_repository import TaskRepository
from ...domain.value_objects.task_id import TaskId
from ...domain.events import TaskDeleted
from ...domain.interfaces.database_session import IDatabaseSessionFactory
from ...domain.interfaces.logging_service import ILoggingService


class DeleteTaskUseCase:
    """Use case for deleting a task"""
    
    def __init__(self, 
                 task_repository: TaskRepository,
                 db_session_factory: Optional[IDatabaseSessionFactory] = None,
                 logging_service: Optional[ILoggingService] = None):
        self._task_repository = task_repository
        self._db_session_factory = db_session_factory
        self._logger = logging.getLogger(__name__) if not logging_service else logging_service.get_logger(__name__)
    
    def execute(self, task_id: Union[str, int]) -> bool:
        """Execute the delete task use case"""
        # Convert to domain value object (handle both int and str)
        if isinstance(task_id, int):
            domain_task_id = TaskId.from_int(task_id)
        else:
            domain_task_id = TaskId.from_string(str(task_id))
        
        # Find the task
        task = self._task_repository.find_by_id(domain_task_id)
        if not task:
            return False
        
        # Mark task as deleted (triggers domain event)
        task.mark_as_deleted()
        
        # Get the git_branch_id before deleting
        git_branch_id = task.git_branch_id if hasattr(task, 'git_branch_id') else None
        
        # Delete from repository
        success = self._task_repository.delete(domain_task_id)
        
        if success:
            # Update branch task count using domain interface
            if git_branch_id:
                try:
                    with self._db_session_factory.create_session() as session:
                        # Query through domain interface (this would need a proper entity import)
                        # For now, we'll use a placeholder approach
                        # TODO: Implement proper branch repository pattern
                        self._logger.info(f"Task deleted, should update branch {git_branch_id} task count")
                except Exception as e:
                    self._logger.warning(f"Failed to update branch task count: {e}")
            
            # Handle domain events
            events = task.get_events()
            for event in events:
                if isinstance(event, TaskDeleted):
                    # Could trigger cleanup, notifications, etc.
                    pass
        
        return success 