"""Test auto-context creation when creating tasks"""
import pytest
from unittest.mock import MagicMock, patch
from datetime import datetime, timezone

from fastmcp.task_management.application.use_cases.create_task import CreateTaskUseCase
from fastmcp.task_management.application.dtos.task import CreateTaskRequest
from fastmcp.task_management.domain.entities.task import Task
from fastmcp.task_management.domain.value_objects.task_id import TaskId


class TestTaskCreateAutoContext:
    
    def setup_method(self, method):
        """Clean up before each test"""
        # This is a unit test that doesn't need database setup
        pass

    """Test auto-context creation for tasks"""
    
    def test_create_task_auto_creates_context(self):
        """Test that creating a task automatically creates task context"""
        # Arrange
        task_id = "9482917d-bc3d-458c-b747-3b871a4e5fe3"
        git_branch_id = "a582917d-bc3d-458c-b747-3b871a4e5fe3"
        
        # Create mock repository
        mock_task_repo = MagicMock()
        mock_task_repo.get_next_id.return_value = TaskId(task_id)
        mock_task_repo.git_branch_exists.return_value = True
        mock_task_repo.save.return_value = True
        
        # Create request
        request = CreateTaskRequest(
            title="Test Task",
            description="Test Description",
            git_branch_id=git_branch_id,
            status="todo",
            priority="medium",
            user_id="test_user_123"
        )
        
        # Create use case
        use_case = CreateTaskUseCase(mock_task_repo)
        
        # Mock context facade
        with patch('fastmcp.task_management.application.factories.unified_context_facade_factory.UnifiedContextFacadeFactory') as mock_factory_class:
            mock_facade = MagicMock()
            mock_facade.create_context.return_value = {"success": True}
            
            mock_factory = MagicMock()
            mock_factory.create_facade.return_value = mock_facade
            mock_factory_class.return_value = mock_factory
            
            # Act
            result = use_case.execute(request)
        
        # Assert
        assert result.success is True
        assert result.task.id == task_id
        
        # Verify context creation was attempted
        mock_factory.create_facade.assert_called_once_with(
            user_id="test_user_123",
            git_branch_id=git_branch_id
        )
        
        # Verify context was created with correct data
        mock_facade.create_context.assert_called_once()
        context_call = mock_facade.create_context.call_args
        assert context_call[1]["level"] == "task"
        assert context_call[1]["context_id"] == task_id
        assert context_call[1]["data"]["branch_id"] == git_branch_id
        assert context_call[1]["data"]["task_data"]["title"] == "Test Task"
    
    def test_create_task_continues_on_context_failure(self):
        """Test that task creation continues even if context creation fails"""
        # Arrange
        task_id = "6d12f80c-15cd-481f-9d2b-8493cc13b162"
        git_branch_id = "b582917d-bc3d-458c-b747-3b871a4e5fe3"
        
        # Create mock repository
        mock_task_repo = MagicMock()
        mock_task_repo.get_next_id.return_value = TaskId(task_id)
        mock_task_repo.git_branch_exists.return_value = True
        mock_task_repo.save.return_value = True
        
        # Create request
        request = CreateTaskRequest(
            title="Test Task",
            description="Test Description",
            git_branch_id=git_branch_id,
            status="todo",
            priority="medium",
            user_id="test_user_123"
        )
        
        # Create use case
        use_case = CreateTaskUseCase(mock_task_repo)
        
        # Mock context facade to fail
        with patch('fastmcp.task_management.application.factories.unified_context_facade_factory.UnifiedContextFacadeFactory') as mock_factory_class:
            mock_facade = MagicMock()
            mock_facade.create_context.return_value = {"success": False, "error": "Context creation failed"}
            
            mock_factory = MagicMock()
            mock_factory.create_facade.return_value = mock_facade
            mock_factory_class.return_value = mock_factory
            
            # Act
            result = use_case.execute(request)
        
        # Assert - Task creation should still succeed
        assert result.success is True
        assert result.task.id == task_id
        
        # Verify context creation was attempted
        mock_factory.create_facade.assert_called_once()
        mock_facade.create_context.assert_called_once()
    
    def test_create_task_handles_context_exception(self):
        """Test that task creation handles exceptions during context creation"""
        # Arrange
        task_id = "a910f283-20d5-42c6-871a-f4f4101c8f63"
        git_branch_id = "c582917d-bc3d-458c-b747-3b871a4e5fe3"
        
        # Create mock repository
        mock_task_repo = MagicMock()
        mock_task_repo.get_next_id.return_value = TaskId(task_id)
        mock_task_repo.git_branch_exists.return_value = True
        mock_task_repo.save.return_value = True
        
        # Create request
        request = CreateTaskRequest(
            title="Test Task",
            description="Test Description",
            git_branch_id=git_branch_id,
            status="todo",
            priority="medium",
            user_id="test_user_123"
        )
        
        # Create use case
        use_case = CreateTaskUseCase(mock_task_repo)
        
        # Mock context facade to raise exception
        with patch('fastmcp.task_management.application.factories.unified_context_facade_factory.UnifiedContextFacadeFactory') as mock_factory_class:
            mock_factory_class.side_effect = Exception("Context system unavailable")
            
            # Act
            result = use_case.execute(request)
        
        # Assert - Task creation should still succeed
        assert result.success is True
        assert result.task.id == task_id
    
    def test_create_task_with_dependencies_and_context(self):
        """Test that task creation with dependencies still creates context"""
        # Arrange
        task_id = "d910f283-20d5-42c6-871a-f4f4101c8f63"
        git_branch_id = "e582917d-bc3d-458c-b747-3b871a4e5fe3"
        dependency_id = "f910f283-20d5-42c6-871a-f4f4101c8f63"
        
        # Create mock repository
        mock_task_repo = MagicMock()
        mock_task_repo.get_next_id.return_value = TaskId(task_id)
        mock_task_repo.git_branch_exists.return_value = True
        mock_task_repo.save.return_value = True
        
        # Create request with dependencies
        request = CreateTaskRequest(
            title="Test Task",
            description="Test Description",
            git_branch_id=git_branch_id,
            status="todo",
            priority="medium",
            dependencies=[dependency_id],
            user_id="test_user_123"
        )
        
        # Create use case
        use_case = CreateTaskUseCase(mock_task_repo)
        
        # Mock context facade
        with patch('fastmcp.task_management.application.factories.unified_context_facade_factory.UnifiedContextFacadeFactory') as mock_factory_class:
            mock_facade = MagicMock()
            mock_facade.create_context.return_value = {"success": True}
            
            mock_factory = MagicMock()
            mock_factory.create_facade.return_value = mock_facade
            mock_factory_class.return_value = mock_factory
            
            # Act
            result = use_case.execute(request)
        
        # Assert
        assert result.success is True
        assert result.task.id == task_id
        
        # Verify context creation was attempted
        mock_factory.create_facade.assert_called_once_with(
            user_id="test_user_123",
            git_branch_id=git_branch_id
        )
        mock_facade.create_context.assert_called_once()