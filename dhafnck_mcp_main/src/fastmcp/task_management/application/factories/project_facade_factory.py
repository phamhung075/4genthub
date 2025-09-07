"""Project Facade Factory

Factory for creating project application facades with proper dependency injection following DDD patterns.

CRITICAL CHANGE: This factory now requires proper user authentication.
The default_id parameter has been removed to enforce security requirements.
"""

import logging
from typing import Optional, Dict
from ...domain.constants import validate_user_id
from ...domain.exceptions.authentication_exceptions import UserAuthenticationRequiredError
from ...application.facades.project_application_facade import ProjectApplicationFacade
from ...application.services.project_management_service import ProjectManagementService
from ...infrastructure.repositories.project_repository_factory import (
    ProjectRepositoryFactory, 
    GlobalRepositoryManager
)
from ..services.repository_provider_service import RepositoryProviderService

logger = logging.getLogger(__name__)


class ProjectFacadeFactory:
    """
    Factory for creating project application facades with proper DDD dependency injection.
    
    This factory ensures proper layering and dependency direction:
    - Creates facades with injected services
    - Services are created with injected repositories
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
        Uses RepositoryProviderService to obtain repositories following DDD principles.
            
        Returns:
            ProjectFacadeFactory: The singleton instance
        """
        if cls._instance is None:
            # Use RepositoryProviderService - DDD compliant
            repository_provider = RepositoryProviderService.get_instance()
            cls._instance = cls(repository_provider)
        return cls._instance
    
    def __init__(self, repository_provider: Optional[RepositoryProviderService] = None):
        """
        Initialize the project facade factory.
        
        Args:
            repository_provider: Service for providing repository instances
        """
        # Skip initialization if already done (singleton pattern)
        if self._initialized:
            return
            
        self._repository_provider = repository_provider
        self._facades_cache: Dict[str, ProjectApplicationFacade] = {}
        self._initialized = True
        logger.info("ProjectFacadeFactory initialized")
    
    def create_project_facade(self, 
                            user_id: str) -> ProjectApplicationFacade:
        """
        Create a project application facade with proper dependency injection.
        
        Args:
            user_id: User identifier (required - authentication is mandatory)
            
        Returns:
            ProjectApplicationFacade instance with injected dependencies
            
        Raises:
            UserAuthenticationRequiredError: If user_id is not provided or invalid
        """
        # Validate user authentication is provided
        user_id = validate_user_id(user_id, "Project facade creation")
        # Create cache key after validation
        cache_key = f"{user_id}"
        
        # Check cache first
        if cache_key in self._facades_cache:
            logger.debug(f"Returning cached project facade for {cache_key}")
            return self._facades_cache[cache_key]
        
        # Create repository using repository provider (DDD compliant)
        if not self._repository_provider:
            raise ValueError("Repository provider is required for project facade creation")
        
        project_repository = self._repository_provider.get_project_repository(user_id)
        
        # Create service with repository
        project_service = ProjectManagementService(project_repo=project_repository)
        
        # Create facade with service
        facade = ProjectApplicationFacade(project_service=project_service)
        
        # Cache the facade
        self._facades_cache[cache_key] = facade
        
        logger.info(f"Created new project facade for {cache_key}")
        return facade
    
    def clear_cache(self):
        """Clear the facades cache."""
        self._facades_cache.clear()
        logger.info("Project facades cache cleared")
    
    def get_cached_facade(self, user_id: str) -> Optional[ProjectApplicationFacade]:
        """
        Get a cached facade if available.
        
        Args:
            user_id: User identifier (required)
            
        Returns:
            Cached facade or None
            
        Raises:
            UserAuthenticationRequiredError: If user_id is not provided or invalid
        """
        # Validate user authentication is provided
        user_id = validate_user_id(user_id, "Get cached facade")
        cache_key = f"{user_id}"
        return self._facades_cache.get(cache_key)