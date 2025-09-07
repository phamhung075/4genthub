"""
Comprehensive tests for CreateTaskUseCase

This module tests the CreateTaskUseCase functionality including:
- Task creation with various parameters
- Validation scenarios and error handling
- Context creation integration
- User authentication and isolation
- Branch validation and task counting
"""

import pytest
from unittest.mock import Mock, patch, MagicMock
from datetime import datetime
from typing import Optional

from fastmcp.task_management.application.use_cases.create_task import CreateTaskUseCase
from fastmcp.task_management.application.dtos.task import (
    CreateTaskRequest,
    CreateTaskResponse,
    TaskResponse
)
from fastmcp.task_management.domain.entities.task import Task
from fastmcp.task_management.domain.value_objects import TaskStatus, Priority
from fastmcp.task_management.domain.value_objects.task_status import TaskStatusEnum
from fastmcp.task_management.domain.value_objects.priority import PriorityLevel
from fastmcp.task_management.domain.value_objects.task_id import TaskId
from fastmcp.task_management.domain.exceptions.authentication_exceptions import UserAuthenticationRequiredError


class TestCreateTaskUseCase:
    """Test suite for CreateTaskUseCase"""
    
    @pytest.fixture
    def mock_task_repository(self):
        """Create a mock task repository"""
        repository = Mock()
        repository.get_next_id.return_value = TaskId("test-task-id")
        repository.save.return_value = True
        repository.git_branch_exists.return_value = True
        return repository
    
    @pytest.fixture
    def use_case(self, mock_task_repository):
        """Create CreateTaskUseCase instance with mock repository"""
        return CreateTaskUseCase(mock_task_repository)
    
    @pytest.fixture
    def basic_request(self):
        """Create a basic CreateTaskRequest"""
        return CreateTaskRequest(
            title="Test Task",
            description="Test task description",
            git_branch_id="branch-123",
            status="todo",
            priority="medium",
            user_id="user-123"
        )
    
    def test_create_task_success_basic(self, use_case, mock_task_repository, basic_request):
        """Test successful task creation with basic parameters"""
        # Mock Task.create to return a task entity
        mock_task = Mock(spec=Task)
        mock_task.id = TaskId("test-task-id")
        mock_task.title = "Test Task"
        mock_task.description = "Test task description"
        mock_task.git_branch_id = "branch-123"
        mock_task.status = TaskStatus(TaskStatusEnum.TODO.value)
        mock_task.priority = Priority(PriorityLevel.MEDIUM.label)
        mock_task.get_events.return_value = []
        mock_task.set_context_id = Mock()
        
        with patch('fastmcp.task_management.domain.entities.task.Task.create', return_value=mock_task), \
             patch('fastmcp.task_management.infrastructure.database.database_config.get_session'), \
             patch('fastmcp.task_management.application.factories.unified_context_facade_factory.UnifiedContextFacadeFactory') as mock_factory:
            
            # Mock context facade
            mock_context_facade = Mock()
            mock_context_facade.create_context.return_value = {"success": True}
            mock_factory.return_value.create_facade.return_value = mock_context_facade
            
            response = use_case.execute(basic_request)
        
        assert response.success is True
        assert response.task is not None
        assert response.task.title == "Test Task"
        assert response.error is None
        mock_task_repository.save.assert_called_once()
    
    def test_create_task_with_long_title(self, use_case, mock_task_repository):
        """Test task creation with title longer than 200 characters"""
        long_title = "a" * 250
        request = CreateTaskRequest(
            title=long_title,
            description="Test description",
            git_branch_id="branch-123",
            user_id="user-123"
        )
        
        mock_task = Mock(spec=Task)
        mock_task.id = TaskId("test-task-id")
        mock_task.title = long_title[:200]  # Should be truncated
        mock_task.get_events.return_value = []
        mock_task.set_context_id = Mock()
        
        with patch('fastmcp.task_management.domain.entities.task.Task.create', return_value=mock_task), \
             patch('fastmcp.task_management.infrastructure.database.database_config.get_session'), \
             patch('fastmcp.task_management.application.factories.unified_context_facade_factory.UnifiedContextFacadeFactory') as mock_factory:
            
            mock_context_facade = Mock()
            mock_context_facade.create_context.return_value = {"success": True}
            mock_factory.return_value.create_facade.return_value = mock_context_facade
            
            response = use_case.execute(request)
        
        assert response.success is True
        # Verify title was truncated in Task.create call
        Task.create.assert_called_once()
        call_args = Task.create.call_args[1]
        assert len(call_args['title']) == 200
    
    def test_create_task_with_long_description(self, use_case, mock_task_repository):
        """Test task creation with description longer than 1000 characters"""
        long_description = "b" * 1100
        request = CreateTaskRequest(
            title="Test Task",
            description=long_description,
            git_branch_id="branch-123",
            user_id="user-123"
        )
        
        mock_task = Mock(spec=Task)
        mock_task.id = TaskId("test-task-id")
        mock_task.description = long_description[:1000]  # Should be truncated
        mock_task.get_events.return_value = []
        mock_task.set_context_id = Mock()
        
        with patch('fastmcp.task_management.domain.entities.task.Task.create', return_value=mock_task), \
             patch('fastmcp.task_management.infrastructure.database.database_config.get_session'), \
             patch('fastmcp.task_management.application.factories.unified_context_facade_factory.UnifiedContextFacadeFactory') as mock_factory:
            
            mock_context_facade = Mock()
            mock_context_facade.create_context.return_value = {"success": True}
            mock_factory.return_value.create_facade.return_value = mock_context_facade
            
            response = use_case.execute(request)
        
        assert response.success is True
        # Verify description was truncated in Task.create call
        Task.create.assert_called_once()
        call_args = Task.create.call_args[1]
        assert len(call_args['description']) == 1000
    
    def test_create_task_invalid_git_branch_id(self, use_case, mock_task_repository):
        """Test task creation with non-existent git_branch_id"""
        mock_task_repository.git_branch_exists.return_value = False
        
        request = CreateTaskRequest(
            title="Test Task",
            description="Test description",
            git_branch_id="invalid-branch-123",
            user_id="user-123"
        )
        
        response = use_case.execute(request)
        
        assert response.success is False
        assert "git_branch_id 'invalid-branch-123' does not exist" in response.error
        mock_task_repository.save.assert_not_called()
    
    def test_create_task_with_dependencies(self, use_case, mock_task_repository):
        """Test task creation with valid dependencies"""
        request = CreateTaskRequest(
            title="Test Task",
            description="Test description",
            git_branch_id="branch-123",
            dependencies=["dep-1", "dep-2"],
            user_id="user-123"
        )
        
        mock_task = Mock(spec=Task)
        mock_task.id = TaskId("test-task-id")
        mock_task.add_dependency = Mock()
        mock_task.get_events.return_value = []
        mock_task.set_context_id = Mock()
        
        with patch('fastmcp.task_management.domain.entities.task.Task.create', return_value=mock_task), \
             patch('fastmcp.task_management.infrastructure.database.database_config.get_session'), \
             patch('fastmcp.task_management.application.factories.unified_context_facade_factory.UnifiedContextFacadeFactory') as mock_factory:
            
            mock_context_facade = Mock()
            mock_context_facade.create_context.return_value = {"success": True}
            mock_factory.return_value.create_facade.return_value = mock_context_facade
            
            response = use_case.execute(request)
        
        assert response.success is True
        # Verify dependencies were added
        assert mock_task.add_dependency.call_count == 2
        mock_task.add_dependency.assert_any_call(TaskId("dep-1"))
        mock_task.add_dependency.assert_any_call(TaskId("dep-2"))
    
    def test_create_task_invalid_dependency_ids(self, use_case, mock_task_repository, caplog):
        """Test task creation with invalid dependency IDs"""
        request = CreateTaskRequest(
            title="Test Task",
            description="Test description",
            git_branch_id="branch-123",
            dependencies=["", "   ", "valid-dep"],
            user_id="user-123"
        )
        
        mock_task = Mock(spec=Task)
        mock_task.id = TaskId("test-task-id")
        mock_task.add_dependency = Mock(side_effect=[None, None, ValueError("Invalid dependency")])
        mock_task.get_events.return_value = []
        mock_task.set_context_id = Mock()
        
        with patch('fastmcp.task_management.domain.entities.task.Task.create', return_value=mock_task), \
             patch('fastmcp.task_management.infrastructure.database.database_config.get_session'), \
             patch('fastmcp.task_management.application.factories.unified_context_facade_factory.UnifiedContextFacadeFactory') as mock_factory:
            
            mock_context_facade = Mock()
            mock_context_facade.create_context.return_value = {"success": True}
            mock_factory.return_value.create_facade.return_value = mock_context_facade
            
            response = use_case.execute(request)
        
        assert response.success is True
        # Only valid dependency should be processed (empty strings are skipped)
        assert mock_task.add_dependency.call_count == 1
        # Check that warning was logged for invalid dependency
        assert "Skipping invalid dependency" in caplog.text
    
    def test_save_failure(self, use_case, mock_task_repository):
        """Test handling of repository save failure"""
        mock_task_repository.save.return_value = False  # Simulate save failure
        
        request = CreateTaskRequest(
            title="Test Task",
            description="Test description",
            git_branch_id="branch-123",
            user_id="user-123"
        )
        
        mock_task = Mock(spec=Task)
        mock_task.get_events.return_value = []
        
        with patch('fastmcp.task_management.domain.entities.task.Task.create', return_value=mock_task):
            response = use_case.execute(request)
        
        assert response.success is False
        assert "Failed to save task to database" in response.error
    
    def test_branch_task_count_update(self, use_case, mock_task_repository):
        """Test that branch task count is updated after successful task creation"""
        request = CreateTaskRequest(
            title="Test Task",
            description="Test description",
            git_branch_id="branch-123",
            user_id="user-123"
        )
        
        mock_task = Mock(spec=Task)
        mock_task.id = TaskId("test-task-id")
        mock_task.get_events.return_value = []
        mock_task.set_context_id = Mock()
        
        # Mock database session and branch
        mock_session = Mock()
        mock_branch = Mock()
        mock_branch.task_count = 5
        mock_session.query.return_value.filter.return_value.first.return_value = mock_branch
        
        with patch('fastmcp.task_management.domain.entities.task.Task.create', return_value=mock_task), \
             patch('fastmcp.task_management.infrastructure.database.database_config.get_session', return_value=mock_session), \
             patch('fastmcp.task_management.application.factories.unified_context_facade_factory.UnifiedContextFacadeFactory') as mock_factory:
            
            mock_context_facade = Mock()
            mock_context_facade.create_context.return_value = {"success": True}
            mock_factory.return_value.create_facade.return_value = mock_context_facade
            
            response = use_case.execute(request)
        
        assert response.success is True
        # Verify task count was incremented
        assert mock_branch.task_count == 6
        mock_session.commit.assert_called_once()
    
    def test_missing_user_id_authentication_error(self, use_case, mock_task_repository):
        """Test that missing user_id raises UserAuthenticationRequiredError during context creation"""
        request = CreateTaskRequest(
            title="Test Task",
            description="Test description",
            git_branch_id="branch-123"
            # No user_id provided
        )
        
        mock_task = Mock(spec=Task)
        mock_task.id = TaskId("test-task-id")
        mock_task.get_events.return_value = []
        mock_task.set_context_id = Mock()
        
        with patch('fastmcp.task_management.domain.entities.task.Task.create', return_value=mock_task), \
             patch('fastmcp.task_management.infrastructure.database.database_config.get_session'):
            
            response = use_case.execute(request)
        
        # Task should be created successfully, but context creation should fail
        # The use case logs context errors but doesn't fail task creation
        assert response.success is True
        # Context creation should not have been attempted due to missing user_id
    
    def test_context_creation_failure_doesnt_fail_task(self, use_case, mock_task_repository, caplog):
        """Test that context creation failure doesn't prevent task creation"""
        request = CreateTaskRequest(
            title="Test Task",
            description="Test description",
            git_branch_id="branch-123",
            user_id="user-123"
        )
        
        mock_task = Mock(spec=Task)
        mock_task.id = TaskId("test-task-id")
        mock_task.get_events.return_value = []
        mock_task.set_context_id = Mock()
        
        with patch('fastmcp.task_management.domain.entities.task.Task.create', return_value=mock_task), \
             patch('fastmcp.task_management.infrastructure.database.database_config.get_session'), \
             patch('fastmcp.task_management.application.factories.unified_context_facade_factory.UnifiedContextFacadeFactory') as mock_factory:
            
            # Mock context facade to fail
            mock_context_facade = Mock()
            mock_context_facade.create_context.return_value = {"success": False, "error": "Context creation failed"}
            mock_factory.return_value.create_facade.return_value = mock_context_facade
            
            response = use_case.execute(request)
        
        assert response.success is True  # Task creation should still succeed
        # Check that context creation failure was logged
        assert "Failed to create task context" in caplog.text
    
    def test_invalid_status_value_error(self, use_case, mock_task_repository):
        """Test that invalid status raises ValueError"""
        request = CreateTaskRequest(
            title="Test Task",
            description="Test description",
            git_branch_id="branch-123",
            status="invalid_status",
            user_id="user-123"
        )
        
        with patch('fastmcp.task_management.domain.value_objects.TaskStatus') as mock_status:
            mock_status.side_effect = ValueError("Invalid status")
            
            with pytest.raises(ValueError, match="Invalid status"):
                use_case.execute(request)
        
        mock_task_repository.save.assert_not_called()
    
    def test_invalid_priority_value_error(self, use_case, mock_task_repository):
        """Test that invalid priority raises ValueError"""
        request = CreateTaskRequest(
            title="Test Task",
            description="Test description",
            git_branch_id="branch-123",
            priority="invalid_priority",
            user_id="user-123"
        )
        
        with patch('fastmcp.task_management.domain.value_objects.Priority') as mock_priority:
            mock_priority.side_effect = ValueError("Invalid priority")
            
            with pytest.raises(ValueError, match="Invalid priority"):
                use_case.execute(request)
        
        mock_task_repository.save.assert_not_called()
    
    def test_general_exception_handling(self, use_case, mock_task_repository):
        """Test handling of general exceptions during task creation"""
        request = CreateTaskRequest(
            title="Test Task",
            description="Test description",
            git_branch_id="branch-123",
            user_id="user-123"
        )
        
        # Mock Task.create to raise a general exception
        with patch('fastmcp.task_management.domain.entities.task.Task.create', side_effect=RuntimeError("Database error")):
            response = use_case.execute(request)
        
        assert response.success is False
        assert "Failed to create task: Database error" in response.error
        mock_task_repository.save.assert_not_called()
    
    def test_default_values_applied_correctly(self, use_case, mock_task_repository):
        """Test that default values are applied correctly when not provided"""
        request = CreateTaskRequest(
            title="Test Task",
            description="Test description",
            git_branch_id="branch-123",
            user_id="user-123"
            # No status or priority provided
        )
        
        mock_task = Mock(spec=Task)
        mock_task.id = TaskId("test-task-id")
        mock_task.get_events.return_value = []
        mock_task.set_context_id = Mock()
        
        with patch('fastmcp.task_management.domain.entities.task.Task.create', return_value=mock_task) as mock_create, \
             patch('fastmcp.task_management.infrastructure.database.database_config.get_session'), \
             patch('fastmcp.task_management.application.factories.unified_context_facade_factory.UnifiedContextFacadeFactory') as mock_factory:
            
            mock_context_facade = Mock()
            mock_context_facade.create_context.return_value = {"success": True}
            mock_factory.return_value.create_facade.return_value = mock_context_facade
            
            response = use_case.execute(request)
        
        assert response.success is True
        
        # Verify Task.create was called with default values
        call_args = mock_create.call_args[1]
        assert str(call_args['status']) == TaskStatusEnum.TODO.value
        assert str(call_args['priority']) == PriorityLevel.MEDIUM.label
    
    def test_context_creation_success_sets_context_id(self, use_case, mock_task_repository):
        """Test that successful context creation sets context_id on task"""
        request = CreateTaskRequest(
            title="Test Task",
            description="Test description",
            git_branch_id="branch-123",
            user_id="user-123"
        )
        
        mock_task = Mock(spec=Task)
        mock_task.id = TaskId("test-task-id")
        mock_task.get_events.return_value = []
        mock_task.set_context_id = Mock()
        
        with patch('fastmcp.task_management.domain.entities.task.Task.create', return_value=mock_task), \
             patch('fastmcp.task_management.infrastructure.database.database_config.get_session'), \
             patch('fastmcp.task_management.application.factories.unified_context_facade_factory.UnifiedContextFacadeFactory') as mock_factory:
            
            mock_context_facade = Mock()
            mock_context_facade.create_context.return_value = {"success": True}
            mock_factory.return_value.create_facade.return_value = mock_context_facade
            
            response = use_case.execute(request)
        
        assert response.success is True
        # Verify context_id was set on the task
        mock_task.set_context_id.assert_called_once()
        # Verify repository save was called twice (once for initial save, once after context creation)
        assert mock_task_repository.save.call_count == 2