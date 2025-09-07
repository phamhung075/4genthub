"""Subtask Facade Factory

Application layer factory for creating subtask facades with proper dependency injection.
"""

from ..facades.subtask_application_facade import SubtaskApplicationFacade
from ...infrastructure.repositories.subtask_repository_factory import SubtaskRepositoryFactory
from ...infrastructure.repositories.task_repository_factory import TaskRepositoryFactory


class SubtaskFacadeFactory:
    """
    Factory for creating subtask application facades with proper DDD dependency injection.
    
    This factory encapsulates the creation logic for subtask facades, ensuring
    proper dependency injection and separation of concerns.
    """
    
    def __init__(self, subtask_repository_factory: SubtaskRepositoryFactory, task_repository_factory: TaskRepositoryFactory = None):
        """
        Initialize the subtask facade factory.
        
        Args:
            subtask_repository_factory: Factory for creating subtask repositories
            task_repository_factory: Factory for creating task repositories
        """
        self._subtask_repository_factory = subtask_repository_factory
        self._task_repository_factory = task_repository_factory
    
    def create_subtask_facade(self, project_id: str = "default_project", user_id: str = None) -> SubtaskApplicationFacade:
        """
        Create a subtask application facade with proper dependency injection.
        
        This method demonstrates how to properly construct application facades
        with all required dependencies using dependency injection.
        
        Args:
            project_id: Project identifier for repository creation
            user_id: User identifier for authentication and audit trails
            
        Returns:
            Configured subtask application facade
        """
        # Create facade with factory-based approach for dynamic repository creation
        return SubtaskApplicationFacade(
            task_repository_factory=self._task_repository_factory,
            subtask_repository_factory=self._subtask_repository_factory
        )