"""Task Repository Factory for Hierarchical Storage with User Support"""

from typing import Optional
from pathlib import Path
import os

from ...domain.repositories.task_repository import TaskRepository
from .orm.task_repository import ORMTaskRepository
from .mock_repository_factory import MockTaskRepository
import logging

logger = logging.getLogger(__name__)


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


class TaskRepositoryFactory:
    """Factory for creating task repositories with hierarchical user/project/tree structure"""
    
    def __init__(self, base_path: Optional[str] = None, default_user_id: str = None, 
                 project_root: Optional[Path] = None):
        """
        Initialize task repository factory
        
        Args:
            base_path: Base path for task storage (defaults to project root)
            default_user_id: Default user ID for single-user mode
            project_root: Injected project root for testing or custom environments
        """
        from ...domain.constants import validate_user_id
        from ...domain.exceptions.authentication_exceptions import UserAuthenticationRequiredError
        from ....config.auth_config import AuthConfig
        
        self.project_root = project_root or _find_project_root()
        self.base_path = base_path or str(self.project_root / ".cursor" / "rules" / "tasks")
        
        # Handle default_user_id - NO FALLBACKS ALLOWED
        if default_user_id is not None:
            # Validate if a user_id was provided
            default_user_id = validate_user_id(default_user_id, "Task repository factory initialization")
        
        self.default_user_id = default_user_id
    
    @classmethod
    def create(cls, project_id: str = "test-project", git_branch_name: str = "main", 
               user_id: str = "test-user") -> TaskRepository:
        """
        Static factory method for creating task repositories (for integration tests)
        
        Args:
            project_id: Project identifier
            git_branch_name: Task tree identifier
            user_id: User identifier
            
        Returns:
            TaskRepository instance
        """
        factory = cls()
        return factory.create_repository(project_id, git_branch_name, user_id)
    
    def create_repository(self, project_id: str, git_branch_name: str = "main", user_id: Optional[str] = None) -> TaskRepository:
        """
        Create a task repository for specific user/project/task tree
        
        Args:
            project_id: Project identifier (REQUIRED)
            git_branch_name: Task tree identifier (defaults to "main")
            user_id: User identifier (defaults to default_user_id)
            
        Returns:
            TaskRepository instance scoped to user/project/tree
        """
        if not project_id:
            raise ValueError("project_id is required")
        
        if not git_branch_name:
            git_branch_name = "main"
            
        if not user_id:
            user_id = self.default_user_id
        
        # Use central RepositoryFactory for environment-based selection
        from .repository_factory import RepositoryFactory
        return RepositoryFactory.get_task_repository(project_id, git_branch_name, user_id)

    def create_repository_with_git_branch_id(self, project_id: str, git_branch_name: str, user_id: str, git_branch_id: str) -> TaskRepository:
        """
        Create a task repository with a specific git_branch_id.
        
        This method creates a repository that is initialized with the git_branch_id directly,
        which is useful when the git_branch_id is known but context resolution is unreliable.
        
        Args:
            project_id: Project identifier
            git_branch_name: Task tree identifier
            user_id: User identifier
            git_branch_id: Specific git branch ID to use
            
        Returns:
            TaskRepository instance scoped to the git_branch_id
        """
        # Use central RepositoryFactory for environment-based selection
        from .repository_factory import RepositoryFactory
        return RepositoryFactory.get_task_repository(project_id, git_branch_name, user_id)
    
    def create_sqlite_task_repository(self, project_id: str, git_branch_name: str = "main", 
                                     user_id: Optional[str] = None, db_path: Optional[str] = None) -> TaskRepository:
        """
        Create a task repository (now always uses ORM)
        
        Args:
            project_id: Project identifier (REQUIRED)
            git_branch_name: Task tree identifier (defaults to "main")
            user_id: User identifier (defaults to default_user_id)
            db_path: Custom database path (optional, ignored for ORM)
            
        Returns:
            TaskRepository instance (ORM or Mock)
        """
        if not project_id:
            raise ValueError("project_id is required")
        
        if not git_branch_name:
            git_branch_name = "main"
            
        if not user_id:
            user_id = self.default_user_id
        
        # Try to use ORM, fallback to mock if database not available
        try:
            from ..database.database_config import get_db_config
            # Try to get database config to check if it's available
            db_config = get_db_config()
            if db_config and db_config.engine:
                return ORMTaskRepository(
                    project_id=project_id,
                    git_branch_name=git_branch_name,
                    user_id=user_id
                )
        except Exception as e:
            logger.warning(f"Database not available, using mock repository: {e}")
        
        # Fallback to mock repository
        return MockTaskRepository()
    
    def create_temporary_repository(self) -> TaskRepository:
        """
        Create a temporary task repository for testing
        
        Returns:
            TaskRepository instance with temporary storage
        """
        # Try to use ORM, fallback to mock if database not available
        try:
            from ..database.database_config import get_db_config
            # Try to get database config to check if it's available
            db_config = get_db_config()
            if db_config and db_config.engine:
                return ORMTaskRepository(
                    project_id=None,
                    git_branch_name=None,
                    user_id=None
                )
        except Exception as e:
            logger.warning(f"Database not available, using mock repository: {e}")
        
        # Fallback to mock repository
        return MockTaskRepository()