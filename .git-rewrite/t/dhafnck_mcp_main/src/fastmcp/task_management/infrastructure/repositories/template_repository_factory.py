"""Template Repository Factory for Database Type Selection"""

from typing import Optional
from pathlib import Path
import os

from ...domain.repositories.template_repository import TemplateRepositoryInterface
from .orm.template_repository import ORMTemplateRepository


def _find_project_root() -> Path:
    """Find project root by looking for dhafnck_mcp_main directory"""
    current_path = Path(__file__).resolve()
    
    # Walk up the directory tree looking for dhafnck_mcp_main
    while current_path.parent != current_path:
        if (current_path / "dhafnck_mcp_main").exists():
            return current_path
        current_path = current_path.parent
    
    # If not found, use current working directory as fallback
    cwd = Path.cwd()
    if (cwd / "dhafnck_mcp_main").exists():
        return cwd
        
    # Last resort - use the directory containing dhafnck_mcp_main
    current_path = Path(__file__).resolve()
    while current_path.parent != current_path:
        if current_path.name == "dhafnck_mcp_main":
            return current_path.parent
        current_path = current_path.parent
    
    # Absolute fallback
    # Use environment variable or default data path
    data_path = os.environ.get('DHAFNCK_DATA_PATH', '/data')
    # If running in development, try to find project root
    if not os.path.exists(data_path):
        # Try current working directory
        cwd = Path.cwd()
        if (cwd / "dhafnck_mcp_main").exists():
            return cwd
        # Try parent directories
        current = Path(__file__).resolve()
        while current.parent != current:
            if (current / "dhafnck_mcp_main").exists():
                return current
            current = current.parent
        # Fall back to temp directory for safety
        return Path("/tmp/dhafnck_project")
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
        Create a template repository (always uses ORM)
        
        Args:
            db_path: Custom database path (optional, ignored for ORM)
            
        Returns:
            ORMTemplateRepository instance
        """
        # Always use ORM repository
        return ORMTemplateRepository()
    
    def create_sqlite_repository(self, db_path: Optional[str] = None) -> TemplateRepositoryInterface:
        """
        Create a template repository (now always uses ORM)
        
        Args:
            db_path: Custom database path (optional, ignored for ORM)
            
        Returns:
            ORMTemplateRepository instance
        """
        # Always use ORM repository
        return ORMTemplateRepository()
    
    def create_orm_repository(self) -> TemplateRepositoryInterface:
        """
        Create an ORM template repository
        
        Returns:
            ORMTemplateRepository instance
        """
        return ORMTemplateRepository()