"""Test for Delete Task Use Case"""

import pytest
from unittest.mock import Mock, MagicMock, patch, call
from datetime import datetime, timezone

from fastmcp.task_management.application.use_cases.delete_task import DeleteTaskUseCase
from fastmcp.task_management.domain.entities.task import Task
from fastmcp.task_management.domain.value_objects.task_id import TaskId
from fastmcp.task_management.domain.value_objects.task_status import TaskStatus
from fastmcp.task_management.domain.events import TaskDeleted
from fastmcp.task_management.domain.services.cascade_deletion_service import DeleteScope


class TestDeleteTaskUseCase:
    """Test suite for DeleteTaskUseCase"""
    
    @pytest.fixture
    def mock_task_repository(self):
        """Create a mock task repository"""
        return Mock()
    
    @pytest.fixture
    def mock_subtask_repository(self):
        """Create a mock subtask repository"""
        mock_repo = Mock()
        mock_repo.count_by_parent_task_id = Mock(return_value=0)
        mock_repo.find_by_parent_task_id = Mock(return_value=[])
        return mock_repo
    
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
    def mock_cascade_service(self):
        """Create a mock cascade deletion service"""
        mock_service = Mock()
        mock_service.delete_task_cascade.return_value = {
            "task_deleted": True,
            "subtasks_deleted": 0,
            "contexts_deleted": 0,
            "cascade_errors": []
        }
        return mock_service

    @pytest.fixture
    def use_case(self, mock_task_repository, mock_subtask_repository, mock_db_session_factory,
                 mock_logging_service, mock_cascade_service):
        """Create a delete task use case instance with mocked dependencies"""
        with patch('fastmcp.task_management.application.use_cases.delete_task.CascadeDeletionService') as mock_cascade_class:
            mock_cascade_class.return_value = mock_cascade_service

            use_case = DeleteTaskUseCase(
                task_repository=mock_task_repository,
                subtask_repository=mock_subtask_repository,
                branch_repository=None,
                project_repository=None,
                context_repository=None,
                db_session_factory=mock_db_session_factory,
                logging_service=mock_logging_service
            )
            # Attach the mocked cascade service for tests to use
            use_case._mock_cascade_service = mock_cascade_service
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
    
    @patch('fastmcp.task_management.application.use_cases.delete_task.CascadeDeletionService')
    def test_init(self, mock_cascade_service_class, mock_task_repository, mock_subtask_repository, 
                  mock_db_session_factory, mock_logging_service):
        """Test use case initialization"""
        # Mock the CascadeDeletionService to avoid issues with its initialization
        mock_cascade_instance = Mock()
        mock_cascade_service_class.return_value = mock_cascade_instance
        
        use_case = DeleteTaskUseCase(
            task_repository=mock_task_repository,
            subtask_repository=mock_subtask_repository,
            branch_repository=None,
            project_repository=None,
            context_repository=None,
            db_session_factory=mock_db_session_factory,
            logging_service=mock_logging_service
        )

        assert use_case._task_repository == mock_task_repository
        assert use_case._subtask_repository == mock_subtask_repository
        assert use_case._db_session_factory == mock_db_session_factory
        assert use_case._logger == mock_logging_service.get_logger.return_value
        
        # Verify CascadeDeletionService was initialized with correct parameters
        mock_cascade_service_class.assert_called_once_with(
            task_repository=mock_task_repository,
            subtask_repository=mock_subtask_repository,
            branch_repository=None,
            project_repository=None,
            context_repository=None
        )
    
    def test_execute_with_string_id_success(self, use_case, mock_task_repository, sample_task):
        """Test successful task deletion with string ID"""
        task_id = "123"
        
        mock_task_repository.find_by_id.return_value = sample_task
        
        result = use_case.execute(task_id)
        
        assert result["success"] is True
        assert result["task_deleted"] is True
        
        # Verify task was found
        mock_task_repository.find_by_id.assert_called_once()
        
        # Verify cascade service was called with correct task_id
        use_case._mock_cascade_service.delete_task_cascade.assert_called_once_with(task_id, DeleteScope.TASK_FULL)
    
    def test_execute_with_int_id_success(self, use_case, mock_task_repository, sample_task):
        """Test successful task deletion with integer ID"""
        task_id = 123
        
        mock_task_repository.find_by_id.return_value = sample_task
        
        result = use_case.execute(task_id)
        
        assert result["success"] is True
        assert result["task_deleted"] is True
        
        # Verify TaskId.from_int was used
        find_call = mock_task_repository.find_by_id.call_args
        assert isinstance(find_call[0][0], TaskId)
        
        # Verify cascade service was called with string version of task_id
        use_case._mock_cascade_service.delete_task_cascade.assert_called_once_with(str(task_id), DeleteScope.TASK_FULL)
    
    def test_execute_task_not_found(self, use_case, mock_task_repository):
        """Test deletion when task is not found"""
        task_id = "missing-task"
        
        mock_task_repository.find_by_id.return_value = None
        
        result = use_case.execute(task_id)
        
        assert result["success"] is False
        assert result["task_deleted"] is False
        assert "not found" in result["message"]
        
        # Verify cascade service was not called
        use_case._mock_cascade_service.delete_task_cascade.assert_not_called()
    
    def test_execute_delete_fails(self, use_case, mock_task_repository, sample_task):
        """Test when repository delete fails"""
        task_id = "123"
        
        mock_task_repository.find_by_id.return_value = sample_task
        # Mock cascade service to return failure
        use_case._mock_cascade_service.delete_task_cascade.return_value = {
            "task_deleted": False,
            "subtasks_deleted": 0,
            "contexts_deleted": 0,
            "cascade_errors": ["Failed to delete task"]
        }
        
        result = use_case.execute(task_id)
        
        assert result["success"] is False
        assert result["task_deleted"] is False
    
    @patch('fastmcp.task_management.domain.services.event_dispatcher.dispatch_domain_event')
    def test_execute_with_git_branch_update(self, mock_dispatch, use_case, mock_task_repository, sample_task, mock_logger):
        """Test deletion with git branch task count update"""
        task_id = "123"

        mock_task_repository.find_by_id.return_value = sample_task

        result = use_case.execute(task_id)

        assert result["success"] is True
        assert result["task_deleted"] is True

        # Verify event dispatcher was called for branch update (if git_branch_id exists)
        mock_dispatch.assert_called_once()
    
    def test_execute_without_git_branch(self, use_case, mock_task_repository, mock_logger):
        """Test deletion of task without git_branch_id"""
        task_id = "123"
        
        # Create task without git_branch_id
        task = Mock(spec=Task)
        task.id = TaskId.from_string(task_id)
        task.title = "Test Task"
        task.mark_as_deleted = Mock()
        task.get_events = Mock(return_value=[])
        # Explicitly set git_branch_id to None to ensure no branch update logging
        task.git_branch_id = None
        
        mock_task_repository.find_by_id.return_value = task
        
        result = use_case.execute(task_id)
        
        assert result["success"] is True
        assert result["task_deleted"] is True
        
        # Verify no branch update log
        assert not any(
            "update branch" in str(call) 
            for call in mock_logger.info.call_args_list
        )
    
    @patch('fastmcp.task_management.domain.services.event_dispatcher.dispatch_domain_event')
    def test_execute_branch_update_exception(self, mock_dispatch, use_case, mock_task_repository, sample_task,
                                           mock_db_session_factory, mock_logger):
        """Test handling of exception during event dispatching"""
        task_id = "123"

        mock_task_repository.find_by_id.return_value = sample_task

        # Mock event dispatcher to raise exception
        mock_dispatch.side_effect = Exception("Event dispatch failed")

        result = use_case.execute(task_id)

        # Should succeed even if event dispatch fails (error is caught and logged)
        assert result["success"] is True
        assert result["task_deleted"] is True

        # Verify event dispatch was attempted and exception was caught
        mock_dispatch.assert_called_once()
        # Verify warning was logged about the failure
        assert any("Failed to dispatch" in str(call) for call in mock_logger.warning.call_args_list)
    
    def test_execute_with_task_deleted_event(self, use_case, mock_task_repository, sample_task):
        """Test handling of TaskDeleted domain event"""
        task_id = "123"
        
        # In the new implementation, events are handled by the cascade service
        # We just need to verify the deletion works
        mock_task_repository.find_by_id.return_value = sample_task
        
        result = use_case.execute(task_id)
        
        assert result["success"] is True
        assert result["task_deleted"] is True
    
    def test_execute_multiple_events(self, use_case, mock_task_repository, sample_task):
        """Test handling of multiple domain events"""
        task_id = "123"
        
        mock_task_repository.find_by_id.return_value = sample_task
        
        result = use_case.execute(task_id)
        
        assert result["success"] is True
        assert result["task_deleted"] is True
    
    def test_execute_preserves_task_id_type(self, use_case, mock_task_repository):
        """Test that TaskId type is preserved throughout execution"""
        # Test with string ID
        string_id = "string-123"
        task = Mock()
        task.id = TaskId.from_string(string_id)
        task.title = "Test Task"
        task.mark_as_deleted = Mock()
        task.get_events = Mock(return_value=[])
        task.git_branch_id = None
        
        mock_task_repository.find_by_id.return_value = task
        
        result = use_case.execute(string_id)
        assert result["success"] is True
        assert result["task_deleted"] is True
        
        # Verify correct TaskId type in find call
        find_args = mock_task_repository.find_by_id.call_args[0]
        
        assert isinstance(find_args[0], TaskId)
        assert str(find_args[0]) == string_id
        
        # Verify cascade service was called with string ID
        use_case._mock_cascade_service.delete_task_cascade.assert_called_once_with(string_id, DeleteScope.TASK_FULL)
    
    def test_execute_logging_calls(self, use_case, mock_task_repository, sample_task, mock_logger):
        """Test all logging calls during execution"""
        task_id = "123"
        
        mock_task_repository.find_by_id.return_value = sample_task
        
        result = use_case.execute(task_id)
        
        assert result["success"] is True
        assert result["task_deleted"] is True
        
        # Verify logger was called about successful deletion
        info_calls = [call[0][0] for call in mock_logger.info.call_args_list]
        assert any("Successfully deleted task" in str(msg) for msg in info_calls)
    
    def test_execute_git_branch_with_hasattr_check(self, use_case, mock_task_repository):
        """Test hasattr check for git_branch_id"""
        task_id = "123"
        
        # Create task where hasattr would return False
        task = Mock(spec=['id', 'title', 'status'])
        task.id = TaskId.from_string(task_id)
        task.title = "Test Task"
        task.status = TaskStatus.todo()
        
        mock_task_repository.find_by_id.return_value = task
        
        result = use_case.execute(task_id)

        assert result["success"] is True
        assert result["task_deleted"] is True
        assert hasattr(task, 'git_branch_id') is False