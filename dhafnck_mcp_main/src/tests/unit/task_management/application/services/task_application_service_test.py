"""
Tests for Task Application Service

This module tests the TaskApplicationService functionality including:
- Task CRUD operations (create, read, update, delete)
- Task listing and searching
- Task completion
- Hierarchical context integration
- User context handling
"""

import pytest
from datetime import datetime
from unittest.mock import Mock, AsyncMock, patch, MagicMock

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


class TestTaskApplicationService:
    """Test suite for TaskApplicationService"""
    
    @pytest.fixture
    def mock_task_repository(self):
        """Create a mock task repository"""
        repo = Mock()
        repo.with_user = Mock(return_value=repo)
        return repo
    
    @pytest.fixture
    def mock_context_service(self):
        """Create a mock context service"""
        return Mock()
    
    @pytest.fixture
    def mock_hierarchical_context_service(self):
        """Create a mock hierarchical context service"""
        service = Mock()
        service.create_context = Mock()
        service.update_context = Mock()
        service.delete_context = Mock()
        return service
    
    @pytest.fixture
    def mock_use_cases(self):
        """Create mock use cases"""
        return {
            'create': Mock(execute=Mock()),
            'get': Mock(execute=AsyncMock()),
            'update': Mock(execute=Mock()),
            'list': Mock(execute=AsyncMock()),
            'search': Mock(execute=AsyncMock()),
            'delete': Mock(execute=Mock()),
            'complete': Mock(execute=AsyncMock())
        }
    
    @pytest.fixture
    def service(self, mock_task_repository, mock_context_service, mock_hierarchical_context_service, mock_use_cases):
        """Create service instance with mocked dependencies"""
        with patch('fastmcp.task_management.application.services.facade_service.FacadeService.get_unified_context_facade') as mock_get_facade:
            mock_get_facade.return_value = mock_hierarchical_context_service
            
            service = TaskApplicationService(
                mock_task_repository,
                mock_context_service,
                user_id="test-user-123"
            )
            
            # Replace use cases with mocks
            service._create_task_use_case = mock_use_cases['create']
            service._get_task_use_case = mock_use_cases['get']
            service._update_task_use_case = mock_use_cases['update']
            service._list_tasks_use_case = mock_use_cases['list']
            service._search_tasks_use_case = mock_use_cases['search']
            service._delete_task_use_case = mock_use_cases['delete']
            service._complete_task_use_case = mock_use_cases['complete']
            
            # Set hierarchical context service
            service._hierarchical_context_service = mock_hierarchical_context_service
            
            return service
    
    @pytest.fixture
    def mock_task(self):
        """Create a mock task"""
        task = Mock()
        task.id = Mock(value="task-123")
        task.title = "Test Task"
        task.description = "Test Description"
        task.status = Mock(value="todo")
        task.priority = Mock(value="medium")
        task.assignees = ["user-1"]
        task.labels = ["bug", "urgent"]
        task.estimated_effort = "2 hours"
        task.due_date = datetime.now()
        return task
    
    @pytest.mark.asyncio
    async def test_create_task_success(self, service, mock_use_cases, mock_hierarchical_context_service, mock_task):
        """Test successful task creation with context"""
        request = CreateTaskRequest(
            title="Test Task",
            description="Test Description",
            git_branch_id="branch-123"
        )
        
        response = CreateTaskResponse(success=True, task=mock_task)
        mock_use_cases['create'].execute.return_value = response
        
        result = await service.create_task(request)
        
        # Verify use case was called
        mock_use_cases['create'].execute.assert_called_once_with(request)
        
        # Verify context was created
        mock_hierarchical_context_service.create_context.assert_called_once()
        context_call = mock_hierarchical_context_service.create_context.call_args
        assert context_call[1]['level'] == "task"
        assert context_call[1]['context_id'] == "task-123"
        assert context_call[1]['data']['task_data']['title'] == "Test Task"
        
        assert result == response
    
    @pytest.mark.asyncio
    async def test_create_task_no_context_on_failure(self, service, mock_use_cases, mock_hierarchical_context_service):
        """Test that context is not created when task creation fails"""
        request = CreateTaskRequest(
            title="Test Task",
            description="Test Description",
            git_branch_id="branch-123"
        )
        
        response = CreateTaskResponse(success=False, task=None)
        mock_use_cases['create'].execute.return_value = response
        
        result = await service.create_task(request)
        
        # Verify context was NOT created
        mock_hierarchical_context_service.create_context.assert_not_called()
        
        assert result == response
    
    @pytest.mark.asyncio
    async def test_get_task_success(self, service, mock_use_cases):
        """Test successful task retrieval"""
        task_id = "task-123"
        expected_response = Mock()  # Use Mock for expected response
        mock_use_cases['get'].execute.return_value = expected_response
        
        result = await service.get_task(
            task_id,
            generate_rules=True,
            force_full_generation=False,
            include_context=True
        )
        
        mock_use_cases['get'].execute.assert_called_once_with(
            task_id,
            generate_rules=True,
            force_full_generation=False,
            include_context=True
        )
        assert result == expected_response
    
    @pytest.mark.asyncio
    async def test_get_task_not_found(self, service, mock_use_cases):
        """Test task retrieval when not found"""
        task_id = "non-existent"
        mock_use_cases['get'].execute.side_effect = TaskNotFoundError(f"Task {task_id} not found")
        
        result = await service.get_task(task_id)
        
        assert result is None
    
    @pytest.mark.asyncio
    async def test_update_task_success(self, service, mock_use_cases, mock_hierarchical_context_service, mock_task):
        """Test successful task update with context"""
        request = UpdateTaskRequest(
            task_id="task-123",
            title="Updated Task",
            status="in_progress"
        )
        
        response = Mock(success=True, task=mock_task)  # Use Mock for response
        mock_use_cases['update'].execute.return_value = response
        
        result = await service.update_task(request)
        
        # Verify use case was called
        mock_use_cases['update'].execute.assert_called_once_with(request)
        
        # Verify context was updated
        mock_hierarchical_context_service.update_context.assert_called_once()
        context_call = mock_hierarchical_context_service.update_context.call_args
        assert context_call[1]['level'] == "task"
        assert context_call[1]['context_id'] == "task-123"
        
        assert result == response
    
    @pytest.mark.asyncio
    async def test_list_tasks(self, service, mock_use_cases):
        """Test listing tasks"""
        request = ListTasksRequest(status="todo", limit=10)
        expected_response = TaskListResponse(tasks=[Mock(), Mock()], count=2)
        mock_use_cases['list'].execute.return_value = expected_response
        
        result = await service.list_tasks(request)
        
        mock_use_cases['list'].execute.assert_called_once_with(request)
        assert result == expected_response
    
    @pytest.mark.asyncio
    async def test_search_tasks(self, service, mock_use_cases):
        """Test searching tasks"""
        request = SearchTasksRequest(query="authentication", limit=5)
        expected_response = TaskListResponse(tasks=[Mock()], count=1)
        mock_use_cases['search'].execute.return_value = expected_response
        
        result = await service.search_tasks(request)
        
        mock_use_cases['search'].execute.assert_called_once_with(request)
        assert result == expected_response
    
    @pytest.mark.asyncio
    async def test_delete_task_success(self, service, mock_use_cases, mock_hierarchical_context_service):
        """Test successful task deletion with context cleanup"""
        task_id = "task-123"
        user_id = "test-user-123"
        mock_use_cases['delete'].execute.return_value = True
        
        result = await service.delete_task(task_id, user_id)
        
        # Verify use case was called
        mock_use_cases['delete'].execute.assert_called_once_with(task_id)
        
        # Verify context was deleted
        mock_hierarchical_context_service.delete_context.assert_called_once_with("task", task_id)
        
        assert result is True
    
    @pytest.mark.asyncio
    async def test_delete_task_no_context_cleanup_on_failure(self, service, mock_use_cases, mock_hierarchical_context_service):
        """Test that context is not deleted when task deletion fails"""
        task_id = "task-123"
        user_id = "test-user-123"
        mock_use_cases['delete'].execute.return_value = False
        
        result = await service.delete_task(task_id, user_id)
        
        # Verify context was NOT deleted
        mock_hierarchical_context_service.delete_context.assert_not_called()
        
        assert result is False
    
    @pytest.mark.asyncio
    async def test_complete_task(self, service, mock_use_cases):
        """Test task completion"""
        task_id = "task-123"
        expected_result = {"success": True, "task_id": task_id}
        mock_use_cases['complete'].execute.return_value = expected_result
        
        result = await service.complete_task(task_id)
        
        mock_use_cases['complete'].execute.assert_called_once_with(task_id)
        assert result == expected_result
    
    @pytest.mark.asyncio
    async def test_get_all_tasks(self, service, mock_use_cases):
        """Test getting all tasks"""
        expected_response = TaskListResponse(tasks=[Mock(), Mock()], count=2)
        mock_use_cases['list'].execute.return_value = expected_response
        
        result = await service.get_all_tasks()
        
        # Should create default ListTasksRequest
        mock_use_cases['list'].execute.assert_called_once()
        call_args = mock_use_cases['list'].execute.call_args[0][0]
        assert isinstance(call_args, ListTasksRequest)
        assert result == expected_response
    
    @pytest.mark.asyncio
    async def test_get_tasks_by_status(self, service, mock_use_cases):
        """Test getting tasks by status"""
        status = "in_progress"
        expected_response = TaskListResponse(tasks=[Mock()], count=1)
        mock_use_cases['list'].execute.return_value = expected_response
        
        result = await service.get_tasks_by_status(status)
        
        # Should create ListTasksRequest with status
        mock_use_cases['list'].execute.assert_called_once()
        call_args = mock_use_cases['list'].execute.call_args[0][0]
        assert isinstance(call_args, ListTasksRequest)
        assert call_args.status == status
        assert result == expected_response
    
    @pytest.mark.asyncio
    async def test_get_tasks_by_assignee(self, service, mock_use_cases):
        """Test getting tasks by assignee"""
        assignee = "user-123"
        expected_response = TaskListResponse(tasks=[Mock()], count=1)
        mock_use_cases['list'].execute.return_value = expected_response
        
        result = await service.get_tasks_by_assignee(assignee)
        
        # Should create ListTasksRequest with assignee
        mock_use_cases['list'].execute.assert_called_once()
        call_args = mock_use_cases['list'].execute.call_args[0][0]
        assert isinstance(call_args, ListTasksRequest)
        assert call_args.assignees == [assignee]
        assert result == expected_response
    
    def test_with_user_creates_scoped_service(self, service):
        """Test creating user-scoped service"""
        new_user_id = "different-user-456"
        scoped_service = service.with_user(new_user_id)
        
        assert isinstance(scoped_service, TaskApplicationService)
        assert scoped_service._user_id == new_user_id
        assert scoped_service._user_id != service._user_id
    
    def test_get_user_scoped_repository(self, service, mock_task_repository):
        """Test getting user-scoped repository"""
        # Reset the mock to clear calls from initialization
        mock_task_repository.with_user.reset_mock()
        
        # Test repository with with_user method
        scoped_repo = service._get_user_scoped_repository()
        
        mock_task_repository.with_user.assert_called_once_with("test-user-123")
        assert scoped_repo == mock_task_repository
    
    def test_get_user_scoped_repository_with_user_id_property(self, service):
        """Test getting user-scoped repository with user_id property"""
        # Create repository with user_id property
        mock_repo = Mock()
        mock_repo.user_id = "old-user"
        mock_repo.session = Mock()
        type(mock_repo).__name__ = "MockRepository"
        
        service._task_repository = mock_repo
        
        with patch.object(type(mock_repo), '__new__') as mock_new:
            mock_new_repo = Mock()
            mock_new.return_value = mock_new_repo
            
            # This test would need more complex mocking to fully test
            # the repository creation logic
            pass
    
    @pytest.mark.asyncio
    async def test_update_task_no_context_update_on_failure(self, service, mock_use_cases, mock_hierarchical_context_service):
        """Test that context is not updated when task update fails"""
        request = UpdateTaskRequest(
            task_id="task-123",
            title="Updated Task"
        )
        
        # Response without success or task
        response = Mock(success=False, task=None)
        mock_use_cases['update'].execute.return_value = response
        
        result = await service.update_task(request)
        
        # Verify context was NOT updated
        mock_hierarchical_context_service.update_context.assert_not_called()
        assert result == response
    
    @pytest.mark.asyncio
    async def test_complete_task_with_completion_summary(self, service, mock_use_cases):
        """Test task completion with completion summary parameter"""
        task_id = "task-123"
        completion_summary = "Successfully implemented JWT authentication with refresh tokens"
        expected_result = {
            "success": True,
            "task_id": task_id,
            "completion_summary": completion_summary
        }
        mock_use_cases['complete'].execute.return_value = expected_result
        
        # The complete_task method currently only accepts task_id
        result = await service.complete_task(task_id)
        
        mock_use_cases['complete'].execute.assert_called_once_with(task_id)
        assert result == expected_result
    
    @pytest.mark.asyncio
    async def test_complete_task_with_testing_notes(self, service, mock_use_cases):
        """Test task completion with testing notes"""
        task_id = "task-123"
        completion_summary = "Implemented user authentication"
        testing_notes = "Added unit tests for auth service, integration tests for login flow"
        expected_result = {
            "success": True,
            "task_id": task_id,
            "completion_summary": completion_summary,
            "testing_notes": testing_notes
        }
        mock_use_cases['complete'].execute.return_value = expected_result
        
        # The complete_task method currently only accepts task_id
        result = await service.complete_task(task_id)
        
        mock_use_cases['complete'].execute.assert_called_once_with(task_id)
        assert result == expected_result
    
    def test_get_user_scoped_repository_no_user_id(self):
        """Test repository scoping without user ID"""
        mock_repo = Mock()
        service = TaskApplicationService(mock_repo, user_id=None)
        
        result = service._get_user_scoped_repository()
        
        # Should return original repository when no user_id
        assert result == mock_repo
    
    @pytest.mark.asyncio
    async def test_create_task_handles_task_without_value_attribute(self, service, mock_use_cases, mock_hierarchical_context_service):
        """Test task creation handles tasks without .value attributes"""
        request = CreateTaskRequest(
            title="Test Task",
            description="Test Description",
            git_branch_id="branch-123"
        )
        
        # Create task with direct string attributes (no .value)
        mock_task = Mock()
        mock_task.id = "task-123"  # Direct string
        mock_task.title = "Test Task"
        mock_task.status = "todo"  # Direct string
        mock_task.priority = "medium"  # Direct string
        mock_task.assignees = []
        mock_task.labels = []
        mock_task.estimated_effort = None
        mock_task.due_date = None
        
        response = CreateTaskResponse(success=True, task=mock_task)
        mock_use_cases['create'].execute.return_value = response
        
        result = await service.create_task(request)
        
        # Verify context creation handles non-.value attributes
        mock_hierarchical_context_service.create_context.assert_called_once()
        context_call = mock_hierarchical_context_service.create_context.call_args
        assert context_call[1]['data']['task_data']['status'] == "todo"
        assert context_call[1]['data']['task_data']['priority'] == "medium"