"""
Comprehensive Tests for Task API Controller (Interface Layer)

Test Coverage:
- Controller delegation to application facades
- No direct WebSocket notification logic in controllers
- API responses don't trigger notifications
- Proper separation of concerns (DDD clean architecture)
- Controller passes correct parameters to use cases

Following DDD Architecture:
- Interface Layer (Controllers) -> Application Layer (Use Cases) -> Domain Layer
- Notifications handled ONLY in Application Layer, never in Interface Layer
"""

import pytest
from unittest.mock import Mock, patch, MagicMock
from datetime import datetime

from fastmcp.task_management.interface.api_controllers.task_api_controller import TaskAPIController
from fastmcp.task_management.application.dtos.task.create_task_request import CreateTaskRequest
from fastmcp.task_management.application.dtos.task.update_task_request import UpdateTaskRequest
from fastmcp.task_management.application.dtos.task.list_tasks_request import ListTasksRequest
from fastmcp.types import TaskResponse, TasksResponse, DeleteResponse


class TestTaskAPIControllerDelegation:
    """
    Test suite for verifying proper delegation patterns.
    Controllers should delegate to application layer, not handle business logic.
    """

    @pytest.fixture
    def mock_facade_service(self):
        """Create a mock facade service"""
        facade = Mock()
        facade.get_task_facade = Mock(return_value=Mock())
        return facade

    @pytest.fixture
    def controller(self, mock_facade_service):
        """Create controller with mocked dependencies"""
        with patch('fastmcp.task_management.interface.api_controllers.task_api_controller.task_api_controller.FacadeService') as MockFacadeService:
            MockFacadeService.get_instance.return_value = mock_facade_service
            controller = TaskAPIController()
            return controller

    def test_create_task_delegates_to_handler(self, controller):
        """Test that create_task delegates to CRUD handler, not direct notification"""
        # Arrange
        request = Mock(spec=CreateTaskRequest)
        request.title = "Test Task"
        request.git_branch_id = "branch-123"
        request.assignees = ["agent-1"]
        user_id = "user-123"
        session = Mock()

        mock_response = Mock(spec=TaskResponse)
        controller.crud_handler.create_task = Mock(return_value=mock_response)

        # Act
        result = controller.create_task(request, user_id, session)

        # Assert
        controller.crud_handler.create_task.assert_called_once_with(request, user_id, session)
        assert result == mock_response

        # Critical: Verify controller does NOT call WebSocketNotificationService
        with pytest.raises(AttributeError):
            controller.WebSocketNotificationService  # Should not exist on controller

    def test_update_task_delegates_to_handler(self, controller):
        """Test that update_task delegates properly without notification logic"""
        # Arrange
        task_id = "task-123"
        request = Mock(spec=UpdateTaskRequest)
        request.title = "Updated Task"
        user_id = "user-123"
        session = Mock()

        mock_response = Mock(spec=TaskResponse)
        controller.crud_handler.update_task = Mock(return_value=mock_response)

        # Act
        result = controller.update_task(task_id, request, user_id, session)

        # Assert
        controller.crud_handler.update_task.assert_called_once_with(task_id, request, user_id, session)
        assert result == mock_response

    def test_delete_task_delegates_to_handler(self, controller):
        """Test that delete_task delegates properly without notification logic"""
        # Arrange
        task_id = "task-123"
        user_id = "user-123"
        session = Mock()

        mock_response = Mock(spec=DeleteResponse)
        controller.crud_handler.delete_task = Mock(return_value=mock_response)

        # Act
        result = controller.delete_task(task_id, user_id, session)

        # Assert
        controller.crud_handler.delete_task.assert_called_once_with(task_id, user_id, session)
        assert result == mock_response

    def test_list_tasks_delegates_to_handler(self, controller):
        """Test that list_tasks delegates properly"""
        # Arrange
        request = Mock(spec=ListTasksRequest)
        user_id = "user-123"
        session = Mock()

        mock_response = Mock(spec=TasksResponse)
        controller.crud_handler.list_tasks = Mock(return_value=mock_response)

        # Act
        result = controller.list_tasks(request, user_id, session)

        # Assert
        controller.crud_handler.list_tasks.assert_called_once_with(request, user_id, session)
        assert result == mock_response


class TestTaskAPIControllerArchitectureBoundaries:
    """
    Test suite for DDD architectural boundaries.
    Verify controllers don't violate layer separation.
    """

    @pytest.fixture
    def controller(self):
        """Create controller for architecture tests"""
        with patch('fastmcp.task_management.interface.api_controllers.task_api_controller.task_api_controller.FacadeService'):
            return TaskAPIController()

    def test_controller_does_not_import_websocket_service(self, controller):
        """Test that controller doesn't directly import WebSocketNotificationService"""
        import inspect
        source = inspect.getsource(TaskAPIController)

        # Controller should NOT import or use WebSocketNotificationService
        assert "WebSocketNotificationService" not in source, \
            "Controller should not directly import WebSocketNotificationService - violates DDD architecture"
        assert "broadcast_task_event" not in source, \
            "Controller should not call broadcast_task_event - violates DDD architecture"

    def test_controller_does_not_have_notification_methods(self, controller):
        """Test that controller doesn't have notification-related methods"""
        # Get all methods of the controller
        methods = [method for method in dir(controller) if not method.startswith('_')]

        # Controller should NOT have any notification methods
        notification_keywords = ['notify', 'broadcast', 'websocket', 'notification']
        for method in methods:
            for keyword in notification_keywords:
                assert keyword not in method.lower(), \
                    f"Controller has notification-related method '{method}' - violates DDD architecture"

    def test_controller_only_delegates_to_handlers(self, controller):
        """Test that all public methods only delegate to handlers"""
        import inspect
        from unittest.mock import Mock, MagicMock

        # Get all public methods (excluding special methods and mocks)
        public_methods = [name for name in dir(controller)
                         if not name.startswith('_') and callable(getattr(controller, name))]

        for method_name in public_methods:
            method = getattr(controller, method_name)

            # Skip mock objects (from fixtures)
            if isinstance(method, (Mock, MagicMock)):
                continue

            try:
                source = inspect.getsource(method)
            except (TypeError, OSError):
                # Skip if source not available (e.g., built-in methods, mocks)
                continue

            # Method should delegate to handler (crud_handler, workflow_handler, etc.)
            handler_delegation = any(keyword in source for keyword in
                                   ['crud_handler', 'workflow_handler', 'search_handler', 'dependency_handler'])

            if not handler_delegation:
                # Allow __init__ and other setup methods
                if method_name not in ['__init__']:
                    pytest.fail(f"Method '{method_name}' doesn't delegate to handler - may contain business logic")


class TestTaskAPIControllerResponseIntegrity:
    """
    Test suite for API response integrity.
    Verify responses don't contain notification logic or side effects.
    """

    @pytest.fixture
    def controller(self):
        """Create controller with mocked dependencies"""
        with patch('fastmcp.task_management.interface.api_controllers.task_api_controller.task_api_controller.FacadeService'):
            return TaskAPIController()

    def test_create_task_response_does_not_trigger_notification(self, controller):
        """Test that API response creation doesn't trigger notifications"""
        # Mock the handler to return a clean response
        mock_task_response = Mock(spec=TaskResponse)
        mock_task_response.id = "task-123"
        mock_task_response.title = "Test Task"

        controller.crud_handler = Mock()
        controller.crud_handler.create_task = Mock(return_value=mock_task_response)

        # Spy on WebSocketNotificationService to ensure it's NOT called from controller
        with patch('fastmcp.task_management.application.services.websocket_notification_service.WebSocketNotificationService') as mock_ws_service:
            request = Mock(spec=CreateTaskRequest)
            request.title = "Test"
            request.git_branch_id = "branch-123"
            request.assignees = ["agent-1"]

            result = controller.create_task(request, "user-123", Mock())

            # Verify WebSocketNotificationService was NOT called from controller level
            # (It should only be called from use case/application layer)
            assert not mock_ws_service.called, \
                "WebSocketNotificationService should NOT be called from controller level"

    def test_update_task_response_is_clean(self, controller):
        """Test that update response doesn't contain notification metadata"""
        mock_response = Mock(spec=TaskResponse)
        mock_response.id = "task-123"

        controller.crud_handler = Mock()
        controller.crud_handler.update_task = Mock(return_value=mock_response)

        result = controller.update_task("task-123", Mock(spec=UpdateTaskRequest), "user-123", Mock())

        # Response should be clean TaskResponse, not modified with notification data
        assert isinstance(result, (Mock, TaskResponse))
        assert not hasattr(result, 'notification_sent'), \
            "Response should not contain notification metadata"
        assert not hasattr(result, 'websocket_triggered'), \
            "Response should not contain WebSocket metadata"

    def test_delete_task_response_is_clean(self, controller):
        """Test that delete response doesn't contain notification metadata"""
        mock_response = Mock(spec=DeleteResponse)
        mock_response.success = True

        controller.crud_handler = Mock()
        controller.crud_handler.delete_task = Mock(return_value=mock_response)

        result = controller.delete_task("task-123", "user-123", Mock())

        # Response should be clean DeleteResponse
        assert isinstance(result, (Mock, DeleteResponse))
        assert not hasattr(result, 'notification_sent'), \
            "Delete response should not contain notification metadata"


class TestTaskAPIControllerParameterPassing:
    """
    Test suite for parameter passing integrity.
    Verify controllers pass correct parameters to application layer.
    """

    @pytest.fixture
    def controller(self):
        """Create controller with mocked dependencies"""
        with patch('fastmcp.task_management.interface.api_controllers.task_api_controller.task_api_controller.FacadeService'):
            return TaskAPIController()

    def test_create_task_passes_all_required_parameters(self, controller):
        """Test that create delegates with all required parameters"""
        request = Mock(spec=CreateTaskRequest)
        request.title = "Test Task"
        request.git_branch_id = "branch-123"
        request.assignees = ["agent-1"]
        user_id = "user-123"
        session = Mock()

        controller.crud_handler = Mock()
        controller.crud_handler.create_task = Mock(return_value=Mock())

        controller.create_task(request, user_id, session)

        # Verify all parameters passed correctly
        controller.crud_handler.create_task.assert_called_once()
        call_args = controller.crud_handler.create_task.call_args

        assert call_args[0][0] == request, "Request not passed correctly"
        assert call_args[0][1] == user_id, "User ID not passed correctly"
        assert call_args[0][2] == session, "Session not passed correctly"

    def test_update_task_passes_task_id_correctly(self, controller):
        """Test that update passes task_id as first parameter"""
        task_id = "task-123"
        request = Mock(spec=UpdateTaskRequest)
        user_id = "user-123"
        session = Mock()

        controller.crud_handler = Mock()
        controller.crud_handler.update_task = Mock(return_value=Mock())

        controller.update_task(task_id, request, user_id, session)

        # Verify task_id is first parameter
        call_args = controller.crud_handler.update_task.call_args
        assert call_args[0][0] == task_id, "Task ID should be first parameter"
        assert call_args[0][1] == request, "Request should be second parameter"

    def test_delete_task_passes_identifiers_correctly(self, controller):
        """Test that delete passes task_id and user_id correctly"""
        task_id = "task-123"
        user_id = "user-123"
        session = Mock()

        controller.crud_handler = Mock()
        controller.crud_handler.delete_task = Mock(return_value=Mock())

        controller.delete_task(task_id, user_id, session)

        # Verify parameters
        call_args = controller.crud_handler.delete_task.call_args
        assert call_args[0][0] == task_id
        assert call_args[0][1] == user_id
        assert call_args[0][2] == session


class TestTaskAPIControllerErrorHandling:
    """
    Test suite for error handling.
    Verify controllers handle errors without triggering notifications.
    """

    @pytest.fixture
    def controller(self):
        """Create controller with mocked dependencies"""
        with patch('fastmcp.task_management.interface.api_controllers.task_api_controller.task_api_controller.FacadeService'):
            return TaskAPIController()

    def test_create_task_error_does_not_trigger_notification(self, controller):
        """Test that errors don't trigger notification attempts"""
        controller.crud_handler = Mock()
        controller.crud_handler.create_task = Mock(side_effect=Exception("Database error"))

        with patch('fastmcp.task_management.application.services.websocket_notification_service.WebSocketNotificationService') as mock_ws:
            request = Mock(spec=CreateTaskRequest)
            request.title = "Test"
            request.git_branch_id = "branch-123"
            request.assignees = ["agent-1"]

            with pytest.raises(Exception):
                controller.create_task(request, "user-123", Mock())

            # Verify no notification attempt from controller level
            assert not mock_ws.called, \
                "Controller should not attempt notification on error"

    def test_update_task_error_propagates_cleanly(self, controller):
        """Test that update errors propagate without notification side effects"""
        controller.crud_handler = Mock()
        controller.crud_handler.update_task = Mock(side_effect=ValueError("Invalid status"))

        with pytest.raises(ValueError):
            controller.update_task("task-123", Mock(spec=UpdateTaskRequest), "user-123", Mock())

        # Error should propagate cleanly without notification attempts


class TestTaskAPIControllerCompleteTaskWorkflow:
    """
    Test suite for complete_task workflow.
    Verify completion workflow delegates correctly.
    """

    @pytest.fixture
    def controller(self):
        """Create controller with mocked dependencies"""
        with patch('fastmcp.task_management.interface.api_controllers.task_api_controller.task_api_controller.FacadeService'):
            return TaskAPIController()

    def test_complete_task_delegates_to_workflow_handler(self, controller):
        """Test that complete_task uses workflow handler"""
        task_id = "task-123"
        completion_summary = "Completed successfully"
        testing_notes = "All tests passing"
        user_id = "user-123"
        session = Mock()

        mock_response = Mock(spec=TaskResponse)
        controller.workflow_handler = Mock()
        controller.workflow_handler.complete_task = Mock(return_value=mock_response)

        result = controller.complete_task(task_id, completion_summary, testing_notes, user_id, session)

        # Verify delegation
        controller.workflow_handler.complete_task.assert_called_once_with(
            task_id, completion_summary, testing_notes, user_id, session
        )
        assert result == mock_response

    def test_complete_task_does_not_send_notification_from_controller(self, controller):
        """Test that completion notification happens in application layer, not controller"""
        controller.workflow_handler = Mock()
        controller.workflow_handler.complete_task = Mock(return_value=Mock(spec=TaskResponse))

        with patch('fastmcp.task_management.application.services.websocket_notification_service.WebSocketNotificationService') as mock_ws:
            controller.complete_task("task-123", "Done", None, "user-123", Mock())

            # WebSocket service should NOT be called from controller
            assert not mock_ws.called, \
                "Completion notification should be in application layer, not controller"
