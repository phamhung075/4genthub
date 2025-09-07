"""Git Branch Facade Factory

Factory for creating git branch application facades with proper dependency injection following DDD patterns.
"""

import logging
from typing import Optional, Dict
from ..facades.git_branch_application_facade import GitBranchApplicationFacade
from ...domain.repositories.git_branch_repository import GitBranchRepository
from ...infrastructure.repositories.git_branch_repository_factory import GitBranchRepositoryFactory

logger = logging.getLogger(__name__)


class GitBranchFacadeFactory:
    """
    Factory for creating git branch application facades with proper DDD dependency injection.
    
    This factory ensures proper layering and dependency direction:
    - Creates facades with injected repositories
    - Repositories handle data persistence
    """
    
    def __init__(self, git_branch_repository_factory: Optional[GitBranchRepositoryFactory] = None):
        """
        Initialize the git branch facade factory.
        
        Args:
            git_branch_repository_factory: Optional factory for creating git branch repositories
        """
        self._git_branch_repository_factory = git_branch_repository_factory
        self._facades_cache: Dict[str, GitBranchApplicationFacade] = {}
        logger.info("GitBranchFacadeFactory initialized")
    
    def create_git_branch_facade(self, 
                                project_id: str = "default_project",
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
        
        # Create GitBranchService with user context
        from ..services.git_branch_service import GitBranchService
        git_branch_service = GitBranchService(user_id=user_id)
        
        # Create facade with service, project_id and user_id
        facade = GitBranchApplicationFacade(
            git_branch_service=git_branch_service, 
            project_id=project_id,
            user_id=user_id
        )
        
        # Cache the facade
        self._facades_cache[cache_key] = facade
        
        logger.info(f"Created new git branch facade for {cache_key}")
        return facade
    
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