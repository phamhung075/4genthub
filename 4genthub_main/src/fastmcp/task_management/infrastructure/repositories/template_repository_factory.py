"""Template Repository Factory for Database Type Selection"""

from typing import Optional
from pathlib import Path
import os

from ...domain.repositories.template_repository import TemplateRepositoryInterface
from .orm.template_repository import ORMTemplateRepository


def _find_project_root() -> Path:
    """Find project root by looking for 4genthub_main directory"""
    current_path = Path(__file__).resolve()
    
    # Walk up the directory tree looking for 4genthub_main
    while current_path.parent != current_path:
        if (current_path / "4genthub_main").exists():
            return current_path
        current_path = current_path.parent
    
    # If not found, use current working directory as fallback
    cwd = Path.cwd()
    if (cwd / "4genthub_main").exists():
        return cwd
        
    # Last resort - use the directory containing 4genthub_main
    current_path = Path(__file__).resolve()
    while current_path.parent != current_path:
        if current_path.name == "4genthub_main":
            return current_path.parent
        current_path = current_path.parent
    
    # Absolute fallback
    # Use environment variable or default data path
    data_path = os.environ.get('4GENTHUB_DATA_PATH', '/data')
    # If running in development, try to find project root
    if not os.path.exists(data_path):
        # Try current working directory
        cwd = Path.cwd()
        if (cwd / "4genthub_main").exists():
            return cwd
        # Try parent directories
        current = Path(__file__).resolve()
        while current.parent != current:
            if (current / "4genthub_main").exists():
                return current
            current = current.parent
        # Fall back to temp directory for safety
        return Path("/tmp/4genthub_project")
    return Path(data_path)


class TemplateRepositoryFactory:
    """Factory for creating template repositories based on database type"""
    
    def __init__(self, project_root: Optional[Path] = None):
        """
        Initialize template repository factory
        
        Args:
            project_root: Injected project root for testing or custom environments
        """
        self.project_root = project_root or _find_project_root()
    
    def create_repository(self, db_path: Optional[str] = None) -> TemplateRepositoryInterface:
        """
        Create a template repository based on environment configuration
        
        Args:
            db_path: Custom database path (optional, ignored for ORM)
            
        Returns:
            TemplateRepository instance based on environment
        """
        # Check environment variables for proper repository selection
        env = os.getenv('ENVIRONMENT', 'production')
        db_type = os.getenv('DATABASE_TYPE')
        redis_enabled = os.getenv('REDIS_ENABLED', 'false').lower() == 'true'

        if not db_type:
            raise ValueError(
                "DATABASE_TYPE environment variable is not set. "
                "Please set DATABASE_TYPE to 'postgresql', 'sqlite', or 'supabase'"
            )
        
        # For test environment, use mock if available
        if env == 'test':
            try:
                from .mock_repository_factory import MockTemplateRepository
                return MockTemplateRepository()
            except ImportError:
                pass  # Fall through to ORM
        
        # For now, always use ORM repository as base
        base_repo = ORMTemplateRepository()
        
        # Wrap with cache if Redis is enabled and not in test environment
        if redis_enabled and env != 'test':
            try:
                from .cached.cached_template_repository import CachedTemplateRepository
                return CachedTemplateRepository(base_repo)
            except ImportError:
                pass  # Use base repository without caching
        
        return base_repo
    
    def create_sqlite_repository(self, db_path: Optional[str] = None) -> TemplateRepositoryInterface:
        """
        Create a template repository (delegates to create_repository for consistency)
        
        Args:
            db_path: Custom database path (optional, ignored for ORM)
            
        Returns:
            TemplateRepository instance based on environment
        """
        # Delegate to create_repository for environment checking
        return self.create_repository(db_path)
    
    def create_orm_repository(self) -> TemplateRepositoryInterface:
        """
        Create an ORM template repository (delegates to create_repository for consistency)
        
        Returns:
            TemplateRepository instance based on environment
        """
        # Delegate to create_repository for environment checking
        return self.create_repository()