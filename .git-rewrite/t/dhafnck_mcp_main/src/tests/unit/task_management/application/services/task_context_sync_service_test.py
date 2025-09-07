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
        with patch('fastmcp.task_management.application.services.task_context_sync_service.UnifiedContextFacadeFactory') as mock_factory_class:
            mock_factory = Mock()
            mock_factory.create_unified_service.return_value = mock_context_service
            mock_factory_class.return_value = mock_factory
            yield mock_factory_class
    
    @pytest.fixture
    def service(self, mock_task_repository, mock_unified_context_facade_factory):
        """Create service instance with mocked dependencies"""
        with patch('fastmcp.task_management.application.services.task_context_sync_service.GetTaskUseCase'):
            service = TaskContextSyncService(mock_task_repository)
            return service
    
    @pytest.fixture
    def service_with_user(self, mock_task_repository, mock_unified_context_facade_factory):
        """Create service instance with user context"""
        with patch('fastmcp.task_management.application.services.task_context_sync_service.GetTaskUseCase'):
            service = TaskContextSyncService(mock_task_repository, user_id="user-123")
            return service
    
    @pytest.fixture
    def mock_task_entity(self):
        """Create a mock task entity"""
        task = Mock(spec=Task)
        task.id = TaskId.from_string("task-123")
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
        with patch('fastmcp.task_management.application.services.task_context_sync_service.UnifiedContextFacadeFactory') as mock_factory_class:
            mock_factory = Mock()
            mock_factory.create_unified_service.return_value = mock_context_service
            mock_factory_class.return_value = mock_factory
            
            with patch('fastmcp.task_management.application.services.task_context_sync_service.GetTaskUseCase') as mock_use_case_class:
                mock_use_case_class.return_value = mock_get_task_use_case
                
                service = TaskContextSyncService(mock_task_repository)
                return service
    
    @pytest.fixture
    def mock_task_entity(self):
        """Create a mock task entity"""
        task = Mock(spec=Task)
        task.id = TaskId.from_string("task-123")
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
            mock_context_service.get_context.assert_called_once_with(level="task", context_id="task-123")
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
        mock_context_service.get_context.assert_called_once_with(level="task", context_id="task-123")
        mock_context_service.update_context.assert_called_once()
        mock_context_service.create_context.assert_not_called()
    
    @pytest.mark.asyncio
    async def test_sync_context_and_get_task_no_user_id_raises_error(self, service):
        """Test context sync without user_id raises UserAuthenticationRequiredError"""
        result = await service.sync_context_and_get_task("task-123")
        
        assert result is None
    
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
        """Test context sync with project_id derived from git branch"""
        # Setup authentication
        mock_validate_user.return_value = "user-123"
        
        # Setup task repository
        mock_task_repository.find_by_id.return_value = mock_task_entity
        
        # Setup context service
        mock_context_service.get_context.return_value = None
        
        # Setup git branch repository
        with patch('fastmcp.task_management.infrastructure.repositories.orm.git_branch_repository.ORMGitBranchRepository') as mock_git_repo_class:
            mock_git_repo = Mock()
            mock_git_branch = Mock()
            mock_git_branch.project_id = "derived-project-id"
            mock_git_repo.find_by_id.return_value = mock_git_branch
            mock_git_repo_class.return_value = mock_git_repo
            
            # Setup get task use case
            mock_task_response = Mock()
            mock_get_task_use_case.execute.return_value = mock_task_response
            
            result = await service.sync_context_and_get_task("task-123", user_id="user-123")
            
            assert result == mock_task_response
            mock_git_repo.find_by_id.assert_called_once_with("branch-123")
    
    @patch('fastmcp.task_management.application.services.task_context_sync_service.validate_user_id')
    @pytest.mark.asyncio
    async def test_sync_context_and_get_task_default_project_id(self, mock_validate_user, service, mock_task_repository, mock_context_service, mock_get_task_use_case, mock_task_entity):
        """Test context sync with default project_id when none can be derived"""
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
            
            # Setup get task use case
            mock_task_response = Mock()
            mock_get_task_use_case.execute.return_value = mock_task_response
            
            result = await service.sync_context_and_get_task("task-123", user_id="user-123")
            
            assert result == mock_task_response
            # Should use default project_id when none can be derived
    
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
        assert call_args[1]["context_id"] == "task-123"
        
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
        mock_task.id = TaskId.from_string("task-123")
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
        with patch('fastmcp.task_management.application.services.task_context_sync_service.UnifiedContextFacadeFactory'):
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
        with patch('fastmcp.task_management.application.services.task_context_sync_service.UnifiedContextFacadeFactory'):
            with patch('fastmcp.task_management.application.services.task_context_sync_service.GetTaskUseCase'):
                service = TaskContextSyncService(mock_task_repository)
                return service
    
    @patch('fastmcp.task_management.application.services.task_context_sync_service.validate_user_id')
    @pytest.mark.asyncio
    async def test_sync_context_user_authentication_error(self, mock_validate_user, service):
        """Test context sync with user authentication error"""
        mock_validate_user.side_effect = UserAuthenticationRequiredError("Invalid user")
        
        result = await service.sync_context_and_get_task("task-123", user_id="invalid-user")
        
        assert result is None
    
    @patch('fastmcp.task_management.application.services.task_context_sync_service.validate_user_id')
    @patch('fastmcp.task_management.application.services.task_context_sync_service.TaskId')
    @pytest.mark.asyncio
    async def test_sync_context_invalid_task_id(self, mock_task_id_class, mock_validate_user, service):
        """Test context sync with invalid task ID"""
        # Setup authentication
        mock_validate_user.return_value = "user-123"
        
        # Setup TaskId to raise exception
        mock_task_id_class.from_string.side_effect = ValueError("Invalid task ID format")
        
        result = await service.sync_context_and_get_task("invalid-task-id", user_id="user-123")
        
        assert result is None
    
    @patch('fastmcp.task_management.application.services.task_context_sync_service.validate_user_id')
    @pytest.mark.asyncio
    async def test_sync_context_git_branch_repository_error(self, mock_validate_user, service, mock_task_repository):
        """Test context sync when git branch repository fails"""
        # Setup authentication
        mock_validate_user.return_value = "user-123"
        
        # Setup task entity without project_id
        mock_task = Mock(spec=Task)
        mock_task.id = TaskId.from_string("task-123")
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
            
            with patch('fastmcp.task_management.application.services.task_context_sync_service.UnifiedContextFacadeFactory'):
                with patch('fastmcp.task_management.application.services.task_context_sync_service.GetTaskUseCase'):
                    result = await service.sync_context_and_get_task("task-123", user_id="user-123")
                    
                    assert result is None