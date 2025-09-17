"""
Tests for Update Task Use Case
"""

import pytest
import asyncio
from unittest.mock import Mock, AsyncMock, patch, MagicMock
import logging
from datetime import datetime, timezone, date

from fastmcp.task_management.application.use_cases.update_task import UpdateTaskUseCase
from fastmcp.task_management.application.dtos.task import (
    UpdateTaskRequest,
    UpdateTaskResponse,
    TaskResponse
)
from fastmcp.task_management.domain.repositories.task_repository import TaskRepository
from fastmcp.task_management.domain.entities.task import Task
from fastmcp.task_management.domain.value_objects.task_id import TaskId
from fastmcp.task_management.domain.value_objects.task_status import TaskStatus
from fastmcp.task_management.domain.value_objects.priority import Priority
from fastmcp.task_management.domain.exceptions.task_exceptions import TaskNotFoundError
from fastmcp.task_management.domain.events import TaskUpdated


class TestUpdateTaskUseCase:
    """Test the UpdateTaskUseCase class"""
    
    @pytest.fixture
    def mock_task_repository(self):
        """Create a mock task repository"""
        return Mock(spec=TaskRepository)
    
    @pytest.fixture
    def mock_context_sync_service(self):
        """Create a mock context sync service"""
        service = Mock()
        service.sync_context_and_get_task = AsyncMock()
        return service
    
    @pytest.fixture
    def use_case(self, mock_task_repository):
        """Create a use case instance"""
        return UpdateTaskUseCase(task_repository=mock_task_repository)
    
    @pytest.fixture
    def sample_task(self):
        """Create a sample task entity"""
        task = Mock(spec=Task)
        task.id = TaskId("12345678-1234-5678-1234-567812345678")
        task.title = "Original Task"
        task.description = "Original description"
        task.git_branch_id = "branch-456"
        task.project_id = "project-123"
        task.status = TaskStatus.TODO
        task.priority = Priority.medium()
        task.assignees = ["user-1"]
        task.labels = ["original"]
        task.context_id = None
        task.details = "Original details"
        task.estimated_effort = "2 hours"
        task.due_date = None
        task.created_at = datetime.now(timezone.utc)
        task.updated_at = datetime.now(timezone.utc)
        
        # Mock domain methods
        task.update_title = Mock()
        task.update_description = Mock()
        task.update_status = Mock()
        task.update_priority = Mock()
        task.update_details = Mock()
        task.update_estimated_effort = Mock()
        task.update_assignees = Mock()
        task.update_labels = Mock()
        task.update_due_date = Mock()
        task.set_context_id = Mock()
        task.get_events = Mock(return_value=[])
        task.to_dict = Mock(return_value={"id": str(task.id), "title": task.title})
        
        return task
    
    @pytest.fixture
    def basic_update_request(self):
        """Create a basic update request"""
        return UpdateTaskRequest(
            task_id="12345678-1234-5678-1234-567812345678",
            title="Updated Task Title"
        )
    
    @pytest.fixture
    def comprehensive_update_request(self):
        """Create a comprehensive update request with all fields"""
        return UpdateTaskRequest(
            task_id="12345678-1234-5678-1234-567812345678",
            title="Updated Task",
            description="Updated description",
            status="in_progress",
            priority="high",
            details="Updated details",
            estimated_effort="4 hours",
            assignees=["user-1", "user-2"],
            labels=["updated", "important"],
            due_date=date(2023, 12, 31),
            context_id="context-456"
        )
    
    def test_execute_successful_title_update(self, use_case, mock_task_repository, 
                                           sample_task, basic_update_request):
        """Test successful update of task title only"""
        # Arrange
        mock_task_repository.find_by_id.return_value = sample_task
        mock_task_repository.save.return_value = None
        
        with patch('fastmcp.task_management.application.use_cases.update_task.TaskResponse') as mock_task_response:
            with patch('fastmcp.task_management.application.use_cases.update_task.UpdateTaskResponse') as mock_update_response:
                mock_response_instance = Mock()
                mock_task_response.from_domain.return_value = mock_response_instance
                mock_update_response.success_response.return_value = Mock()
                
                # Act
                result = use_case.execute(basic_update_request)
                
                # Assert
                assert result is not None
                
                # Verify task was found (may be called multiple times during update process)
                assert mock_task_repository.find_by_id.called
                # Check the first call has the right task ID
                first_call_args = mock_task_repository.find_by_id.call_args_list[0][0]
                assert isinstance(first_call_args[0], TaskId)
                
                # Verify only title was updated
                sample_task.update_title.assert_called_once_with("Updated Task Title")
                sample_task.update_description.assert_not_called()
                sample_task.update_status.assert_not_called()
                
                # Verify task was saved
                mock_task_repository.save.assert_called_once_with(sample_task)
                
                # Verify response creation
                mock_task_response.from_domain.assert_called_once_with(sample_task)
                mock_update_response.success_response.assert_called_once_with(mock_response_instance)
    
    def test_execute_comprehensive_update(self, use_case, mock_task_repository, 
                                        sample_task, comprehensive_update_request):
        """Test comprehensive update with all fields"""
        # Arrange
        mock_task_repository.find_by_id.return_value = sample_task
        mock_task_repository.save.return_value = None
        
        with patch('fastmcp.task_management.application.use_cases.update_task.TaskResponse') as mock_task_response:
            with patch('fastmcp.task_management.application.use_cases.update_task.UpdateTaskResponse') as mock_update_response:
                mock_response_instance = Mock()
                mock_task_response.from_domain.return_value = mock_response_instance
                mock_update_response.success_response.return_value = Mock()
                
                # Act
                result = use_case.execute(comprehensive_update_request)
                
                # Assert
                assert result is not None
                
                # Verify all update methods were called
                sample_task.update_title.assert_called_once_with("Updated Task")
                sample_task.update_description.assert_called_once_with("Updated description")
                sample_task.update_details.assert_called_once_with("Updated details")
                sample_task.update_estimated_effort.assert_called_once_with("4 hours")
                sample_task.update_assignees.assert_called_once_with(["user-1", "user-2"])
                sample_task.update_labels.assert_called_once_with(["updated", "important"])
                sample_task.update_due_date.assert_called_once_with(date(2023, 12, 31))
                sample_task.set_context_id.assert_called_once_with("context-456")
                
                # Verify status and priority updates with domain objects
                sample_task.update_status.assert_called_once()
                sample_task.update_priority.assert_called_once()
                
                # Verify task was saved
                mock_task_repository.save.assert_called_once_with(sample_task)
    
    def test_execute_task_not_found(self, use_case, mock_task_repository, basic_update_request):
        """Test TaskNotFoundError when task doesn't exist"""
        # Arrange
        mock_task_repository.find_by_id.return_value = None
        
        # Act & Assert
        with pytest.raises(TaskNotFoundError) as exc_info:
            use_case.execute(basic_update_request)
        
        assert f"Task {basic_update_request.task_id} not found" in str(exc_info.value)
        assert mock_task_repository.find_by_id.called
        mock_task_repository.save.assert_not_called()
    
    def test_execute_with_string_task_id(self, use_case, mock_task_repository, sample_task):
        """Test task ID conversion from string"""
        # Arrange
        request = UpdateTaskRequest(task_id="12345678-1234-5678-1234-567812345678", title="Updated")
        mock_task_repository.find_by_id.return_value = sample_task
        mock_task_repository.save.return_value = None
        
        with patch('fastmcp.task_management.application.use_cases.update_task.TaskResponse'):
            with patch('fastmcp.task_management.application.use_cases.update_task.UpdateTaskResponse'):
                # Act
                result = use_case.execute(request)
                
                # Assert
                assert result is not None
                assert mock_task_repository.find_by_id.called
                called_task_id = mock_task_repository.find_by_id.call_args[0][0]
                assert isinstance(called_task_id, TaskId)
    
    def test_execute_with_integer_task_id(self, use_case, mock_task_repository, sample_task):
        """Test task ID conversion from integer"""
        # Arrange
        request = UpdateTaskRequest(task_id=12345, title="Updated")
        mock_task_repository.find_by_id.return_value = sample_task
        mock_task_repository.save.return_value = None
        
        with patch('fastmcp.task_management.application.use_cases.update_task.TaskResponse'):
            with patch('fastmcp.task_management.application.use_cases.update_task.UpdateTaskResponse'):
                # Act
                result = use_case.execute(request)
                
                # Assert
                assert result is not None
                assert mock_task_repository.find_by_id.called
                called_task_id = mock_task_repository.find_by_id.call_args[0][0]
                assert isinstance(called_task_id, TaskId)
    
    def test_execute_with_task_id_object(self, use_case, mock_task_repository, sample_task):
        """Test with TaskId object as input"""
        # Arrange
        task_id_obj = TaskId("12345678-1234-5678-1234-567812345678")
        request = UpdateTaskRequest(task_id=task_id_obj, title="Updated")
        mock_task_repository.find_by_id.return_value = sample_task
        mock_task_repository.save.return_value = None
        
        with patch('fastmcp.task_management.application.use_cases.update_task.TaskResponse'):
            with patch('fastmcp.task_management.application.use_cases.update_task.UpdateTaskResponse'):
                # Act
                result = use_case.execute(request)
                
                # Assert
                assert result is not None
                assert mock_task_repository.find_by_id.called
                # Verify the TaskId object was used
                called_task_id = mock_task_repository.find_by_id.call_args_list[0][0][0]
                assert called_task_id == task_id_obj
    
    def test_execute_context_sync_success(self, use_case, mock_task_repository, sample_task, basic_update_request):
        """Test successful context sync after update"""
        # Arrange
        mock_task_repository.find_by_id.return_value = sample_task
        mock_task_repository.save.return_value = None
        
        # Mock the context sync service import and creation
        with patch('fastmcp.task_management.application.services.task_context_sync_service.TaskContextSyncService') as mock_sync_service_class:
            mock_sync_service = Mock()
            mock_sync_service.sync_context_and_get_task = AsyncMock(return_value=sample_task)
            mock_sync_service_class.return_value = mock_sync_service
            
            with patch('fastmcp.task_management.application.use_cases.update_task.TaskResponse'):
                with patch('fastmcp.task_management.application.use_cases.update_task.UpdateTaskResponse'):
                    # Act
                    result = use_case.execute(basic_update_request)
                    
                    # Assert
                    assert result is not None
                    # Context sync should have been created
                    assert use_case._context_sync_service is not None
    
    def test_execute_context_sync_failure_doesnt_fail_update(self, use_case, mock_task_repository, 
                                                           sample_task, basic_update_request, caplog):
        """Test that context sync failure doesn't fail the update operation"""
        # Arrange
        mock_task_repository.find_by_id.return_value = sample_task
        mock_task_repository.save.return_value = None
        
        with patch.object(use_case, '_sync_task_context_after_update') as mock_sync:
            mock_sync.side_effect = Exception("Context sync failed")
            
            with patch('fastmcp.task_management.application.use_cases.update_task.TaskResponse'):
                with patch('fastmcp.task_management.application.use_cases.update_task.UpdateTaskResponse'):
                    # Act
                    with caplog.at_level(logging.WARNING):
                        result = use_case.execute(basic_update_request)
                    
                    # Assert
                    assert result is not None
                    assert "Context sync failed" in caplog.text
                    assert "task update succeeded" in caplog.text
    
    def test_execute_domain_events_processing(self, use_case, mock_task_repository, 
                                            sample_task, basic_update_request):
        """Test domain events are processed after update"""
        # Arrange
        mock_event = Mock(spec=TaskUpdated)
        sample_task.get_events.return_value = [mock_event]
        mock_task_repository.find_by_id.return_value = sample_task
        mock_task_repository.save.return_value = None
        
        with patch('fastmcp.task_management.application.use_cases.update_task.TaskResponse'):
            with patch('fastmcp.task_management.application.use_cases.update_task.UpdateTaskResponse'):
                # Act
                result = use_case.execute(basic_update_request)
                
                # Assert
                assert result is not None
                sample_task.get_events.assert_called_once()
    
    def test_execute_context_id_set_last(self, use_case, mock_task_repository, sample_task):
        """Test that context_id is set after other updates"""
        # Arrange
        request = UpdateTaskRequest(
            task_id="12345678-1234-5678-1234-567812345678",
            title="Updated Title",
            context_id="new-context-123"
        )
        mock_task_repository.find_by_id.return_value = sample_task
        mock_task_repository.save.return_value = None
        
        # Track call order
        call_order = []
        sample_task.update_title.side_effect = lambda x: call_order.append('title')
        sample_task.set_context_id.side_effect = lambda x: call_order.append('context_id')
        
        with patch('fastmcp.task_management.application.use_cases.update_task.TaskResponse'):
            with patch('fastmcp.task_management.application.use_cases.update_task.UpdateTaskResponse'):
                # Act
                result = use_case.execute(request)
                
                # Assert
                assert result is not None
                assert call_order == ['title', 'context_id']  # context_id should be last
    
    def test_execute_logging_context_id_updates(self, use_case, mock_task_repository, 
                                               sample_task, caplog):
        """Test logging of context_id updates"""
        # Arrange
        request = UpdateTaskRequest(
            task_id="12345678-1234-5678-1234-567812345678",
            context_id="new-context-456"
        )
        sample_task.context_id = "new-context-456"  # Simulate context_id after set
        mock_task_repository.find_by_id.return_value = sample_task
        mock_task_repository.save.return_value = None
        
        with patch('fastmcp.task_management.application.use_cases.update_task.TaskResponse'):
            with patch('fastmcp.task_management.application.use_cases.update_task.UpdateTaskResponse'):
                # Act
                with caplog.at_level(logging.INFO):
                    result = use_case.execute(request)
                
                # Assert
                assert result is not None
                assert "Setting context_id to: new-context-456" in caplog.text
    
    @pytest.mark.parametrize("field_name,field_value", [
        ("title", "New Title"),
        ("description", "New Description"),
        ("status", "done"),
        ("priority", "low"),
        ("details", "New Details"),
        ("estimated_effort", "5 hours"),
        ("assignees", ["new-user"]),
        ("labels", ["new-label"]),
        ("due_date", date(2024, 1, 1)),
        ("context_id", "new-context"),
    ])
    def test_execute_individual_field_updates(self, use_case, mock_task_repository, sample_task,
                                            field_name, field_value):
        """Test individual field updates"""
        # Arrange
        request_data = {"task_id": "12345678-1234-5678-1234-567812345678", field_name: field_value}
        request = UpdateTaskRequest(**request_data)
        mock_task_repository.find_by_id.return_value = sample_task
        mock_task_repository.save.return_value = None
        
        with patch('fastmcp.task_management.application.use_cases.update_task.TaskResponse'):
            with patch('fastmcp.task_management.application.use_cases.update_task.UpdateTaskResponse'):
                # Act
                result = use_case.execute(request)
                
                # Assert
                assert result is not None
                mock_task_repository.save.assert_called_once_with(sample_task)
    
    def test_execute_none_values_not_updated(self, use_case, mock_task_repository, sample_task):
        """Test that None values don't trigger updates"""
        # Arrange
        request = UpdateTaskRequest(
            task_id="12345678-1234-5678-1234-567812345678",
            title="Updated Title",
            description=None,  # Should not update
            status=None,       # Should not update
            priority=None      # Should not update
        )
        mock_task_repository.find_by_id.return_value = sample_task
        mock_task_repository.save.return_value = None
        
        with patch('fastmcp.task_management.application.use_cases.update_task.TaskResponse'):
            with patch('fastmcp.task_management.application.use_cases.update_task.UpdateTaskResponse'):
                # Act
                result = use_case.execute(request)
                
                # Assert
                assert result is not None
                sample_task.update_title.assert_called_once_with("Updated Title")
                sample_task.update_description.assert_not_called()
                sample_task.update_status.assert_not_called()
                sample_task.update_priority.assert_not_called()
    
    def test_sync_task_context_after_update_no_event_loop(self, use_case, mock_task_repository, 
                                                         sample_task, basic_update_request):
        """Test context sync when no event loop is running"""
        # Arrange
        mock_task_repository.find_by_id.return_value = sample_task
        mock_task_repository.save.return_value = None
        
        with patch('fastmcp.task_management.application.services.task_context_sync_service.TaskContextSyncService') as mock_sync_service_class:
            mock_sync_service = Mock()
            mock_sync_service.sync_context_and_get_task = AsyncMock(return_value=sample_task)
            mock_sync_service_class.return_value = mock_sync_service
            
            with patch('asyncio.get_running_loop') as mock_get_loop:
                mock_get_loop.side_effect = RuntimeError("No running event loop")
                
                with patch('asyncio.run') as mock_run:
                    mock_run.return_value = sample_task
                    
                    with patch('fastmcp.task_management.application.use_cases.update_task.TaskResponse'):
                        with patch('fastmcp.task_management.application.use_cases.update_task.UpdateTaskResponse'):
                            # Act
                            result = use_case.execute(basic_update_request)
                            
                            # Assert
                            assert result is not None
                            mock_run.assert_called_once()
    
    def test_sync_task_context_in_async_context(self, use_case, mock_task_repository, 
                                               sample_task, basic_update_request, caplog):
        """Test context sync when already in async context"""
        # Arrange
        mock_task_repository.find_by_id.return_value = sample_task
        mock_task_repository.save.return_value = None
        
        with patch('asyncio.get_running_loop') as mock_get_loop:
            mock_get_loop.return_value = Mock()  # Simulate running loop
            
            with patch('fastmcp.task_management.application.use_cases.update_task.TaskResponse'):
                with patch('fastmcp.task_management.application.use_cases.update_task.UpdateTaskResponse'):
                    # Act
                    with caplog.at_level(logging.INFO):
                        result = use_case.execute(basic_update_request)
                    
                    # Assert
                    assert result is not None
                    assert "Context sync triggered" in caplog.text