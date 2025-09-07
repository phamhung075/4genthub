"""
Unit tests for Task Application Service with User Scoping

Tests task operations with user isolation and context management.
"""

import pytest
from unittest.mock import Mock, AsyncMock, patch, MagicMock
from datetime import datetime

from fastmcp.task_management.application.services.task_application_service import (
    TaskApplicationService
)
from fastmcp.task_management.application.dtos.task import (
    CreateTaskRequest, UpdateTaskRequest, ListTasksRequest, SearchTasksRequest
)
from fastmcp.task_management.domain.exceptions.task_exceptions import TaskNotFoundError


class TestTaskApplicationService:
    """Test cases for TaskApplicationService with user scoping"""
    
    @pytest.fixture
    def mock_task_repository(self):
        """Create a mock task repository"""
        repo = Mock()
        repo.with_user = Mock(return_value=repo)
        repo.user_id = None
        repo.session = Mock()
        return repo
    
    @pytest.fixture
    def mock_context_service(self):
        """Create a mock context service"""
        return Mock()
    
    @pytest.fixture
    def mock_unified_context_service(self):
        """Create a mock unified context service"""
        service = Mock()
        service.create_context = Mock(return_value=True)
        service.update_context = Mock(return_value=True)
        service.delete_context = Mock(return_value=True)
        return service
    
    @pytest.fixture
    def mock_use_cases(self):
        """Create mock use cases"""
        use_cases = {
            'create': Mock(),
            'get': Mock(),
            'update': Mock(),
            'list': Mock(),
            'search': Mock(),
            'delete': Mock(),
            'complete': Mock()
        }
        # Set execute methods
        for name, use_case in use_cases.items():
            if name in ['get', 'list', 'search', 'complete']:
                use_case.execute = AsyncMock()
            else:
                use_case.execute = Mock()
        return use_cases
    
    @pytest.fixture
    def service(self, mock_task_repository, mock_context_service, mock_unified_context_service, mock_use_cases):
        """Create service instance with mocks"""
        with patch('fastmcp.task_management.application.factories.unified_context_facade_factory.UnifiedContextFacadeFactory') as mock_factory:
            mock_factory.return_value.create_unified_service.return_value = mock_unified_context_service
            
            with patch('fastmcp.task_management.application.services.task_application_service.CreateTaskUseCase', return_value=mock_use_cases['create']):
                with patch('fastmcp.task_management.application.services.task_application_service.GetTaskUseCase', return_value=mock_use_cases['get']):
                    with patch('fastmcp.task_management.application.services.task_application_service.UpdateTaskUseCase', return_value=mock_use_cases['update']):
                        with patch('fastmcp.task_management.application.services.task_application_service.ListTasksUseCase', return_value=mock_use_cases['list']):
                            with patch('fastmcp.task_management.application.services.task_application_service.SearchTasksUseCase', return_value=mock_use_cases['search']):
                                with patch('fastmcp.task_management.application.services.task_application_service.DeleteTaskUseCase', return_value=mock_use_cases['delete']):
                                    with patch('fastmcp.task_management.application.services.task_application_service.CompleteTaskUseCase', return_value=mock_use_cases['complete']):
                                        with patch('fastmcp.task_management.infrastructure.repositories.task_context_repository.TaskContextRepository'):
                                            with patch('fastmcp.task_management.infrastructure.database.database_config.get_db_config'):
                                                service = TaskApplicationService(
                                                    mock_task_repository,
                                                    mock_context_service,
                                                    "test_user"
                                                )
                                            service._use_cases = mock_use_cases  # Store for easy access
                                            service._hierarchical_context_service = mock_unified_context_service
                                            return service
    
    @pytest.fixture
    def mock_task(self):
        """Create a mock task entity"""
        task = Mock()
        task.id = Mock(value="task123")
        task.title = "Test Task"
        task.description = "Test Description"
        task.status = Mock(value="todo")
        task.priority = Mock(value="medium")
        task.assignees = ["user1"]
        task.labels = ["test"]
        task.estimated_effort = "2 hours"
        task.due_date = None
        return task
    
    def test_init(self, mock_task_repository, mock_context_service):
        """Test service initialization"""
        user_id = "test_user"
        
        with patch('fastmcp.task_management.application.factories.unified_context_facade_factory.UnifiedContextFacadeFactory'):
            with patch('fastmcp.task_management.application.services.task_application_service.CreateTaskUseCase'):
                with patch('fastmcp.task_management.application.services.task_application_service.GetTaskUseCase'):
                    with patch('fastmcp.task_management.application.services.task_application_service.UpdateTaskUseCase'):
                        with patch('fastmcp.task_management.application.services.task_application_service.ListTasksUseCase'):
                            with patch('fastmcp.task_management.application.services.task_application_service.SearchTasksUseCase'):
                                with patch('fastmcp.task_management.application.services.task_application_service.DeleteTaskUseCase'):
                                    with patch('fastmcp.task_management.application.services.task_application_service.CompleteTaskUseCase'):
                                        with patch('fastmcp.task_management.infrastructure.repositories.task_context_repository.TaskContextRepository'):
                                            with patch('fastmcp.task_management.infrastructure.database.database_config.get_db_config'):
                                                service = TaskApplicationService(
                                                    mock_task_repository,
                                                    mock_context_service,
                                                    user_id
                                                )
        
        assert service._task_repository == mock_task_repository
        assert service._context_service == mock_context_service
        assert service._user_id == user_id
    
    def test_get_user_scoped_repository_with_with_user(self, service, mock_task_repository):
        """Test getting user-scoped repository with with_user method"""
        scoped_repo = Mock()
        mock_task_repository.with_user.return_value = scoped_repo
        mock_task_repository.with_user.reset_mock()  # Reset call count from service initialization
        
        result = service._get_user_scoped_repository()
        
        mock_task_repository.with_user.assert_called_once_with("test_user")
        assert result == scoped_repo
    
    def test_get_user_scoped_repository_with_user_id_property(self, service, mock_task_repository):
        """Test getting user-scoped repository with user_id property"""
        # Setup repository with different user_id
        if hasattr(mock_task_repository, 'with_user'):
            del mock_task_repository.with_user  # Remove with_user method completely
        mock_task_repository.user_id = "different_user"
        
        with patch('fastmcp.task_management.application.services.task_application_service.type') as mock_type:
            mock_class = Mock()
            new_repo = Mock()
            mock_class.return_value = new_repo
            mock_type.return_value = mock_class
            
            result = service._get_user_scoped_repository()
            
            mock_class.assert_called_once_with(mock_task_repository.session, user_id="test_user")
            assert result == new_repo
    
    def test_with_user(self, service, mock_task_repository, mock_context_service):
        """Test creating user-scoped service"""
        new_user_id = "new_user"
        new_service = service.with_user(new_user_id)
        
        assert isinstance(new_service, TaskApplicationService)
        assert new_service._user_id == new_user_id
        assert new_service._task_repository == mock_task_repository
        assert new_service._context_service == mock_context_service
    
    @pytest.mark.asyncio
    async def test_create_task_with_context(self, service, mock_task):
        """Test creating a task with automatic context creation"""
        # Setup
        request = CreateTaskRequest(
            git_branch_id="branch123",
            title="Test Task",
            description="Test Description"
        )
        
        response = Mock()
        response.success = True
        response.task = mock_task
        
        service._use_cases['create'].execute.return_value = response
        
        # Execute
        result = await service.create_task(request)
        
        # Assert
        assert result == response
        service._use_cases['create'].execute.assert_called_once_with(request)
        
        # Verify context was created
        service._hierarchical_context_service.create_context.assert_called_once()
        call_args = service._hierarchical_context_service.create_context.call_args
        assert call_args[1]["level"] == "task"
        assert call_args[1]["context_id"] == "task123"
        assert call_args[1]["data"]["task_data"]["title"] == "Test Task"
        assert call_args[1]["data"]["task_data"]["status"] == "todo"
    
    @pytest.mark.asyncio
    async def test_create_task_without_success(self, service):
        """Test creating a task that fails doesn't create context"""
        # Setup
        request = CreateTaskRequest(
            git_branch_id="branch123",
            title="Test Task",
            description="Test Description"
        )
        
        response = Mock()
        response.success = False
        
        service._use_cases['create'].execute.return_value = response
        
        # Execute
        result = await service.create_task(request)
        
        # Assert
        assert result == response
        service._hierarchical_context_service.create_context.assert_not_called()
    
    @pytest.mark.asyncio
    async def test_get_task_success(self, service):
        """Test getting a task successfully"""
        task_id = "task123"
        expected_response = Mock()
        
        service._use_cases['get'].execute.return_value = expected_response
        
        result = await service.get_task(
            task_id,
            generate_rules=True,
            force_full_generation=False,
            include_context=True
        )
        
        assert result == expected_response
        service._use_cases['get'].execute.assert_called_once_with(
            task_id,
            generate_rules=True,
            force_full_generation=False,
            include_context=True
        )
    
    @pytest.mark.asyncio
    async def test_get_task_not_found(self, service):
        """Test getting a non-existent task"""
        task_id = "nonexistent"
        
        service._use_cases['get'].execute.side_effect = TaskNotFoundError("Task not found")
        
        result = await service.get_task(task_id)
        
        assert result is None
    
    @pytest.mark.asyncio
    async def test_update_task_with_context(self, service, mock_task):
        """Test updating a task with automatic context update"""
        # Setup
        request = UpdateTaskRequest(
            task_id="task123",
            title="Updated Task"
        )
        
        response = Mock()
        response.success = True
        response.task = mock_task
        
        service._use_cases['update'].execute.return_value = response
        
        # Execute
        result = await service.update_task(request)
        
        # Assert
        assert result == response
        service._use_cases['update'].execute.assert_called_once_with(request)
        
        # Verify context was updated
        service._hierarchical_context_service.update_context.assert_called_once()
        call_args = service._hierarchical_context_service.update_context.call_args
        assert call_args[1]["level"] == "task"
        assert call_args[1]["context_id"] == "task123"
        assert call_args[1]["changes"]["task_data"]["title"] == "Test Task"
    
    @pytest.mark.asyncio
    async def test_list_tasks(self, service):
        """Test listing tasks"""
        request = ListTasksRequest(status="todo")
        expected_response = Mock()
        
        service._use_cases['list'].execute.return_value = expected_response
        
        result = await service.list_tasks(request)
        
        assert result == expected_response
        service._use_cases['list'].execute.assert_called_once_with(request)
    
    @pytest.mark.asyncio
    async def test_search_tasks(self, service):
        """Test searching tasks"""
        request = SearchTasksRequest(query="test")
        expected_response = Mock()
        
        service._use_cases['search'].execute.return_value = expected_response
        
        result = await service.search_tasks(request)
        
        assert result == expected_response
        service._use_cases['search'].execute.assert_called_once_with(request)
    
    @pytest.mark.asyncio
    async def test_delete_task_with_context(self, service):
        """Test deleting a task with automatic context deletion"""
        task_id = "task123"
        user_id = "user456"
        
        service._use_cases['delete'].execute.return_value = True
        
        result = await service.delete_task(task_id, user_id)
        
        assert result is True
        service._use_cases['delete'].execute.assert_called_once_with(task_id)
        
        # Verify context was deleted
        service._hierarchical_context_service.delete_context.assert_called_once_with("task", task_id)
    
    @pytest.mark.asyncio
    async def test_delete_task_failed(self, service):
        """Test deleting a task that fails doesn't delete context"""
        task_id = "task123"
        user_id = "user456"
        
        service._use_cases['delete'].execute.return_value = False
        
        result = await service.delete_task(task_id, user_id)
        
        assert result is False
        service._hierarchical_context_service.delete_context.assert_not_called()
    
    @pytest.mark.asyncio
    async def test_complete_task(self, service):
        """Test completing a task"""
        task_id = "task123"
        expected_result = {"success": True, "task_id": task_id}
        
        service._use_cases['complete'].execute.return_value = expected_result
        
        result = await service.complete_task(task_id)
        
        assert result == expected_result
        service._use_cases['complete'].execute.assert_called_once_with(task_id)
    
    @pytest.mark.asyncio
    async def test_get_all_tasks(self, service):
        """Test getting all tasks"""
        expected_response = Mock()
        
        service._use_cases['list'].execute.return_value = expected_response
        
        result = await service.get_all_tasks()
        
        assert result == expected_response
        service._use_cases['list'].execute.assert_called_once()
        # Verify empty request was created
        call_args = service._use_cases['list'].execute.call_args[0][0]
        assert isinstance(call_args, ListTasksRequest)
    
    @pytest.mark.asyncio
    async def test_get_tasks_by_status(self, service):
        """Test getting tasks by status"""
        status = "in_progress"
        expected_response = Mock()
        
        service._use_cases['list'].execute.return_value = expected_response
        
        result = await service.get_tasks_by_status(status)
        
        assert result == expected_response
        service._use_cases['list'].execute.assert_called_once()
        # Verify request was created with status
        call_args = service._use_cases['list'].execute.call_args[0][0]
        assert isinstance(call_args, ListTasksRequest)
        assert call_args.status == status
    
    @pytest.mark.asyncio
    async def test_get_tasks_by_assignee(self, service):
        """Test getting tasks by assignee"""
        assignee = "user123"
        expected_response = Mock()
        
        service._use_cases['list'].execute.return_value = expected_response
        
        result = await service.get_tasks_by_assignee(assignee)
        
        assert result == expected_response
        service._use_cases['list'].execute.assert_called_once()
        # Verify request was created with assignee
        call_args = service._use_cases['list'].execute.call_args[0][0]
        assert isinstance(call_args, ListTasksRequest)
        assert call_args.assignees == [assignee]
    
    def test_task_with_due_date(self, service):
        """Test task with due date handling"""
        # Create task with due date
        task = Mock()
        task.id = Mock(value="task123")
        task.title = "Test Task"
        task.description = "Test"
        task.status = Mock(value="todo")
        task.priority = Mock(value="high")
        task.assignees = []
        task.labels = []
        task.estimated_effort = None
        task.due_date = datetime.now()
        
        request = CreateTaskRequest(
            git_branch_id="branch123",
            title="Test Task",
            description="Test"
        )
        
        response = Mock()
        response.success = True
        response.task = task
        
        service._use_cases['create'].execute.return_value = response
        
        # Execute synchronously (the method is async but we're testing the sync part)
        import asyncio
        result = asyncio.run(service.create_task(request))
        
        # Verify context creation includes due_date
        call_args = service._hierarchical_context_service.create_context.call_args
        assert call_args[1]["data"]["task_data"]["due_date"] == task.due_date
    
    def test_task_id_extraction_variations(self, service):
        """Test different task ID formats"""
        # Test with task.id as object with value attribute
        task1 = Mock()
        task1.id = Mock(value="task123")
        task1.title = "Test"
        task1.status = Mock(value="todo")
        task1.priority = Mock(value="low")
        task1.assignees = []
        task1.labels = []
        task1.estimated_effort = None
        task1.due_date = None
        
        # Test with task.id as string
        task2 = Mock()
        task2.id = "task456"
        task2.title = "Test"
        task2.status = "in_progress"
        task2.priority = "high"
        task2.assignees = []
        task2.labels = []
        task2.estimated_effort = None
        task2.due_date = None
        
        for task in [task1, task2]:
            request = CreateTaskRequest(
                git_branch_id="branch123",
                title="Test",
                description=""
            )
            
            response = Mock()
            response.success = True
            response.task = task
            
            service._use_cases['create'].execute.return_value = response
            
            import asyncio
            asyncio.run(service.create_task(request))
            
            # Verify correct ID was extracted
            call_args = service._hierarchical_context_service.create_context.call_args
            expected_id = task.id.value if hasattr(task.id, 'value') else task.id
            assert call_args[1]["context_id"] == str(expected_id)