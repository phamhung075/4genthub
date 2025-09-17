"""Subtask Facade Factory

Application layer factory for creating subtask facades with proper dependency injection.

DDD COMPLIANCE: This factory uses RepositoryProviderService to obtain repositories,
maintaining proper layer separation by not importing from infrastructure.
"""

from ...application.facades.subtask_application_facade import SubtaskApplicationFacade
from ..services.repository_provider_service import RepositoryProviderService


class SubtaskFacadeFactory:
    """
    Factory for creating subtask application facades with proper DDD dependency injection.
    
    This factory encapsulates the creation logic for subtask facades, ensuring
    proper dependency injection and separation of concerns.
    
    Implements singleton pattern to avoid expensive repeated initialization.
    """
    
    # Class-level singleton instance
    _instance = None
    _initialized = False
    
    @classmethod
    def get_instance(cls):
        """
        Get the singleton instance of the factory.
        
        Uses RepositoryProviderService to obtain repositories following DDD principles.
            
        Returns:
            SubtaskFacadeFactory: The singleton instance
        """
        if cls._instance is None:
            # Use RepositoryProviderService - DDD compliant
            repository_provider = RepositoryProviderService.get_instance()
            cls._instance = cls(repository_provider)
        return cls._instance
    
    def __init__(self, repository_provider: RepositoryProviderService):
        """
        Initialize the subtask facade factory.
        
        Args:
            repository_provider: Service for providing repository instances
        """
        self._repository_provider = repository_provider
    
    def create_facade(self, project_id: str = None, git_branch_id: str = None, user_id: str = None, task_id: str = None) -> SubtaskApplicationFacade:
        """Alias for create_subtask_facade for consistency with other factories"""
        return self.create_subtask_facade(project_id, user_id, task_id)
    
    def create_subtask_facade(self, project_id: str = None, user_id: str = None, task_id: str = None) -> SubtaskApplicationFacade:
        """
        Create a subtask application facade with proper dependency injection.
        
        This method demonstrates how to properly construct application facades
        with all required dependencies using dependency injection.
        
        Args:
            project_id: Project identifier for repository creation (optional if task_id provided)
            user_id: User identifier for authentication and audit trails
            task_id: Task identifier for context derivation (will auto-derive project context)
            
        Returns:
            Configured subtask application facade
        """
        # CRITICAL FIX: Pass user_id to repository creation for proper authentication
        # Create repositories using provider service with user context
        task_repository = self._repository_provider.get_task_repository(
            project_id=project_id,
            user_id=user_id
        )
        subtask_repository = self._repository_provider.get_subtask_repository(
            project_id=project_id,
            user_id=user_id
        )
        
        # Create facade with repositories - proper DDD layering
        return SubtaskApplicationFacade(
            task_repository=task_repository,
            subtask_repository=subtask_repository,
            user_id=user_id
        )