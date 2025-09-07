"""Delete Task Use Case"""

from typing import Union

from ...domain.repositories.task_repository import TaskRepository
from ...domain.value_objects.task_id import TaskId
from ...domain.events import TaskDeleted


class DeleteTaskUseCase:
    """Use case for deleting a task"""
    
    def __init__(self, task_repository: TaskRepository):
        self._task_repository = task_repository
    
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
            # Update branch task count
            if git_branch_id:
                try:
                    from ...infrastructure.database.database_config import get_db_session
                    from ...infrastructure.database.models import ProjectGitBranch
                    import logging
                    logger = logging.getLogger(__name__)
                    
                    with get_db_session() as session:
                        branch = session.query(ProjectGitBranch).filter(
                            ProjectGitBranch.id == git_branch_id
                        ).first()
                        if branch and branch.task_count > 0:
                            branch.task_count = branch.task_count - 1
                            session.commit()
                            logger.info(f"Updated task_count to {branch.task_count} for branch {git_branch_id}")
                except Exception as e:
                    import logging
                    logging.getLogger(__name__).warning(f"Failed to update branch task count: {e}")
            
            # Handle domain events
            events = task.get_events()
            for event in events:
                if isinstance(event, TaskDeleted):
                    # Could trigger cleanup, notifications, etc.
                    pass
        
        return success 