"""Task Facade Factory

Application layer factory for creating task facades with proper dependency injection.

CRITICAL CHANGE: This factory now requires proper user authentication.
The default_id fallback has been removed to enforce security requirements.

DDD COMPLIANCE: This factory uses RepositoryProviderService to obtain repositories,
maintaining proper layer separation by not importing from infrastructure.
"""

from ..services.repository_provider_service import RepositoryProviderService
from .unified_context_facade_factory import UnifiedContextFacadeFactory as ContextServiceFactory


class TaskFacadeFactory:
    """
    Factory for creating task application facades with proper DDD dependency injection.
    
    This factory encapsulates the creation logic for task facades, ensuring
    proper dependency injection and separation of concerns.
    
    Implements singleton pattern to avoid expensive repeated initialization.
    """
    
    # Class-level singleton instance
    _instance = None
    _initialized = False
    
    def __new__(cls, *args, **kwargs):
        """Implement singleton pattern"""
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance
    
    @classmethod
    def get_instance(cls):
        """
        Get the singleton instance of the factory.
        
        This is the preferred way to get the factory instance.
        Uses RepositoryProviderService to obtain repositories following DDD principles.
            
        Returns:
            TaskFacadeFactory: The singleton instance
        """
        if cls._instance is None:
            # Use RepositoryProviderService - DDD compliant
            repository_provider = RepositoryProviderService.get_instance()
            cls._instance = cls(repository_provider)
        return cls._instance
    
    def __init__(self, repository_provider: RepositoryProviderService):
        """
        Initialize the task facade factory.
        
        Args:
            repository_provider: Service for providing repository instances
        """
        # Skip initialization if already done (singleton pattern)
        if self._initialized:
            return
            
        self._repository_provider = repository_provider
        
        # Try to initialize context service factory, but handle database unavailability
        try:
            # Use singleton instance of ContextServiceFactory
            self._context_service_factory = ContextServiceFactory.get_instance()
        except Exception as e:
            import logging
            logger = logging.getLogger(__name__)
            logger.warning(f"Could not initialize ContextServiceFactory: {e}")
            logger.warning("Context operations will not be available")
            self._context_service_factory = None
        
        # Mark as initialized for singleton pattern
        TaskFacadeFactory._initialized = True
    
    from typing import TYPE_CHECKING, Any
    if TYPE_CHECKING:
        from ...application.facades.task_application_facade import TaskApplicationFacade as _TaskApplicationFacade

    def create_task_facade(self, project_id: str = None, git_branch_id: str = None, user_id: str = None) -> object:
        """
        Create a task application facade with proper dependency injection.
        
        This method demonstrates how to properly construct application facades
        with all required dependencies using dependency injection.
        
        Args:
            project_id: Project identifier for repository creation (optional for task-only operations)
            git_branch_id: Git branch UUID (if None, will use default branch)
            user_id: User identifier
            
        Returns:
            Configured task application facade
        """
        # Import validation and auth config
        from ...domain.constants import validate_user_id
        from ...domain.exceptions.authentication_exceptions import UserAuthenticationRequiredError
        from ....config.auth_config import AuthConfig
        
        # Validate user authentication (MVP mode will provide default if needed)
        user_id = validate_user_id(user_id, "Task facade creation")
        
        # If project_id is None, create a system-level repository for task operations
        if project_id is None:
            # Use a special system-level repository that can operate across projects
            # This is needed for task GET operations where we only have task_id
            # Use repository provider service - proper DDD layering
            # Repository is obtained through the provider service
            task_repository = self._repository_provider.get_task_repository(
                project_id=None,
                git_branch_name=None,
                user_id=user_id
            )
        else:
            # Create task repository for facade construction
            # Repository provider handles the details
            task_repository = self._repository_provider.get_task_repository(
                project_id=project_id,
                git_branch_name=None,
                user_id=user_id
            )
        
        # Create subtask repository using provider
        # CRITICAL FIX: Always create subtask repository regardless of project_id
        # Subtasks can be retrieved by parent task ID without project context
        subtask_repository = self._repository_provider.get_subtask_repository(
            project_id=project_id,  # Can be None, repository will handle it
            git_branch_name=None,
            user_id=user_id
        )
        
        # Create context service for context integration if available
        context_service = None
        if self._context_service_factory:
            context_service = self._context_service_factory.create_facade(
                user_id=user_id,
                project_id=project_id,
                git_branch_id=git_branch_id
            )
        
        # Create git branch repository for the facade to use in context derivation
        git_branch_repository = self._repository_provider.get_git_branch_repository(user_id=user_id)
        
        # Create and return facade with all repositories and services
        # The facade will create its own use cases internally
        from ...application.facades.task_application_facade import TaskApplicationFacade
        return TaskApplicationFacade(task_repository, subtask_repository, context_service, git_branch_repository)

    def create_task_facade_with_git_branch_id(self, project_id: str, git_branch_name: str, user_id: str, git_branch_id: str) -> object:
        """
        Create a task application facade with a specific git_branch_id.
        
        This method creates a facade where the task repository is initialized with
        the git_branch_id directly, bypassing the need for context resolution.
        
        Args:
            project_id: Project identifier for repository creation
            git_branch_name: Task tree identifier
            user_id: User identifier
            git_branch_id: Specific git branch ID to use
            
        Returns:
            Configured task application facade
        """
        # Import validation and auth config
        from ...domain.constants import validate_user_id
        from ...domain.exceptions.authentication_exceptions import UserAuthenticationRequiredError
        from ....config.auth_config import AuthConfig
        
        # Validate user authentication (MVP mode will provide default if needed)
        user_id = validate_user_id(user_id, "Task facade with git_branch_id creation")
        
        # Create task repository using provider
        task_repository = self._repository_provider.get_task_repository(
            project_id=project_id,
            git_branch_name=git_branch_name,
            user_id=user_id
        )
        
        # Create subtask repository using provider
        subtask_repository = None
        if project_id:
            # Only create subtask repository when we have a project_id
            subtask_repository = self._repository_provider.get_subtask_repository(
                project_id=project_id,
                git_branch_name=None,
                user_id=user_id
            )
        
        # Create context service for context integration if available
        context_service = None
        if self._context_service_factory:
            context_service = self._context_service_factory.create_facade(
                user_id=user_id,
                project_id=project_id,
                git_branch_id=git_branch_id
            )
        
        # Create git branch repository for the facade to use in context derivation
        git_branch_repository = self._repository_provider.get_git_branch_repository(user_id=user_id)
        
        # Create and return facade with all repositories and services
        from ...application.facades.task_application_facade import TaskApplicationFacade
        return TaskApplicationFacade(task_repository, subtask_repository, context_service, git_branch_repository)