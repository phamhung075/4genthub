"""Project Service Factory

Factory for creating project management services with proper dependency injection following DDD patterns.
"""

from typing import Optional
from ..services.project_management_service import ProjectManagementService
from ..services.project_application_service import ProjectApplicationService
from ...infrastructure.utilities.path_resolver import PathResolver
from ...domain.repositories.project_repository import ProjectRepository
from ...infrastructure.repositories.project_repository_factory import (
    ProjectRepositoryFactory, 
    RepositoryConfig,
    get_default_repository,
    get_sqlite_repository
)


class ProjectServiceFactory:
    """Factory for creating project management services with proper DDD dependency injection"""
    
    def __init__(self, path_resolver: PathResolver, project_repository: Optional[ProjectRepository] = None):
        self._path_resolver = path_resolver
        self._project_repository = project_repository
    
    def create_project_service(self, projects_file_path: Optional[str] = None) -> ProjectManagementService:
        """Create a legacy project management service with proper dependencies (projects_file_path is ignored)"""
        repository = self._project_repository or self._get_default_repository()
        return ProjectManagementService(
            project_repo=repository
        )
    
    def create_project_application_service(self, user_id: Optional[str] = None) -> ProjectApplicationService:
        """Create a DDD-compliant project application service"""
        repository = self._project_repository or self._get_repository_for_user(user_id)
        return ProjectApplicationService(
            project_repository=repository
        )
    
    def _get_default_repository(self) -> ProjectRepository:
        """Get default project repository"""
        if self._project_repository:
            return self._project_repository
        return get_default_repository()
    
    def _get_repository_for_user(self, user_id: str) -> ProjectRepository:
        """Get repository for specific user"""
        if self._project_repository:
            return self._project_repository
        return ProjectRepositoryFactory.create(user_id=user_id)
    
    def create_sqlite_service(self, user_id: Optional[str] = None, db_path: Optional[str] = None) -> ProjectApplicationService:
        """Create service with SQLite repository (legacy support)"""
        repository = get_sqlite_repository(user_id=user_id, db_path=db_path)
        return ProjectApplicationService(project_repository=repository)
    
    def create_service_from_config(self, config: RepositoryConfig) -> ProjectApplicationService:
        """Create service from repository configuration"""
        repository = config.create_repository()
        return ProjectApplicationService(project_repository=repository)
    
    def create_service_from_environment(self, user_id: Optional[str] = None) -> ProjectApplicationService:
        """Create service using environment configuration"""
        config = RepositoryConfig.from_environment()
        config.user_id = user_id
        return self.create_service_from_config(config)
    
    def set_project_repository(self, repository: ProjectRepository) -> None:
        """Set the project repository for dependency injection"""
        self._project_repository = repository
    
    def get_project_repository(self) -> Optional[ProjectRepository]:
        """Get the current project repository"""
        return self._project_repository


# Convenience factory functions

def create_project_service_factory(
    path_resolver: Optional[PathResolver] = None,
    project_repository: Optional[ProjectRepository] = None
) -> ProjectServiceFactory:
    """Create a project service factory with optional dependencies"""
    if not path_resolver:
        path_resolver = PathResolver()
    
    return ProjectServiceFactory(
        path_resolver=path_resolver,
        project_repository=project_repository
    )


def create_default_project_service() -> ProjectApplicationService:
    """Create a project service with default configuration"""
    factory = create_project_service_factory()
    return factory.create_project_application_service()


def create_project_service_for_user(user_id: str) -> ProjectApplicationService:
    """Create a project service for specific user"""
    factory = create_project_service_factory()
    return factory.create_project_application_service(user_id=user_id)


def create_sqlite_project_service(
    user_id: Optional[str] = None, 
    db_path: Optional[str] = None
) -> ProjectApplicationService:
    """Create a project service with SQLite repository (legacy support)"""
    factory = create_project_service_factory()
    return factory.create_sqlite_service(user_id=user_id, db_path=db_path)


# Export factory and convenience functions
__all__ = [
    "ProjectServiceFactory",
    "create_project_service_factory",
    "create_default_project_service",
    "create_project_service_for_user",
    "create_sqlite_project_service"
]
