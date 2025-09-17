"""Test suite for TaskRepositoryFactory.

Tests the task repository factory including:
- Repository creation with proper scoping
- Authentication and user validation
- Database availability handling
- Path resolution and configuration
- Error handling and fallbacks
"""

import pytest
import os
import tempfile
from pathlib import Path
from unittest.mock import Mock, patch, MagicMock

from fastmcp.task_management.infrastructure.repositories.task_repository_factory import (
    TaskRepositoryFactory,
    _find_project_root
)
from fastmcp.task_management.domain.repositories.task_repository import TaskRepository
from fastmcp.task_management.infrastructure.repositories.orm.task_repository import ORMTaskRepository
from fastmcp.task_management.infrastructure.repositories.mock_repository_factory import MockTaskRepository
from fastmcp.task_management.domain.exceptions.authentication_exceptions import (
    UserAuthenticationRequiredError,
    DefaultUserProhibitedError
)


class TestFindProjectRoot:
    """Test cases for _find_project_root function."""
    
    def test_find_project_root_from_file_location(self):
        """Test finding project root from current file location."""
        with tempfile.TemporaryDirectory() as temp_dir:
            temp_path = Path(temp_dir)
            agenthub_dir = temp_path / "agenthub_main"
            agenthub_dir.mkdir()
            
            # Mock __file__ to be in the temp directory structure
            mock_file_path = agenthub_dir / "src" / "test_file.py"
            mock_file_path.parent.mkdir(parents=True)
            mock_file_path.touch()
            
            with patch('fastmcp.task_management.infrastructure.repositories.task_repository_factory.__file__', str(mock_file_path)):
                result = _find_project_root()
                assert result == temp_path
    
    def test_find_project_root_fallback_to_cwd(self):
        """Test fallback to current working directory."""
        with tempfile.TemporaryDirectory() as temp_dir:
            temp_path = Path(temp_dir)
            agenthub_dir = temp_path / "agenthub_main"
            agenthub_dir.mkdir()
            
            with patch('pathlib.Path.cwd', return_value=temp_path):
                with patch('fastmcp.task_management.infrastructure.repositories.task_repository_factory.__file__', '/non/existent/path'):
                    result = _find_project_root()
                    assert result == temp_path
    
    def test_find_project_root_from_agenthub_main_name(self):
        """Test finding project root when current path is agenthub_main."""
        with tempfile.TemporaryDirectory() as temp_dir:
            temp_path = Path(temp_dir)
            agenthub_dir = temp_path / "agenthub_main"
            agenthub_dir.mkdir()
            
            mock_file_path = agenthub_dir / "src" / "test_file.py"
            mock_file_path.parent.mkdir(parents=True)
            mock_file_path.touch()
            
            with patch('fastmcp.task_management.infrastructure.repositories.task_repository_factory.__file__', str(mock_file_path)):
                result = _find_project_root()
                assert result == temp_path
    
    @patch.dict(os.environ, {'AGENTHUB_DATA_PATH': '/custom/data'})
    def test_find_project_root_environment_variable(self):
        """Test using environment variable for data path."""
        def mock_exists(path):
            # Only return True for the environment variable path
            return str(path) == '/custom/data'
        
        with patch('os.path.exists', side_effect=mock_exists):
            with patch('pathlib.Path.cwd', return_value=Path("/tmp")):  # No agenthub_main here
                with patch('fastmcp.task_management.infrastructure.repositories.task_repository_factory.__file__', '/non/existent/path'):
                    result = _find_project_root()
                    assert result == Path("/custom/data")
    
    def test_find_project_root_absolute_fallback(self):
        """Test absolute fallback when nothing else works."""
        with patch('os.path.exists', return_value=False):
            with patch('pathlib.Path.cwd', return_value=Path("/tmp")):
                with patch('fastmcp.task_management.infrastructure.repositories.task_repository_factory.__file__', '/non/existent/path'):
                    result = _find_project_root()
                    assert result == Path("/tmp/agenthub_project")


class TestTaskRepositoryFactory:
    """Test cases for TaskRepositoryFactory."""
    
    def setup_method(self):
        """Set up test fixtures."""
        self.temp_dir = tempfile.mkdtemp()
        self.project_root = Path(self.temp_dir)
        
        # Clear environment variables
        if 'ALLOW_DEFAULT_USER' in os.environ:
            del os.environ['ALLOW_DEFAULT_USER']
    
    def teardown_method(self):
        """Clean up test environment."""
        import shutil
        shutil.rmtree(self.temp_dir)
        
        if 'ALLOW_DEFAULT_USER' in os.environ:
            del os.environ['ALLOW_DEFAULT_USER']
    
    def test_init_with_custom_path(self):
        """Test factory initialization with custom base path."""
        custom_path = "/custom/path"
        factory = TaskRepositoryFactory(
            base_path=custom_path,
            default_user_id="test-user",
            project_root=self.project_root
        )
        
        assert factory.base_path == custom_path
        assert factory.default_user_id == "test-user"
        assert factory.project_root == self.project_root
    
    def test_init_with_default_path(self):
        """Test factory initialization with default path."""
        factory = TaskRepositoryFactory(
            default_user_id="test-user",
            project_root=self.project_root
        )
        
        expected_path = str(self.project_root / ".cursor" / "rules" / "tasks")
        assert factory.base_path == expected_path
        assert factory.default_user_id == "test-user"
    
    def test_init_without_compatibility_mode(self):
        """Test factory initialization without compatibility mode."""
        factory = TaskRepositoryFactory(project_root=self.project_root)
        
        assert factory.default_user_id is None
    
    def test_init_with_prohibited_default_user(self):
        """Test factory initialization with prohibited default user."""
        with pytest.raises(DefaultUserProhibitedError):
            TaskRepositoryFactory(
                default_user_id="default_id",
                project_root=self.project_root
            )
    
    def test_create_static_method(self):
        """Test static create method."""
        with patch.object(TaskRepositoryFactory, 'create_repository') as mock_create:
            mock_repo = Mock(spec=TaskRepository)
            mock_create.return_value = mock_repo
            
            result = TaskRepositoryFactory.create(
                project_id="test-project",
                git_branch_name="test-branch",
                user_id="test-user"
            )
            
            assert result == mock_repo
    
    @patch('fastmcp.task_management.infrastructure.database.database_config.get_db_config')
    def test_create_repository_with_orm(self, mock_get_db_config):
        """Test repository creation with ORM when database is available."""
        # Mock database availability
        mock_db_config = Mock()
        mock_db_config.engine = Mock()
        mock_get_db_config.return_value = mock_db_config
        
        factory = TaskRepositoryFactory(
            default_user_id="test-user",
            project_root=self.project_root
        )
        
        with patch('fastmcp.task_management.infrastructure.repositories.task_repository_factory.ORMTaskRepository') as mock_orm:
            mock_repo = Mock(spec=ORMTaskRepository)
            mock_orm.return_value = mock_repo
            
            result = factory.create_repository("test-project", "test-branch")
            
            assert result == mock_repo
            mock_orm.assert_called_once_with(
                project_id="test-project",
                git_branch_name="test-branch",
                user_id="test-user"
            )
    
    @patch('fastmcp.task_management.infrastructure.database.database_config.get_db_config')
    def test_create_repository_fallback_to_mock(self, mock_get_db_config):
        """Test repository creation falls back to mock when database unavailable."""
        # Mock database unavailability
        mock_get_db_config.side_effect = Exception("Database not available")
        
        factory = TaskRepositoryFactory(
            default_user_id="test-user",
            project_root=self.project_root
        )
        
        result = factory.create_repository("test-project", "test-branch")
        
        assert isinstance(result, MockTaskRepository)
    
    def test_create_repository_missing_project_id(self):
        """Test repository creation fails without project_id."""
        factory = TaskRepositoryFactory(
            default_user_id="test-user",
            project_root=self.project_root
        )
        
        with pytest.raises(ValueError, match="project_id is required"):
            factory.create_repository("")
        
        with pytest.raises(ValueError, match="project_id is required"):
            factory.create_repository(None)
    
    def test_create_repository_default_branch_name(self):
        """Test repository creation with default branch name."""
        factory = TaskRepositoryFactory(
            default_user_id="test-user",
            project_root=self.project_root
        )
        
        with patch('fastmcp.task_management.infrastructure.database.database_config.get_db_config') as mock_get_db_config:
            mock_get_db_config.side_effect = Exception("No DB")
            
            result = factory.create_repository("test-project", None)
            
            assert isinstance(result, MockTaskRepository)
    
    def test_create_repository_with_user_id_override(self):
        """Test repository creation with user_id override."""
        factory = TaskRepositoryFactory(
            default_user_id="default-user",
            project_root=self.project_root
        )
        
        with patch('fastmcp.task_management.infrastructure.database.database_config.get_db_config') as mock_get_db_config:
            mock_db_config = Mock()
            mock_db_config.engine = Mock()
            mock_get_db_config.return_value = mock_db_config
            
            with patch('fastmcp.task_management.infrastructure.repositories.task_repository_factory.ORMTaskRepository') as mock_orm:
                mock_repo = Mock()
                mock_orm.return_value = mock_repo
                
                factory.create_repository("test-project", "test-branch", "override-user")
                
                mock_orm.assert_called_once_with(
                    project_id="test-project",
                    git_branch_name="test-branch",
                    user_id="override-user"
                )
    
    @patch('fastmcp.task_management.infrastructure.database.database_config.get_db_config')
    def test_create_repository_with_git_branch_id(self, mock_get_db_config):
        """Test repository creation with specific git_branch_id."""
        mock_db_config = Mock()
        mock_db_config.engine = Mock()
        mock_get_db_config.return_value = mock_db_config
        
        factory = TaskRepositoryFactory(
            default_user_id="test-user",
            project_root=self.project_root
        )
        
        with patch('fastmcp.task_management.infrastructure.repositories.task_repository_factory.ORMTaskRepository') as mock_orm:
            mock_repo = Mock()
            mock_orm.return_value = mock_repo
            
            result = factory.create_repository_with_git_branch_id(
                "test-project", "test-branch", "test-user", "git-branch-123"
            )
            
            assert result == mock_repo
            mock_orm.assert_called_once_with(
                git_branch_id="git-branch-123",
                project_id="test-project",
                git_branch_name="test-branch",
                user_id="test-user"
            )
    
    @patch('fastmcp.task_management.infrastructure.database.database_config.get_db_config')
    def test_create_repository_with_git_branch_id_fallback(self, mock_get_db_config):
        """Test repository creation with git_branch_id falls back to mock."""
        mock_get_db_config.side_effect = Exception("Database not available")
        
        factory = TaskRepositoryFactory(
            default_user_id="test-user",
            project_root=self.project_root
        )
        
        result = factory.create_repository_with_git_branch_id(
            "test-project", "test-branch", "test-user", "git-branch-123"
        )
        
        assert isinstance(result, MockTaskRepository)
    
    @patch('fastmcp.task_management.infrastructure.database.database_config.get_db_config')
    def test_create_sqlite_task_repository(self, mock_get_db_config):
        """Test SQLite repository creation (now uses ORM)."""
        mock_db_config = Mock()
        mock_db_config.engine = Mock()
        mock_get_db_config.return_value = mock_db_config
        
        factory = TaskRepositoryFactory(
            default_user_id="test-user",
            project_root=self.project_root
        )
        
        with patch('fastmcp.task_management.infrastructure.repositories.task_repository_factory.ORMTaskRepository') as mock_orm:
            mock_repo = Mock()
            mock_orm.return_value = mock_repo
            
            result = factory.create_sqlite_task_repository(
                "test-project", "test-branch", db_path="/custom/db/path"
            )
            
            assert result == mock_repo
            mock_orm.assert_called_once_with(
                project_id="test-project",
                git_branch_name="test-branch",
                user_id="test-user"
            )
    
    def test_create_sqlite_task_repository_missing_project_id(self):
        """Test SQLite repository creation fails without project_id."""
        factory = TaskRepositoryFactory(
            default_user_id="test-user",
            project_root=self.project_root
        )
        
        with pytest.raises(ValueError, match="project_id is required"):
            factory.create_sqlite_task_repository("")
    
    @patch('fastmcp.task_management.infrastructure.database.database_config.get_db_config')
    def test_create_temporary_repository(self, mock_get_db_config):
        """Test temporary repository creation."""
        mock_db_config = Mock()
        mock_db_config.engine = Mock()
        mock_get_db_config.return_value = mock_db_config
        
        factory = TaskRepositoryFactory(project_root=self.project_root)
        
        with patch('fastmcp.task_management.infrastructure.repositories.task_repository_factory.ORMTaskRepository') as mock_orm:
            mock_repo = Mock()
            mock_orm.return_value = mock_repo
            
            result = factory.create_temporary_repository()
            
            assert result == mock_repo
            mock_orm.assert_called_once_with(
                project_id=None,
                git_branch_name=None,
                user_id=None
            )
    
    @patch('fastmcp.task_management.infrastructure.database.database_config.get_db_config')
    def test_create_temporary_repository_fallback(self, mock_get_db_config):
        """Test temporary repository creation falls back to mock."""
        mock_get_db_config.side_effect = Exception("Database not available")
        
        factory = TaskRepositoryFactory(project_root=self.project_root)
        
        result = factory.create_temporary_repository()
        
        assert isinstance(result, MockTaskRepository)
    
    def test_repository_creation_thread_safety(self):
        """Test thread safety of repository creation."""
        import threading
        
        factory = TaskRepositoryFactory(
            default_user_id="test-user",
            project_root=self.project_root
        )
        
        results = []
        errors = []
        
        def create_repo(project_id):
            try:
                repo = factory.create_repository(project_id, "main")
                results.append((project_id, repo))
            except Exception as e:
                errors.append(e)
        
        # Create multiple threads
        threads = []
        for i in range(5):
            thread = threading.Thread(target=create_repo, args=(f"project-{i}",))
            threads.append(thread)
            thread.start()
        
        # Wait for all threads
        for thread in threads:
            thread.join()
        
        # Check no errors
        assert len(errors) == 0
        assert len(results) == 5
        
        # Each repository should be a valid instance
        for project_id, repo in results:
            assert isinstance(repo, (ORMTaskRepository, MockTaskRepository))
    
    def test_special_characters_in_identifiers(self):
        """Test handling of special characters in project and branch names."""
        factory = TaskRepositoryFactory(
            default_user_id="test-user",
            project_root=self.project_root
        )
        
        special_projects = [
            "project-with-dashes",
            "project_with_underscores",
            "project.with.dots",
            "project@special#chars"
        ]
        
        special_branches = [
            "feature/user-auth",
            "bugfix/login-issue",
            "release/v1.0.0"
        ]
        
        for project_id in special_projects:
            for branch_name in special_branches:
                repo = factory.create_repository(project_id, branch_name)
                assert isinstance(repo, (ORMTaskRepository, MockTaskRepository))


class TestTaskRepositoryFactoryIntegration:
    """Integration tests for TaskRepositoryFactory."""
    
    def setup_method(self):
        """Set up test fixtures."""
        self.temp_dir = tempfile.mkdtemp()
        self.project_root = Path(self.temp_dir)
        
        if 'ALLOW_DEFAULT_USER' in os.environ:
            del os.environ['ALLOW_DEFAULT_USER']
    
    def teardown_method(self):
        """Clean up test environment."""
        import shutil
        shutil.rmtree(self.temp_dir)
        
        if 'ALLOW_DEFAULT_USER' in os.environ:
            del os.environ['ALLOW_DEFAULT_USER']
    
    def test_complete_workflow_with_authentication(self):
        """Test complete workflow with authentication integration."""
        # Initialize factory with explicit user_id
        factory = TaskRepositoryFactory(project_root=self.project_root, default_user_id="test-user-123")
        
        # Create repository should work with valid user
        repo = factory.create_repository("test-project", "main", user_id="test-user-456")
        assert isinstance(repo, (ORMTaskRepository, MockTaskRepository))
        
        # Verify repository was created successfully
        assert repo is not None
    
    def test_complete_workflow_without_authentication(self):
        """Test complete workflow without authentication (strict mode)."""
        # Initialize factory without user in strict mode
        factory = TaskRepositoryFactory(project_root=self.project_root)
        
        # Should have no default user
        assert factory.default_user_id is None
        
        # Repository creation should still work but use None user_id
        repo = factory.create_repository("test-project", "main", "explicit-user")
        assert isinstance(repo, (ORMTaskRepository, MockTaskRepository))


if __name__ == "__main__":
    pytest.main([__file__])