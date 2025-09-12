"""Comprehensive tests for TaskApplicationService."""

import pytest
from unittest.mock import Mock, AsyncMock, MagicMock, patch
from typing import Optional, Any
import uuid

# Mock imports before importing the service
import sys
from unittest.mock import MagicMock

# Mock all the use case modules
mock_modules = [
    'fastmcp.task_management.application.use_cases.create_task',
    'fastmcp.task_management.application.use_cases.get_task',
    'fastmcp.task_management.application.use_cases.update_task',
    'fastmcp.task_management.application.use_cases.list_tasks',
    'fastmcp.task_management.application.use_cases.search_tasks',
    'fastmcp.task_management.application.use_cases.delete_task',
    'fastmcp.task_management.application.use_cases.complete_task',
    'fastmcp.task_management.application.services.unified_context_service',
    'fastmcp.task_management.application.services.facade_service'
]

for module in mock_modules:
    sys.modules[module] = MagicMock()

from fastmcp.task_management.application.services.task_application_service import TaskApplicationService
from fastmcp.task_management.application.dtos.task import (
    CreateTaskRequest,
    CreateTaskResponse,
    TaskResponse,
    UpdateTaskRequest,
    ListTasksRequest,
    TaskListResponse,
    SearchTasksRequest
)
from fastmcp.task_management.domain.exceptions.task_exceptions import TaskNotFoundError
from fastmcp.task_management.domain.repositories.task_repository import TaskRepository


class TestTaskApplicationService:
    """Test cases for TaskApplicationService."""

    @pytest.fixture
    def mock_task_repository(self):
        """Create mock task repository."""
        return Mock(spec=TaskRepository)

    @pytest.fixture
    def mock_context_service(self):
        """Create mock context service."""
        return Mock()

    @pytest.fixture
    def user_id(self):
        """Test user ID."""
        return "test-user-123"

    @pytest.fixture
    def sample_task_data(self):
        """Sample task data for testing."""
        return {
            'title': 'Test Task',
            'description': 'Test Description',
            'git_branch_id': str(uuid.uuid4()),
            'status': 'todo',
            'priority': 'medium',
            'assignees': ['user1', 'user2'],
            'labels': ['backend', 'urgent'],
            'estimated_effort': '2 hours',
            'due_date': None
        }

    @pytest.fixture
    def mock_task_entity(self, sample_task_data):
        """Create mock task entity."""
        task = Mock()
        task.id = Mock()
        task.id.value = str(uuid.uuid4())
        task.title = sample_task_data['title']
        task.description = sample_task_data['description']
        task.status = Mock()
        task.status.value = sample_task_data['status']
        task.priority = Mock()
        task.priority.value = sample_task_data['priority']
        task.assignees = sample_task_data['assignees']
        task.labels = sample_task_data['labels']
        task.estimated_effort = sample_task_data['estimated_effort']
        task.due_date = sample_task_data['due_date']
        return task

    def test_init_with_all_parameters(self, mock_task_repository, mock_context_service, user_id):
        """Test TaskApplicationService initialization with all parameters."""
        service = TaskApplicationService(
            task_repository=mock_task_repository,
            context_service=mock_context_service,
            user_id=user_id
        )
        
        assert service._task_repository == mock_task_repository
        assert service._context_service == mock_context_service
        assert service._user_id == user_id
        assert service._hierarchical_context_service is not None

    def test_init_minimal_parameters(self, mock_task_repository):
        """Test TaskApplicationService initialization with minimal parameters."""
        service = TaskApplicationService(task_repository=mock_task_repository)
        
        assert service._task_repository == mock_task_repository
        assert service._context_service is None
        assert service._user_id is None

    def test_get_user_scoped_repository_with_with_user_method(self, mock_task_repository, user_id):
        """Test _get_user_scoped_repository when repository supports with_user method."""
        mock_scoped_repo = Mock()
        mock_task_repository.with_user.return_value = mock_scoped_repo
        
        service = TaskApplicationService(mock_task_repository, user_id=user_id)
        result = service._get_user_scoped_repository()
        
        assert result == mock_scoped_repo
        mock_task_repository.with_user.assert_called_once_with(user_id)

    def test_get_user_scoped_repository_with_user_id_property(self, user_id):
        """Test _get_user_scoped_repository when repository has user_id property."""
        mock_task_repository = Mock()
        mock_task_repository.user_id = "different-user"
        mock_task_repository.session = Mock()
        
        service = TaskApplicationService(mock_task_repository, user_id=user_id)
        
        # Mock the repository class constructor
        mock_repo_class = Mock()
        mock_new_repo = Mock()
        mock_repo_class.return_value = mock_new_repo
        
        with patch('builtins.type', return_value=mock_repo_class):
            result = service._get_user_scoped_repository()
            
            mock_repo_class.assert_called_once_with(mock_task_repository.session, user_id=user_id)
            assert result == mock_new_repo

    def test_get_user_scoped_repository_fallback(self, mock_task_repository, user_id):
        """Test _get_user_scoped_repository fallback when no scoping available."""
        # Remove with_user and user_id attributes
        if hasattr(mock_task_repository, 'with_user'):
            delattr(mock_task_repository, 'with_user')
        if hasattr(mock_task_repository, 'user_id'):
            delattr(mock_task_repository, 'user_id')
        
        service = TaskApplicationService(mock_task_repository, user_id=user_id)
        result = service._get_user_scoped_repository()
        
        assert result == mock_task_repository

    def test_with_user(self, mock_task_repository, mock_context_service, user_id):
        """Test with_user method creates new service instance."""
        service = TaskApplicationService(mock_task_repository, mock_context_service)
        
        new_user_id = "new-user-456"
        new_service = service.with_user(new_user_id)
        
        assert isinstance(new_service, TaskApplicationService)
        assert new_service._user_id == new_user_id
        assert new_service._task_repository == mock_task_repository
        assert new_service._context_service == mock_context_service

    async def test_create_task_success(self, mock_task_repository, mock_context_service, user_id, mock_task_entity, sample_task_data):
        """Test successful task creation with context creation."""
        service = TaskApplicationService(
            task_repository=mock_task_repository,
            context_service=mock_context_service,
            user_id=user_id
        )
        
        # Arrange
        request = CreateTaskRequest(**sample_task_data)
        response = CreateTaskResponse(success=True, task=mock_task_entity)
        
        service._create_task_use_case.execute.return_value = response
        
        # Act
        result = await service.create_task(request)
        
        # Assert
        assert result == response
        service._create_task_use_case.execute.assert_called_once_with(request)
        service._hierarchical_context_service.create_context.assert_called_once()

    async def test_create_task_without_success_flag(self, mock_task_repository, mock_context_service, user_id, sample_task_data):
        """Test task creation when response doesn't have success flag."""
        service = TaskApplicationService(
            task_repository=mock_task_repository,
            context_service=mock_context_service,
            user_id=user_id
        )
        
        # Arrange
        request = CreateTaskRequest(**sample_task_data)
        response = Mock()  # Response without success attribute
        
        service._create_task_use_case.execute.return_value = response
        
        # Act
        result = await service.create_task(request)
        
        # Assert
        assert result == response
        service._hierarchical_context_service.create_context.assert_not_called()

    async def test_get_task_success(self, mock_task_repository, mock_context_service, user_id):
        """Test successful task retrieval."""
        service = TaskApplicationService(
            task_repository=mock_task_repository,
            context_service=mock_context_service,
            user_id=user_id
        )
        
        # Arrange
        task_id = "test-task-123"
        expected_response = TaskResponse(id=task_id)
        service._get_task_use_case.execute = AsyncMock(return_value=expected_response)
        
        # Act
        result = await service.get_task(
            task_id=task_id,
            generate_rules=True,
            force_full_generation=False,
            include_context=True
        )
        
        # Assert
        assert result == expected_response
        service._get_task_use_case.execute.assert_called_once_with(
            task_id,
            generate_rules=True,
            force_full_generation=False,
            include_context=True
        )

    async def test_get_task_not_found(self, mock_task_repository, mock_context_service, user_id):
        """Test task retrieval when task not found."""
        service = TaskApplicationService(
            task_repository=mock_task_repository,
            context_service=mock_context_service,
            user_id=user_id
        )
        
        # Arrange
        task_id = "nonexistent-task"
        service._get_task_use_case.execute = AsyncMock(side_effect=TaskNotFoundError("Task not found"))
        
        # Act
        result = await service.get_task(task_id)
        
        # Assert
        assert result is None

    async def test_update_task_success(self, mock_task_repository, mock_context_service, user_id, mock_task_entity, sample_task_data):
        """Test successful task update with context update."""
        service = TaskApplicationService(
            task_repository=mock_task_repository,
            context_service=mock_context_service,
            user_id=user_id
        )
        
        # Arrange
        task_id = str(uuid.uuid4())
        request = UpdateTaskRequest(task_id=task_id, title="Updated Title")
        response = Mock()
        response.success = True
        response.task = mock_task_entity
        
        service._update_task_use_case.execute.return_value = response
        
        # Act
        result = await service.update_task(request)
        
        # Assert
        assert result == response
        service._update_task_use_case.execute.assert_called_once_with(request)
        service._hierarchical_context_service.update_context.assert_called_once()

    async def test_update_task_without_success_flag(self, mock_task_repository, mock_context_service, user_id):
        """Test task update when response doesn't have success flag."""
        service = TaskApplicationService(
            task_repository=mock_task_repository,
            context_service=mock_context_service,
            user_id=user_id
        )
        
        # Arrange
        request = UpdateTaskRequest(task_id="test-id", title="Test")
        response = Mock()  # Response without success attribute
        
        service._update_task_use_case.execute.return_value = response
        
        # Act
        result = await service.update_task(request)
        
        # Assert
        assert result == response
        service._hierarchical_context_service.update_context.assert_not_called()

    async def test_list_tasks(self, mock_task_repository, mock_context_service, user_id):
        """Test task listing."""
        service = TaskApplicationService(
            task_repository=mock_task_repository,
            context_service=mock_context_service,
            user_id=user_id
        )
        
        # Arrange
        request = ListTasksRequest(status="todo")
        expected_response = TaskListResponse(tasks=[])
        service._list_tasks_use_case.execute = AsyncMock(return_value=expected_response)
        
        # Act
        result = await service.list_tasks(request)
        
        # Assert
        assert result == expected_response
        service._list_tasks_use_case.execute.assert_called_once_with(request)

    async def test_search_tasks(self, mock_task_repository, mock_context_service, user_id):
        """Test task searching."""
        service = TaskApplicationService(
            task_repository=mock_task_repository,
            context_service=mock_context_service,
            user_id=user_id
        )
        
        # Arrange
        request = SearchTasksRequest(query="test query")
        expected_response = TaskListResponse(tasks=[])
        service._search_tasks_use_case.execute = AsyncMock(return_value=expected_response)
        
        # Act
        result = await service.search_tasks(request)
        
        # Assert
        assert result == expected_response
        service._search_tasks_use_case.execute.assert_called_once_with(request)

    async def test_delete_task_success(self, mock_task_repository, mock_context_service, user_id):
        """Test successful task deletion with context cleanup."""
        service = TaskApplicationService(
            task_repository=mock_task_repository,
            context_service=mock_context_service,
            user_id=user_id
        )
        
        # Arrange
        task_id = "test-task-123"
        user_id = "test-user"
        service._delete_task_use_case.execute.return_value = True
        
        # Act
        result = await service.delete_task(task_id, user_id)
        
        # Assert
        assert result is True
        service._delete_task_use_case.execute.assert_called_once_with(task_id)
        service._hierarchical_context_service.delete_context.assert_called_once_with("task", task_id)

    async def test_delete_task_failure(self, mock_task_repository, mock_context_service, user_id):
        """Test task deletion failure without context cleanup."""
        service = TaskApplicationService(
            task_repository=mock_task_repository,
            context_service=mock_context_service,
            user_id=user_id
        )
        
        # Arrange
        task_id = "test-task-123"
        user_id = "test-user"
        service._delete_task_use_case.execute.return_value = False
        
        # Act
        result = await service.delete_task(task_id, user_id)
        
        # Assert
        assert result is False
        service._delete_task_use_case.execute.assert_called_once_with(task_id)
        service._hierarchical_context_service.delete_context.assert_not_called()

    async def test_complete_task(self, mock_task_repository, mock_context_service, user_id):
        """Test task completion."""
        service = TaskApplicationService(
            task_repository=mock_task_repository,
            context_service=mock_context_service,
            user_id=user_id
        )
        
        # Arrange
        task_id = "test-task-123"
        expected_result = {"status": "completed"}
        service._complete_task_use_case.execute = AsyncMock(return_value=expected_result)
        
        # Act
        result = await service.complete_task(task_id)
        
        # Assert
        assert result == expected_result
        service._complete_task_use_case.execute.assert_called_once_with(task_id)

    async def test_get_all_tasks(self, mock_task_repository, mock_context_service, user_id):
        """Test getting all tasks."""
        service = TaskApplicationService(
            task_repository=mock_task_repository,
            context_service=mock_context_service,
            user_id=user_id
        )
        
        # Arrange
        expected_response = TaskListResponse(tasks=[])
        service._list_tasks_use_case.execute = AsyncMock(return_value=expected_response)
        
        # Act
        result = await service.get_all_tasks()
        
        # Assert
        assert result == expected_response
        service._list_tasks_use_case.execute.assert_called_once()
        call_args = service._list_tasks_use_case.execute.call_args[0][0]
        assert isinstance(call_args, ListTasksRequest)

    async def test_get_tasks_by_status(self, mock_task_repository, mock_context_service, user_id):
        """Test getting tasks by status."""
        service = TaskApplicationService(
            task_repository=mock_task_repository,
            context_service=mock_context_service,
            user_id=user_id
        )
        
        # Arrange
        status = "in_progress"
        expected_response = TaskListResponse(tasks=[])
        service._list_tasks_use_case.execute = AsyncMock(return_value=expected_response)
        
        # Act
        result = await service.get_tasks_by_status(status)
        
        # Assert
        assert result == expected_response
        service._list_tasks_use_case.execute.assert_called_once()
        call_args = service._list_tasks_use_case.execute.call_args[0][0]
        assert isinstance(call_args, ListTasksRequest)
        assert call_args.status == status

    async def test_get_tasks_by_assignee(self, mock_task_repository, mock_context_service, user_id):
        """Test getting tasks by assignee."""
        service = TaskApplicationService(
            task_repository=mock_task_repository,
            context_service=mock_context_service,
            user_id=user_id
        )
        
        # Arrange
        assignee = "test-user"
        expected_response = TaskListResponse(tasks=[])
        service._list_tasks_use_case.execute = AsyncMock(return_value=expected_response)
        
        # Act
        result = await service.get_tasks_by_assignee(assignee)
        
        # Assert
        assert result == expected_response
        service._list_tasks_use_case.execute.assert_called_once()
        call_args = service._list_tasks_use_case.execute.call_args[0][0]
        assert isinstance(call_args, ListTasksRequest)
        assert call_args.assignees == [assignee]

    def test_use_case_initialization(self, mock_task_repository, mock_context_service, user_id):
        """Test that all use cases are properly initialized."""
        service = TaskApplicationService(
            task_repository=mock_task_repository,
            context_service=mock_context_service,
            user_id=user_id
        )
        
        # Check that all use cases are initialized
        assert service._create_task_use_case is not None
        assert service._get_task_use_case is not None
        assert service._update_task_use_case is not None
        assert service._list_tasks_use_case is not None
        assert service._search_tasks_use_case is not None
        assert service._delete_task_use_case is not None
        assert service._complete_task_use_case is not None

    async def test_create_task_with_entity_without_value_attributes(self, mock_task_repository, mock_context_service, user_id, sample_task_data):
        """Test task creation when entity attributes don't have .value property."""
        service = TaskApplicationService(
            task_repository=mock_task_repository,
            context_service=mock_context_service,
            user_id=user_id
        )
        
        # Arrange
        request = CreateTaskRequest(**sample_task_data)
        
        # Create mock task without .value attributes
        mock_task = Mock()
        mock_task.id = str(uuid.uuid4())  # Direct value, no .value attribute
        mock_task.title = sample_task_data['title']
        mock_task.description = sample_task_data['description']
        mock_task.status = sample_task_data['status']  # Direct value, no .value attribute
        mock_task.priority = sample_task_data['priority']  # Direct value, no .value attribute
        mock_task.assignees = sample_task_data['assignees']
        mock_task.labels = sample_task_data['labels']
        mock_task.estimated_effort = sample_task_data['estimated_effort']
        mock_task.due_date = sample_task_data['due_date']
        
        response = CreateTaskResponse(success=True, task=mock_task)
        service._create_task_use_case.execute.return_value = response
        
        # Act
        result = await service.create_task(request)
        
        # Assert
        assert result == response
        service._hierarchical_context_service.create_context.assert_called_once()

    async def test_edge_cases_and_error_handling(self, mock_task_repository, mock_context_service, user_id):
        """Test various edge cases and error handling scenarios."""
        service = TaskApplicationService(
            task_repository=mock_task_repository,
            context_service=mock_context_service,
            user_id=user_id
        )
        
        # Test with None values
        request = CreateTaskRequest(
            title="Test Task",
            git_branch_id=str(uuid.uuid4()),
            description=None,
            status=None,
            assignees=None
        )
        
        # Create response with None task
        response = CreateTaskResponse(success=True, task=None)
        service._create_task_use_case.execute.return_value = response
        
        # Should not crash and not call context creation
        result = await service.create_task(request)
        assert result == response
        service._hierarchical_context_service.create_context.assert_not_called()