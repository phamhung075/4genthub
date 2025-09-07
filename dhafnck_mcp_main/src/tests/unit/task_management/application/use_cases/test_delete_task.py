"""
Tests for Delete Task Use Case
"""

import pytest
from unittest.mock import Mock, MagicMock, patch
import logging

from fastmcp.task_management.application.use_cases.delete_task import DeleteTaskUseCase
from fastmcp.task_management.domain.repositories.task_repository import TaskRepository
from fastmcp.task_management.domain.entities.task import Task
from fastmcp.task_management.domain.value_objects.task_id import TaskId
from fastmcp.task_management.domain.value_objects.task_status import TaskStatus
from fastmcp.task_management.domain.value_objects.priority import Priority
from fastmcp.task_management.domain.events import TaskDeleted
from fastmcp.task_management.domain.interfaces.database_session import IDatabaseSessionFactory
from fastmcp.task_management.domain.interfaces.logging_service import ILoggingService
from datetime import datetime


class TestDeleteTaskUseCase:
    """Test the DeleteTaskUseCase class"""
    
    @pytest.fixture
    def mock_task_repository(self):
        """Create a mock task repository"""
        return Mock(spec=TaskRepository)
    
    @pytest.fixture
    def mock_db_session_factory(self):
        """Create a mock database session factory"""
        mock_factory = Mock(spec=IDatabaseSessionFactory)
        mock_session = MagicMock()
        # Create a context manager mock
        context_manager = MagicMock()
        context_manager.__enter__.return_value = mock_session
        context_manager.__exit__.return_value = None
        mock_factory.create_session.return_value = context_manager
        return mock_factory
    
    @pytest.fixture
    def mock_logger(self):
        """Create a mock logger"""
        return Mock()
    
    @pytest.fixture
    def mock_logging_service(self, mock_logger):
        """Create a mock logging service"""
        mock_service = Mock(spec=ILoggingService)
        mock_service.get_logger.return_value = mock_logger
        return mock_service
    
    @pytest.fixture
    def use_case(self, mock_task_repository, mock_db_session_factory, mock_logging_service):
        """Create a use case instance with mocked dependencies"""
        return DeleteTaskUseCase(
            task_repository=mock_task_repository,
            db_session_factory=mock_db_session_factory,
            logging_service=mock_logging_service
        )
    
    @pytest.fixture
    def sample_task(self):
        """Create a sample task entity"""
        task = Mock(spec=Task)
        task.id = TaskId("12345678-1234-5678-1234-567812345678")
        task.git_branch_id = "branch-456"
        task.title = "Test Task"
        task.status = TaskStatus.TODO
        task.priority = Priority.high()
        task.created_at = datetime.now()
        task.updated_at = datetime.now()
        
        # Mock domain events
        task_deleted_event = TaskDeleted(
            task_id=task.id,
            title=task.title,
            deleted_at=datetime.now()
        )
        task.get_events.return_value = [task_deleted_event]
        task.mark_as_deleted.return_value = None
        
        return task
    
    def test_execute_successful_deletion_with_string_id(self, use_case, mock_task_repository, sample_task):
        """Test successful task deletion with string ID"""
        # Arrange
        task_id = "12345678-1234-5678-1234-567812345678"
        mock_task_repository.find_by_id.return_value = sample_task
        mock_task_repository.delete.return_value = True
        
        # Act
        result = use_case.execute(task_id)
        
        # Assert
        assert result is True
        
        # Verify repository interactions
        mock_task_repository.find_by_id.assert_called_once()
        called_task_id = mock_task_repository.find_by_id.call_args[0][0]
        assert isinstance(called_task_id, TaskId)
        assert str(called_task_id) == task_id
        
        # Verify task was marked as deleted and repository delete was called
        sample_task.mark_as_deleted.assert_called_once()
        mock_task_repository.delete.assert_called_once()
        
        # Verify domain events were processed
        sample_task.get_events.assert_called_once()
    
    def test_execute_successful_deletion_with_integer_id(self, use_case, mock_task_repository, sample_task):
        """Test successful task deletion with integer ID"""
        # Arrange
        task_id = 12345
        mock_task_repository.find_by_id.return_value = sample_task
        mock_task_repository.delete.return_value = True
        
        # Act
        result = use_case.execute(task_id)
        
        # Assert
        assert result is True
        
        # Verify repository interactions
        mock_task_repository.find_by_id.assert_called_once()
        called_task_id = mock_task_repository.find_by_id.call_args[0][0]
        assert isinstance(called_task_id, TaskId)
        
        # Verify task processing
        sample_task.mark_as_deleted.assert_called_once()
        mock_task_repository.delete.assert_called_once()
    
    def test_execute_task_not_found(self, use_case, mock_task_repository):
        """Test deletion when task is not found"""
        # Arrange
        task_id = "99999999-9999-9999-9999-999999999999"  # Valid UUID format but non-existent
        mock_task_repository.find_by_id.return_value = None
        
        # Act
        result = use_case.execute(task_id)
        
        # Assert
        assert result is False
        
        # Verify only find was called, not delete
        mock_task_repository.find_by_id.assert_called_once()
        mock_task_repository.delete.assert_not_called()
    
    def test_execute_repository_delete_fails(self, use_case, mock_task_repository, sample_task):
        """Test when repository delete operation fails"""
        # Arrange
        task_id = "12345678-1234-5678-1234-567812345678"
        mock_task_repository.find_by_id.return_value = sample_task
        mock_task_repository.delete.return_value = False  # Delete fails
        
        # Act
        result = use_case.execute(task_id)
        
        # Assert
        assert result is False
        
        # Verify task was found and marked as deleted but delete failed
        sample_task.mark_as_deleted.assert_called_once()
        mock_task_repository.delete.assert_called_once()
        
        # Events should not be processed on failure
        sample_task.get_events.assert_not_called()
    
    def test_execute_with_git_branch_id_update_success(self, use_case, mock_task_repository, 
                                                       sample_task, mock_db_session_factory, mock_logger):
        """Test successful deletion with git branch ID update"""
        # Arrange
        task_id = "12345678-1234-5678-1234-567812345678"
        sample_task.git_branch_id = "branch-789"
        mock_task_repository.find_by_id.return_value = sample_task
        mock_task_repository.delete.return_value = True
        
        # Act
        result = use_case.execute(task_id)
        
        # Assert
        assert result is True
        
        # Verify database session was used for branch update
        mock_db_session_factory.create_session.assert_called_once()
        
        # Verify info logging about branch update
        mock_logger.info.assert_called()
        info_calls = [call[0][0] for call in mock_logger.info.call_args_list]
        branch_update_logged = any("should update branch" in msg for msg in info_calls)
        assert branch_update_logged
    
    def test_execute_with_git_branch_id_update_exception(self, use_case, mock_task_repository, 
                                                        sample_task, mock_db_session_factory, mock_logger):
        """Test deletion with git branch ID update exception"""
        # Arrange
        task_id = "12345678-1234-5678-1234-567812345678"
        sample_task.git_branch_id = "branch-789"
        mock_task_repository.find_by_id.return_value = sample_task
        mock_task_repository.delete.return_value = True
        
        # Make session creation raise an exception
        mock_db_session_factory.create_session.side_effect = Exception("Database error")
        
        # Act
        result = use_case.execute(task_id)
        
        # Assert
        assert result is True  # Should still succeed despite branch update failure
        
        # Verify warning was logged
        mock_logger.warning.assert_called()
        warning_calls = [call[0][0] for call in mock_logger.warning.call_args_list]
        branch_error_logged = any("Failed to update branch task count" in msg for msg in warning_calls)
        assert branch_error_logged
    
    def test_execute_without_git_branch_id(self, use_case, mock_task_repository, sample_task, mock_logger):
        """Test deletion of task without git_branch_id"""
        # Arrange
        task_id = "12345678-1234-5678-1234-567812345678"
        # Remove git_branch_id from task
        del sample_task.git_branch_id
        mock_task_repository.find_by_id.return_value = sample_task
        mock_task_repository.delete.return_value = True
        
        # Act
        result = use_case.execute(task_id)
        
        # Assert
        assert result is True
        
        # Verify no branch update info was logged
        info_calls = [call[0][0] for call in mock_logger.info.call_args_list] if mock_logger.info.called else []
        branch_update_logged = any("should update branch" in msg for msg in info_calls)
        assert not branch_update_logged
    
    def test_execute_domain_events_processing(self, use_case, mock_task_repository, sample_task):
        """Test domain events are properly processed"""
        # Arrange
        task_id = "12345678-1234-5678-1234-567812345678"
        mock_task_repository.find_by_id.return_value = sample_task
        mock_task_repository.delete.return_value = True
        
        # Create multiple events
        task_deleted_event = TaskDeleted(
            task_id=sample_task.id,
            title=sample_task.title,
            deleted_at=datetime.now()
        )
        other_event = Mock()  # Non-TaskDeleted event
        sample_task.get_events.return_value = [task_deleted_event, other_event]
        
        # Act
        result = use_case.execute(task_id)
        
        # Assert
        assert result is True
        
        # Verify events were retrieved and processed
        sample_task.get_events.assert_called_once()
    
    @pytest.mark.parametrize("task_id_input,expected_conversion", [
        ("11111111-1111-1111-1111-111111111111", "string"),  # Valid UUID format
        (12345, "int"),
        (0, "int"),
        ("22222222-2222-2222-2222-222222222222", "string"),  # Valid UUID format
        ("12345678-1234-5678-1234-567812345678", "string"),
    ])
    def test_task_id_conversion(self, use_case, mock_task_repository, sample_task, 
                               task_id_input, expected_conversion):
        """Test task ID conversion for different input types"""
        # Arrange
        mock_task_repository.find_by_id.return_value = sample_task
        mock_task_repository.delete.return_value = True
        
        # Act
        result = use_case.execute(task_id_input)
        
        # Assert
        assert result is True
        
        # Verify correct conversion method was used
        mock_task_repository.find_by_id.assert_called_once()
        called_task_id = mock_task_repository.find_by_id.call_args[0][0]
        assert isinstance(called_task_id, TaskId)
    
    def test_logging_initialization(self, mock_task_repository, mock_logging_service, mock_logger):
        """Test proper logger initialization"""
        # Arrange & Act
        use_case = DeleteTaskUseCase(
            task_repository=mock_task_repository,
            logging_service=mock_logging_service
        )
        
        # Assert
        mock_logging_service.get_logger.assert_called_once()
        logger_call_args = mock_logging_service.get_logger.call_args[0][0]
        assert "delete_task" in logger_call_args
    
    def test_execute_task_without_hasattr_git_branch_id(self, use_case, mock_task_repository):
        """Test deletion of task that doesn't have git_branch_id attribute"""
        # Arrange
        task_id = "12345678-1234-5678-1234-567812345678"
        task_without_branch = Mock(spec=Task)
        task_without_branch.id = TaskId(task_id)
        task_without_branch.get_events.return_value = []
        task_without_branch.mark_as_deleted.return_value = None
        # Simulate hasattr returning False
        
        mock_task_repository.find_by_id.return_value = task_without_branch
        mock_task_repository.delete.return_value = True
        
        # Act
        result = use_case.execute(task_id)
        
        # Assert
        assert result is True
        task_without_branch.mark_as_deleted.assert_called_once()
        mock_task_repository.delete.assert_called_once()
    
    def test_execute_with_none_git_branch_id(self, use_case, mock_task_repository, sample_task, mock_logger):
        """Test deletion when git_branch_id is None"""
        # Arrange
        task_id = "12345678-1234-5678-1234-567812345678"
        sample_task.git_branch_id = None  # Explicitly None
        mock_task_repository.find_by_id.return_value = sample_task
        mock_task_repository.delete.return_value = True
        
        # Act
        result = use_case.execute(task_id)
        
        # Assert
        assert result is True
        
        # Verify no branch update info was logged
        info_calls = [call[0][0] for call in mock_logger.info.call_args_list] if mock_logger.info.called else []
        branch_update_logged = any("should update branch" in msg for msg in info_calls)
        assert not branch_update_logged