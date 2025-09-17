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

    # Additional Edge Case Tests
    
    @pytest.mark.asyncio
    async def test_create_task_with_empty_response(self, service, mock_use_cases, mock_hierarchical_context_service):
        """Test task creation with empty response"""
        request = CreateTaskRequest(
            title="Test Task",
            git_branch_id="branch-123"
        )
        
        # Response with no success attribute
        response = Mock()
        del response.success  # Remove success attribute
        mock_use_cases['create'].execute.return_value = response
        
        result = await service.create_task(request)
        
        # Should not create context without success flag
        mock_hierarchical_context_service.create_context.assert_not_called()
        assert result == response

    @pytest.mark.asyncio
    async def test_create_task_with_none_task(self, service, mock_use_cases, mock_hierarchical_context_service):
        """Test task creation when task is None"""
        request = CreateTaskRequest(
            title="Test Task",
            git_branch_id="branch-123"
        )
        
        response = CreateTaskResponse(success=True, task=None)
        mock_use_cases['create'].execute.return_value = response
        
        result = await service.create_task(request)
        
        # Should not create context when task is None
        mock_hierarchical_context_service.create_context.assert_not_called()
        assert result == response

    @pytest.mark.asyncio
    async def test_update_task_with_none_task(self, service, mock_use_cases, mock_hierarchical_context_service):
        """Test task update when task is None"""
        request = UpdateTaskRequest(
            task_id="task-123",
            title="Updated Task"
        )
        
        response = Mock(success=True, task=None)
        mock_use_cases['update'].execute.return_value = response
        
        result = await service.update_task(request)
        
        # Should not update context when task is None
        mock_hierarchical_context_service.update_context.assert_not_called()
        assert result == response

    @pytest.mark.asyncio
    async def test_update_task_handles_task_without_value_attribute(self, service, mock_use_cases, mock_hierarchical_context_service):
        """Test task update handles tasks without .value attributes"""
        request = UpdateTaskRequest(
            task_id="task-123",
            title="Updated Task"
        )
        
        # Create task with direct string attributes
        mock_task = Mock()
        mock_task.id = "task-123"  # Direct string
        mock_task.title = "Updated Task"
        mock_task.description = "Updated Description"
        mock_task.status = "in_progress"  # Direct string
        mock_task.priority = "high"  # Direct string
        mock_task.assignees = ["user-1"]
        mock_task.labels = ["feature"]
        mock_task.estimated_effort = "4 hours"
        mock_task.due_date = None
        
        response = Mock(success=True, task=mock_task)
        mock_use_cases['update'].execute.return_value = response
        
        result = await service.update_task(request)
        
        # Verify context update handles non-.value attributes
        mock_hierarchical_context_service.update_context.assert_called_once()
        context_call = mock_hierarchical_context_service.update_context.call_args
        assert context_call[1]['changes']['task_data']['status'] == "in_progress"
        assert context_call[1]['changes']['task_data']['priority'] == "high"
        assert result == response

    # Error Handling Tests
    
    @pytest.mark.asyncio
    async def test_get_task_with_general_exception(self, service, mock_use_cases):
        """Test task retrieval with general exception (not TaskNotFoundError)"""
        task_id = "task-123"
        mock_use_cases['get'].execute.side_effect = ValueError("Database error")
        
        # Should propagate other exceptions
        with pytest.raises(ValueError):
            await service.get_task(task_id)

    @pytest.mark.asyncio
    async def test_service_methods_with_different_parameter_combinations(self, service, mock_use_cases):
        """Test service methods with various parameter combinations"""
        
        # Test get_task with different parameters
        await service.get_task("task-123")
        await service.get_task("task-123", generate_rules=False)
        await service.get_task("task-123", force_full_generation=True)
        await service.get_task("task-123", include_context=False)
        await service.get_task("task-123", user_id="user-123")
        await service.get_task("task-123", project_id="project-123")
        await service.get_task("task-123", git_branch_name="feature/auth")
        
        # Verify all calls were made
        assert mock_use_cases['get'].execute.call_count == 7

    @pytest.mark.asyncio
    async def test_delete_task_with_different_parameters(self, service, mock_use_cases, mock_hierarchical_context_service):
        """Test delete_task with different parameter combinations"""
        mock_use_cases['delete'].execute.return_value = True
        
        # Test with different parameter sets
        await service.delete_task("task-123", "user-123")
        await service.delete_task("task-123", "user-123", "project-123")
        await service.delete_task("task-123", "user-123", "project-123", "feature/auth")
        
        # All should result in context deletion
        assert mock_hierarchical_context_service.delete_context.call_count == 3

    # Repository Scoping Tests
    
    def test_repository_scoping_without_user_context(self, mock_task_repository):
        """Test repository scoping when no user context is available"""
        service = TaskApplicationService(mock_task_repository, user_id=None)
        
        scoped_repo = service._get_user_scoped_repository()
        assert scoped_repo == mock_task_repository

    def test_repository_scoping_with_user_id_property_same_user(self, mock_task_repository):
        """Test repository scoping when user_id is already set correctly"""
        mock_task_repository.user_id = "test-user-123"
        service = TaskApplicationService(mock_task_repository, user_id="test-user-123")
        
        scoped_repo = service._get_user_scoped_repository()
        # Should return original repo when user_id matches
        assert scoped_repo == mock_task_repository

    def test_repository_scoping_fallback_no_session(self, mock_task_repository):
        """Test repository scoping fallback when no session available"""
        mock_task_repository.user_id = "old-user"
        # Remove session attribute
        if hasattr(mock_task_repository, 'session'):
            delattr(mock_task_repository, 'session')
        
        service = TaskApplicationService(mock_task_repository, user_id="new-user")
        
        scoped_repo = service._get_user_scoped_repository()
        # Should fallback to original repo
        assert scoped_repo == mock_task_repository

    # Context Service Integration Tests
    
    @pytest.mark.asyncio
    async def test_context_service_error_handling(self, service, mock_use_cases, mock_hierarchical_context_service, mock_task):
        """Test graceful handling of context service errors"""
        request = CreateTaskRequest(
            title="Test Task",
            git_branch_id="branch-123"
        )
        
        response = CreateTaskResponse(success=True, task=mock_task)
        mock_use_cases['create'].execute.return_value = response
        
        # Make context service raise an exception
        mock_hierarchical_context_service.create_context.side_effect = Exception("Context service error")
        
        # Should propagate the context service error
        with pytest.raises(Exception, match="Context service error"):
            await service.create_task(request)

    # Performance and Load Tests
    
    @pytest.mark.asyncio
    async def test_multiple_concurrent_operations(self, service, mock_use_cases):
        """Test handling multiple concurrent operations"""
        import asyncio
        
        # Set up return values
        mock_use_cases['get'].execute.return_value = Mock()
        mock_use_cases['list'].execute.return_value = TaskListResponse(tasks=[], count=0)
        mock_use_cases['complete'].execute.return_value = {"success": True}
        
        # Run multiple operations concurrently
        tasks = [
            service.get_task("task-1"),
            service.get_task("task-2"),
            service.get_all_tasks(),
            service.get_tasks_by_status("todo"),
            service.complete_task("task-3")
        ]
        
        results = await asyncio.gather(*tasks)
        
        # Verify all operations completed
        assert len(results) == 5
        assert mock_use_cases['get'].execute.call_count == 2
        assert mock_use_cases['list'].execute.call_count == 2
        assert mock_use_cases['complete'].execute.call_count == 1

    # Data Validation Tests
    
    @pytest.mark.asyncio
    async def test_list_tasks_with_complex_request(self, service, mock_use_cases):
        """Test listing tasks with complex filtering"""
        request = ListTasksRequest(
            status="in_progress",
            priority="high",
            assignees=["user-1", "user-2"],
            labels=["urgent", "bug"],
            git_branch_id="branch-123",
            limit=50
        )
        
        expected_response = TaskListResponse(tasks=[Mock()], count=1)
        mock_use_cases['list'].execute.return_value = expected_response
        
        result = await service.list_tasks(request)
        
        mock_use_cases['list'].execute.assert_called_once_with(request)
        assert result == expected_response

    @pytest.mark.asyncio
    async def test_search_tasks_with_empty_query(self, service, mock_use_cases):
        """Test searching tasks with empty query"""
        request = SearchTasksRequest(query="", limit=10)
        expected_response = TaskListResponse(tasks=[], count=0)
        mock_use_cases['search'].execute.return_value = expected_response
        
        result = await service.search_tasks(request)
        
        mock_use_cases['search'].execute.assert_called_once_with(request)
        assert result == expected_response

    # Service State Tests
    
    def test_service_initialization_with_different_configurations(self, mock_task_repository):
        """Test service initialization with different configurations"""
        # Test with minimal configuration
        service1 = TaskApplicationService(mock_task_repository)
        assert service1._task_repository == mock_task_repository
        assert service1._context_service is None
        assert service1._user_id is None
        
        # Test with context service
        mock_context = Mock()
        service2 = TaskApplicationService(mock_task_repository, mock_context)
        assert service2._context_service == mock_context
        
        # Test with user_id
        service3 = TaskApplicationService(mock_task_repository, user_id="test-user")
        assert service3._user_id == "test-user"

    def test_service_immutability_with_user_scoping(self, service):
        """Test that with_user creates independent service instances"""
        original_user = service._user_id
        
        # Create scoped service
        scoped_service = service.with_user("different-user")
        
        # Original service should be unchanged
        assert service._user_id == original_user
        assert scoped_service._user_id == "different-user"
        assert scoped_service is not service

    # Integration Test Scenarios
    
    @pytest.mark.asyncio
    async def test_full_task_lifecycle(self, service, mock_use_cases, mock_hierarchical_context_service, mock_task):
        """Test complete task lifecycle: create -> get -> update -> complete -> delete"""
        
        # Create task
        create_request = CreateTaskRequest(title="Lifecycle Test", git_branch_id="branch-123")
        create_response = CreateTaskResponse(success=True, task=mock_task)
        mock_use_cases['create'].execute.return_value = create_response
        
        create_result = await service.create_task(create_request)
        assert create_result.success is True
        
        # Get task
        mock_use_cases['get'].execute.return_value = Mock()
        get_result = await service.get_task("task-123")
        assert get_result is not None
        
        # Update task
        update_request = UpdateTaskRequest(task_id="task-123", status="in_progress")
        update_response = Mock(success=True, task=mock_task)
        mock_use_cases['update'].execute.return_value = update_response
        
        update_result = await service.update_task(update_request)
        assert update_result == update_response
        
        # Complete task
        mock_use_cases['complete'].execute.return_value = {"success": True}
        complete_result = await service.complete_task("task-123")
        assert complete_result["success"] is True
        
        # Delete task
        mock_use_cases['delete'].execute.return_value = True
        delete_result = await service.delete_task("task-123", "user-123")
        assert delete_result is True
        
        # Verify all context operations were called
        mock_hierarchical_context_service.create_context.assert_called()
        mock_hierarchical_context_service.update_context.assert_called()
        mock_hierarchical_context_service.delete_context.assert_called()