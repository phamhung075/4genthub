"""Git Branch Facade Factory

Factory for creating git branch application facades with proper dependency injection following DDD patterns.
"""

import logging
from typing import Optional, Dict
from ...application.facades.git_branch_application_facade import GitBranchApplicationFacade
from ...domain.repositories.git_branch_repository import GitBranchRepository
from ...infrastructure.repositories.git_branch_repository_factory import GitBranchRepositoryFactory

logger = logging.getLogger(__name__)


class GitBranchFacadeFactory:
    """
    Factory for creating git branch application facades with proper DDD dependency injection.
    
    This factory ensures proper layering and dependency direction:
    - Creates facades with injected repositories
    - Repositories handle data persistence
    
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
        
        Returns:
            GitBranchFacadeFactory: The singleton instance
        """
        if cls._instance is None:
            cls._instance = cls()
        return cls._instance
    
    def __init__(self, git_branch_repository_factory: Optional[GitBranchRepositoryFactory] = None):
        """
        Initialize the git branch facade factory.
        
        Args:
            git_branch_repository_factory: Optional factory for creating git branch repositories
        """
        # Skip initialization if already done (singleton pattern)
        if self._initialized:
            return
            
        self._git_branch_repository_factory = git_branch_repository_factory
        self._facades_cache: Dict[str, GitBranchApplicationFacade] = {}
        
        # Mark as initialized for singleton pattern
        GitBranchFacadeFactory._initialized = True
        logger.info("GitBranchFacadeFactory initialized")
    
    def create_facade(self, 
                     project_id: Optional[str] = None,
                     user_id: Optional[str] = None) -> GitBranchApplicationFacade:
        """
        Create a git branch application facade with proper dependency injection.
        
        This method follows the naming convention used by other facade factories.
        
        Args:
            project_id: Optional project identifier for scoping
            user_id: Optional user identifier for authentication
            
        Returns:
            GitBranchApplicationFacade instance with injected dependencies
        """
        # Require project_id for DDD compliance
        if project_id is None:
            raise ValueError("project_id is required for git branch facade creation (no fallback allowed for DDD compliance)")
            
        return self.create_git_branch_facade(project_id=project_id, user_id=user_id)
    
    def create_git_branch_facade(self, 
                                project_id: str = None,
                                user_id: Optional[str] = None) -> GitBranchApplicationFacade:
        """
        Create a git branch application facade with proper dependency injection.
        
        Args:
            project_id: Project identifier for scoping
            user_id: User identifier for authentication
            
        Returns:
            GitBranchApplicationFacade instance with injected dependencies
        """
        # Create cache key including user_id for proper isolation
        cache_key = f"{project_id}:{user_id or 'no_user'}"
        
        # Check cache first
        if cache_key in self._facades_cache:
            logger.debug(f"Returning cached git branch facade for {cache_key}")
            return self._facades_cache[cache_key]
        
        # Create repositories using RepositoryProviderService for DDD compliance
        from ..services.repository_provider_service import RepositoryProviderService
        repo_provider = RepositoryProviderService.get_instance()
        
        # Get project repository with user context
        project_repo = repo_provider.get_project_repository(user_id=user_id)
        if user_id and hasattr(project_repo, 'with_user'):
            project_repo = project_repo.with_user(user_id)
        
        # Get git branch repository with user context  
        git_branch_repo = repo_provider.get_git_branch_repository(user_id=user_id)
        if user_id and hasattr(git_branch_repo, 'with_user'):
            git_branch_repo = git_branch_repo.with_user(user_id)
        
        # Create GitBranchService with repositories
        from ...application.services.git_branch_service import GitBranchService
        git_branch_service = GitBranchService(
            project_repo=project_repo,
            git_branch_repo=git_branch_repo,
            user_id=user_id
        )
        
        # Create facade with service, project_repo, project_id and user_id
        facade = GitBranchApplicationFacade(
            git_branch_service=git_branch_service,
            project_repo=project_repo,
            project_id=project_id,
            user_id=user_id
        )
        
        # Cache the facade
        self._facades_cache[cache_key] = facade
        
        logger.info(f"Created new git branch facade for {cache_key}")
        return facade
    
    def get_branch_facade(self, 
                         project_id: str,
                         user_id: Optional[str] = None) -> GitBranchApplicationFacade:
        """
        Get a git branch application facade (alias for create_facade).
        
        This method provides the interface expected by controllers and services.
        
        Args:
            project_id: Project identifier for scoping
            user_id: User identifier for authentication
            
        Returns:
            GitBranchApplicationFacade instance
        """
        return self.create_facade(project_id=project_id, user_id=user_id)
    
    def clear_cache(self):
        """Clear the facades cache."""
        self._facades_cache.clear()
        logger.info("Git branch facades cache cleared")
    
    def get_cached_facade(self, project_id: str, user_id: Optional[str] = None) -> Optional[GitBranchApplicationFacade]:
        """
        Get a cached facade if available.
        
        Args:
            project_id: Project identifier
            user_id: User identifier for authentication
            
        Returns:
            Cached facade or None
        """
        cache_key = f"{project_id}:{user_id or 'no_user'}"
        return self._facades_cache.get(cache_key)