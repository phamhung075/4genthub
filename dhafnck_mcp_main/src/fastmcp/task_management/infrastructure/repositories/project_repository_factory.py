"""Project Repository Factory - Clean DDD Implementation"""

import os
import logging
from typing import Optional, Dict, Any, Type
from enum import Enum

from ...domain.repositories.project_repository import ProjectRepository
from .orm.project_repository import ORMProjectRepository
from .mock_repository_factory import MockProjectRepository

logger = logging.getLogger(__name__)


class RepositoryType(Enum):
    """Available repository implementation types"""
    ORM = "orm"
    IN_MEMORY = "in_memory"
    MOCK = "mock"


class ProjectRepositoryFactory:
    """Factory for creating project repository instances following DDD principles"""
    
    _instances: Dict[str, ProjectRepository] = {}
    _repository_types: Dict[RepositoryType, Type[ProjectRepository]] = {
        RepositoryType.ORM: ORMProjectRepository,
        RepositoryType.MOCK: MockProjectRepository,
    }
    
    @classmethod
    def create(
        cls,
        repository_type: Optional[RepositoryType] = None,
        user_id: Optional[str] = None,
        db_path: Optional[str] = None,
        **kwargs
    ) -> ProjectRepository:
        """
        Create a project repository instance
        
        Args:
            repository_type: Type of repository to create
            user_id: User identifier for multi-user support
            db_path: Database path for SQLite repositories
            **kwargs: Additional repository-specific parameters
            
        Returns:
            ProjectRepository instance
        """
        # Validate user authentication
        from ...domain.constants import validate_user_id
        from ...domain.exceptions.authentication_exceptions import UserAuthenticationRequiredError
        from ....config.auth_config import AuthConfig
        
        logger.info(f"🔍 Project Repository Factory: Creating repository with user_id: {user_id}")
        logger.info(f"🔧 Repository type: {repository_type}, db_path: {db_path}")
        print(f"DEBUG: ProjectRepositoryFactory.create called with user_id={user_id}")
        
        if user_id is None:
            logger.error(f"❌ Project Repository Factory: No user_id provided - authentication is required")
            raise UserAuthenticationRequiredError("Project repository creation")
        else:
            logger.info(f"✅ Project Repository Factory: Using provided user_id: {user_id}")
            user_id = validate_user_id(user_id, "Project repository creation")
        
        # Use default repository type if not specified
        if repository_type is None:
            repository_type = cls._get_default_type()
        
        # Generate cache key
        cache_key = cls._generate_cache_key(repository_type, user_id, db_path)
        
        # Return cached instance if available
        if cache_key in cls._instances:
            logger.debug(f"Returning cached repository: {cache_key}")
            return cls._instances[cache_key]
        
        # Create new instance
        try:
            repository = cls._create_instance(repository_type, user_id, db_path, **kwargs)
        except Exception as e:
            logger.warning(f"Failed to create {repository_type} repository, falling back to mock: {e}")
            # Fallback to mock repository
            repository_type = RepositoryType.MOCK
            cache_key = cls._generate_cache_key(repository_type, user_id, db_path)
            if cache_key in cls._instances:
                return cls._instances[cache_key]
            repository = cls._create_instance(repository_type, user_id, db_path, **kwargs)
        
        # Cache the instance
        cls._instances[cache_key] = repository
        
        logger.info(f"Created repository: {repository_type.value} for user: {user_id}")
        return repository
    
    @classmethod
    def _get_default_type(cls) -> RepositoryType:
        """Get default repository type from environment"""
        # Check environment variables properly
        env = os.getenv('ENVIRONMENT', 'production')
        db_type = os.getenv('DATABASE_TYPE', 'supabase')
        
        logger.debug(f"[ProjectRepositoryFactory] Environment: {env}, Database Type: {db_type}")
        
        # Test environment - use mock
        if env == 'test':
            logger.info("[ProjectRepositoryFactory] Test environment detected, using MOCK")
            return RepositoryType.MOCK
        
        # Production/development - use ORM
        # Try to verify database is available
        try:
            from ..database.database_config import get_db_config
            db_config = get_db_config()
            if db_config and db_config.engine:
                logger.info("[ProjectRepositoryFactory] Database available, using ORM")
                return RepositoryType.ORM
        except Exception as e:
            logger.warning(f"Database not available, falling back to mock: {e}")
        
        return RepositoryType.MOCK
    
    @classmethod
    def _generate_cache_key(
        cls, 
        repository_type: RepositoryType, 
        user_id: str, 
        db_path: Optional[str]
    ) -> str:
        """Generate cache key for repository instance"""
        type_value = repository_type.value if hasattr(repository_type, 'value') else str(repository_type)
        return f"{type_value}:{user_id}:{db_path if db_path else 'memory'}"
    
    @classmethod
    def _create_instance(
        cls,
        repository_type: RepositoryType,
        user_id: str,
        db_path: Optional[str],
        **kwargs
    ) -> ProjectRepository:
        """Create repository instance of specified type"""
        
        if repository_type not in cls._repository_types:
            type_value = repository_type.value if hasattr(repository_type, 'value') else str(repository_type)
            raise ValueError(f"Unsupported repository type: {type_value}")
        
        repository_class = cls._repository_types[repository_type]
        
        try:
            if repository_type == RepositoryType.ORM:
                # For ORM repositories, we need to handle db_path differently
                # since it affects the global database configuration
                if db_path:
                    # TODO: Implement per-repository database configuration
                    # For now, set environment variable to ensure correct database is used
                    import os
                    old_db_path = os.environ.get('MCP_DB_PATH')
                    os.environ['MCP_DB_PATH'] = db_path
                    try:
                        # Clear the global database config to use new path
                        from ..database.database_config import close_db
                        close_db()
                        return repository_class(user_id=user_id, **kwargs)
                    finally:
                        # Restore original environment
                        if old_db_path:
                            os.environ['MCP_DB_PATH'] = old_db_path
                        else:
                            os.environ.pop('MCP_DB_PATH', None)
                else:
                    return repository_class(user_id=user_id, **kwargs)
            elif repository_type == RepositoryType.MOCK:
                # Mock repositories don't need any parameters
                return repository_class()
            else:
                return repository_class(user_id=user_id, **kwargs)
                
        except Exception as e:
            logger.error(f"Failed to create {repository_type.value} repository: {e}")
            # Fallback to Mock if ORM fails
            if repository_type == RepositoryType.ORM:
                logger.info("Falling back to Mock repository")
                return MockProjectRepository()
            raise
    
    # Method removed - no longer needed since ORM is always available
    
    @classmethod
    def register_type(
        cls,
        repository_type: RepositoryType,
        repository_class: Type[ProjectRepository]
    ) -> None:
        """Register a new repository type"""
        cls._repository_types[repository_type] = repository_class
        logger.info(f"Registered repository type: {repository_type.value}")
    
    @classmethod
    def clear_cache(cls) -> None:
        """Clear all cached instances"""
        cls._instances.clear()
        logger.info("Repository cache cleared")
    
    @classmethod
    def get_info(cls) -> Dict[str, Any]:
        """Get factory information"""
        return {
            "available_types": [rt.value for rt in cls._repository_types.keys()],
            "cached_instances": len(cls._instances),
            "default_type": cls._get_default_type().value,
            "environment": {
                "MCP_PROJECT_REPOSITORY_TYPE": os.getenv("MCP_PROJECT_REPOSITORY_TYPE"),
                "MCP_DB_PATH": os.getenv("MCP_DB_PATH")
            }
        }


class RepositoryConfig:
    """Configuration for repository creation"""
    
    def __init__(
        self,
        repository_type: Optional[str] = None,
        user_id: Optional[str] = None,
        db_path: Optional[str] = None,
        **kwargs
    ):
        self.repository_type = self._validate_type(repository_type)
        self.user_id = user_id
        self.db_path = db_path
        self.kwargs = kwargs
    
    def _validate_type(self, repository_type: Optional[str]) -> RepositoryType:
        """Validate and convert repository type"""
        if repository_type is None:
            return RepositoryType.ORM
        
        try:
            return RepositoryType(repository_type.lower())
        except ValueError:
            logger.warning(f"Invalid repository type '{repository_type}', using ORM")
            return RepositoryType.ORM
    
    def create_repository(self) -> ProjectRepository:
        """Create repository from this configuration"""
        return ProjectRepositoryFactory.create(
            repository_type=self.repository_type,
            user_id=self.user_id,
            db_path=self.db_path,
            **self.kwargs
        )
    
    @classmethod
    def from_environment(cls) -> 'RepositoryConfig':
        """Create configuration from environment variables"""
        return cls(
            repository_type=os.getenv("MCP_PROJECT_REPOSITORY_TYPE"),
            user_id=os.getenv("MCP_USER_ID"),  # No default - authentication required
            db_path=os.getenv("MCP_DB_PATH")
        )


class GlobalRepositoryManager:
    """Global repository instance manager"""
    
    _default_repository: Optional[ProjectRepository] = None
    _user_repositories: Dict[str, ProjectRepository] = {}
    
    @classmethod
    def get_default(cls) -> ProjectRepository:
        """Get default global repository"""
        if cls._default_repository is None:
            # Use compatibility mode authentication for default repository
            cls._default_repository = ProjectRepositoryFactory.create(user_id=None)
        return cls._default_repository
    
    @classmethod
    def get_for_user(cls, user_id: str) -> ProjectRepository:
        """Get repository for specific user"""
        if user_id not in cls._user_repositories:
            cls._user_repositories[user_id] = ProjectRepositoryFactory.create(user_id=user_id)
        return cls._user_repositories[user_id]
    
    @classmethod
    def clear_all(cls) -> None:
        """Clear all managed repositories"""
        cls._default_repository = None
        cls._user_repositories.clear()
        ProjectRepositoryFactory.clear_cache()
    
    @classmethod
    def get_status(cls) -> Dict[str, Any]:
        """Get manager status"""
        return {
            "has_default": cls._default_repository is not None,
            "user_count": len(cls._user_repositories),
            "factory_info": ProjectRepositoryFactory.get_info()
        }


# Convenience functions for clean API

def create_project_repository(
    user_id: Optional[str] = None,
    repository_type: Optional[str] = None,
    db_path: Optional[str] = None
) -> ProjectRepository:
    """Create a project repository instance"""
    repo_type = RepositoryType(repository_type) if repository_type else None
    return ProjectRepositoryFactory.create(
        repository_type=repo_type,
        user_id=user_id,
        db_path=db_path
    )


def get_sqlite_repository(
    user_id: Optional[str] = None,
    db_path: Optional[str] = None
) -> ORMProjectRepository:
    """Get ORM project repository (legacy compatibility method)"""
    return ProjectRepositoryFactory.create(
        repository_type=RepositoryType.ORM,
        user_id=user_id,
        db_path=db_path
    )


def get_default_repository() -> ProjectRepository:
    """Get default global repository"""
    return GlobalRepositoryManager.get_default()


def get_user_repository(user_id: str) -> ProjectRepository:
    """Get repository for specific user"""
    return GlobalRepositoryManager.get_for_user(user_id)


# Export clean API
__all__ = [
    "ProjectRepositoryFactory",
    "RepositoryType", 
    "RepositoryConfig",
    "GlobalRepositoryManager",
    "create_project_repository",
    "get_sqlite_repository",
    "get_default_repository",
    "get_user_repository"
] 