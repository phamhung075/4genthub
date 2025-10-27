"""
Tests for Task Context Sync Service

This module tests the TaskContextSyncService functionality including:
- Context synchronization for tasks
- User authentication and validation
- Context creation and updates
- Integration with unified context service
- Error handling and fallback behavior
- User scoping and repository management
"""

import pytest
from unittest.mock import Mock, AsyncMock, patch
from datetime import datetime

from fastmcp.task_management.application.services.task_context_sync_service import TaskContextSyncService
from fastmcp.task_management.domain.entities.task import Task
from fastmcp.task_management.domain.repositories.task_repository import TaskRepository
from fastmcp.task_management.domain.value_objects.task_id import TaskId
from fastmcp.task_management.domain.value_objects.task_status import TaskStatus  
from fastmcp.task_management.domain.value_objects.priority import Priority
from fastmcp.task_management.domain.exceptions.authentication_exceptions import UserAuthenticationRequiredError


class TestTaskContextSyncService:
    """Test suite for TaskContextSyncService"""
    
    @pytest.fixture
    def mock_task_repository(self):
        """Create a mock task repository"""
        repo = Mock(spec=TaskRepository)
        repo.find_by_id = Mock()
        repo.with_user = Mock(return_value=repo)
        return repo
    
    @pytest.fixture
    def mock_context_service(self):
        """Create a mock context service"""
        service = Mock()
        service.get_context = Mock()
        service.create_context = Mock()
        service.update_context = Mock()
        return service
    
    @pytest.fixture
    def mock_unified_context_facade_factory(self, mock_context_service):
        """Create a mock unified context facade factory"""
        with patch('fastmcp.task_management.application.services.facade_service.FacadeService.get_unified_context_facade') as mock_get_facade:
            mock_get_facade.return_value = mock_context_service
            yield mock_get_facade
    
    @pytest.fixture
    def service(self, mock_task_repository, mock_context_service, mock_unified_context_facade_factory):
        """Create service instance with mocked dependencies"""
        with patch('fastmcp.task_management.application.services.task_context_sync_service.GetTaskUseCase'):
            service = TaskContextSyncService(mock_task_repository, mock_context_service)
            return service
    
    @pytest.fixture
    def service_with_user(self, mock_task_repository, mock_context_service, mock_unified_context_facade_factory):
        """Create service instance with user context"""
        with patch('fastmcp.task_management.application.services.task_context_sync_service.GetTaskUseCase'):
            service = TaskContextSyncService(mock_task_repository, mock_context_service, user_id="user-123")
            return service
    
    @pytest.fixture
    def mock_task_entity(self):
        """Create a mock task entity"""
        task = Mock(spec=Task)
        task.id = TaskId.from_string("12345678-1234-5678-1234-567812345678")
        task.title = "Test Task"
        task.description = "Test Description"
        task.status = TaskStatus.TODO
        task.priority = Priority.medium()
        task.assignees = ["user-1"]
        task.labels = ["test"]
        task.estimated_effort = "2 hours"
        task.due_date = datetime(2025, 12, 31)
        task.git_branch_id = "branch-123"
        return task
    
    def test_service_initialization(self, mock_task_repository, mock_unified_context_facade_factory):
        """Test service initialization with dependencies"""
        with patch('fastmcp.task_management.application.services.task_context_sync_service.GetTaskUseCase') as mock_use_case:
            service = TaskContextSyncService(mock_task_repository)
            
            assert service._task_repository == mock_task_repository
            assert service._user_id is None
            mock_unified_context_facade_factory.assert_called_once()
            mock_use_case.assert_called_once()
    
    def test_service_initialization_with_user(self, mock_task_repository, mock_unified_context_facade_factory):
        """Test service initialization with user context"""
        with patch('fastmcp.task_management.application.services.task_context_sync_service.GetTaskUseCase'):
            service = TaskContextSyncService(mock_task_repository, user_id="user-123")
            
            assert service._user_id == "user-123"
    
    def test_with_user_creates_new_instance(self, service, mock_task_repository):
        """Test that with_user creates a new service instance with user context"""
        user_service = service.with_user("user-456")
        
        assert user_service != service
        assert user_service._user_id == "user-456"
        assert user_service._task_repository == mock_task_repository
    
    def test_get_user_scoped_repository_with_user_support(self, service_with_user):
        """Test getting user-scoped repository when repository supports it"""
        mock_repo = Mock()
        mock_user_repo = Mock()
        mock_repo.with_user.return_value = mock_user_repo
        
        result = service_with_user._get_user_scoped_repository(mock_repo)
        
        assert result == mock_user_repo
        mock_repo.with_user.assert_called_once_with("user-123")
    
    def test_get_user_scoped_repository_without_user_support(self, service_with_user):
        """Test getting repository when it doesn't support user scoping"""
        mock_repo = Mock()
        del mock_repo.with_user  # Remove with_user method
        
        result = service_with_user._get_user_scoped_repository(mock_repo)
        
        assert result == mock_repo
    
    def test_get_user_scoped_repository_no_user_id(self, service):
        """Test getting repository when no user_id is set"""
        mock_repo = Mock()
        mock_repo.with_user = Mock()
        
        result = service._get_user_scoped_repository(mock_repo)
        
        assert result == mock_repo
        mock_repo.with_user.assert_not_called()


class TestTaskContextSyncServiceSyncContext:
    """Test suite for sync_context_and_get_task method"""
    
    @pytest.fixture
    def mock_task_repository(self):
        """Create a mock task repository"""
        repo = Mock(spec=TaskRepository)
        repo.find_by_id = Mock()
        repo.with_user = Mock(return_value=repo)
        return repo
    
    @pytest.fixture
    def mock_context_service(self):
        """Create a mock context service"""
        service = Mock()
        service.get_context = Mock()
        service.create_context = Mock()
        service.update_context = Mock()
        return service
    
    @pytest.fixture
    def mock_get_task_use_case(self):
        """Create a mock get task use case"""
        use_case = Mock()
        use_case.execute = AsyncMock()
        return use_case
    
    @pytest.fixture
    def service(self, mock_task_repository, mock_context_service, mock_get_task_use_case):
        """Create service instance with mocked dependencies"""
        with patch('fastmcp.task_management.application.services.facade_service.FacadeService.get_unified_context_facade') as mock_get_facade:
            mock_get_facade.return_value = mock_context_service
            
            with patch('fastmcp.task_management.application.services.task_context_sync_service.GetTaskUseCase') as mock_use_case_class:
                mock_use_case_class.return_value = mock_get_task_use_case
                
                service = TaskContextSyncService(mock_task_repository, mock_context_service)
                return service
    
    @pytest.fixture
    def mock_task_entity(self):
        """Create a mock task entity"""
        task = Mock(spec=Task)
        task.id = TaskId.from_string("12345678-1234-5678-1234-567812345678")
        task.title = "Test Task"
        task.description = "Test Description"
        task.status = TaskStatus.TODO
        task.priority = Priority.medium()
        task.assignees = ["user-1"]
        task.labels = ["test"]
        task.estimated_effort = "2 hours"
        task.due_date = datetime(2025, 12, 31)
        task.git_branch_id = "branch-123"
        return task
    
    @patch('fastmcp.task_management.application.services.task_context_sync_service.validate_user_id')
    @pytest.mark.asyncio
    async def test_sync_context_and_get_task_success_create_context(self, mock_validate_user, service, mock_task_repository, mock_context_service, mock_get_task_use_case, mock_task_entity):
        """Test successful context sync with context creation"""
        # Setup authentication
        mock_validate_user.return_value = "user-123"
        
        # Setup task repository
        mock_task_repository.find_by_id.return_value = mock_task_entity
        
        # Setup context service - no existing context
        mock_context_service.get_context.return_value = None
        
        # Setup git branch repository
        with patch('fastmcp.task_management.infrastructure.repositories.orm.git_branch_repository.ORMGitBranchRepository') as mock_git_repo_class:
            mock_git_repo = Mock()
            mock_git_branch = Mock()
            mock_git_branch.project_id = "project-456"
            mock_git_repo.find_by_id.return_value = mock_git_branch
            mock_git_repo_class.return_value = mock_git_repo
            
            # Setup get task use case
            mock_task_response = Mock()
            mock_get_task_use_case.execute.return_value = mock_task_response
            
            result = await service.sync_context_and_get_task(
                "task-123",
                user_id="user-123",
                project_id="project-456",
                git_branch_name="main"
            )
            
            assert result == mock_task_response
            mock_validate_user.assert_called_once_with("user-123", "Task context sync")
            mock_task_repository.find_by_id.assert_called_once()
            mock_context_service.get_context.assert_called_once_with(level="task", context_id="12345678-1234-5678-1234-567812345678")
            mock_context_service.create_context.assert_called_once()
            mock_get_task_use_case.execute.assert_called_once_with(
                "task-123",
                generate_rules=False,
                force_full_generation=False,
                include_context=True
            )
    
    @patch('fastmcp.task_management.application.services.task_context_sync_service.validate_user_id')
    @pytest.mark.asyncio
    async def test_sync_context_and_get_task_success_update_context(self, mock_validate_user, service, mock_task_repository, mock_context_service, mock_get_task_use_case, mock_task_entity):
        """Test successful context sync with context update"""
        # Setup authentication
        mock_validate_user.return_value = "user-123"
        
        # Setup task repository
        mock_task_repository.find_by_id.return_value = mock_task_entity
        
        # Setup context service - existing context
        mock_existing_context = {"existing": "data"}
        mock_context_service.get_context.return_value = mock_existing_context
        
        # Setup get task use case
        mock_task_response = Mock()
        mock_get_task_use_case.execute.return_value = mock_task_response
        
        result = await service.sync_context_and_get_task(
            "task-123",
            user_id="user-123",
            project_id="project-456"
        )
        
        assert result == mock_task_response
        mock_context_service.get_context.assert_called_once_with(level="task", context_id="12345678-1234-5678-1234-567812345678")
        mock_context_service.update_context.assert_called_once()
        mock_context_service.create_context.assert_not_called()
    
    @pytest.mark.asyncio
    async def test_sync_context_and_get_task_no_user_id_raises_error(self, service):
        """Test context sync without user_id raises UserAuthenticationRequiredError"""
        from fastmcp.task_management.domain.exceptions.authentication_exceptions import UserAuthenticationRequiredError
        
        with pytest.raises(UserAuthenticationRequiredError) as exc_info:
            await service.sync_context_and_get_task("task-123")
        
        assert "Task context sync" in str(exc_info.value)
    
    @patch('fastmcp.task_management.application.services.task_context_sync_service.validate_user_id')
    @pytest.mark.asyncio
    async def test_sync_context_and_get_task_task_not_found(self, mock_validate_user, service, mock_task_repository):
        """Test context sync when task is not found"""
        # Setup authentication
        mock_validate_user.return_value = "user-123"
        
        # Setup task repository - task not found
        mock_task_repository.find_by_id.return_value = None
        
        result = await service.sync_context_and_get_task("12345678-1234-1234-1234-123456789012", user_id="user-123")
        
        assert result is None
        mock_task_repository.find_by_id.assert_called_once()
    
    @patch('fastmcp.task_management.application.services.task_context_sync_service.validate_user_id')
    @pytest.mark.asyncio
    async def test_sync_context_and_get_task_project_id_from_git_branch(self, mock_validate_user, service, mock_task_repository, mock_context_service, mock_get_task_use_case, mock_task_entity):
        """Test context sync with task that has git_branch_id"""
        # Setup authentication
        mock_validate_user.return_value = "user-123"
        
        # Setup task entity with git_branch_id
        mock_task_entity.git_branch_id = "branch-123"
        
        # Setup task repository
        mock_task_repository.find_by_id.return_value = mock_task_entity
        
        # Setup context service
        mock_context_service.get_context.return_value = None
        
        # Setup get task use case
        mock_task_response = Mock()
        mock_get_task_use_case.execute.return_value = mock_task_response
        
        result = await service.sync_context_and_get_task("task-123", user_id="user-123", project_id="project-456")
        
        assert result == mock_task_response
        # Verify context was created with correct parent branch references
        mock_context_service.create_context.assert_called_once()
        call_args = mock_context_service.create_context.call_args
        assert call_args[1]['data']['parent_branch_id'] == "branch-123"
        assert call_args[1]['data']['parent_branch_context_id'] == "branch-123"
    
    @patch('fastmcp.task_management.application.services.task_context_sync_service.validate_user_id')
    @pytest.mark.asyncio
    async def test_sync_context_and_get_task_default_project_id(self, mock_validate_user, service, mock_task_repository, mock_context_service, mock_get_task_use_case, mock_task_entity):
        """Test context sync requires project_id (no default fallback allowed)"""
        # Setup authentication
        mock_validate_user.return_value = "user-123"
        
        # Setup task repository
        mock_task_repository.find_by_id.return_value = mock_task_entity
        
        # Setup context service
        mock_context_service.get_context.return_value = None
        
        # Setup git branch repository - no git branch found
        with patch('fastmcp.task_management.infrastructure.repositories.orm.git_branch_repository.ORMGitBranchRepository') as mock_git_repo_class:
            mock_git_repo = Mock()
            mock_git_repo.find_by_id.return_value = None
            mock_git_repo_class.return_value = mock_git_repo
            
            # Test that sync requires project_id
            with pytest.raises(ValueError, match="project_id is required"):
                await service.sync_context_and_get_task("task-123", user_id="user-123")
            
            # Test successful sync with project_id provided
            mock_task_response = Mock()
            mock_get_task_use_case.execute.return_value = mock_task_response
            
            result = await service.sync_context_and_get_task("task-123", user_id="user-123", project_id="test-project")
            
            assert result == mock_task_response
    
    @patch('fastmcp.task_management.application.services.task_context_sync_service.validate_user_id')
    @pytest.mark.asyncio
    async def test_sync_context_and_get_task_error_handling(self, mock_validate_user, service, mock_task_repository):
        """Test context sync error handling"""
        # Setup authentication
        mock_validate_user.return_value = "user-123"
        
        # Setup task repository to raise exception
        mock_task_repository.find_by_id.side_effect = Exception("Database connection failed")
        
        result = await service.sync_context_and_get_task("task-123", user_id="user-123")
        
        assert result is None
    
    @patch('fastmcp.task_management.application.services.task_context_sync_service.validate_user_id')
    @pytest.mark.asyncio
    async def test_sync_context_and_get_task_context_data_structure(self, mock_validate_user, service, mock_task_repository, mock_context_service, mock_get_task_use_case, mock_task_entity):
        """Test that context data is structured correctly"""
        # Setup authentication
        mock_validate_user.return_value = "user-123"
        
        # Setup task repository
        mock_task_repository.find_by_id.return_value = mock_task_entity
        
        # Setup context service
        mock_context_service.get_context.return_value = None
        
        # Setup get task use case
        mock_task_response = Mock()
        mock_get_task_use_case.execute.return_value = mock_task_response
        
        result = await service.sync_context_and_get_task("task-123", user_id="user-123", project_id="test-project")
        
        # Verify context creation was called with correct structure
        mock_context_service.create_context.assert_called_once()
        call_args = mock_context_service.create_context.call_args
        
        assert call_args[1]["level"] == "task"
        assert call_args[1]["context_id"] == "12345678-1234-5678-1234-567812345678"
        
        context_data = call_args[1]["data"]
        assert "task_data" in context_data
        assert "parent_branch_id" in context_data
        assert "parent_branch_context_id" in context_data
        
        task_data = context_data["task_data"]
        assert task_data["title"] == "Test Task"
        assert task_data["description"] == "Test Description"
        assert task_data["status"] == "todo"
        assert task_data["priority"] == "medium"
        assert task_data["assignees"] == ["user-1"]
        assert task_data["labels"] == ["test"]
        assert task_data["estimated_effort"] == "2 hours"
        assert task_data["due_date"] == datetime(2025, 12, 31)
    
    @patch('fastmcp.task_management.application.services.task_context_sync_service.validate_user_id')
    @pytest.mark.asyncio
    async def test_sync_context_and_get_task_with_user_scoped_repository(self, mock_validate_user, mock_task_repository):
        """Test context sync with user-scoped repository"""
        # Setup authentication
        mock_validate_user.return_value = "user-123"
        
        # Setup user-scoped repository
        mock_user_repo = Mock()
        mock_task_repository.with_user.return_value = mock_user_repo
        
        # Setup task entity
        mock_task = Mock(spec=Task)
        mock_task.id = TaskId.from_string("12345678-1234-5678-1234-567812345678")
        mock_task.title = "User Task"
        mock_task.description = "User Description"
        mock_task.status = TaskStatus.TODO
        mock_task.priority = Priority.high()
        mock_task.assignees = ["user-123"]
        mock_task.labels = ["user-task"]
        mock_task.estimated_effort = "1 hour"
        mock_task.due_date = None
        mock_task.git_branch_id = "user-branch-123"
        
        mock_user_repo.find_by_id.return_value = mock_task
        
        # Create service with user context
        with patch('fastmcp.task_management.application.services.facade_service.FacadeService.get_unified_context_facade'):
            with patch('fastmcp.task_management.application.services.task_context_sync_service.GetTaskUseCase') as mock_use_case_class:
                mock_get_task_use_case = Mock()
                mock_get_task_use_case.execute = AsyncMock(return_value=Mock())
                mock_use_case_class.return_value = mock_get_task_use_case
                
                service = TaskContextSyncService(mock_task_repository, user_id="user-123")
                result = await service.sync_context_and_get_task("task-123", user_id="user-123", project_id="user-project")
                
                # Verify user-scoped repository was used
                mock_task_repository.with_user.assert_called_once_with("user-123")
                mock_user_repo.find_by_id.assert_called_once()


class TestTaskContextSyncServiceErrorScenarios:
    """Test suite for error scenarios and edge cases"""
    
    @pytest.fixture
    def mock_task_repository(self):
        """Create a mock task repository"""
        repo = Mock(spec=TaskRepository)
        repo.find_by_id = Mock()
        return repo
    
    @pytest.fixture
    def service(self, mock_task_repository):
        """Create service instance with mocked dependencies"""
        with patch('fastmcp.task_management.application.services.facade_service.FacadeService.get_unified_context_facade'):
            with patch('fastmcp.task_management.application.services.task_context_sync_service.GetTaskUseCase'):
                service = TaskContextSyncService(mock_task_repository)
                return service
    
    @patch('fastmcp.task_management.application.services.task_context_sync_service.validate_user_id')
    @pytest.mark.asyncio
    async def test_sync_context_user_authentication_error(self, mock_validate_user, service):
        """Test context sync with user authentication error"""
        from fastmcp.task_management.domain.exceptions.authentication_exceptions import UserAuthenticationRequiredError
        
        mock_validate_user.side_effect = UserAuthenticationRequiredError("Invalid user")
        
        with pytest.raises(UserAuthenticationRequiredError) as exc_info:
            await service.sync_context_and_get_task("task-123", user_id="invalid-user")
        
        assert "Invalid user" in str(exc_info.value)
    
    @patch('fastmcp.task_management.application.services.task_context_sync_service.validate_user_id')
    @patch('fastmcp.task_management.application.services.task_context_sync_service.TaskId')
    @pytest.mark.asyncio
    async def test_sync_context_invalid_task_id(self, mock_task_id_class, mock_validate_user, service):
        """Test context sync with invalid task ID - ValueError is re-raised"""
        # Setup authentication
        mock_validate_user.return_value = "user-123"
        
        # Setup TaskId to raise exception
        mock_task_id_class.from_string.side_effect = ValueError("Invalid task ID format")
        
        with pytest.raises(ValueError) as exc_info:
            await service.sync_context_and_get_task("invalid-task-id", user_id="user-123")
        
        assert "Invalid task ID format" in str(exc_info.value)
    
    @patch('fastmcp.task_management.application.services.task_context_sync_service.validate_user_id')
    @pytest.mark.asyncio
    async def test_sync_context_git_branch_repository_error(self, mock_validate_user, service, mock_task_repository):
        """Test context sync when git branch repository fails"""
        # Setup authentication
        mock_validate_user.return_value = "user-123"
        
        # Setup task entity without project_id
        mock_task = Mock(spec=Task)
        mock_task.id = TaskId.from_string("12345678-1234-5678-1234-567812345678")
        mock_task.title = "Test Task"
        mock_task.description = "Test Description"
        mock_task.status = TaskStatus.TODO
        mock_task.priority = Priority.medium()
        mock_task.assignees = []
        mock_task.labels = []
        mock_task.estimated_effort = None
        mock_task.due_date = None
        mock_task.git_branch_id = "branch-123"
        
        mock_task_repository.find_by_id.return_value = mock_task
        
        # Setup git branch repository to raise exception
        with patch('fastmcp.task_management.infrastructure.repositories.orm.git_branch_repository.ORMGitBranchRepository') as mock_git_repo_class:
            mock_git_repo_class.side_effect = Exception("Git repository error")
            
            with patch('fastmcp.task_management.application.services.facade_service.FacadeService.get_unified_context_facade'):
                with patch('fastmcp.task_management.application.services.task_context_sync_service.GetTaskUseCase'):
                    # Test that project_id is required even when git repository has errors
                    with pytest.raises(ValueError, match="project_id is required"):
                        await service.sync_context_and_get_task("task-123", user_id="user-123")
                    
                    # Test with project_id provided - should return None due to repository error
                    result = await service.sync_context_and_get_task("task-123", user_id="user-123", project_id="test-project")
                    assert result is None


class TestTaskContextSyncServiceSyncSubtaskCounts:
    """Test suite for sync_subtask_counts method"""

    @pytest.fixture
    def mock_task_repository(self):
        """Create a mock task repository"""
        repo = Mock(spec=TaskRepository)
        return repo

    @pytest.fixture
    def mock_subtask_repository(self):
        """Create a mock subtask repository"""
        repo = Mock()
        repo.find_by_parent_task_id = Mock()
        repo.with_user = Mock(return_value=repo)
        return repo

    @pytest.fixture
    def mock_context_service(self):
        """Create a mock context service"""
        service = Mock()
        service.get_context = Mock()
        service.update_context = Mock()
        return service

    @pytest.fixture
    def service(self, mock_task_repository, mock_context_service):
        """Create service instance with mocked dependencies"""
        with patch('fastmcp.task_management.application.services.facade_service.FacadeService.get_unified_context_facade') as mock_get_facade:
            mock_get_facade.return_value = mock_context_service
            with patch('fastmcp.task_management.application.services.task_context_sync_service.GetTaskUseCase'):
                service = TaskContextSyncService(mock_task_repository, mock_context_service)
                return service

    @pytest.fixture
    def mock_subtasks(self):
        """Create mock subtasks with different statuses"""
        subtask1 = Mock()
        subtask1.id = TaskId.from_string("11111111-1111-1111-1111-111111111111")
        subtask1.title = "Subtask 1"
        subtask1.description = "Description 1"
        subtask1.status = "done"
        subtask1.assignees = ["user-1"]
        subtask1.progress_notes = "Completed"

        subtask2 = Mock()
        subtask2.id = TaskId.from_string("22222222-2222-2222-2222-222222222222")
        subtask2.title = "Subtask 2"
        subtask2.description = "Description 2"
        subtask2.status = "in_progress"
        subtask2.assignees = ["user-2"]
        subtask2.progress_notes = "Working on it"

        subtask3 = Mock()
        subtask3.id = TaskId.from_string("33333333-3333-3333-3333-333333333333")
        subtask3.title = "Subtask 3"
        subtask3.description = None
        subtask3.status = "todo"
        subtask3.assignees = []
        subtask3.progress_notes = ""

        return [subtask1, subtask2, subtask3]

    @pytest.mark.asyncio
    async def test_sync_subtask_counts_calculates_correctly(self, service, mock_subtask_repository, mock_context_service, mock_subtasks):
        """Test that subtask counts are calculated correctly"""
        # Setup
        task_id = "12345678-1234-5678-1234-567812345678"
        mock_subtask_repository.find_by_parent_task_id.return_value = mock_subtasks
        mock_context_service.get_context.return_value = {
            "success": True,
            "context_data": {"metadata": {}}
        }

        # Execute
        await service.sync_subtask_counts(task_id, mock_subtask_repository)

        # Verify counts calculation
        mock_context_service.update_context.assert_called_once()
        call_args = mock_context_service.update_context.call_args
        context_data = call_args[1]["data"]

        assert context_data["subtasks"]["total_count"] == 3
        assert context_data["subtasks"]["completed_count"] == 1  # Only subtask1 is done
        # Progress: 1/3 * 100 = 33.33...
        assert abs(context_data["subtasks"]["progress_percentage"] - 33.33) < 0.01

    @pytest.mark.asyncio
    async def test_sync_subtask_counts_updates_progress_percentage(self, service, mock_subtask_repository, mock_context_service):
        """Test that progress percentage is updated correctly"""
        # Setup - all subtasks completed
        task_id = "12345678-1234-5678-1234-567812345678"
        completed_subtasks = []
        for i in range(4):
            st = Mock()
            st.id = TaskId.from_string(f"{i}{i}{i}{i}{i}{i}{i}{i}-1111-1111-1111-111111111111")
            st.title = f"Subtask {i}"
            st.description = f"Desc {i}"
            st.status = "completed"
            st.assignees = []
            st.progress_notes = ""
            completed_subtasks.append(st)

        mock_subtask_repository.find_by_parent_task_id.return_value = completed_subtasks
        mock_context_service.get_context.return_value = {
            "success": True,
            "context_data": {}
        }

        # Execute
        await service.sync_subtask_counts(task_id, mock_subtask_repository)

        # Verify 100% progress
        call_args = mock_context_service.update_context.call_args
        context_data = call_args[1]["data"]
        assert context_data["subtasks"]["progress_percentage"] == 100.0

    @pytest.mark.asyncio
    async def test_sync_subtask_counts_builds_items_array(self, service, mock_subtask_repository, mock_context_service, mock_subtasks):
        """Test that subtask items array is built correctly"""
        task_id = "12345678-1234-5678-1234-567812345678"
        mock_subtask_repository.find_by_parent_task_id.return_value = mock_subtasks
        mock_context_service.get_context.return_value = {
            "success": True,
            "context_data": {}
        }

        # Execute
        await service.sync_subtask_counts(task_id, mock_subtask_repository)

        # Verify items array structure
        call_args = mock_context_service.update_context.call_args
        subtask_items = call_args[1]["data"]["subtasks"]["items"]

        assert len(subtask_items) == 3

        # Verify first item structure
        assert subtask_items[0]["id"] == "11111111-1111-1111-1111-111111111111"
        assert subtask_items[0]["title"] == "Subtask 1"
        assert subtask_items[0]["description"] == "Description 1"
        assert subtask_items[0]["status"] == "done"
        assert subtask_items[0]["completed"] is True
        assert subtask_items[0]["assignees"] == ["user-1"]
        assert subtask_items[0]["progress_notes"] == "Completed"

        # Verify third item (with None description)
        assert subtask_items[2]["description"] == ""
        assert subtask_items[2]["completed"] is False

    @pytest.mark.asyncio
    async def test_sync_subtask_counts_handles_empty_subtasks(self, service, mock_subtask_repository, mock_context_service):
        """Test handling when there are no subtasks"""
        task_id = "12345678-1234-5678-1234-567812345678"
        mock_subtask_repository.find_by_parent_task_id.return_value = []
        mock_context_service.get_context.return_value = {
            "success": True,
            "context_data": {}
        }

        # Execute
        await service.sync_subtask_counts(task_id, mock_subtask_repository)

        # Verify empty counts
        call_args = mock_context_service.update_context.call_args
        context_data = call_args[1]["data"]

        assert context_data["subtasks"]["total_count"] == 0
        assert context_data["subtasks"]["completed_count"] == 0
        assert context_data["subtasks"]["progress_percentage"] == 0.0
        assert context_data["subtasks"]["items"] == []

    @pytest.mark.asyncio
    async def test_sync_subtask_counts_handles_missing_context_gracefully(self, service, mock_subtask_repository, mock_context_service, mock_subtasks):
        """Test that sync handles missing context gracefully"""
        task_id = "12345678-1234-5678-1234-567812345678"
        mock_subtask_repository.find_by_parent_task_id.return_value = mock_subtasks
        mock_context_service.get_context.return_value = None  # No context exists

        # Execute - should not raise exception
        await service.sync_subtask_counts(task_id, mock_subtask_repository)

        # Verify update was not called
        mock_context_service.update_context.assert_not_called()

    @pytest.mark.asyncio
    async def test_sync_subtask_counts_handles_repository_error(self, service, mock_subtask_repository, mock_context_service):
        """Test error handling when repository fails"""
        task_id = "12345678-1234-5678-1234-567812345678"
        mock_subtask_repository.find_by_parent_task_id.side_effect = Exception("Database error")

        # Execute - should not raise exception (error is logged)
        await service.sync_subtask_counts(task_id, mock_subtask_repository)

        # Verify update was not called due to error
        mock_context_service.update_context.assert_not_called()

    @pytest.mark.asyncio
    async def test_sync_subtask_counts_with_user_scoped_repository(self, mock_task_repository, mock_subtask_repository, mock_context_service, mock_subtasks):
        """Test that user-scoped repository is used when user_id is set"""
        task_id = "12345678-1234-5678-1234-567812345678"

        # Create service with user context
        with patch('fastmcp.task_management.application.services.facade_service.FacadeService.get_unified_context_facade') as mock_get_facade:
            mock_get_facade.return_value = mock_context_service
            with patch('fastmcp.task_management.application.services.task_context_sync_service.GetTaskUseCase'):
                service = TaskContextSyncService(mock_task_repository, mock_context_service, user_id="user-123")

                # Setup
                mock_user_repo = Mock()
                mock_user_repo.find_by_parent_task_id.return_value = mock_subtasks
                mock_subtask_repository.with_user.return_value = mock_user_repo

                mock_context_service.get_context.return_value = {
                    "success": True,
                    "context_data": {}
                }

                # Execute
                await service.sync_subtask_counts(task_id, mock_subtask_repository)

                # Verify user-scoped repository was used
                mock_subtask_repository.with_user.assert_called_once_with("user-123")
                mock_user_repo.find_by_parent_task_id.assert_called_once()


class TestTaskContextSyncServiceSyncTaskStatus:
    """Test suite for sync_task_status method"""

    @pytest.fixture
    def mock_task_repository(self):
        """Create a mock task repository"""
        return Mock(spec=TaskRepository)

    @pytest.fixture
    def mock_context_service(self):
        """Create a mock context service"""
        service = Mock()
        service.get_context = Mock()
        service.update_context = Mock()
        return service

    @pytest.fixture
    def service(self, mock_task_repository, mock_context_service):
        """Create service instance with mocked dependencies"""
        with patch('fastmcp.task_management.application.services.facade_service.FacadeService.get_unified_context_facade') as mock_get_facade:
            mock_get_facade.return_value = mock_context_service
            with patch('fastmcp.task_management.application.services.task_context_sync_service.GetTaskUseCase'):
                service = TaskContextSyncService(mock_task_repository, mock_context_service)
                return service

    @pytest.mark.asyncio
    async def test_sync_task_status_updates_metadata(self, service, mock_context_service):
        """Test that task status is synced to context metadata"""
        task_id = "12345678-1234-5678-1234-567812345678"
        new_status = "in_progress"

        # Setup existing context
        mock_context_service.get_context.return_value = {
            "success": True,
            "context_data": {
                "metadata": {"status": "todo"}
            }
        }

        # Execute
        await service.sync_task_status(task_id, new_status)

        # Verify status was updated
        mock_context_service.update_context.assert_called_once()
        call_args = mock_context_service.update_context.call_args
        context_data = call_args[1]["data"]

        assert context_data["metadata"]["status"] == "in_progress"

    @pytest.mark.asyncio
    async def test_sync_task_status_creates_metadata_section(self, service, mock_context_service):
        """Test that metadata section is created if missing"""
        task_id = "12345678-1234-5678-1234-567812345678"
        new_status = "done"

        # Setup context without metadata
        mock_context_service.get_context.return_value = {
            "success": True,
            "context_data": {}
        }

        # Execute
        await service.sync_task_status(task_id, new_status)

        # Verify metadata was created with status
        call_args = mock_context_service.update_context.call_args
        context_data = call_args[1]["data"]

        assert "metadata" in context_data
        assert context_data["metadata"]["status"] == "done"

    @pytest.mark.asyncio
    async def test_sync_task_status_handles_missing_context(self, service, mock_context_service):
        """Test that sync handles missing context gracefully"""
        task_id = "12345678-1234-5678-1234-567812345678"
        new_status = "blocked"

        # Setup - no context exists
        mock_context_service.get_context.return_value = None

        # Execute - should not raise exception
        await service.sync_task_status(task_id, new_status)

        # Verify update was not called
        mock_context_service.update_context.assert_not_called()

    @pytest.mark.asyncio
    async def test_sync_task_status_handles_error(self, service, mock_context_service):
        """Test error handling during status sync"""
        task_id = "12345678-1234-5678-1234-567812345678"
        new_status = "in_progress"

        # Setup context service to raise exception
        mock_context_service.get_context.side_effect = Exception("Context service error")

        # Execute - should not raise exception (error is logged)
        await service.sync_task_status(task_id, new_status)

        # Verify update was not called due to error
        mock_context_service.update_context.assert_not_called()


class TestTaskContextSyncServiceSyncTaskMetadata:
    """Test suite for sync_task_metadata method"""

    @pytest.fixture
    def mock_task_repository(self):
        """Create a mock task repository"""
        return Mock(spec=TaskRepository)

    @pytest.fixture
    def mock_context_service(self):
        """Create a mock context service"""
        service = Mock()
        service.get_context = Mock()
        service.update_context = Mock()
        return service

    @pytest.fixture
    def service(self, mock_task_repository, mock_context_service):
        """Create service instance with mocked dependencies"""
        with patch('fastmcp.task_management.application.services.facade_service.FacadeService.get_unified_context_facade') as mock_get_facade:
            mock_get_facade.return_value = mock_context_service
            with patch('fastmcp.task_management.application.services.task_context_sync_service.GetTaskUseCase'):
                service = TaskContextSyncService(mock_task_repository, mock_context_service)
                return service

    @pytest.fixture
    def mock_task_entity(self):
        """Create a comprehensive mock task entity"""
        task = Mock(spec=Task)
        task.status = TaskStatus.IN_PROGRESS
        task.priority = Priority.high()
        task.labels = ["bug", "urgent"]
        task.assignees = ["user-1", "@user-2", "user-3"]
        task.created_at = datetime(2025, 1, 15, 10, 30, 0)
        task.updated_at = datetime(2025, 1, 20, 14, 45, 30)
        task.estimated_effort = "3 days"
        return task

    @pytest.mark.asyncio
    async def test_sync_task_metadata_copies_all_fields(self, service, mock_context_service, mock_task_entity):
        """Test that all metadata fields are synced correctly"""
        task_id = "12345678-1234-5678-1234-567812345678"

        # Setup existing context
        mock_context_service.get_context.return_value = {
            "success": True,
            "context_data": {}
        }

        # Execute
        await service.sync_task_metadata(task_id, mock_task_entity)

        # Verify all fields were synced
        call_args = mock_context_service.update_context.call_args
        context_data = call_args[1]["data"]

        # Check metadata fields
        assert context_data["metadata"]["status"] == "in_progress"
        assert context_data["metadata"]["priority"] == "high"
        assert context_data["metadata"]["labels"] == ["bug", "urgent"]
        assert context_data["metadata"]["created_at"] == "2025-01-15T10:30:00"
        assert context_data["metadata"]["updated_at"] == "2025-01-20T14:45:30"

        # Check objective fields
        assert context_data["objective"]["estimated_effort"] == "3 days"

    @pytest.mark.asyncio
    async def test_sync_task_metadata_adds_at_prefix_to_assignees(self, service, mock_context_service, mock_task_entity):
        """Test that assignees get @ prefix added correctly"""
        task_id = "12345678-1234-5678-1234-567812345678"

        mock_context_service.get_context.return_value = {
            "success": True,
            "context_data": {}
        }

        # Execute
        await service.sync_task_metadata(task_id, mock_task_entity)

        # Verify @ prefix handling
        call_args = mock_context_service.update_context.call_args
        assignees = call_args[1]["data"]["metadata"]["assignees"]

        assert assignees == ["@user-1", "@user-2", "@user-3"]
        # Verify that "@user-2" wasn't double-prefixed
        assert "@@user-2" not in assignees

    @pytest.mark.asyncio
    async def test_sync_task_metadata_creates_sections_if_missing(self, service, mock_context_service, mock_task_entity):
        """Test that metadata and objective sections are created if missing"""
        task_id = "12345678-1234-5678-1234-567812345678"

        # Setup context without metadata or objective
        mock_context_service.get_context.return_value = {
            "success": True,
            "context_data": {"some_other_field": "value"}
        }

        # Execute
        await service.sync_task_metadata(task_id, mock_task_entity)

        # Verify sections were created
        call_args = mock_context_service.update_context.call_args
        context_data = call_args[1]["data"]

        assert "metadata" in context_data
        assert "objective" in context_data
        assert "some_other_field" in context_data  # Existing data preserved

    @pytest.mark.asyncio
    async def test_sync_task_metadata_handles_missing_optional_fields(self, service, mock_context_service):
        """Test handling of tasks with missing optional fields"""
        task_id = "12345678-1234-5678-1234-567812345678"

        # Create task without optional fields
        minimal_task = Mock(spec=Task)
        minimal_task.status = TaskStatus.TODO
        minimal_task.priority = Priority.low()
        # No labels attribute
        # No assignees attribute
        # No timestamps
        # No estimated_effort

        mock_context_service.get_context.return_value = {
            "success": True,
            "context_data": {}
        }

        # Execute - should not raise exception
        await service.sync_task_metadata(task_id, minimal_task)

        # Verify basic fields were synced
        call_args = mock_context_service.update_context.call_args
        context_data = call_args[1]["data"]

        assert context_data["metadata"]["status"] == "todo"
        assert context_data["metadata"]["priority"] == "low"

    @pytest.mark.asyncio
    async def test_sync_task_metadata_handles_missing_context(self, service, mock_context_service, mock_task_entity):
        """Test that sync handles missing context gracefully"""
        task_id = "12345678-1234-5678-1234-567812345678"

        # Setup - no context exists
        mock_context_service.get_context.return_value = None

        # Execute - should not raise exception
        await service.sync_task_metadata(task_id, mock_task_entity)

        # Verify update was not called
        mock_context_service.update_context.assert_not_called()

    @pytest.mark.asyncio
    async def test_sync_task_metadata_handles_error(self, service, mock_context_service, mock_task_entity):
        """Test error handling during metadata sync"""
        task_id = "12345678-1234-5678-1234-567812345678"

        # Setup context service to raise exception
        mock_context_service.get_context.side_effect = Exception("Sync error")

        # Execute - should not raise exception (error is logged)
        await service.sync_task_metadata(task_id, mock_task_entity)

        # Verify update was not called due to error
        mock_context_service.update_context.assert_not_called()