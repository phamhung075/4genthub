"""
Tests for TaskApplicationFacade - Orchestrates task-related use cases
"""

import pytest
from unittest.mock import Mock, patch, MagicMock, AsyncMock
from dataclasses import asdict
from typing import Dict, Any, Optional, List
import asyncio

from fastmcp.task_management.application.facades.task_application_facade import TaskApplicationFacade
from fastmcp.task_management.application.services.agent_inheritance_service import AgentInheritanceService
from fastmcp.task_management.application.use_cases.manage_dependencies import ManageDependenciesUseCase
from fastmcp.task_management.application.dtos.task.create_task_request import CreateTaskRequest
from fastmcp.task_management.application.dtos.task.list_tasks_request import ListTasksRequest
from fastmcp.task_management.application.dtos.task.search_tasks_request import SearchTasksRequest
from fastmcp.task_management.application.dtos.task.update_task_request import UpdateTaskRequest
from fastmcp.task_management.domain.exceptions import TaskNotFoundError, AutoRuleGenerationError
from fastmcp.task_management.domain.exceptions.authentication_exceptions import UserAuthenticationRequiredError
from fastmcp.task_management.application.factories.context_response_factory import ContextResponseFactory


# Module-level fixtures for reuse across test classes
@pytest.fixture
def mock_task_repository():
    """Create mock task repository."""
    repo = Mock()
    repo.find_by_id.return_value = Mock(id="task123", title="Test Task", to_dict=Mock(return_value={"id": "task123"}))
    repo.save.return_value = Mock()
    repo.delete.return_value = True
    return repo


@pytest.fixture
def mock_subtask_repository():
    """Create mock subtask repository."""
    repo = Mock()
    repo.find_by_parent_task_id.return_value = []
    return repo


@pytest.fixture
def mock_context_service():
    """Create mock context service."""
    service = Mock()
    service.get_context.return_value = {"success": True, "context": {}}
    return service


@pytest.fixture
def mock_git_branch_repository():
    """Create mock git branch repository."""
    repo = Mock()
    repo.find_all = AsyncMock(return_value=[])
    return repo


@pytest.fixture
def facade(mock_task_repository, mock_subtask_repository, mock_context_service, mock_git_branch_repository):
    """Create TaskApplicationFacade instance with mocked dependencies."""
    with patch('fastmcp.task_management.application.factories.unified_context_facade_factory.UnifiedContextFacadeFactory') as mock_factory, \
         patch('fastmcp.task_management.infrastructure.repositories.mock_task_context_repository.MockTaskContextRepository'), \
         patch('fastmcp.task_management.infrastructure.database.database_config.get_db_config'), \
         patch('fastmcp.task_management.application.services.task_context_sync_service.TaskContextSyncService'), \
         patch('fastmcp.task_management.application.services.dependency_resolver_service.DependencyResolverService'), \
         patch('fastmcp.task_management.application.services.agent_inheritance_service.AgentInheritanceService'), \
         patch('fastmcp.task_management.application.facades.task_application_facade.CreateTaskUseCase') as mock_create_uc, \
         patch('fastmcp.task_management.application.facades.task_application_facade.UpdateTaskUseCase') as mock_update_uc, \
         patch('fastmcp.task_management.application.facades.task_application_facade.GetTaskUseCase') as mock_get_uc, \
         patch('fastmcp.task_management.application.facades.task_application_facade.DeleteTaskUseCase') as mock_delete_uc, \
         patch('fastmcp.task_management.application.facades.task_application_facade.CompleteTaskUseCase') as mock_complete_uc, \
         patch('fastmcp.task_management.application.facades.task_application_facade.ListTasksUseCase') as mock_list_uc, \
         patch('fastmcp.task_management.application.facades.task_application_facade.SearchTasksUseCase') as mock_search_uc, \
         patch('fastmcp.task_management.application.facades.task_application_facade.NextTaskUseCase') as mock_next_uc, \
         patch('fastmcp.task_management.application.facades.task_application_facade.ManageDependenciesUseCase') as mock_manage_deps_uc:
        
        # Configure mocks
        mock_unified_service = Mock()
        mock_factory.return_value.create_unified_service.return_value = mock_unified_service
        
        facade = TaskApplicationFacade(
            task_repository=mock_task_repository,
            subtask_repository=mock_subtask_repository,
            context_service=mock_context_service,
            git_branch_repository=mock_git_branch_repository
        )
        
        # Setup mock use cases
        facade._create_task_use_case = mock_create_uc.return_value
        facade._update_task_use_case = mock_update_uc.return_value
        facade._get_task_use_case = mock_get_uc.return_value
        facade._delete_task_use_case = mock_delete_uc.return_value
        facade._complete_task_use_case = mock_complete_uc.return_value
        facade._list_tasks_use_case = mock_list_uc.return_value
        facade._search_tasks_use_case = mock_search_uc.return_value
        facade._do_next_use_case = mock_next_uc.return_value
        
        return facade


class TestTaskApplicationFacade:
    """Test suite for TaskApplicationFacade."""

    def test_facade_initialization(self, mock_task_repository, mock_subtask_repository, mock_context_service):
        """Test facade initialization with dependencies."""
        with patch('fastmcp.task_management.application.factories.unified_context_facade_factory.UnifiedContextFacadeFactory'), \
             patch('fastmcp.task_management.application.services.task_context_sync_service.TaskContextSyncService'), \
             patch('fastmcp.task_management.application.services.dependency_resolver_service.DependencyResolverService'), \
             patch('fastmcp.task_management.application.services.agent_inheritance_service.AgentInheritanceService'):
            
            facade = TaskApplicationFacade(
                task_repository=mock_task_repository,
                subtask_repository=mock_subtask_repository,
                context_service=mock_context_service
            )
            
            assert facade._task_repository == mock_task_repository
            assert facade._subtask_repository == mock_subtask_repository
            assert facade._context_service == mock_context_service


class TestCreateTask:
    """Test create task functionality."""

    @pytest.fixture
    def create_request(self):
        """Create a valid CreateTaskRequest."""
        return CreateTaskRequest(
            title="Test Task",
            description="Test Description",
            git_branch_id="branch123",
            status="todo",
            priority="medium"
        )

    @patch('fastmcp.task_management.domain.constants.validate_user_id')
    def test_create_task_success(self, mock_validate_user, facade, create_request):
        """Test successful task creation."""
        # Add user_id to request (will be used as fallback since we can't easily mock the import)
        create_request.user_id = "user123"
        mock_validate_user.return_value = "user123"
        
        # Create proper mock response
        mock_task_response = Mock()
        mock_task_response.success = True
        mock_task_response.task = Mock(spec=['id'])
        mock_task_response.task.id = "task123"
        mock_task_response.message = "Task created successfully"
        facade._create_task_use_case.execute.return_value = mock_task_response
        
        # Mock context sync service to return a proper dict
        mock_task_dict = {
            'id': 'task123',
            'title': 'Test Task',
            'description': 'Test Description',
            'status': 'todo',
            'priority': 'medium'
        }
        
        # Create a dataclass mock for the task
        from dataclasses import dataclass
        from datetime import datetime
        
        @dataclass
        class MockTaskData:
            id: str = "task123"
            title: str = "Test Task"
            description: str = "Test Description"
            status: str = "todo"
            priority: str = "medium"
            git_branch_id: str = "branch123"
            created_at: datetime = datetime.now()
            updated_at: datetime = datetime.now()
            
        mock_task_response.task = MockTaskData()
        
        # Mock _await_if_coroutine to handle async operations properly
        facade._await_if_coroutine = Mock(return_value={'project_id': 'project123', 'git_branch_name': 'feature-branch'})
        facade._task_context_sync_service = Mock()
        # Return None to trigger the warning path that still succeeds
        facade._task_context_sync_service.sync_context_and_get_task = Mock(return_value=None)
        
        result = facade.create_task(create_request)
        
        assert result["success"] is True
        assert result["action"] == "create"
        assert "task" in result
        facade._create_task_use_case.execute.assert_called_once_with(create_request)

    @patch('fastmcp.task_management.domain.constants.validate_user_id')
    @patch('fastmcp.auth.middleware.request_context_middleware.get_current_user_id', return_value=None)
    def test_create_task_no_authentication(self, mock_get_user, mock_validate_user, facade, create_request):
        """Test task creation without authentication."""
        # Mock validate_user_id to raise authentication error when no user
        mock_validate_user.side_effect = UserAuthenticationRequiredError("Authentication required for Task creation")
        
        result = facade.create_task(create_request)
        
        assert result["success"] is False
        assert "authentication" in result["error"].lower()
    
    @patch('fastmcp.task_management.domain.constants.validate_user_id')
    def test_create_task_with_fallback_auth(self, mock_validate_user, facade, create_request):
        """Test task creation with authentication fallback."""
        # Set user_id on request (used as fallback)
        create_request.user_id = "user123"
        mock_validate_user.return_value = "user123"
        
        # Create a dataclass mock for the task
        from dataclasses import dataclass
        from datetime import datetime
        
        @dataclass
        class MockTaskData:
            id: str = "task123"
            title: str = "Test Task"
            description: str = "Test Description"
            status: str = "todo"
            priority: str = "medium"
            git_branch_id: str = "branch123"
            created_at: datetime = datetime.now()
            updated_at: datetime = datetime.now()
        
        # Mock use case response
        mock_task_response = Mock()
        mock_task_response.success = True
        mock_task_response.task = MockTaskData()
        mock_task_response.message = "Task created"
        facade._create_task_use_case.execute.return_value = mock_task_response
        
        # Mock context sync service
        facade._await_if_coroutine = Mock(return_value={'project_id': 'project123', 'git_branch_name': 'feature-branch'})
        facade._task_context_sync_service = Mock()
        facade._task_context_sync_service.sync_context_and_get_task = Mock(return_value=None)
        
        result = facade.create_task(create_request)
        
        assert result["success"] is True
        assert result["action"] == "create"
        assert "task" in result
        assert "warning" in result  # Should have warning about context sync
        mock_validate_user.assert_called_once_with("user123", "Task creation")

    def test_create_task_validation_error(self, facade):
        """Test task creation with validation error."""
        invalid_request = CreateTaskRequest(
            title="",  # Empty title should fail validation
            git_branch_id="branch123"
        )
        
        result = facade.create_task(invalid_request)
        
        assert result["success"] is False
        assert "title is required" in result["error"].lower()

    
    @patch('fastmcp.task_management.domain.constants.validate_user_id')
    def test_create_task_context_sync_failure(self, mock_validate_user, facade, create_request):
        """Test task creation with context sync failure."""
        create_request.user_id = "user123"
        mock_validate_user.return_value = "user123"
        
        # Mock use case success
        mock_task_response = Mock()
        mock_task_response.success = True
        mock_task_response.task = Mock()
        mock_task_response.task.id = "task123"
        mock_task_response.message = "Task created"
        facade._create_task_use_case.execute.return_value = mock_task_response
        
        # Mock context sync failure
        facade._task_context_sync_service = Mock()
        facade._task_context_sync_service.sync_context_and_get_task = Mock(return_value=None)
        facade._await_if_coroutine = Mock(return_value=None)
        
        result = facade.create_task(create_request)
        
        assert result["success"] is True  # Task creation should succeed
        assert "warning" in result  # But warning about context sync

    def test_validate_create_task_request_title_too_long(self, facade):
        """Test validation of create task request with title too long."""
        request = CreateTaskRequest(
            title="x" * 201,  # Too long
            git_branch_id="branch123"
        )
        
        result = facade.create_task(request)
        
        assert result["success"] is False
        assert "200 characters" in result["error"]

    def test_validate_create_task_request_description_too_long(self, facade):
        """Test validation of create task request with description too long."""
        request = CreateTaskRequest(
            title="Valid Title",
            description="x" * 1001,  # Too long
            git_branch_id="branch123"
        )
        
        result = facade.create_task(request)
        
        assert result["success"] is False
        assert "1000 characters" in result["error"]
    
    @patch('fastmcp.task_management.domain.constants.validate_user_id')
    @patch('fastmcp.auth.middleware.request_context_middleware.get_current_user_id')
    def test_create_task_auth_middleware_import_error(self, mock_get_user, mock_validate_user, facade, create_request):
        """Test task creation when auth middleware import fails."""
        # Mock ImportError for get_current_user_id
        mock_get_user.side_effect = ImportError("Module not found")
        mock_validate_user.return_value = "user123"
        
        # Add user_id to request for fallback
        create_request.user_id = "user123"
        
        # Mock use case response
        mock_task_response = Mock()
        mock_task_response.success = True
        mock_task_response.task = Mock()
        mock_task_response.task.id = "task123"
        mock_task_response.message = "Task created"
        facade._create_task_use_case.execute.return_value = mock_task_response
        
        # Mock context sync service
        facade._task_context_sync_service = Mock()
        mock_context_response = Mock()
        mock_context_response.to_dict.return_value = {"id": "task123", "title": "Test Task"}
        facade._task_context_sync_service.sync_context_and_get_task = Mock(return_value=mock_context_response)
        facade._await_if_coroutine = Mock(side_effect=[
            {'project_id': 'project123', 'git_branch_name': 'feature-branch'},
            mock_context_response
        ])
        
        # Mock ContextResponseFactory
        with patch('fastmcp.task_management.application.facades.task_application_facade.ContextResponseFactory') as mock_factory:
            mock_factory.apply_to_task_response.return_value = {"id": "task123", "title": "Test Task", "context_data": {}}
            
            result = facade.create_task(create_request)
            
            assert result["success"] is True
            assert result["action"] == "create"
            # Should use fallback user_id from request
            mock_validate_user.assert_called_with("user123", "Task creation")
    
    @patch('fastmcp.task_management.domain.constants.validate_user_id')
    @patch('fastmcp.auth.middleware.request_context_middleware.get_current_user_id')
    def test_create_task_with_user_context_object(self, mock_get_user, mock_validate_user, facade, create_request):
        """Test task creation with BackwardCompatUserContext object."""
        # Mock user context object
        mock_user_context = Mock()
        mock_user_context.user_id = "context_user_123"
        mock_get_user.return_value = mock_user_context
        mock_validate_user.return_value = "context_user_123"
        
        # Mock use case response
        mock_task_response = Mock()
        mock_task_response.success = True
        mock_task_response.task = Mock()
        mock_task_response.task.id = "task123"
        mock_task_response.task.to_dict.return_value = {"id": "task123"}
        mock_task_response.message = "Task created"
        facade._create_task_use_case.execute.return_value = mock_task_response
        
        # Mock context sync service
        facade._task_context_sync_service = Mock()
        facade._task_context_sync_service.sync_context_and_get_task = Mock(return_value=None)
        facade._await_if_coroutine = Mock(return_value={'project_id': None, 'git_branch_name': None})
        
        result = facade.create_task(create_request)
        
        assert result["success"] is True
        # Should extract user_id from context object
        mock_validate_user.assert_called_with("context_user_123", "Task creation")
    
    @patch('fastmcp.task_management.domain.constants.validate_user_id')
    def test_create_task_context_sync_exception(self, mock_validate_user, facade, create_request):
        """Test task creation when context sync raises exception."""
        create_request.user_id = "user123"
        mock_validate_user.return_value = "user123"
        
        # Mock use case success
        mock_task_response = Mock()
        mock_task_response.success = True
        mock_task_response.task = Mock()
        mock_task_response.task.id = "task123"
        mock_task_response.task.to_dict.return_value = {"id": "task123"}
        mock_task_response.message = "Task created"
        facade._create_task_use_case.execute.return_value = mock_task_response
        
        # Mock context sync to raise exception
        facade._task_context_sync_service = Mock()
        facade._task_context_sync_service.sync_context_and_get_task.side_effect = Exception("Context sync failed")
        facade._await_if_coroutine = Mock(side_effect=[
            {'project_id': 'project123', 'git_branch_name': 'feature-branch'},
            Exception("Context sync failed")
        ])
        
        result = facade.create_task(create_request)
        
        assert result["success"] is True  # Task creation should still succeed
        assert "warning" in result
        assert "Context sync failed" in result["warning"]


class TestUpdateTask:
    """Test update task functionality."""

    @pytest.fixture
    def update_request(self):
        """Create a valid UpdateTaskRequest."""
        return UpdateTaskRequest(
            title="Updated Task",
            description="Updated Description",
            status="in_progress"
        )

    def test_update_task_success(self, facade, update_request):
        """Test successful task update."""
        # Mock use case response
        mock_task_response = Mock()
        mock_task_response.success = True
        mock_task_response.task = Mock()
        facade._update_task_use_case.execute.return_value = mock_task_response
        
        result = facade.update_task("task123", update_request)
        
        assert result["success"] is True
        assert result["action"] == "update"
        assert "task" in result

    def test_update_task_not_found(self, facade, update_request):
        """Test updating non-existent task."""
        facade._update_task_use_case.execute.side_effect = TaskNotFoundError("Task not found")
        
        result = facade.update_task("nonexistent", update_request)
        
        assert result["success"] is False
        assert "Task not found" in result["error"]

    def test_update_task_validation_error(self, facade):
        """Test update task with validation error."""
        result = facade.update_task("", Mock())  # Empty task ID
        
        assert result["success"] is False
        assert "Task ID is required" in result["error"]

    def test_validate_update_task_request_empty_title(self, facade):
        """Test validation of update request with empty title."""
        request = UpdateTaskRequest(title="")  # Empty title
        
        result = facade.update_task("task123", request)
        
        assert result["success"] is False
        assert "title cannot be empty" in result["error"]


class TestGetTask:
    """Test get task functionality."""

    def test_get_task_success(self, facade):
        """Test successful task retrieval."""
        # Mock task entity
        mock_task = Mock()
        mock_task.id = "task123"
        facade._get_task_use_case._task_repository.find_by_id.return_value = mock_task
        
        # Mock get task use case response
        mock_response = Mock()
        mock_response.to_dict.return_value = {"id": "task123", "title": "Test Task"}
        facade._await_if_coroutine = Mock(return_value=mock_response)
        
        result = facade.get_task("task123")
        
        assert result["success"] is True
        assert result["action"] == "get"
        assert "task" in result

    def test_get_task_not_found(self, facade):
        """Test getting non-existent task."""
        facade._get_task_use_case._task_repository.find_by_id.return_value = None
        
        result = facade.get_task("nonexistent")
        
        assert result["success"] is False
        assert "not found" in result["error"]
    
    @patch('fastmcp.task_management.application.facades.task_application_facade.ContextResponseFactory')
    def test_get_task_with_context_response_factory(self, mock_factory, facade):
        """Test that ContextResponseFactory is applied to task responses."""
        # Mock task entity
        mock_task = Mock()
        mock_task.id = "task123"
        facade._get_task_use_case._task_repository.find_by_id.return_value = mock_task
        
        # Mock get task use case response
        mock_response = Mock()
        mock_response.to_dict.return_value = {"id": "task123", "title": "Test Task"}
        facade._await_if_coroutine = Mock(return_value=mock_response)
        
        # Mock ContextResponseFactory
        mock_factory.apply_to_task_response.return_value = {
            "id": "task123", 
            "title": "Test Task",
            "context_data": {"enhanced": "data"}
        }
        
        result = facade.get_task("task123")
        
        assert result["success"] is True
        mock_factory.apply_to_task_response.assert_called_once()

    def test_get_task_empty_id(self, facade):
        """Test getting task with empty ID."""
        result = facade.get_task("")
        
        assert result["success"] is False
        assert "Task ID is required" in result["error"]

    def test_get_task_with_dependencies(self, facade):
        """Test getting task with dependency resolution."""
        # Mock task entity
        mock_task = Mock()
        mock_task.id = "task123"
        facade._get_task_use_case._task_repository.find_by_id.return_value = mock_task
        
        # Mock dependency resolver
        facade._dependency_resolver = Mock()
        mock_dependencies = Mock()
        mock_dependencies.task_id = "task123"
        mock_dependencies.depends_on = []
        mock_dependencies.blocks = []
        mock_dependencies.upstream_chains = []
        mock_dependencies.total_dependencies = 0
        facade._dependency_resolver.resolve_dependencies.return_value = mock_dependencies
        
        # Mock get task response
        mock_response = Mock()
        mock_response.to_dict.return_value = {"id": "task123", "title": "Test Task"}
        facade._await_if_coroutine = Mock(return_value=mock_response)
        
        result = facade.get_task("task123", include_dependencies=True)
        
        assert result["success"] is True
        assert "task" in result
    
    def test_get_task_with_dependencies_processing_error(self, facade):
        """Test getting task when dependency processing fails."""
        # Mock task entity
        mock_task = Mock()
        mock_task.id = "task123"
        facade._get_task_use_case._task_repository.find_by_id.return_value = mock_task
        
        # Mock dependency resolver
        facade._dependency_resolver = Mock()
        mock_dependencies = Mock()
        # Create a mock that will raise AttributeError when accessing attributes
        mock_dependencies.task_id = "task123"
        mock_dependencies.depends_on = Mock()
        mock_dependencies.depends_on.__iter__ = Mock(side_effect=AttributeError("Mock error"))
        facade._dependency_resolver.resolve_dependencies.return_value = mock_dependencies
        
        # Mock get task response
        mock_response = Mock()
        mock_response.to_dict.return_value = {"id": "task123", "title": "Test Task"}
        facade._await_if_coroutine = Mock(return_value=mock_response)
        
        result = facade.get_task("task123", include_dependencies=True)
        
        assert result["success"] is True
        assert "task" in result
        # Should have error info instead of dependency relationships
        assert "dependency_relationships_error" in result["task"]

    def test_get_task_with_async_repository(self, facade):
        """Test get task when repository returns coroutine."""
        # Mock task entity
        mock_task = Mock()
        mock_task.id = "task123"
        
        # Mock async find_by_id
        async def async_find_by_id(task_id):
            return mock_task
        
        facade._get_task_use_case._task_repository.find_by_id = Mock(return_value=asyncio.create_task(async_find_by_id(mock_task.id)))
        
        # Mock get task response
        mock_response = Mock()
        mock_response.to_dict.return_value = {"id": "task123", "title": "Test Task"}
        facade._await_if_coroutine = Mock(side_effect=[mock_task, mock_response])
        
        result = facade.get_task("task123")
        
        assert result["success"] is True
        assert result["action"] == "get"
        assert "task" in result
    
    def test_get_task_auto_rule_generation_error(self, facade):
        """Test handling auto rule generation errors."""
        # Mock task entity
        mock_task = Mock()
        mock_task.id = "task123"
        facade._get_task_use_case._task_repository.find_by_id.return_value = mock_task
        
        facade._await_if_coroutine = Mock(side_effect=[
            AutoRuleGenerationError("Rule generation failed"),
            Mock(to_dict=Mock(return_value={"id": "task123"}))
        ])
        
        result = facade.get_task("task123")
        
        assert result["success"] is True
        assert "warning" in result


class TestDeleteTask:
    """Test delete task functionality."""

    def test_delete_task_success(self, facade):
        """Test successful task deletion."""
        facade._delete_task_use_case.execute.return_value = True
        
        result = facade.delete_task("task123")
        
        assert result["success"] is True
        assert result["action"] == "delete"
        assert "deleted successfully" in result["message"]

    def test_delete_task_failure(self, facade):
        """Test failed task deletion."""
        facade._delete_task_use_case.execute.return_value = False
        
        result = facade.delete_task("task123")
        
        assert result["success"] is False
        assert "Failed to delete" in result["error"]

    def test_delete_task_empty_id(self, facade):
        """Test deleting task with empty ID."""
        result = facade.delete_task("")
        
        assert result["success"] is False
        assert "Task ID is required" in result["error"]

    def test_delete_task_not_found(self, facade):
        """Test deleting non-existent task."""
        facade._delete_task_use_case.execute.side_effect = TaskNotFoundError("Task not found")
        
        result = facade.delete_task("nonexistent")
        
        assert result["success"] is False
        assert "Task not found" in result["error"]


class TestCompleteTask:
    """Test complete task functionality."""

    def test_complete_task_success(self, facade):
        """Test successful task completion."""
        mock_result = {
            "success": True,
            "message": "Task completed successfully",
            "context": {}
        }
        facade._complete_task_use_case.execute.return_value = mock_result
        
        result = facade.complete_task("task123", "Completed all requirements")
        
        assert result["success"] is True
        assert result["action"] == "complete"
        assert result["task_id"] == "task123"

    def test_complete_task_with_testing_notes(self, facade):
        """Test task completion with testing notes."""
        mock_result = {
            "success": True,
            "message": "Task completed successfully",
            "context": {}
        }
        facade._complete_task_use_case.execute.return_value = mock_result
        
        result = facade.complete_task("task123", "Completed", "All tests passed")
        
        assert result["success"] is True
        facade._complete_task_use_case.execute.assert_called_once_with(
            "task123",
            completion_summary="Completed",
            testing_notes="All tests passed"
        )

    def test_complete_task_empty_id(self, facade):
        """Test completing task with empty ID."""
        result = facade.complete_task("")
        
        assert result["success"] is False
        assert "Task ID is required" in result["error"]

    def test_complete_task_not_found(self, facade):
        """Test completing non-existent task."""
        facade._complete_task_use_case.execute.side_effect = TaskNotFoundError("Task not found")
        
        result = facade.complete_task("nonexistent")
        
        assert result["success"] is False
        assert "Task not found" in result["error"]

    def test_complete_task_use_case_error(self, facade):
        """Test handling use case execution errors."""
        facade._complete_task_use_case.execute.side_effect = Exception("Use case failed")
        
        result = facade.complete_task("task123")
        
        assert result["success"] is False
        assert "Unexpected error" in result["error"]


class TestListTasks:
    """Test list tasks functionality."""

    @pytest.fixture
    def list_request(self):
        """Create a valid ListTasksRequest."""
        return ListTasksRequest(
            git_branch_id="branch123",
            status="active",
            limit=10
        )

    def test_list_tasks_success(self, facade, list_request):
        """Test successful task listing."""
        # Mock use case response
        mock_response = Mock()
        mock_response.tasks = [
            Mock(id="task1", to_dict=Mock(return_value={"id": "task1"})),
            Mock(id="task2", to_dict=Mock(return_value={"id": "task2"}))
        ]
        mock_response.count = 2
        mock_response.filters_applied = {"status": "active"}
        facade._list_tasks_use_case.execute.return_value = mock_response
        
        result = facade.list_tasks(list_request, minimal=False)
        
        assert result["success"] is True
        assert result["action"] == "list"
        assert len(result["tasks"]) == 2
        assert result["count"] == 2

    def test_list_tasks_minimal(self, facade, list_request):
        """Test listing tasks with minimal data."""
        # Mock use case response
        mock_task = Mock()
        mock_task.id = "task1"
        mock_task.title = "Test Task"
        mock_task.status = "active"
        mock_task.created_at = Mock()
        mock_task.updated_at = Mock()
        mock_task.dependencies = []
        
        mock_response = Mock()
        mock_response.tasks = [mock_task]
        mock_response.count = 1
        mock_response.filters_applied = {}
        facade._list_tasks_use_case.execute.return_value = mock_response
        
        with patch('fastmcp.task_management.application.facades.task_application_facade.TaskListItemResponse') as mock_dto:
            mock_dto.from_task_response.return_value.to_dict.return_value = {"id": "task1", "title": "Test Task"}
            
            result = facade.list_tasks(list_request, minimal=True)
            
            assert result["success"] is True
            assert result["minimal"] is True

    @patch('fastmcp.task_management.application.facades.task_application_facade.PerformanceConfig')
    def test_list_tasks_performance_mode(self, mock_perf_config, facade, list_request):
        """Test listing tasks in performance mode."""
        mock_perf_config.is_performance_mode.return_value = True
        
        with patch('fastmcp.task_management.application.facades.task_application_facade.OptimizedTaskRepository') as mock_repo:
            mock_repo.return_value.list_tasks_minimal.return_value = [
                {"id": "task1", "title": "Task 1"},
                {"id": "task2", "title": "Task 2"}
            ]
            
            result = facade.list_tasks(list_request, minimal=True)
            
            assert result["success"] is True
            assert result["performance_mode"] is True
            assert len(result["tasks"]) == 2

    def test_list_tasks_with_dependencies(self, facade, list_request):
        """Test listing tasks with dependency information."""
        # Mock task
        mock_task = Mock()
        mock_task.id = "task1"
        mock_task.to_dict.return_value = {"id": "task1"}
        mock_task.dependencies = ["dep1"]
        
        # Mock response
        mock_response = Mock()
        mock_response.tasks = [mock_task]
        mock_response.count = 1
        mock_response.filters_applied = {}
        facade._list_tasks_use_case.execute.return_value = mock_response
        
        # Mock dependency resolver
        facade._dependency_resolver = Mock()
        mock_dependencies = Mock()
        mock_dependencies.total_dependencies = 1
        mock_dependencies.completed_dependencies = 0
        mock_dependencies.can_start = False
        mock_dependencies.is_blocked = True
        mock_dependencies.is_blocking_others = False
        mock_dependencies.dependency_completion_percentage = 0.0
        mock_dependencies.dependency_summary = "Blocked on dependencies"
        mock_dependencies.blocking_reasons = ["Waiting for task A"]
        facade._dependency_resolver.resolve_dependencies.return_value = mock_dependencies
        
        result = facade.list_tasks(list_request, include_dependencies=True, minimal=False)
        
        assert result["success"] is True
        assert "dependency_summary" in result["tasks"][0]
    
    def test_list_tasks_with_context(self, facade, list_request):
        """Test listing tasks with context information."""
        # Mock task
        mock_task = Mock()
        mock_task.id = "task1"
        mock_task.to_dict.return_value = {"id": "task1"}
        mock_task.dependencies = []
        mock_task.title = "Test Task"
        mock_task.status = "active"
        mock_task.created_at = Mock()
        mock_task.updated_at = Mock()
        
        # Mock response
        mock_response = Mock()
        mock_response.tasks = [mock_task]
        mock_response.count = 1
        mock_response.filters_applied = {}
        facade._list_tasks_use_case.execute.return_value = mock_response
        
        # Mock add_context_to_task
        facade._add_context_to_task = Mock(return_value={
            "id": "task1",
            "context_data": {"test": "context"},
            "context_available": True
        })
        
        result = facade.list_tasks(list_request, include_context=True, minimal=False)
        
        assert result["success"] is True
        facade._add_context_to_task.assert_called_once()
    
    @patch('fastmcp.task_management.application.facades.task_application_facade.PerformanceConfig')
    @patch('fastmcp.task_management.application.facades.task_application_facade.OptimizedTaskRepository')
    def test_list_tasks_performance_mode_with_dependencies(self, mock_repo_class, mock_perf_config, facade, list_request):
        """Test listing tasks in performance mode with dependencies."""
        mock_perf_config.is_performance_mode.return_value = True
        
        # Mock optimized repository
        mock_repo = mock_repo_class.return_value
        mock_repo.list_tasks_minimal.return_value = [
            {"id": "task1", "title": "Task 1", "is_blocked": False},
            {"id": "task2", "title": "Task 2", "is_blocked": False}
        ]
        
        # Mock dependency resolver
        facade._dependency_resolver = Mock()
        mock_dependencies = Mock()
        mock_dependencies.is_blocked = True
        facade._dependency_resolver.resolve_dependencies.return_value = mock_dependencies
        
        result = facade.list_tasks(list_request, include_dependencies=True, minimal=True)
        
        assert result["success"] is True
        assert result["performance_mode"] is True
        # Should have called dependency resolver for each task
        assert facade._dependency_resolver.resolve_dependencies.call_count == 2
        # Tasks should have is_blocked updated
        assert result["tasks"][0]["is_blocked"] is True
        assert result["tasks"][1]["is_blocked"] is True

    def test_list_tasks_exception(self, facade, list_request):
        """Test handling exceptions in list tasks."""
        facade._list_tasks_use_case.execute.side_effect = Exception("Database error")
        
        result = facade.list_tasks(list_request)
        
        assert result["success"] is False
        assert "Unexpected error" in result["error"]


class TestSearchTasks:
    """Test search tasks functionality."""

    @pytest.fixture
    def search_request(self):
        """Create a valid SearchTasksRequest."""
        return SearchTasksRequest(
            query="test search",
            git_branch_id="branch123"
        )

    def test_search_tasks_success(self, facade, search_request):
        """Test successful task search."""
        # Mock use case response
        mock_response = Mock()
        mock_response.tasks = [
            Mock(to_dict=Mock(return_value={"id": "task1", "title": "Test Task 1"}))
        ]
        mock_response.count = 1
        mock_response.query = "test search"
        facade._search_tasks_use_case.execute.return_value = mock_response
        
        result = facade.search_tasks(search_request)
        
        assert result["success"] is True
        assert result["action"] == "search"
        assert result["query"] == "test search"
        assert len(result["tasks"]) == 1

    def test_search_tasks_empty_query(self, facade):
        """Test search with empty query."""
        invalid_request = SearchTasksRequest(query="", git_branch_id="branch123")
        
        result = facade.search_tasks(invalid_request)
        
        assert result["success"] is False
        assert "Search query is required" in result["error"]

    def test_search_tasks_with_context(self, facade, search_request):
        """Test search tasks with context data."""
        # Mock use case response
        mock_task = Mock()
        mock_task.to_dict.return_value = {"id": "task1", "title": "Test Task"}
        
        mock_response = Mock()
        mock_response.tasks = [mock_task]
        mock_response.count = 1
        mock_response.query = "test search"
        facade._search_tasks_use_case.execute.return_value = mock_response
        
        # Mock _add_context_to_task method
        facade._add_context_to_task = Mock(return_value={"id": "task1", "context_data": {}})
        
        result = facade.search_tasks(search_request, include_context=True)
        
        assert result["success"] is True
        facade._add_context_to_task.assert_called_once()


class TestGetNextTask:
    """Test get next task functionality."""

    @pytest.mark.asyncio
    async def test_get_next_task_success(self, facade):
        """Test successful next task retrieval."""
        # Mock next task response
        mock_response = Mock()
        mock_response.has_next = True
        mock_response.next_item = {"id": "task123", "title": "Next Task"}
        mock_response.context = {}
        mock_response.context_info = "Context information"
        mock_response.message = "Found next task"
        
        facade._do_next_use_case.execute = AsyncMock(return_value=mock_response)
        
        result = await facade.get_next_task(
            user_id="user123",
            project_id="project456",
            git_branch_id="branch789"
        )
        
        assert result["success"] is True
        assert result["action"] == "next"
        assert result["task"]["has_next"] is True

    @pytest.mark.asyncio
    async def test_get_next_task_no_tasks(self, facade):
        """Test next task when no tasks available."""
        facade._do_next_use_case.execute = AsyncMock(return_value=None)
        
        result = await facade.get_next_task()
        
        assert result["success"] is False
        assert "No tasks found" in result["message"]

    @pytest.mark.asyncio
    async def test_get_next_task_exception(self, facade):
        """Test handling exceptions in next task."""
        facade._do_next_use_case.execute = AsyncMock(side_effect=Exception("Service error"))
        
        result = await facade.get_next_task()
        
        assert result["success"] is False
        assert "Unexpected error" in result["error"]


class TestDependencyManagement:
    """Test dependency management functionality."""

    def test_add_dependency_success(self, facade, mock_task_repository):
        """Test successful dependency addition."""
        # Mock tasks
        mock_task = Mock()
        mock_task.add_dependency = Mock()
        mock_task.to_dict.return_value = {"id": "task123"}
        
        mock_dependency = Mock()
        mock_dependency.id = "dep123"
        
        mock_task_repository.find_by_id.side_effect = [mock_task, mock_dependency]
        mock_task_repository.save.return_value = mock_task
        
        result = facade.add_dependency("task123", "dep123")
        
        assert result["success"] is True
        mock_task.add_dependency.assert_called_once()

    def test_add_dependency_empty_ids(self, facade):
        """Test adding dependency with empty IDs."""
        result = facade.add_dependency("", "dep123")
        
        assert result["success"] is True
        assert "No-op" in result["message"]

    def test_add_dependency_task_not_found(self, facade, mock_task_repository):
        """Test adding dependency when task not found."""
        mock_task_repository.find_by_id.return_value = None
        
        result = facade.add_dependency("nonexistent", "dep123")
        
        assert result["success"] is False
        assert "not found" in result["error"]

    def test_add_dependency_circular(self, facade, mock_task_repository):
        """Test adding circular dependency."""
        mock_task = Mock()
        mock_task.add_dependency.side_effect = ValueError("cannot depend on itself")
        
        mock_dependency = Mock()
        mock_dependency.id = "dep123"
        
        mock_task_repository.find_by_id.side_effect = [mock_task, mock_dependency]
        
        result = facade.add_dependency("task123", "dep123")
        
        assert result["success"] is False

    def test_remove_dependency_success(self, facade, mock_task_repository):
        """Test successful dependency removal."""
        mock_task = Mock()
        mock_task.remove_dependency = Mock()
        mock_task.to_dict.return_value = {"id": "task123"}
        
        mock_task_repository.find_by_id.return_value = mock_task
        mock_task_repository.save.return_value = mock_task
        
        result = facade.remove_dependency("task123", "dep123")
        
        assert result["success"] is True
        mock_task.remove_dependency.assert_called_once()

    def test_remove_dependency_empty_ids(self, facade):
        """Test removing dependency with empty IDs."""
        result = facade.remove_dependency("", "dep123")
        
        assert result["success"] is False
        assert "cannot be empty" in result["error"]


class TestHelperMethods:
    """Test helper methods."""

    def test_await_if_coroutine_regular_value(self, facade):
        """Test _await_if_coroutine with regular value."""
        result = facade._await_if_coroutine("test_value")
        assert result == "test_value"

    def test_await_if_coroutine_with_coroutine(self, facade):
        """Test _await_if_coroutine with coroutine."""
        async def async_func():
            return "async_result"
        
        # Create coroutine
        coro = async_func()
        
        result = facade._await_if_coroutine(coro)
        assert result == "async_result"
    
    def test_await_if_coroutine_with_exception(self, facade):
        """Test _await_if_coroutine with coroutine that raises exception."""
        async def async_func_with_error():
            raise ValueError("Async error")
        
        # Create coroutine
        coro = async_func_with_error()
        
        with pytest.raises(ValueError, match="Async error"):
            facade._await_if_coroutine(coro)

    def test_count_tasks(self, facade):
        """Test count tasks functionality."""
        # Mock use case response
        mock_response = Mock()
        mock_response.count = 5
        facade._list_tasks_use_case.execute.return_value = mock_response
        
        filters = {"status": "active", "git_branch_id": "branch123"}
        result = facade.count_tasks(filters)
        
        assert result["success"] is True
        assert result["count"] == 5

    def test_count_tasks_error(self, facade):
        """Test count tasks with error."""
        facade._list_tasks_use_case.execute.side_effect = Exception("Database error")
        
        result = facade.count_tasks({})
        
        assert result["success"] is False
        assert result["count"] == 0

    def test_list_tasks_summary(self, facade):
        """Test list tasks summary functionality."""
        # Mock task
        mock_task = Mock()
        mock_task.id = "task1"
        mock_task.title = "Test Task"
        mock_task.status = "active"
        mock_task.priority = "high"
        mock_task.created_at.isoformat.return_value = "2024-01-01T00:00:00Z"
        mock_task.updated_at.isoformat.return_value = "2024-01-01T00:00:00Z"
        mock_task.subtasks = []
        mock_task.assignees = []
        mock_task.dependencies = []
        
        # Mock response
        mock_response = Mock()
        mock_response.tasks = [mock_task]
        mock_response.count = 1
        facade._list_tasks_use_case.execute.return_value = mock_response
        
        filters = {"status": "active"}
        result = facade.list_tasks_summary(filters, offset=0, limit=10)
        
        assert result["success"] is True
        assert len(result["tasks"]) == 1
        assert result["tasks"][0]["id"] == "task1"

    def test_list_subtasks_summary(self, facade, mock_subtask_repository):
        """Test list subtasks summary functionality."""
        # Mock subtask
        mock_subtask = Mock()
        mock_subtask.id.value = "subtask1"
        mock_subtask.title = "Test Subtask"
        mock_subtask.status.value = "active"
        mock_subtask.priority.value = "medium"
        mock_subtask.progress_percentage = 50
        mock_subtask.assignees = []
        
        mock_subtask_repository.find_by_parent_task_id.return_value = [mock_subtask]
        facade._subtask_repository = mock_subtask_repository
        
        result = facade.list_subtasks_summary("task123")
        
        assert result["success"] is True
        assert len(result["subtasks"]) == 1
        assert result["subtasks"][0]["id"] == "subtask1"

    def test_list_subtasks_summary_no_repo(self, facade):
        """Test list subtasks summary without subtask repository."""
        facade._subtask_repository = None
        
        result = facade.list_subtasks_summary("task123")
        
        assert result["success"] is False
        assert "not configured" in result["error"]


class TestContextIntegration:
    """Test context integration functionality."""

    @patch('fastmcp.task_management.application.facades.task_application_facade.ProjectManagementService')
    def test_derive_context_from_git_branch_id(self, mock_project_service, facade, mock_git_branch_repository):
        """Test deriving context from git branch ID."""
        # Mock git branch repository find_by_id returns None
        mock_git_branch_repository.find_by_id = AsyncMock(return_value=None)
        
        # Mock project management service fallback
        mock_service_instance = mock_project_service.return_value
        mock_service_instance.get_git_branch_by_id.return_value = {
            "success": True,
            "git_branch": {
                "project_id": "project123",
                "name": "feature-branch"
            }
        }
        
        result = facade._await_if_coroutine(
            facade._derive_context_from_git_branch_id("branch123")
        )
        
        assert result["project_id"] == "project123"
        assert result["git_branch_name"] == "feature-branch"
    
    def test_derive_context_from_git_branch_repository(self, facade, mock_git_branch_repository):
        """Test deriving context from git branch repository directly."""
        # Mock git branch entity
        mock_branch = Mock()
        mock_branch.project_id = "project456"
        mock_branch.name = "main"
        
        mock_git_branch_repository.find_by_id = AsyncMock(return_value=mock_branch)
        
        result = facade._await_if_coroutine(
            facade._derive_context_from_git_branch_id("branch123")
        )
        
        assert result["project_id"] == "project456"
        assert result["git_branch_name"] == "main"
    
    def test_derive_context_with_exception(self, facade, mock_git_branch_repository):
        """Test deriving context when exception occurs."""
        # Mock exception
        mock_git_branch_repository.find_by_id = Mock(side_effect=Exception("Database error"))
        
        result = facade._await_if_coroutine(
            facade._derive_context_from_git_branch_id("branch123")
        )
        
        assert result["project_id"] is None
        assert result["git_branch_name"] is None

    def test_add_context_to_task(self, facade):
        """Test adding context to task dictionary."""
        # Mock get_task method
        facade.get_task = Mock(return_value={
            "success": True,
            "task": {
                "id": "task123",
                "context_data": {"test": "data"},
                "context_available": True
            }
        })
        
        task_dict = {"id": "task123", "title": "Test Task"}
        result = facade._add_context_to_task(task_dict, "task123")
        
        assert result["context_data"]["test"] == "data"
        assert result["context_available"] is True


class TestErrorHandling:
    """Test error handling scenarios."""

    @patch('fastmcp.task_management.domain.constants.validate_user_id')
    def test_validation_error_handling(self, mock_validate_user, facade):
        """Test validation error handling in facade methods."""
        # Mock authentication to pass and focus on validation
        mock_validate_user.return_value = "user123"
        
        # Test with various invalid inputs
        invalid_request = CreateTaskRequest(title="x" * 201, git_branch_id="branch123")
        invalid_request.user_id = "user123"  # Add user_id for auth
        result = facade.create_task(invalid_request)
        
        assert result["success"] is False
        assert result["action"] == "create"
        assert "error" in result
        assert "200 characters" in result["error"]

    def test_exception_propagation(self, facade):
        """Test proper exception propagation in facade methods."""
        facade._create_task_use_case.execute.side_effect = Exception("Unexpected error")
        
        request = CreateTaskRequest(title="Test", git_branch_id="branch123")
        
        with patch('fastmcp.auth.middleware.request_context_middleware.get_current_user_id') as mock_get_user, \
             patch('fastmcp.task_management.application.facades.task_application_facade.validate_user_id') as mock_validate:
            mock_get_user.return_value = "user123"
            mock_validate.return_value = "user123"
            
            result = facade.create_task(request)
            
            assert result["success"] is False
            assert "Unexpected error" in result["error"]

    def test_logging_on_errors(self, facade):
        """Test that errors are logged appropriately."""
        with patch('fastmcp.task_management.application.facades.task_application_facade.logger') as mock_logger:
            facade._delete_task_use_case.execute.side_effect = Exception("Database error")
            
            facade.delete_task("task123")
            
            mock_logger.error.assert_called()


class TestDependencyUseCase:
    """Test dependency management use case functionality."""

    def test_get_dependencies(self, facade):
        """Test getting dependencies through use case."""
        # Mock manage dependencies use case
        facade._manage_dependencies_use_case = Mock()
        facade._manage_dependencies_use_case.get_dependencies.return_value = {
            "dependencies": [
                {"id": "dep1", "title": "Dependency 1", "status": "completed"},
                {"id": "dep2", "title": "Dependency 2", "status": "in_progress"}
            ],
            "dependency_ids": ["dep1", "dep2"],
            "can_start": False
        }
        
        result = facade.get_dependencies("task123")
        
        assert result["success"] is True
        assert result["action"] == "get_dependencies"
        assert len(result["dependencies"]) == 2
        assert result["can_start"] is False

    def test_clear_dependencies(self, facade):
        """Test clearing dependencies through use case."""
        # Mock manage dependencies use case
        facade._manage_dependencies_use_case = Mock()
        mock_response = Mock()
        mock_response.success = True
        mock_response.task_id = "task123"
        mock_response.message = "Cleared 3 dependencies"
        facade._manage_dependencies_use_case.clear_dependencies.return_value = mock_response
        
        result = facade.clear_dependencies("task123")
        
        assert result["success"] is True
        assert result["action"] == "clear_dependencies"
        assert result["dependencies_cleared"] == "3"

    def test_get_blocking_tasks(self, facade):
        """Test getting blocking tasks through use case."""
        # Mock manage dependencies use case
        facade._manage_dependencies_use_case = Mock()
        facade._manage_dependencies_use_case.get_blocking_tasks.return_value = {
            "task_id": "task123",
            "blocking_tasks": [
                {"id": "blocked1", "title": "Blocked Task 1"},
                {"id": "blocked2", "title": "Blocked Task 2"}
            ],
            "blocking_count": 2
        }
        
        result = facade.get_blocking_tasks("task123")
        
        assert result["success"] is True
        assert result["action"] == "get_blocking_tasks"
        assert result["blocking_count"] == 2
        assert len(result["blocking_tasks"]) == 2