"""Tests for Update Task Use Case"""

import pytest
from unittest.mock import Mock, patch, AsyncMock, MagicMock
from datetime import datetime
import asyncio
import logging

from fastmcp.task_management.application.use_cases.update_task import UpdateTaskUseCase
from fastmcp.task_management.application.dtos.task import UpdateTaskRequest, TaskResponse
from fastmcp.task_management.domain import (
    Task, TaskId, TaskStatus, Priority, TaskNotFoundError
)
from fastmcp.task_management.domain.events import TaskUpdated


class TestUpdateTaskUseCase:
    """Test cases for Update Task Use Case"""

    def setup_method(self):
        """Setup test dependencies"""
        self.task_repository = Mock()
        self.use_case = UpdateTaskUseCase(self.task_repository)
        self.logger = logging.getLogger(__name__)
        
        # Create a mock task
        self.task_id = TaskId.from_string("task-123")
        self.mock_task = Mock(spec=Task)
        self.mock_task.id = self.task_id
        self.mock_task.id.value = "task-123"
        self.mock_task.title = "Test Task"
        self.mock_task.description = "Test Description"
        self.mock_task.status = TaskStatus.TODO
        self.mock_task.priority = Priority.MEDIUM
        self.mock_task.context_id = "context-123"
        self.mock_task.git_branch_id = "branch-123"
        self.mock_task.project_id = "project-123"
        self.mock_task.progress_history = {"1": {"content": "Initial", "timestamp": "2024-01-01"}}
        self.mock_task.progress_count = 1
        self.mock_task.get_events = Mock(return_value=[])
        self.mock_task.get_progress_history_text = Mock(return_value="Initial")
        
        # Mock hasattr to return True for our attributes
        self.original_hasattr = hasattr
        
        def custom_hasattr(obj, name):
            if obj == self.mock_task and name in ['value', 'git_branch_id', 'project_id', 'progress_history', 'progress_count', 'get_progress_history_text']:
                return True
            if obj == self.mock_task.status and name == 'value':
                return True
            if obj == self.mock_task.id and name == 'value':
                return True
            return self.original_hasattr(obj, name)
        
        self.hasattr_patch = patch('builtins.hasattr', custom_hasattr)
        self.hasattr_patch.start()

    def teardown_method(self):
        """Cleanup after tests"""
        self.hasattr_patch.stop()

    def test_update_task_not_found(self):
        """Test updating a task that doesn't exist"""
        # Arrange
        request = UpdateTaskRequest(
            task_id="nonexistent-task",
            title="Updated Title"
        )
        self.task_repository.find_by_id.return_value = None
        
        # Act & Assert
        with pytest.raises(TaskNotFoundError) as exc_info:
            self.use_case.execute(request)
        
        assert "Task nonexistent-task not found" in str(exc_info.value)

    def test_update_task_title_only(self):
        """Test updating only the task title"""
        # Arrange
        request = UpdateTaskRequest(
            task_id="task-123",
            title="Updated Title"
        )
        self.task_repository.find_by_id.return_value = self.mock_task
        
        # Act
        response = self.use_case.execute(request)
        
        # Assert
        self.mock_task.update_title.assert_called_once_with("Updated Title")
        self.task_repository.save.assert_called_once_with(self.mock_task)
        assert response.success is True

    def test_update_task_all_fields(self):
        """Test updating all task fields"""
        # Arrange
        due_date = datetime.now()
        request = UpdateTaskRequest(
            task_id="task-123",
            title="Updated Title",
            description="Updated Description",
            status="in_progress",
            priority="high",
            details="Progress update",
            estimated_effort="5 hours",
            assignees=["user1", "user2"],
            labels=["label1", "label2"],
            due_date=due_date,
            progress_percentage=75,
            context_id="new-context-123"
        )
        self.task_repository.find_by_id.return_value = self.mock_task
        
        # Act
        response = self.use_case.execute(request)
        
        # Assert
        self.mock_task.update_title.assert_called_once_with("Updated Title")
        self.mock_task.update_description.assert_called_once_with("Updated Description")
        self.mock_task.update_status.assert_called_once()
        self.mock_task.update_priority.assert_called_once()
        self.mock_task.append_progress.assert_called_once_with("Progress update")
        self.mock_task.update_estimated_effort.assert_called_once_with("5 hours")
        self.mock_task.update_assignees.assert_called_once_with(["user1", "user2"])
        self.mock_task.update_labels.assert_called_once_with(["label1", "label2"])
        self.mock_task.update_due_date.assert_called_once_with(due_date)
        self.mock_task.set_progress_percentage.assert_called_once_with(75)
        self.mock_task.set_context_id.assert_called_once_with("new-context-123")
        self.task_repository.save.assert_called_once_with(self.mock_task)
        assert response.success is True

    def test_update_task_skips_unchanged_status(self):
        """Test that status update is skipped if value hasn't changed"""
        # Arrange
        request = UpdateTaskRequest(
            task_id="task-123",
            status="todo"  # Same as current status
        )
        self.task_repository.find_by_id.return_value = self.mock_task
        
        # Act
        response = self.use_case.execute(request)
        
        # Assert
        self.mock_task.update_status.assert_not_called()
        self.task_repository.save.assert_called_once()
        assert response.success is True

    def test_update_task_skips_unchanged_priority(self):
        """Test that priority update is skipped if value hasn't changed"""
        # Arrange
        request = UpdateTaskRequest(
            task_id="task-123",
            priority="medium"  # Same as current priority
        )
        self.task_repository.find_by_id.return_value = self.mock_task
        
        # Act
        response = self.use_case.execute(request)
        
        # Assert
        self.mock_task.update_priority.assert_not_called()
        self.task_repository.save.assert_called_once()
        assert response.success is True

    @patch('fastmcp.task_management.application.use_cases.update_task.dispatch_domain_event')
    def test_update_task_dispatches_event_on_status_change(self, mock_dispatch):
        """Test that domain event is dispatched when status changes"""
        # Arrange
        request = UpdateTaskRequest(
            task_id="task-123",
            status="in_progress",
            user_id="user-123"
        )
        self.task_repository.find_by_id.return_value = self.mock_task
        
        # Mock status change
        self.mock_task.status = TaskStatus.IN_PROGRESS
        
        # Act
        response = self.use_case.execute(request)
        
        # Assert
        mock_dispatch.assert_called_once()
        assert mock_dispatch.call_args[0][0] == "task_updated"
        event = mock_dispatch.call_args[0][1]
        assert event.task_id == "task-123"
        assert event.old_status == "todo"
        assert event.new_status == "in_progress"
        assert event.user_id == "user-123"

    @patch('fastmcp.task_management.application.use_cases.update_task.dispatch_domain_event')
    def test_update_task_no_event_if_no_change(self, mock_dispatch):
        """Test that no event is dispatched if status doesn't change"""
        # Arrange
        request = UpdateTaskRequest(
            task_id="task-123",
            title="New Title"  # Only title change
        )
        self.task_repository.find_by_id.return_value = self.mock_task
        
        # Act
        response = self.use_case.execute(request)
        
        # Assert
        mock_dispatch.assert_not_called()

    @patch('fastmcp.task_management.application.services.websocket_notification_service.WebSocketNotificationService.sync_broadcast_task_event')
    def test_update_task_sends_websocket_notification(self, mock_websocket):
        """Test that WebSocket notification is sent on task update"""
        # Arrange
        request = UpdateTaskRequest(
            task_id="task-123",
            title="Updated Title",
            user_id="user-123"
        )
        self.task_repository.find_by_id.return_value = self.mock_task
        
        # Act
        response = self.use_case.execute(request)
        
        # Assert
        mock_websocket.assert_called_once()
        assert mock_websocket.call_args[1]['event_type'] == "updated"
        assert mock_websocket.call_args[1]['task_id'] == "task-123"
        assert mock_websocket.call_args[1]['user_id'] == "user-123"
        
        # Verify progress_history is included
        task_data = mock_websocket.call_args[1]['task_data']
        assert 'progress_history' in task_data
        assert task_data['progress_history'] == {"1": {"content": "Initial", "timestamp": "2024-01-01"}}
        assert task_data['progress_count'] == 1
        assert task_data['details'] == "Initial"

    def test_update_task_handles_websocket_failure(self, caplog):
        """Test that WebSocket failure doesn't fail the update"""
        # Arrange
        request = UpdateTaskRequest(
            task_id="task-123",
            title="Updated Title"
        )
        self.task_repository.find_by_id.return_value = self.mock_task
        
        with patch('fastmcp.task_management.application.services.websocket_notification_service.WebSocketNotificationService.sync_broadcast_task_event') as mock_websocket:
            mock_websocket.side_effect = Exception("WebSocket error")
            
            # Act
            with caplog.at_level(logging.WARNING):
                response = self.use_case.execute(request)
            
            # Assert
            assert response.success is True
            assert "Failed to send WebSocket notification" in caplog.text

    def test_update_task_context_sync_with_running_loop(self):
        """Test context sync when already in async context"""
        # Arrange
        request = UpdateTaskRequest(
            task_id="task-123",
            title="Updated Title"
        )
        self.task_repository.find_by_id.return_value = self.mock_task
        
        # Mock async context
        mock_loop = Mock()
        with patch('asyncio.get_running_loop', return_value=mock_loop):
            # Act
            response = self.use_case.execute(request)
            
            # Assert
            assert response.success is True

    def test_update_task_context_sync_without_running_loop(self):
        """Test context sync when not in async context"""
        # Arrange
        request = UpdateTaskRequest(
            task_id="task-123",
            title="Updated Title"
        )
        self.task_repository.find_by_id.return_value = self.mock_task
        
        # Mock no async context
        with patch('asyncio.get_running_loop', side_effect=RuntimeError("No event loop")):
            # Mock the context sync service
            mock_sync_service = Mock()
            mock_sync_service.sync_context_and_get_task = AsyncMock(return_value=self.mock_task)
            
            with patch('fastmcp.task_management.application.services.task_context_sync_service.TaskContextSyncService', return_value=mock_sync_service):
                # Act
                response = self.use_case.execute(request)
                
                # Assert
                assert response.success is True

    def test_update_task_context_sync_failure(self, caplog):
        """Test that context sync failure doesn't fail the update"""
        # Arrange
        request = UpdateTaskRequest(
            task_id="task-123",
            title="Updated Title"
        )
        self.task_repository.find_by_id.return_value = self.mock_task
        
        # Mock context sync failure
        with patch('asyncio.get_running_loop', side_effect=Exception("Context sync error")):
            # Act
            with caplog.at_level(logging.WARNING):
                response = self.use_case.execute(request)
            
            # Assert
            assert response.success is True
            assert "Context sync failed for task" in caplog.text

    def test_update_task_with_domain_events(self):
        """Test handling of domain events"""
        # Arrange
        request = UpdateTaskRequest(
            task_id="task-123",
            title="Updated Title"
        )
        
        # Create a TaskUpdated event
        task_updated_event = TaskUpdated(
            task_id=self.task_id,
            changes={"title": "Updated Title"}
        )
        self.mock_task.get_events.return_value = [task_updated_event]
        self.task_repository.find_by_id.return_value = self.mock_task
        
        # Act
        response = self.use_case.execute(request)
        
        # Assert
        assert response.success is True
        self.mock_task.get_events.assert_called_once()

    def test_convert_to_task_id_from_string(self):
        """Test conversion of string to TaskId"""
        # Act
        result = self.use_case._convert_to_task_id("task-456")
        
        # Assert
        assert isinstance(result, TaskId)
        assert str(result.value) == "task-456"

    def test_convert_to_task_id_from_int(self):
        """Test conversion of int to TaskId"""
        # Act
        result = self.use_case._convert_to_task_id(123)
        
        # Assert
        assert isinstance(result, TaskId)
        assert str(result.value) == "123"

    def test_convert_to_task_id_already_task_id(self):
        """Test conversion when already a TaskId"""
        # Arrange
        task_id = TaskId.from_string("task-789")
        
        # Act
        result = self.use_case._convert_to_task_id(task_id)
        
        # Assert
        assert result == task_id

    def test_update_task_response_from_domain(self):
        """Test that response is properly created from domain model"""
        # Arrange
        request = UpdateTaskRequest(
            task_id="task-123",
            title="Updated Title"
        )
        self.task_repository.find_by_id.return_value = self.mock_task
        
        # Mock TaskResponse.from_domain
        mock_task_response = Mock()
        with patch('fastmcp.task_management.application.dtos.task.TaskResponse.from_domain', return_value=mock_task_response):
            # Act
            response = self.use_case.execute(request)
            
            # Assert
            assert response.success is True
            assert response.task == mock_task_response

    def test_update_task_preserves_context_id_order(self):
        """Test that context_id is set last to avoid being cleared by other updates"""
        # Arrange
        request = UpdateTaskRequest(
            task_id="task-123",
            status="in_progress",
            progress_percentage=50,
            context_id="new-context-456"
        )
        self.task_repository.find_by_id.return_value = self.mock_task
        
        # Track method call order
        call_order = []
        self.mock_task.update_status = Mock(side_effect=lambda x: call_order.append('status'))
        self.mock_task.set_progress_percentage = Mock(side_effect=lambda x: call_order.append('progress'))
        self.mock_task.set_context_id = Mock(side_effect=lambda x: call_order.append('context'))
        
        # Act
        response = self.use_case.execute(request)
        
        # Assert
        assert response.success is True
        assert call_order == ['status', 'progress', 'context']
        assert call_order[-1] == 'context'  # Context must be last