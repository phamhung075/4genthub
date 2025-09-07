"""Test module for SubtaskApplicationFacade."""
import pytest
from unittest.mock import Mock, MagicMock, patch, call
from dataclasses import dataclass, field
from typing import Dict, Any, List
import sqlite3

from fastmcp.task_management.application.facades.subtask_application_facade import SubtaskApplicationFacade
from fastmcp.task_management.domain.exceptions import TaskNotFoundError
from fastmcp.task_management.domain.value_objects.task_id import TaskId
from fastmcp.task_management.domain.entities.task import Task
from fastmcp.task_management.application.use_cases.add_subtask import AddSubtaskRequest
from fastmcp.task_management.application.use_cases.update_subtask import UpdateSubtaskRequest
from fastmcp.task_management.application.dtos.subtask.subtask_response import SubtaskResponse
from fastmcp.task_management.infrastructure.repositories.task_repository_factory import TaskRepositoryFactory
from fastmcp.task_management.infrastructure.repositories.subtask_repository_factory import SubtaskRepositoryFactory


@dataclass
class MockSubtask:
    """Mock subtask for testing."""
    id: str
    title: str
    description: str = ""
    status: str = "todo"
    priority: str = "medium"
    assignees: List[str] = field(default_factory=list)
    progress_percentage: int = 0

    def to_dict(self):
        return {
            "id": self.id,
            "title": self.title,
            "description": self.description,
            "status": self.status,
            "priority": self.priority,
            "assignees": self.assignees,
            "progress_percentage": self.progress_percentage
        }


# Module-level fixtures for sharing across test classes
@pytest.fixture
def mock_task_repository():
    """Create mock task repository."""
    return Mock()


@pytest.fixture
def mock_subtask_repository():
    """Create mock subtask repository."""
    return Mock()


@pytest.fixture
def mock_task_repository_factory():
    """Create mock task repository factory."""
    factory = Mock(spec=TaskRepositoryFactory)
    factory.create_repository = Mock()
    factory.create_system_repository = Mock()
    return factory


@pytest.fixture
def mock_subtask_repository_factory():
    """Create mock subtask repository factory."""
    factory = Mock(spec=SubtaskRepositoryFactory)
    factory.create_subtask_repository = Mock()
    return factory


@pytest.fixture
def facade_with_static_repos(mock_task_repository, mock_subtask_repository):
    """Create facade with static repositories (backward compatibility mode)."""
    return SubtaskApplicationFacade(
        task_repository=mock_task_repository,
        subtask_repository=mock_subtask_repository
    )


@pytest.fixture
def facade_with_factories(mock_task_repository_factory, mock_subtask_repository_factory):
    """Create facade with repository factories (factory mode)."""
    return SubtaskApplicationFacade(
        task_repository_factory=mock_task_repository_factory,
        subtask_repository_factory=mock_subtask_repository_factory
    )


@pytest.fixture
def mock_task():
    """Create mock task."""
    task = Mock(spec=Task)
    task.id = TaskId.from_string("12312312-3123-1231-2312-312312312312")
    task.title = "Test Task"
    task.git_branch_id = "branch_456"
    task.subtask_ids = []
    return task


@pytest.fixture
def mock_add_subtask_response():
    """Create mock add subtask response."""
    response = Mock(spec=SubtaskResponse)
    response.subtask = MockSubtask(
        id="subtask_123",
        title="Test Subtask",
        description="Test description"
    ).to_dict()
    response.task_id = "task_123"
    response.progress = {"completed": 0, "total": 1}
    return response


@pytest.fixture
def mock_update_subtask_response():
    """Create mock update subtask response."""
    response = Mock(spec=SubtaskResponse)
    subtask_data = MockSubtask(
        id="subtask_123",
        title="Updated Subtask",
        status="in_progress"
    ).to_dict()
    response.subtask = subtask_data
    response.to_dict = lambda: subtask_data
    return response


class TestSubtaskApplicationFacade:
    """Test cases for SubtaskApplicationFacade."""


class TestSubtaskCreation:
    """Test subtask creation operations."""
    
    def test_create_subtask_with_static_repos(self, facade_with_static_repos, mock_add_subtask_response):
        """Test creating a subtask with static repositories."""
        # Mock the use case execution
        facade_with_static_repos._add_subtask_use_case.execute = Mock(return_value=mock_add_subtask_response)
        
        # Execute
        result = facade_with_static_repos.handle_manage_subtask(
            action="create",
            task_id="task_123",
            subtask_data={
                "title": "Test Subtask",
                "description": "Test description"
            }
        )
        
        # Verify
        assert result["success"] is True
        assert result["action"] == "create"
        assert "Test Subtask" in result["message"]
        assert result["subtask"]["id"] == "subtask_123"
        assert result["task_id"] == "task_123"
    
    def test_create_subtask_with_factories(self, facade_with_factories, mock_task_repository_factory,
                                          mock_subtask_repository_factory, mock_task, mock_add_subtask_response):
        """Test creating a subtask with repository factories."""
        # Mock system repository and task lookup
        mock_system_repo = Mock()
        mock_system_repo.find_by_id = Mock(return_value=mock_task)
        mock_task_repository_factory.create_system_repository.return_value = mock_system_repo
        
        # Mock context repositories
        mock_task_repo = Mock()
        mock_subtask_repo = Mock()
        mock_task_repository_factory.create_repository.return_value = mock_task_repo
        mock_subtask_repository_factory.create_subtask_repository.return_value = mock_subtask_repo
        
        # Mock database lookup for git branch
        with patch('sqlite3.connect') as mock_connect:
            mock_conn = Mock()
            mock_cursor = Mock()
            
            # Mock git branch lookup
            mock_cursor.fetchone.side_effect = [
                {"project_id": "project_789", "name": "feature-branch"},  # Git branch
                {"user_id": "user_999"}  # Project
            ]
            mock_conn.execute.return_value = mock_cursor
            mock_conn.__enter__ = Mock(return_value=mock_conn)
            mock_conn.__exit__ = Mock(return_value=None)
            mock_connect.return_value = mock_conn
            
            # Mock use case
            with patch('fastmcp.task_management.application.facades.subtask_application_facade.AddSubtaskUseCase') as MockUseCase:
                mock_use_case = Mock()
                mock_use_case.execute = Mock(return_value=mock_add_subtask_response)
                MockUseCase.return_value = mock_use_case
                
                # Execute
                result = facade_with_factories.handle_manage_subtask(
                    action="create",
                    task_id="task_123",
                    subtask_data={
                        "title": "Test Subtask",
                        "description": "Test description",
                        "priority": "high"
                    }
                )
                
                # Verify repositories were created with correct context
                mock_task_repository_factory.create_repository.assert_called_with(
                    "project_789", "feature-branch", "user_999"
                )
                mock_subtask_repository_factory.create_subtask_repository.assert_called_with(
                    "project_789", "feature-branch", "user_999"
                )
                
                # Verify result
                assert result["success"] is True
                assert result["subtask"]["id"] == "subtask_123"
    
    def test_create_subtask_missing_title(self, facade_with_static_repos):
        """Test creating a subtask without title raises error."""
        with pytest.raises(ValueError, match="title is required"):
            facade_with_static_repos.handle_manage_subtask(
                action="create",
                task_id="task_123",
                subtask_data={"description": "No title"}
            )
    
    def test_create_subtask_add_action_alias(self, facade_with_static_repos, mock_add_subtask_response):
        """Test that 'add' action is aliased to 'create'."""
        facade_with_static_repos._add_subtask_use_case.execute = Mock(return_value=mock_add_subtask_response)
        
        result = facade_with_static_repos.handle_manage_subtask(
            action="add",  # Using 'add' instead of 'create'
            task_id="task_123",
            subtask_data={"title": "Test Subtask"}
        )
        
        assert result["success"] is True
        assert result["action"] == "create"


class TestSubtaskUpdate:
    """Test subtask update operations."""
    
    def test_update_subtask_success(self, facade_with_static_repos, mock_update_subtask_response):
        """Test updating a subtask successfully."""
        facade_with_static_repos._update_subtask_use_case.execute = Mock(return_value=mock_update_subtask_response)
        
        result = facade_with_static_repos.handle_manage_subtask(
            action="update",
            task_id="task_123",
            subtask_data={
                "subtask_id": "subtask_123",
                "title": "Updated Subtask",
                "status": "in_progress"
            }
        )
        
        assert result["success"] is True
        assert result["action"] == "update"
        assert result["subtask"]["title"] == "Updated Subtask"
        assert result["subtask"]["status"] == "in_progress"
    
    def test_update_subtask_missing_id(self, facade_with_static_repos):
        """Test updating subtask without ID raises error."""
        with pytest.raises(ValueError, match="subtask_id is required"):
            facade_with_static_repos.handle_manage_subtask(
                action="update",
                task_id="task_123",
                subtask_data={"title": "Updated"}
            )


class TestSubtaskDeletion:
    """Test subtask deletion operations."""
    
    def test_delete_subtask_success(self, facade_with_static_repos):
        """Test deleting a subtask successfully."""
        mock_result = {
            "success": True,
            "progress": {"completed": 1, "total": 5}
        }
        facade_with_static_repos._remove_subtask_use_case.execute = Mock(return_value=mock_result)
        
        result = facade_with_static_repos.handle_manage_subtask(
            action="delete",
            task_id="task_123",
            subtask_data={"subtask_id": "subtask_123"}
        )
        
        assert result["success"] is True
        assert result["action"] == "delete"
        assert "deleted" in result["message"]
        assert result["progress"]["completed"] == 1
    
    def test_delete_subtask_missing_id(self, facade_with_static_repos):
        """Test deleting subtask without ID raises error."""
        with pytest.raises(ValueError, match="subtask_id is required"):
            facade_with_static_repos.handle_manage_subtask(
                action="delete",
                task_id="task_123",
                subtask_data={}
            )


class TestSubtaskRetrieval:
    """Test subtask retrieval operations."""
    
    def test_list_subtasks(self, facade_with_static_repos):
        """Test listing all subtasks for a task."""
        mock_result = {
            "subtasks": [
                {"id": "sub1", "title": "Subtask 1"},
                {"id": "sub2", "title": "Subtask 2"}
            ],
            "progress": {"completed": 1, "total": 2}
        }
        facade_with_static_repos._get_subtasks_use_case.execute = Mock(return_value=mock_result)
        
        result = facade_with_static_repos.handle_manage_subtask(
            action="list",
            task_id="task_123"
        )
        
        assert result["success"] is True
        assert result["action"] == "list"
        assert len(result["subtasks"]) == 2
        assert result["progress"]["total"] == 2
    
    def test_get_single_subtask(self, facade_with_static_repos):
        """Test getting a single subtask."""
        mock_result = {
            "subtask": {"id": "sub1", "title": "Subtask 1", "status": "done"},
            "progress": {"completed": 1, "total": 3}
        }
        facade_with_static_repos._get_subtask_use_case.execute = Mock(return_value=mock_result)
        
        result = facade_with_static_repos.handle_manage_subtask(
            action="get",
            task_id="task_123",
            subtask_data={"subtask_id": "sub1"}
        )
        
        assert result["success"] is True
        assert result["action"] == "get"
        assert result["subtask"]["id"] == "sub1"
        assert result["subtask"]["status"] == "done"
    
    def test_get_subtask_missing_id(self, facade_with_static_repos):
        """Test getting subtask without ID raises error."""
        with pytest.raises(ValueError, match="subtask_id is required"):
            facade_with_static_repos.handle_manage_subtask(
                action="get",
                task_id="task_123",
                subtask_data={}
            )


class TestSubtaskCompletion:
    """Test subtask completion operations."""
    
    def test_complete_subtask_success(self, facade_with_static_repos):
        """Test completing a subtask successfully."""
        mock_result = {
            "success": True,
            "progress": {"completed": 3, "total": 5}
        }
        facade_with_static_repos._complete_subtask_use_case.execute = Mock(return_value=mock_result)
        
        result = facade_with_static_repos.handle_manage_subtask(
            action="complete",
            task_id="task_123",
            subtask_data={"subtask_id": "sub1"}
        )
        
        assert result["success"] is True
        assert result["action"] == "complete"
        assert result["subtask"]["completed"] is True
        assert result["progress"]["completed"] == 3
    
    def test_complete_subtask_missing_id(self, facade_with_static_repos):
        """Test completing subtask without ID raises error."""
        with pytest.raises(ValueError, match="subtask_id is required"):
            facade_with_static_repos.handle_manage_subtask(
                action="complete",
                task_id="task_123",
                subtask_data={}
            )


class TestContextDerivation:
    """Test context derivation from tasks and git branches."""
    
    @pytest.fixture
    def mock_task_repository_factory(self):
        """Create mock task repository factory."""
        factory = Mock(spec=TaskRepositoryFactory)
        factory.create_repository = Mock()
        factory.create_system_repository = Mock()
        return factory
    
    @pytest.fixture
    def mock_subtask_repository_factory(self):
        """Create mock subtask repository factory."""
        factory = Mock(spec=SubtaskRepositoryFactory)
        factory.create_repository = Mock()
        return factory
    
    @pytest.fixture
    def facade_with_factories(self, mock_task_repository_factory, mock_subtask_repository_factory):
        """Create facade with repository factories (factory mode)."""
        return SubtaskApplicationFacade(
            task_repository_factory=mock_task_repository_factory,
            subtask_repository_factory=mock_subtask_repository_factory
        )
    
    def test_derive_context_from_task_with_git_branch(self, facade_with_factories, mock_task_repository_factory):
        """Test deriving context from a task with git branch."""
        # Mock system repository and task
        mock_task = Mock()
        mock_task.git_branch_id = "branch_123"
        
        mock_system_repo = Mock()
        mock_system_repo.find_by_id = Mock(return_value=mock_task)
        mock_task_repository_factory.create_system_repository.return_value = mock_system_repo
        
        # Mock database lookups
        with patch('sqlite3.connect') as mock_connect:
            mock_conn = Mock()
            mock_cursor = Mock()
            
            # First query returns git branch info
            branch_row = {"project_id": "proj_456", "name": "main"}
            # Second query returns project info
            project_row = {"user_id": "user_789"}
            
            mock_cursor.fetchone.side_effect = [branch_row, project_row]
            mock_conn.execute.return_value = mock_cursor
            mock_conn.__enter__ = Mock(return_value=mock_conn)
            mock_conn.__exit__ = Mock(return_value=None)
            mock_connect.return_value = mock_conn
            
            # Execute
            context = facade_with_factories._derive_context_from_task("task_123")
            
            # Verify
            assert context["project_id"] == "proj_456"
            assert context["git_branch_name"] == "main"
            assert context["user_id"] == "user_789"
    
    @patch('fastmcp.task_management.interface.mcp_controllers.auth_helper.get_authenticated_user_id')
    def test_derive_context_fallback_with_auth(self, mock_get_auth_user, facade_with_factories):
        """Test context derivation fallback with authentication."""
        # Mock authentication
        mock_get_auth_user.return_value = "auth_user_123"
        
        # Mock system repository returning None (task not found)
        mock_system_repo = Mock()
        mock_system_repo.find_by_id = Mock(return_value=None)
        facade_with_factories._task_repository_factory.create_system_repository.return_value = mock_system_repo
        
        # Execute
        context = facade_with_factories._derive_context_from_task("task_999")
        
        # Verify fallback values
        assert context["project_id"] == "default_project"
        assert context["git_branch_name"] == "main"
        assert context["user_id"] == "auth_user_123"
    
    @patch('fastmcp.task_management.interface.mcp_controllers.auth_helper.get_authenticated_user_id')
    def test_derive_context_auth_failure(self, mock_get_auth_user, facade_with_factories):
        """Test context derivation fails when authentication fails."""
        # Mock authentication failure
        mock_get_auth_user.side_effect = Exception("Authentication required")
        
        # Mock system repository returning None
        mock_system_repo = Mock()
        mock_system_repo.find_by_id = Mock(return_value=None)
        facade_with_factories._task_repository_factory.create_system_repository.return_value = mock_system_repo
        
        # Execute and expect exception
        with pytest.raises(Exception, match="Authentication required"):
            facade_with_factories._derive_context_from_task("task_999")


class TestBackwardCompatibility:
    """Test backward compatibility with legacy call signatures."""
    
    def test_legacy_positional_arguments(self, facade_with_static_repos, mock_add_subtask_response):
        """Test legacy positional argument style (action, task_id, subtask_data)."""
        facade_with_static_repos._add_subtask_use_case.execute = Mock(return_value=mock_add_subtask_response)
        
        # Call with legacy positional style
        subtask_data = {"title": "Legacy Subtask"}
        result = facade_with_static_repos.handle_manage_subtask(
            "create",
            "task_123",
            subtask_data  # This is in the project_id position
        )
        
        assert result["success"] is True
        assert result["subtask"]["id"] == "subtask_123"
    
    def test_modern_keyword_arguments(self, facade_with_static_repos, mock_add_subtask_response):
        """Test modern keyword argument style."""
        facade_with_static_repos._add_subtask_use_case.execute = Mock(return_value=mock_add_subtask_response)
        
        # Call with modern keyword style
        result = facade_with_static_repos.handle_manage_subtask(
            action="create",
            task_id="task_123",
            subtask_data={"title": "Modern Subtask"},
            project_id="ignored_project",  # Should be ignored in favor of derived context
            git_branch_name="ignored_branch",
            user_id="ignored_user"
        )
        
        assert result["success"] is True
        assert result["subtask"]["id"] == "subtask_123"


class TestErrorHandling:
    """Test error handling scenarios."""
    
    def test_missing_task_id(self, facade_with_static_repos):
        """Test that missing task ID raises ValueError."""
        with pytest.raises(ValueError, match="Task ID is required"):
            facade_with_static_repos.handle_manage_subtask(
                action="create",
                task_id=None,
                subtask_data={"title": "Test"}
            )
    
    def test_unsupported_action(self, facade_with_static_repos):
        """Test that unsupported action raises ValueError."""
        with pytest.raises(ValueError, match="Unsupported subtask action: invalid"):
            facade_with_static_repos.handle_manage_subtask(
                action="invalid",
                task_id="task_123",
                subtask_data={"title": "Test"}
            )
    
    def test_database_error_during_context_derivation(self, facade_with_factories):
        """Test handling database errors during context derivation."""
        # Mock system repository
        mock_task = Mock()
        mock_task.git_branch_id = "branch_123"
        
        mock_system_repo = Mock()
        mock_system_repo.find_by_id = Mock(return_value=mock_task)
        facade_with_factories._task_repository_factory.create_system_repository.return_value = mock_system_repo
        
        # Mock database connection failure
        with patch('sqlite3.connect') as mock_connect:
            mock_connect.side_effect = sqlite3.Error("Database error")
            
            # Mock authentication for fallback
            with patch('fastmcp.task_management.interface.mcp_controllers.auth_helper.get_authenticated_user_id') as mock_auth:
                mock_auth.return_value = "fallback_user"
                
                # Should fall back to defaults
                context = facade_with_factories._derive_context_from_git_branch_id("branch_123")
                
                assert context["project_id"] == "default_project"
                assert context["git_branch_name"] == "main"
                assert context["user_id"] == "fallback_user"