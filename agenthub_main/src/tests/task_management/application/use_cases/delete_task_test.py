"""Test for Delete Task Use Case"""

import pytest
from unittest.mock import Mock, MagicMock, patch, call
from datetime import datetime, timezone

from fastmcp.task_management.application.use_cases.delete_task import DeleteTaskUseCase
from fastmcp.task_management.domain.entities.task import Task
from fastmcp.task_management.domain.value_objects.task_id import TaskId
from fastmcp.task_management.domain.value_objects.task_status import TaskStatus
from fastmcp.task_management.domain.events.task_events import TaskDeleted


class TestDeleteTaskUseCase:
    """Test suite for DeleteTaskUseCase"""
    
    @pytest.fixture
    def mock_task_repository(self):
        """Create a mock task repository"""
        return Mock()
    
    @pytest.fixture  
    def mock_db_session_factory(self):
        """Create a mock database session factory"""
        mock_factory = Mock()
        mock_session = Mock()
        mock_factory.create_session.return_value.__enter__ = Mock(return_value=mock_session)
        mock_factory.create_session.return_value.__exit__ = Mock(return_value=False)
        return mock_factory
    
    @pytest.fixture
    def mock_logger(self):
        """Create a mock logger"""
        return Mock()
    
    @pytest.fixture
    def mock_logging_service(self, mock_logger):
        """Create a mock logging service"""
        mock_service = Mock()
        mock_service.get_logger.return_value = mock_logger
        return mock_service
    
    @pytest.fixture
    def use_case(self, mock_task_repository, mock_db_session_factory, mock_logging_service):
        """Create a delete task use case instance with mocked dependencies"""
        use_case = DeleteTaskUseCase(
            task_repository=mock_task_repository,
            db_session_factory=mock_db_session_factory,
            logging_service=mock_logging_service
        )
        return use_case
    
    @pytest.fixture
    def sample_task(self):
        """Create a sample task"""
        task = Mock(spec=Task)
        task.id = TaskId.from_string("45645645-6456-4564-5645-645645645645")
        task.title = "Test Task"
        task.status = TaskStatus.todo()
        task.git_branch_id = "branch-123"
        
        # Mock methods
        task.mark_as_deleted = Mock()
        task.get_events = Mock(return_value=[])
        
        return task
    
    def test_init(self, mock_task_repository, mock_db_session_factory, mock_logging_service):
        """Test use case initialization"""
        use_case = DeleteTaskUseCase(
            task_repository=mock_task_repository,
            db_session_factory=mock_db_session_factory,
            logging_service=mock_logging_service
        )

        assert use_case._task_repository == mock_task_repository
        assert use_case._db_session_factory == mock_db_session_factory
        assert use_case._logger == mock_logging_service.get_logger.return_value
    
    def test_execute_with_string_id_success(self, use_case, mock_task_repository, sample_task):
        """Test successful task deletion with string ID"""
        task_id = "123"
        
        mock_task_repository.find_by_id.return_value = sample_task
        mock_task_repository.delete.return_value = True
        
        result = use_case.execute(task_id)
        
        assert result is True
        
        # Verify task was found
        find_call = mock_task_repository.find_by_id.call_args
        assert isinstance(find_call[0][0], TaskId)
        assert str(find_call[0][0]) == task_id
        
        # Verify task was marked as deleted
        sample_task.mark_as_deleted.assert_called_once()
        
        # Verify task was deleted from repository
        delete_call = mock_task_repository.delete.call_args
        assert isinstance(delete_call[0][0], TaskId)
        assert str(delete_call[0][0]) == task_id
    
    def test_execute_with_int_id_success(self, use_case, mock_task_repository, sample_task):
        """Test successful task deletion with integer ID"""
        task_id = 123
        
        mock_task_repository.find_by_id.return_value = sample_task
        mock_task_repository.delete.return_value = True
        
        result = use_case.execute(task_id)
        
        assert result is True
        
        # Verify TaskId.from_int was used
        find_call = mock_task_repository.find_by_id.call_args
        assert isinstance(find_call[0][0], TaskId)
    
    def test_execute_task_not_found(self, use_case, mock_task_repository):
        """Test deletion when task is not found"""
        task_id = "missing-task"
        
        mock_task_repository.find_by_id.return_value = None
        
        result = use_case.execute(task_id)
        
        assert result is False
        
        # Verify delete was not called
        mock_task_repository.delete.assert_not_called()
    
    def test_execute_delete_fails(self, use_case, mock_task_repository, sample_task):
        """Test when repository delete fails"""
        task_id = "123"
        
        mock_task_repository.find_by_id.return_value = sample_task
        mock_task_repository.delete.return_value = False
        
        result = use_case.execute(task_id)
        
        assert result is False
        
        # Verify task was still marked as deleted
        sample_task.mark_as_deleted.assert_called_once()
    
    def test_execute_with_git_branch_update(self, use_case, mock_task_repository, sample_task, mock_logger):
        """Test deletion with git branch task count update"""
        task_id = "123"
        
        mock_task_repository.find_by_id.return_value = sample_task
        mock_task_repository.delete.return_value = True
        
        result = use_case.execute(task_id)
        
        assert result is True
        
        # Verify logger was called about branch update
        mock_logger.info.assert_called_with(
            f"Task deleted, should update branch {sample_task.git_branch_id} task count"
        )
    
    def test_execute_without_git_branch(self, use_case, mock_task_repository, mock_logger):
        """Test deletion of task without git_branch_id"""
        task_id = "123"
        
        # Create task without git_branch_id
        task = Mock(spec=Task)
        task.id = TaskId.from_string(task_id)
        task.mark_as_deleted = Mock()
        task.get_events = Mock(return_value=[])
        # Explicitly set git_branch_id to None to ensure no branch update logging
        task.git_branch_id = None
        
        mock_task_repository.find_by_id.return_value = task
        mock_task_repository.delete.return_value = True
        
        result = use_case.execute(task_id)
        
        assert result is True
        
        # Verify no branch update log
        assert not any(
            "update branch" in str(call) 
            for call in mock_logger.info.call_args_list
        )
    
    def test_execute_branch_update_exception(self, use_case, mock_task_repository, sample_task,
                                           mock_db_session_factory, mock_logger):
        """Test handling of exception during branch update"""
        task_id = "123"
        
        mock_task_repository.find_by_id.return_value = sample_task
        mock_task_repository.delete.return_value = True
        
        # Make session creation raise an exception
        mock_db_session_factory.create_session.side_effect = Exception("DB error")
        
        result = use_case.execute(task_id)
        
        # Should still succeed even if branch update fails
        assert result is True
        
        # Verify warning was logged
        mock_logger.warning.assert_called_with(
            "Failed to update branch task count: DB error"
        )
    
    def test_execute_with_task_deleted_event(self, use_case, mock_task_repository, sample_task):
        """Test handling of TaskDeleted domain event"""
        task_id = "123"
        
        # Create domain events
        task_deleted_event = TaskDeleted(task_id=sample_task.id, title=sample_task.title, deleted_at=datetime.now(timezone.utc))
        other_event = Mock()  # Non-TaskDeleted event
        
        sample_task.get_events.return_value = [task_deleted_event, other_event]
        
        mock_task_repository.find_by_id.return_value = sample_task
        mock_task_repository.delete.return_value = True
        
        result = use_case.execute(task_id)
        
        assert result is True
        
        # Verify events were retrieved
        sample_task.get_events.assert_called_once()
    
    def test_execute_multiple_events(self, use_case, mock_task_repository, sample_task):
        """Test handling of multiple domain events"""
        task_id = "123"
        
        # Create multiple TaskDeleted events
        events = [
            TaskDeleted(task_id=sample_task.id, title=sample_task.title, deleted_at=datetime.now(timezone.utc)),
            TaskDeleted(task_id=sample_task.id, title=sample_task.title, deleted_at=datetime.now(timezone.utc)),
            Mock()  # Different event type
        ]
        
        sample_task.get_events.return_value = events
        
        mock_task_repository.find_by_id.return_value = sample_task
        mock_task_repository.delete.return_value = True
        
        result = use_case.execute(task_id)
        
        assert result is True
    
    def test_execute_preserves_task_id_type(self, use_case, mock_task_repository):
        """Test that TaskId type is preserved throughout execution"""
        # Test with string ID
        string_id = "string-123"
        task = Mock()
        task.id = TaskId.from_string(string_id)
        task.mark_as_deleted = Mock()
        task.get_events = Mock(return_value=[])
        task.git_branch_id = None
        
        mock_task_repository.find_by_id.return_value = task
        mock_task_repository.delete.return_value = True
        
        result = use_case.execute(string_id)
        assert result is True
        
        # Verify correct TaskId type in all calls
        find_args = mock_task_repository.find_by_id.call_args[0]
        delete_args = mock_task_repository.delete.call_args[0]
        
        assert isinstance(find_args[0], TaskId)
        assert isinstance(delete_args[0], TaskId)
        assert str(find_args[0]) == string_id
        assert str(delete_args[0]) == string_id
    
    def test_execute_logging_calls(self, use_case, mock_task_repository, sample_task, mock_logger):
        """Test all logging calls during execution"""
        task_id = "123"
        
        mock_task_repository.find_by_id.return_value = sample_task
        mock_task_repository.delete.return_value = True
        
        # Add a TaskDeleted event
        sample_task.get_events.return_value = [TaskDeleted(task_id=sample_task.id, title=sample_task.title, deleted_at=datetime.now(timezone.utc))]
        
        result = use_case.execute(task_id)
        
        assert result is True
        
        # Verify info log about branch update
        info_calls = [call[0][0] for call in mock_logger.info.call_args_list]
        assert any("Task deleted, should update branch" in msg for msg in info_calls)
        assert f"branch {sample_task.git_branch_id}" in info_calls[0]
    
    def test_execute_git_branch_with_hasattr_check(self, use_case, mock_task_repository):
        """Test hasattr check for git_branch_id"""
        task_id = "123"
        
        # Create task where hasattr would return False
        task = Mock(spec=['id', 'mark_as_deleted', 'get_events'])
        task.id = TaskId.from_string(task_id)
        task.mark_as_deleted = Mock()
        task.get_events = Mock(return_value=[])
        
        mock_task_repository.find_by_id.return_value = task
        mock_task_repository.delete.return_value = True
        
        result = use_case.execute(task_id)
        
        assert result is True
        assert hasattr(task, 'git_branch_id') is False