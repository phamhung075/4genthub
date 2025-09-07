"""
Tests for User-Filtered Repository Wrapper for MCP Operations
"""

import pytest
from unittest.mock import Mock, patch, MagicMock
from typing import Any, List, Optional

from fastmcp.auth.mcp_integration.repository_filter import (
    UserFilteredRepository,
    UserFilteredTaskRepository,
    UserFilteredProjectRepository,
    UserFilteredContextRepository,
    create_user_filtered_repository
)


class TestUserFilteredRepository:
    """Test the base UserFilteredRepository abstract class."""

    def test_initialization(self):
        """Test that UserFilteredRepository initializes correctly."""
        base_repo = Mock()
        
        # Create concrete implementation for testing
        class ConcreteUserFilteredRepository(UserFilteredRepository):
            def find_by_id(self, entity_id: Any) -> Optional[Any]:
                return None
            def find_all(self, **filters) -> List[Any]:
                return []
            def save(self, entity: Any) -> Any:
                return entity
            def delete(self, entity_id: Any) -> bool:
                return False
        
        filtered_repo = ConcreteUserFilteredRepository(base_repo, "user_id")
        
        assert filtered_repo._base_repository == base_repo
        assert filtered_repo._user_id_field == "user_id"

    def test_initialization_with_custom_field(self):
        """Test initialization with custom user ID field."""
        base_repo = Mock()
        
        class ConcreteUserFilteredRepository(UserFilteredRepository):
            def find_by_id(self, entity_id: Any) -> Optional[Any]:
                return None
            def find_all(self, **filters) -> List[Any]:
                return []
            def save(self, entity: Any) -> Any:
                return entity
            def delete(self, entity_id: Any) -> bool:
                return False
        
        filtered_repo = ConcreteUserFilteredRepository(base_repo, "owner_id")
        
        assert filtered_repo._user_id_field == "owner_id"

    @patch('fastmcp.auth.mcp_integration.repository_filter.get_current_user_id')
    def test_get_current_user_id_string(self, mock_get_user):
        """Test getting current user ID when it's already a string."""
        mock_get_user.return_value = "user123"
        
        class ConcreteUserFilteredRepository(UserFilteredRepository):
            def find_by_id(self, entity_id: Any) -> Optional[Any]:
                return None
            def find_all(self, **filters) -> List[Any]:
                return []
            def save(self, entity: Any) -> Any:
                return entity
            def delete(self, entity_id: Any) -> bool:
                return False
        
        filtered_repo = ConcreteUserFilteredRepository(Mock())
        user_id = filtered_repo._get_current_user_id()
        
        assert user_id == "user123"

    @patch('fastmcp.auth.mcp_integration.repository_filter.get_current_user_id')
    def test_get_current_user_id_object_with_user_id(self, mock_get_user):
        """Test getting current user ID from object with user_id attribute."""
        mock_user_context = Mock()
        mock_user_context.user_id = "user456"
        mock_get_user.return_value = mock_user_context
        
        class ConcreteUserFilteredRepository(UserFilteredRepository):
            def find_by_id(self, entity_id: Any) -> Optional[Any]:
                return None
            def find_all(self, **filters) -> List[Any]:
                return []
            def save(self, entity: Any) -> Any:
                return entity
            def delete(self, entity_id: Any) -> bool:
                return False
        
        filtered_repo = ConcreteUserFilteredRepository(Mock())
        user_id = filtered_repo._get_current_user_id()
        
        assert user_id == "user456"

    @patch('fastmcp.auth.mcp_integration.repository_filter.get_current_user_id')
    def test_get_current_user_id_fallback_conversion(self, mock_get_user):
        """Test fallback string conversion for user ID."""
        mock_get_user.return_value = 12345  # Non-string, no user_id attribute
        
        class ConcreteUserFilteredRepository(UserFilteredRepository):
            def find_by_id(self, entity_id: Any) -> Optional[Any]:
                return None
            def find_all(self, **filters) -> List[Any]:
                return []
            def save(self, entity: Any) -> Any:
                return entity
            def delete(self, entity_id: Any) -> bool:
                return False
        
        filtered_repo = ConcreteUserFilteredRepository(Mock())
        user_id = filtered_repo._get_current_user_id()
        
        assert user_id == "12345"

    @patch('fastmcp.auth.mcp_integration.repository_filter.get_current_user_id')
    def test_get_current_user_id_no_user(self, mock_get_user):
        """Test error when no user is authenticated."""
        mock_get_user.return_value = None
        
        class ConcreteUserFilteredRepository(UserFilteredRepository):
            def find_by_id(self, entity_id: Any) -> Optional[Any]:
                return None
            def find_all(self, **filters) -> List[Any]:
                return []
            def save(self, entity: Any) -> Any:
                return entity
            def delete(self, entity_id: Any) -> bool:
                return False
        
        filtered_repo = ConcreteUserFilteredRepository(Mock())
        
        with pytest.raises(RuntimeError, match="No authenticated user in context"):
            filtered_repo._get_current_user_id()

    @patch('fastmcp.auth.mcp_integration.repository_filter.get_current_user_id')
    def test_add_user_filter(self, mock_get_user):
        """Test adding user filter to existing filters."""
        mock_get_user.return_value = "user789"
        
        class ConcreteUserFilteredRepository(UserFilteredRepository):
            def find_by_id(self, entity_id: Any) -> Optional[Any]:
                return None
            def find_all(self, **filters) -> List[Any]:
                return []
            def save(self, entity: Any) -> Any:
                return entity
            def delete(self, entity_id: Any) -> bool:
                return False
        
        filtered_repo = ConcreteUserFilteredRepository(Mock())
        
        # Test with existing filters
        filters = {"status": "active", "priority": "high"}
        result = filtered_repo._add_user_filter(filters)
        
        expected = {"status": "active", "priority": "high", "user_id": "user789"}
        assert result == expected

    @patch('fastmcp.auth.mcp_integration.repository_filter.get_current_user_id')
    def test_add_user_filter_empty(self, mock_get_user):
        """Test adding user filter to empty filters."""
        mock_get_user.return_value = "user789"
        
        class ConcreteUserFilteredRepository(UserFilteredRepository):
            def find_by_id(self, entity_id: Any) -> Optional[Any]:
                return None
            def find_all(self, **filters) -> List[Any]:
                return []
            def save(self, entity: Any) -> Any:
                return entity
            def delete(self, entity_id: Any) -> bool:
                return False
        
        filtered_repo = ConcreteUserFilteredRepository(Mock())
        
        # Test with None filters
        result = filtered_repo._add_user_filter(None)
        
        expected = {"user_id": "user789"}
        assert result == expected


class TestUserFilteredTaskRepository:
    """Test UserFilteredTaskRepository implementation."""

    def test_initialization(self):
        """Test task repository initialization."""
        base_repo = Mock()
        filtered_repo = UserFilteredTaskRepository(base_repo)
        
        assert filtered_repo._base_repository == base_repo
        assert filtered_repo._user_id_field == "user_id"

    @patch('fastmcp.auth.mcp_integration.repository_filter.get_current_user_id')
    def test_find_by_id_success(self, mock_get_user):
        """Test successful find by ID with user verification."""
        mock_get_user.return_value = "user123"
        
        base_repo = Mock()
        mock_task = Mock()
        mock_task.user_id = "user123"
        base_repo.find_by_id.return_value = mock_task
        
        filtered_repo = UserFilteredTaskRepository(base_repo)
        result = filtered_repo.find_by_id("task123")
        
        assert result == mock_task
        base_repo.find_by_id.assert_called_once_with("task123")

    @patch('fastmcp.auth.mcp_integration.repository_filter.get_current_user_id')
    def test_find_by_id_wrong_user(self, mock_get_user):
        """Test find by ID returns None for wrong user."""
        mock_get_user.return_value = "user123"
        
        base_repo = Mock()
        mock_task = Mock()
        mock_task.user_id = "different_user"
        base_repo.find_by_id.return_value = mock_task
        
        filtered_repo = UserFilteredTaskRepository(base_repo)
        result = filtered_repo.find_by_id("task123")
        
        assert result is None

    @patch('fastmcp.auth.mcp_integration.repository_filter.get_current_user_id')
    def test_find_by_id_not_found(self, mock_get_user):
        """Test find by ID when task not found."""
        mock_get_user.return_value = "user123"
        
        base_repo = Mock()
        base_repo.find_by_id.return_value = None
        
        filtered_repo = UserFilteredTaskRepository(base_repo)
        result = filtered_repo.find_by_id("task123")
        
        assert result is None

    @patch('fastmcp.auth.mcp_integration.repository_filter.get_current_user_id')
    def test_find_by_id_exception(self, mock_get_user):
        """Test find by ID handles exceptions."""
        mock_get_user.return_value = "user123"
        
        base_repo = Mock()
        base_repo.find_by_id.side_effect = Exception("Database error")
        
        filtered_repo = UserFilteredTaskRepository(base_repo)
        result = filtered_repo.find_by_id("task123")
        
        assert result is None

    @patch('fastmcp.auth.mcp_integration.repository_filter.get_current_user_id')
    def test_find_all_success(self, mock_get_user):
        """Test successful find all with user filter."""
        mock_get_user.return_value = "user123"
        
        base_repo = Mock()
        mock_tasks = [Mock(), Mock()]
        base_repo.find_all.return_value = mock_tasks
        
        filtered_repo = UserFilteredTaskRepository(base_repo)
        result = filtered_repo.find_all(status="active")
        
        assert result == mock_tasks
        base_repo.find_all.assert_called_once_with(status="active", user_id="user123")

    @patch('fastmcp.auth.mcp_integration.repository_filter.get_current_user_id')
    def test_find_all_exception(self, mock_get_user):
        """Test find all handles exceptions."""
        mock_get_user.return_value = "user123"
        
        base_repo = Mock()
        base_repo.find_all.side_effect = Exception("Database error")
        
        filtered_repo = UserFilteredTaskRepository(base_repo)
        result = filtered_repo.find_all()
        
        assert result == []

    @patch('fastmcp.auth.mcp_integration.repository_filter.get_current_user_id')
    def test_find_by_git_branch_id_success(self, mock_get_user):
        """Test find by git branch ID with user filtering."""
        mock_get_user.return_value = "user123"
        
        base_repo = Mock()
        mock_task1 = Mock()
        mock_task1.user_id = "user123"
        mock_task2 = Mock()
        mock_task2.user_id = "different_user"
        mock_task3 = Mock()
        mock_task3.user_id = "user123"
        
        base_repo.find_by_git_branch_id.return_value = [mock_task1, mock_task2, mock_task3]
        
        filtered_repo = UserFilteredTaskRepository(base_repo)
        result = filtered_repo.find_by_git_branch_id("branch123")
        
        assert result == [mock_task1, mock_task3]
        base_repo.find_by_git_branch_id.assert_called_once_with("branch123")

    @patch('fastmcp.auth.mcp_integration.repository_filter.get_current_user_id')
    def test_find_by_git_branch_id_exception(self, mock_get_user):
        """Test find by git branch ID handles exceptions."""
        mock_get_user.return_value = "user123"
        
        base_repo = Mock()
        base_repo.find_by_git_branch_id.side_effect = Exception("Database error")
        
        filtered_repo = UserFilteredTaskRepository(base_repo)
        result = filtered_repo.find_by_git_branch_id("branch123")
        
        assert result == []

    @patch('fastmcp.auth.mcp_integration.repository_filter.get_current_user_id')
    def test_save_new_task(self, mock_get_user):
        """Test saving new task sets user ID."""
        mock_get_user.return_value = "user123"
        
        base_repo = Mock()
        mock_task = Mock()
        mock_task.id = None  # New task
        base_repo.save.return_value = mock_task
        
        filtered_repo = UserFilteredTaskRepository(base_repo)
        result = filtered_repo.save(mock_task)
        
        assert result == mock_task
        assert mock_task.user_id == "user123"
        base_repo.save.assert_called_once_with(mock_task)

    @patch('fastmcp.auth.mcp_integration.repository_filter.get_current_user_id')
    def test_save_existing_task_correct_user(self, mock_get_user):
        """Test saving existing task with correct user."""
        mock_get_user.return_value = "user123"
        
        base_repo = Mock()
        mock_task = Mock()
        mock_task.id = "task123"  # Existing task
        mock_task.user_id = "user123"
        base_repo.save.return_value = mock_task
        
        filtered_repo = UserFilteredTaskRepository(base_repo)
        result = filtered_repo.save(mock_task)
        
        assert result == mock_task
        base_repo.save.assert_called_once_with(mock_task)

    @patch('fastmcp.auth.mcp_integration.repository_filter.get_current_user_id')
    def test_save_existing_task_wrong_user(self, mock_get_user):
        """Test saving existing task with wrong user raises error."""
        mock_get_user.return_value = "user123"
        
        base_repo = Mock()
        mock_task = Mock()
        mock_task.id = "task123"  # Existing task
        mock_task.user_id = "different_user"
        
        filtered_repo = UserFilteredTaskRepository(base_repo)
        
        with pytest.raises(RuntimeError, match="Cannot save task belonging to another user"):
            filtered_repo.save(mock_task)

    @patch('fastmcp.auth.mcp_integration.repository_filter.get_current_user_id')
    def test_save_exception(self, mock_get_user):
        """Test save handles exceptions."""
        mock_get_user.return_value = "user123"
        
        base_repo = Mock()
        base_repo.save.side_effect = Exception("Database error")
        mock_task = Mock()
        mock_task.id = None
        
        filtered_repo = UserFilteredTaskRepository(base_repo)
        
        with pytest.raises(Exception, match="Database error"):
            filtered_repo.save(mock_task)

    @patch.object(UserFilteredTaskRepository, 'find_by_id')
    def test_delete_success(self, mock_find_by_id):
        """Test successful task deletion."""
        mock_task = Mock()
        mock_find_by_id.return_value = mock_task
        
        base_repo = Mock()
        base_repo.delete.return_value = True
        
        filtered_repo = UserFilteredTaskRepository(base_repo)
        result = filtered_repo.delete("task123")
        
        assert result is True
        mock_find_by_id.assert_called_once_with("task123")
        base_repo.delete.assert_called_once_with("task123")

    @patch.object(UserFilteredTaskRepository, 'find_by_id')
    def test_delete_task_not_found(self, mock_find_by_id):
        """Test delete when task not found."""
        mock_find_by_id.return_value = None
        
        base_repo = Mock()
        filtered_repo = UserFilteredTaskRepository(base_repo)
        result = filtered_repo.delete("task123")
        
        assert result is False
        base_repo.delete.assert_not_called()

    @patch.object(UserFilteredTaskRepository, 'find_by_id')
    def test_delete_exception(self, mock_find_by_id):
        """Test delete handles exceptions."""
        mock_find_by_id.side_effect = Exception("Database error")
        
        base_repo = Mock()
        filtered_repo = UserFilteredTaskRepository(base_repo)
        result = filtered_repo.delete("task123")
        
        assert result is False


class TestUserFilteredProjectRepository:
    """Test UserFilteredProjectRepository implementation."""

    @patch('fastmcp.auth.mcp_integration.repository_filter.get_current_user_id')
    def test_find_by_id_success(self, mock_get_user):
        """Test successful find by ID for project."""
        mock_get_user.return_value = "user123"
        
        base_repo = Mock()
        mock_project = Mock()
        mock_project.user_id = "user123"
        base_repo.find_by_id.return_value = mock_project
        
        filtered_repo = UserFilteredProjectRepository(base_repo)
        result = filtered_repo.find_by_id("project123")
        
        assert result == mock_project

    @patch('fastmcp.auth.mcp_integration.repository_filter.get_current_user_id')
    def test_find_all_with_filter(self, mock_get_user):
        """Test find all projects with user filter."""
        mock_get_user.return_value = "user123"
        
        base_repo = Mock()
        mock_projects = [Mock(), Mock()]
        base_repo.find_all.return_value = mock_projects
        
        filtered_repo = UserFilteredProjectRepository(base_repo)
        result = filtered_repo.find_all(status="active")
        
        assert result == mock_projects
        base_repo.find_all.assert_called_once_with(status="active", user_id="user123")

    @patch('fastmcp.auth.mcp_integration.repository_filter.get_current_user_id')
    def test_save_new_project(self, mock_get_user):
        """Test saving new project sets user ID."""
        mock_get_user.return_value = "user123"
        
        base_repo = Mock()
        mock_project = Mock()
        mock_project.id = None  # New project
        base_repo.save.return_value = mock_project
        
        filtered_repo = UserFilteredProjectRepository(base_repo)
        result = filtered_repo.save(mock_project)
        
        assert result == mock_project
        assert mock_project.user_id == "user123"

    @patch('fastmcp.auth.mcp_integration.repository_filter.get_current_user_id')
    def test_save_existing_project_wrong_user(self, mock_get_user):
        """Test saving existing project with wrong user raises error."""
        mock_get_user.return_value = "user123"
        
        base_repo = Mock()
        mock_project = Mock()
        mock_project.id = "project123"
        mock_project.user_id = "different_user"
        
        filtered_repo = UserFilteredProjectRepository(base_repo)
        
        with pytest.raises(RuntimeError, match="Cannot save project belonging to another user"):
            filtered_repo.save(mock_project)

    @patch.object(UserFilteredProjectRepository, 'find_by_id')
    def test_delete_success(self, mock_find_by_id):
        """Test successful project deletion."""
        mock_project = Mock()
        mock_find_by_id.return_value = mock_project
        
        base_repo = Mock()
        base_repo.delete.return_value = True
        
        filtered_repo = UserFilteredProjectRepository(base_repo)
        result = filtered_repo.delete("project123")
        
        assert result is True


class TestUserFilteredContextRepository:
    """Test UserFilteredContextRepository implementation."""

    @patch('fastmcp.auth.mcp_integration.repository_filter.get_current_user_id')
    def test_find_by_id_user_context(self, mock_get_user):
        """Test finding user's own context."""
        mock_get_user.return_value = "user123"
        
        base_repo = Mock()
        mock_context = Mock()
        mock_context.user_id = "user123"
        base_repo.find_by_id.return_value = mock_context
        
        filtered_repo = UserFilteredContextRepository(base_repo)
        result = filtered_repo.find_by_id("context123")
        
        assert result == mock_context

    @patch('fastmcp.auth.mcp_integration.repository_filter.get_current_user_id')
    def test_find_all_includes_user_and_global(self, mock_get_user):
        """Test find all includes both user and global contexts."""
        mock_get_user.return_value = "user123"
        
        base_repo = Mock()
        user_contexts = [Mock(), Mock()]
        global_contexts = [Mock()]
        base_repo.find_all.side_effect = [user_contexts, global_contexts]
        
        filtered_repo = UserFilteredContextRepository(base_repo)
        result = filtered_repo.find_all(level="project")
        
        expected = user_contexts + global_contexts
        assert result == expected
        
        # Verify two calls were made
        assert base_repo.find_all.call_count == 2
        calls = base_repo.find_all.call_args_list
        assert calls[0][1] == {"level": "project", "user_id": "user123"}
        assert calls[1][1] == {"level": "project", "user_id": None}

    @patch('fastmcp.auth.mcp_integration.repository_filter.get_current_user_id')
    def test_save_global_context_sets_user_id(self, mock_get_user):
        """Test saving global context sets user ID for user isolation."""
        mock_get_user.return_value = "user123"
        
        base_repo = Mock()
        mock_context = Mock()
        mock_context.level = "global"
        mock_context.id = None
        base_repo.save.return_value = mock_context
        
        filtered_repo = UserFilteredContextRepository(base_repo)
        result = filtered_repo.save(mock_context)
        
        assert result == mock_context
        assert mock_context.user_id == "user123"

    @patch('fastmcp.auth.mcp_integration.repository_filter.get_current_user_id')
    def test_save_new_non_global_context(self, mock_get_user):
        """Test saving new non-global context."""
        mock_get_user.return_value = "user123"
        
        base_repo = Mock()
        mock_context = Mock()
        mock_context.level = "project"
        mock_context.id = None
        base_repo.save.return_value = mock_context
        
        filtered_repo = UserFilteredContextRepository(base_repo)
        result = filtered_repo.save(mock_context)
        
        assert result == mock_context
        assert mock_context.user_id == "user123"

    @patch('fastmcp.auth.mcp_integration.repository_filter.get_current_user_id')
    def test_save_existing_context_wrong_user(self, mock_get_user):
        """Test saving existing context with wrong user raises error."""
        mock_get_user.return_value = "user123"
        
        base_repo = Mock()
        mock_context = Mock()
        mock_context.level = "project"
        mock_context.id = "context123"
        mock_context.user_id = "different_user"
        
        filtered_repo = UserFilteredContextRepository(base_repo)
        
        with pytest.raises(RuntimeError, match="Cannot save context belonging to another user"):
            filtered_repo.save(mock_context)

    @patch('fastmcp.auth.mcp_integration.repository_filter.get_current_user_id')
    @patch.object(UserFilteredContextRepository, 'find_by_id')
    def test_delete_global_context_prohibited(self, mock_find_by_id, mock_get_user):
        """Test that deleting global contexts is prohibited."""
        mock_get_user.return_value = "user123"
        
        mock_context = Mock()
        mock_context.level = "global"
        mock_find_by_id.return_value = mock_context
        
        base_repo = Mock()
        filtered_repo = UserFilteredContextRepository(base_repo)
        result = filtered_repo.delete("context123")
        
        assert result is False
        base_repo.delete.assert_not_called()

    @patch('fastmcp.auth.mcp_integration.repository_filter.get_current_user_id')
    @patch.object(UserFilteredContextRepository, 'find_by_id')
    def test_delete_non_global_context_success(self, mock_find_by_id, mock_get_user):
        """Test successful deletion of non-global context."""
        mock_get_user.return_value = "user123"
        
        mock_context = Mock()
        mock_context.level = "project"
        mock_find_by_id.return_value = mock_context
        
        base_repo = Mock()
        base_repo.delete.return_value = True
        
        filtered_repo = UserFilteredContextRepository(base_repo)
        result = filtered_repo.delete("context123")
        
        assert result is True
        base_repo.delete.assert_called_once_with("context123")


class TestCreateUserFilteredRepository:
    """Test the factory function for creating user-filtered repositories."""

    def test_create_task_repository(self):
        """Test creating task repository."""
        base_repo = Mock()
        
        filtered_repo = create_user_filtered_repository("task", base_repo)
        
        assert isinstance(filtered_repo, UserFilteredTaskRepository)
        assert filtered_repo._base_repository == base_repo
        assert filtered_repo._user_id_field == "user_id"

    def test_create_project_repository(self):
        """Test creating project repository."""
        base_repo = Mock()
        
        filtered_repo = create_user_filtered_repository("project", base_repo)
        
        assert isinstance(filtered_repo, UserFilteredProjectRepository)
        assert filtered_repo._base_repository == base_repo

    def test_create_context_repository(self):
        """Test creating context repository."""
        base_repo = Mock()
        
        filtered_repo = create_user_filtered_repository("context", base_repo)
        
        assert isinstance(filtered_repo, UserFilteredContextRepository)
        assert filtered_repo._base_repository == base_repo

    def test_create_with_custom_field(self):
        """Test creating repository with custom user ID field."""
        base_repo = Mock()
        
        filtered_repo = create_user_filtered_repository("task", base_repo, "owner_id")
        
        assert isinstance(filtered_repo, UserFilteredTaskRepository)
        assert filtered_repo._user_id_field == "owner_id"

    def test_create_unknown_type(self):
        """Test creating repository with unknown type raises error."""
        base_repo = Mock()
        
        with pytest.raises(ValueError, match="Unknown repository type: unknown"):
            create_user_filtered_repository("unknown", base_repo)


class TestErrorHandling:
    """Test error handling in user-filtered repositories."""

    @patch('fastmcp.auth.mcp_integration.repository_filter.get_current_user_id')
    def test_authentication_error_propagation(self, mock_get_user):
        """Test that authentication errors are properly propagated."""
        mock_get_user.side_effect = RuntimeError("Authentication service unavailable")
        
        base_repo = Mock()
        filtered_repo = UserFilteredTaskRepository(base_repo)
        
        with pytest.raises(RuntimeError, match="Authentication service unavailable"):
            filtered_repo.find_all()

    @patch('fastmcp.auth.mcp_integration.repository_filter.get_current_user_id')
    def test_repository_error_handling(self, mock_get_user):
        """Test handling of repository errors."""
        mock_get_user.return_value = "user123"
        
        base_repo = Mock()
        base_repo.find_all.side_effect = Exception("Database connection failed")
        
        filtered_repo = UserFilteredTaskRepository(base_repo)
        result = filtered_repo.find_all()
        
        # Should return empty list instead of raising exception
        assert result == []

    @patch('fastmcp.auth.mcp_integration.repository_filter.get_current_user_id')
    @patch('fastmcp.auth.mcp_integration.repository_filter.logger')
    def test_logging_on_errors(self, mock_logger, mock_get_user):
        """Test that errors are logged appropriately."""
        mock_get_user.return_value = "user123"
        
        base_repo = Mock()
        base_repo.find_by_id.side_effect = Exception("Database error")
        
        filtered_repo = UserFilteredTaskRepository(base_repo)
        result = filtered_repo.find_by_id("task123")
        
        assert result is None
        mock_logger.error.assert_called()
        
        # Verify error message contains task ID
        error_call = mock_logger.error.call_args[0][0]
        assert "task123" in error_call


class TestContextHandling:
    """Test context handling scenarios."""

    @patch('fastmcp.auth.mcp_integration.repository_filter.get_current_user_id')
    def test_context_with_null_user_id(self, mock_get_user):
        """Test handling contexts with null user_id (global contexts)."""
        mock_get_user.return_value = "user123"
        
        base_repo = Mock()
        mock_context = Mock()
        mock_context.user_id = None  # Global context
        mock_context.level = "global"
        mock_context.id = "global_context"
        base_repo.save.return_value = mock_context
        
        filtered_repo = UserFilteredContextRepository(base_repo)
        result = filtered_repo.save(mock_context)
        
        # Should set user_id for user isolation
        assert mock_context.user_id == "user123"
        assert result == mock_context

    @patch('fastmcp.auth.mcp_integration.repository_filter.get_current_user_id')
    def test_context_validation_allows_none_user_id(self, mock_get_user):
        """Test that existing contexts with None user_id are handled correctly."""
        mock_get_user.return_value = "user123"
        
        base_repo = Mock()
        mock_context = Mock()
        mock_context.level = "project"
        mock_context.id = "context123"
        mock_context.user_id = None  # Existing context without user_id
        base_repo.save.return_value = mock_context
        
        filtered_repo = UserFilteredContextRepository(base_repo)
        
        # Should not raise error for existing contexts with None user_id
        result = filtered_repo.save(mock_context)
        assert result == mock_context