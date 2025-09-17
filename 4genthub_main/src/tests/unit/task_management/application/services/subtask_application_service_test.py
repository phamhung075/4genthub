"""Tests for SubtaskApplicationService"""

import pytest
from unittest.mock import Mock, create_autospec
from typing import Any, Dict, Optional

from fastmcp.task_management.application.services.subtask_application_service import SubtaskApplicationService
from fastmcp.task_management.domain.repositories.task_repository import TaskRepository
from fastmcp.task_management.domain.repositories.subtask_repository import SubtaskRepository
from fastmcp.task_management.application.dtos.subtask import (
    AddSubtaskRequest,
    UpdateSubtaskRequest,
    SubtaskResponse
)
from fastmcp.task_management.application.use_cases.add_subtask import AddSubtaskUseCase
from fastmcp.task_management.application.use_cases.update_subtask import UpdateSubtaskUseCase
from fastmcp.task_management.application.use_cases.remove_subtask import RemoveSubtaskUseCase
from fastmcp.task_management.application.use_cases.complete_subtask import CompleteSubtaskUseCase
from fastmcp.task_management.application.use_cases.get_subtasks import GetSubtasksUseCase
from fastmcp.task_management.application.use_cases.get_subtask import GetSubtaskUseCase


class TestSubtaskApplicationService:
    """Test suite for SubtaskApplicationService"""

    @pytest.fixture
    def mock_task_repository(self):
        """Create a mock task repository"""
        return create_autospec(TaskRepository, instance=True)

    @pytest.fixture
    def mock_subtask_repository(self):
        """Create a mock subtask repository"""
        return create_autospec(SubtaskRepository, instance=True)

    @pytest.fixture
    def mock_add_subtask_response(self):
        """Create a mock AddSubtask response"""
        response = Mock(spec=SubtaskResponse)
        response.success = True
        response.subtask_id = "subtask-123"
        response.message = "Subtask added successfully"
        
        # Create a separate dict for __dict__ access without interfering with Mock attributes
        response_dict = {
            "success": True,
            "subtask_id": "subtask-123",
            "message": "Subtask added successfully"
        }
        response.__dict__.update(response_dict)
        return response

    @pytest.fixture
    def mock_update_subtask_response(self):
        """Create a mock UpdateSubtask response"""
        response = Mock(spec=SubtaskResponse)
        response.success = True
        response.subtask_id = "subtask-123"
        response.message = "Subtask updated successfully"
        
        # Create a separate dict for __dict__ access without interfering with Mock attributes
        response_dict = {
            "success": True,
            "subtask_id": "subtask-123",
            "message": "Subtask updated successfully"
        }
        response.__dict__.update(response_dict)
        return response

    @pytest.fixture
    def service(self, mock_task_repository, mock_subtask_repository):
        """Create a SubtaskApplicationService instance"""
        service = SubtaskApplicationService(mock_task_repository, mock_subtask_repository)
        
        # Mock all use cases
        service._add_subtask_use_case = Mock(spec=AddSubtaskUseCase)
        service._update_subtask_use_case = Mock(spec=UpdateSubtaskUseCase)
        service._remove_subtask_use_case = Mock(spec=RemoveSubtaskUseCase)
        service._complete_subtask_use_case = Mock(spec=CompleteSubtaskUseCase)
        service._get_subtasks_use_case = Mock(spec=GetSubtasksUseCase)
        service._get_subtask_use_case = Mock(spec=GetSubtaskUseCase)
        
        return service

    def test_init(self, mock_task_repository, mock_subtask_repository):
        """Test service initialization"""
        service = SubtaskApplicationService(mock_task_repository, mock_subtask_repository)
        assert service._task_repository == mock_task_repository
        assert service._subtask_repository == mock_subtask_repository
        assert service._user_id is None

    def test_init_with_user_id(self, mock_task_repository, mock_subtask_repository):
        """Test service initialization with user ID"""
        service = SubtaskApplicationService(
            mock_task_repository, 
            mock_subtask_repository, 
            user_id="user-123"
        )
        assert service._user_id == "user-123"

    def test_init_without_subtask_repository(self, mock_task_repository):
        """Test service initialization without subtask repository"""
        service = SubtaskApplicationService(mock_task_repository)
        assert service._task_repository == mock_task_repository
        assert service._subtask_repository is None

    def test_with_user(self, service):
        """Test creating user-scoped service"""
        user_scoped_service = service.with_user("user-456")
        assert isinstance(user_scoped_service, SubtaskApplicationService)
        assert user_scoped_service._user_id == "user-456"
        assert user_scoped_service._task_repository == service._task_repository
        assert user_scoped_service._subtask_repository == service._subtask_repository

    def test_get_user_scoped_repository_no_user(self, service, mock_task_repository):
        """Test getting repository when no user is set"""
        repo = service._get_user_scoped_repository(mock_task_repository)
        assert repo == mock_task_repository

    def test_get_user_scoped_repository_with_user_method(self, service, mock_task_repository):
        """Test getting repository with with_user method"""
        service._user_id = "user-789"
        mock_task_repository.with_user = Mock(return_value=mock_task_repository)
        
        repo = service._get_user_scoped_repository(mock_task_repository)
        
        mock_task_repository.with_user.assert_called_once_with("user-789")
        assert repo == mock_task_repository

    def test_get_user_scoped_repository_none(self, service):
        """Test getting repository when repository is None"""
        repo = service._get_user_scoped_repository(None)
        assert repo is None

    def test_add_subtask(self, service, mock_add_subtask_response):
        """Test adding a subtask"""
        request = AddSubtaskRequest(
            task_id="task-123",
            title="Test Subtask",
            description="Test description",
            assignees=["user1"]
        )
        service._add_subtask_use_case.execute.return_value = mock_add_subtask_response

        result = service.add_subtask(request)

        service._add_subtask_use_case.execute.assert_called_once_with(request)
        assert result == mock_add_subtask_response

    def test_update_subtask(self, service, mock_update_subtask_response):
        """Test updating a subtask"""
        request = UpdateSubtaskRequest(
            task_id="task-123",
            id="subtask-456",
            title="Updated Subtask",
            description="Updated description",
            status="completed",
            assignees=["user2"]
        )
        service._update_subtask_use_case.execute.return_value = mock_update_subtask_response

        result = service.update_subtask(request)

        service._update_subtask_use_case.execute.assert_called_once_with(request)
        assert result == mock_update_subtask_response

    def test_remove_subtask(self, service):
        """Test removing a subtask"""
        expected_result = {"success": True, "message": "Subtask removed"}
        service._remove_subtask_use_case.execute.return_value = expected_result

        result = service.remove_subtask("task-123", "subtask-456")

        service._remove_subtask_use_case.execute.assert_called_once_with("task-123", "subtask-456")
        assert result == expected_result

    def test_complete_subtask(self, service):
        """Test completing a subtask"""
        expected_result = {"success": True, "message": "Subtask completed"}
        service._complete_subtask_use_case.execute.return_value = expected_result

        result = service.complete_subtask("task-123", "subtask-456")

        service._complete_subtask_use_case.execute.assert_called_once_with("task-123", "subtask-456")
        assert result == expected_result

    def test_get_subtasks(self, service):
        """Test getting all subtasks for a task"""
        expected_result = {"success": True, "subtasks": []}
        service._get_subtasks_use_case.execute.return_value = expected_result

        result = service.get_subtasks("task-123")

        service._get_subtasks_use_case.execute.assert_called_once_with("task-123")
        assert result == expected_result

    def test_get_subtask(self, service):
        """Test getting a single subtask"""
        expected_result = {"success": True, "subtask": {"id": "subtask-456"}}
        service._get_subtask_use_case.execute.return_value = expected_result

        result = service.get_subtask("task-123", "subtask-456")

        service._get_subtask_use_case.execute.assert_called_once_with("task-123", "subtask-456")
        assert result == expected_result

    def test_manage_subtasks_add_action(self, service, mock_add_subtask_response):
        """Test manage_subtasks with add action"""
        service._add_subtask_use_case.execute.return_value = mock_add_subtask_response
        
        subtask_data = {
            "title": "New Subtask",
            "description": "New description",
            "assignee": "user1"
        }

        result = service.manage_subtasks("task-123", "add_subtask", subtask_data)

        assert result == mock_add_subtask_response.__dict__
        service._add_subtask_use_case.execute.assert_called_once()
        
        # Check that the correct request was created
        call_args = service._add_subtask_use_case.execute.call_args[0][0]
        assert call_args.task_id == "task-123"
        assert call_args.title == "New Subtask"
        assert call_args.description == "New description"
        assert call_args.assignees == ["user1"]

    def test_manage_subtasks_add_action_short(self, service, mock_add_subtask_response):
        """Test manage_subtasks with short add action"""
        service._add_subtask_use_case.execute.return_value = mock_add_subtask_response
        
        subtask_data = {"title": "New Subtask"}

        result = service.manage_subtasks("task-123", "add", subtask_data)

        assert result == mock_add_subtask_response.__dict__
        service._add_subtask_use_case.execute.assert_called_once()

    def test_manage_subtasks_update_action(self, service, mock_update_subtask_response):
        """Test manage_subtasks with update action"""
        service._update_subtask_use_case.execute.return_value = mock_update_subtask_response
        
        subtask_data = {
            "id": "subtask-456",
            "title": "Updated Subtask",
            "status": "completed"
        }

        result = service.manage_subtasks("task-123", "update_subtask", subtask_data)

        assert result == mock_update_subtask_response.__dict__
        service._update_subtask_use_case.execute.assert_called_once()
        
        # Check that the correct request was created
        call_args = service._update_subtask_use_case.execute.call_args[0][0]
        assert call_args.task_id == "task-123"
        assert call_args.id == "subtask-456"
        assert call_args.title == "Updated Subtask"
        assert call_args.status == "completed"

    def test_manage_subtasks_update_action_short(self, service, mock_update_subtask_response):
        """Test manage_subtasks with short update action"""
        service._update_subtask_use_case.execute.return_value = mock_update_subtask_response
        
        subtask_data = {"id": "subtask-456", "title": "Updated"}

        result = service.manage_subtasks("task-123", "update", subtask_data)

        assert result == mock_update_subtask_response.__dict__

    def test_manage_subtasks_complete_action(self, service):
        """Test manage_subtasks with complete action"""
        expected_result = {"success": True, "message": "Completed"}
        service._complete_subtask_use_case.execute.return_value = expected_result
        
        subtask_data = {"id": "subtask-456"}

        result = service.manage_subtasks("task-123", "complete_subtask", subtask_data)

        assert result == expected_result
        service._complete_subtask_use_case.execute.assert_called_once_with("task-123", "subtask-456")

    def test_manage_subtasks_complete_action_short(self, service):
        """Test manage_subtasks with short complete action"""
        expected_result = {"success": True, "message": "Completed"}
        service._complete_subtask_use_case.execute.return_value = expected_result
        
        subtask_data = {"id": "subtask-456"}

        result = service.manage_subtasks("task-123", "complete", subtask_data)

        assert result == expected_result

    def test_manage_subtasks_complete_action_no_id(self, service):
        """Test manage_subtasks with complete action but no id"""
        subtask_data = {}

        with pytest.raises(ValueError, match="id is required for completing a subtask"):
            service.manage_subtasks("task-123", "complete", subtask_data)

    def test_manage_subtasks_remove_action(self, service):
        """Test manage_subtasks with remove action"""
        expected_result = {"success": True, "message": "Removed"}
        service._remove_subtask_use_case.execute.return_value = expected_result
        
        subtask_data = {"id": "subtask-456"}

        result = service.manage_subtasks("task-123", "remove_subtask", subtask_data)

        assert result == expected_result
        service._remove_subtask_use_case.execute.assert_called_once_with("task-123", "subtask-456")

    def test_manage_subtasks_remove_action_short(self, service):
        """Test manage_subtasks with short remove action"""
        expected_result = {"success": True, "message": "Removed"}
        service._remove_subtask_use_case.execute.return_value = expected_result
        
        subtask_data = {"id": "subtask-456"}

        result = service.manage_subtasks("task-123", "remove", subtask_data)

        assert result == expected_result

    def test_manage_subtasks_remove_action_no_id(self, service):
        """Test manage_subtasks with remove action but no id"""
        subtask_data = {}

        with pytest.raises(ValueError, match="id is required for removing a subtask"):
            service.manage_subtasks("task-123", "remove", subtask_data)

    def test_manage_subtasks_get_action(self, service):
        """Test manage_subtasks with get action"""
        expected_result = {"success": True, "subtask": {"id": "subtask-456"}}
        service._get_subtask_use_case.execute.return_value = expected_result
        
        subtask_data = {"id": "subtask-456"}

        result = service.manage_subtasks("task-123", "get_subtask", subtask_data)

        assert result == expected_result
        service._get_subtask_use_case.execute.assert_called_once_with("task-123", "subtask-456")

    def test_manage_subtasks_get_action_short(self, service):
        """Test manage_subtasks with short get action"""
        expected_result = {"success": True, "subtask": {"id": "subtask-456"}}
        service._get_subtask_use_case.execute.return_value = expected_result
        
        subtask_data = {"id": "subtask-456"}

        result = service.manage_subtasks("task-123", "get", subtask_data)

        assert result == expected_result

    def test_manage_subtasks_get_action_no_id(self, service):
        """Test manage_subtasks with get action but no id"""
        subtask_data = {}

        with pytest.raises(ValueError, match="id is required for getting a subtask"):
            service.manage_subtasks("task-123", "get", subtask_data)

    def test_manage_subtasks_list_action(self, service):
        """Test manage_subtasks with list action"""
        expected_result = {"success": True, "subtasks": []}
        service._get_subtasks_use_case.execute.return_value = expected_result
        
        subtask_data = {}

        result = service.manage_subtasks("task-123", "list_subtasks", subtask_data)

        assert result == expected_result
        service._get_subtasks_use_case.execute.assert_called_once_with("task-123")

    def test_manage_subtasks_list_action_short(self, service):
        """Test manage_subtasks with short list action"""
        expected_result = {"success": True, "subtasks": []}
        service._get_subtasks_use_case.execute.return_value = expected_result
        
        subtask_data = {}

        result = service.manage_subtasks("task-123", "list", subtask_data)

        assert result == expected_result

    def test_manage_subtasks_unknown_action(self, service):
        """Test manage_subtasks with unknown action"""
        subtask_data = {}

        with pytest.raises(ValueError, match="Unknown subtask action: unknown"):
            service.manage_subtasks("task-123", "unknown", subtask_data)

    def test_add_subtask_request_creation(self, service, mock_add_subtask_response):
        """Test that AddSubtaskRequest is created correctly"""
        service._add_subtask_use_case.execute.return_value = mock_add_subtask_response
        
        subtask_data = {
            "title": "Test Title",
            "description": "Test Description",
            "assignee": "test_user"
        }

        service.manage_subtasks("task-123", "add", subtask_data)

        # Verify that the request was created with correct parameters
        call_args = service._add_subtask_use_case.execute.call_args[0][0]
        assert isinstance(call_args, AddSubtaskRequest)
        assert call_args.task_id == "task-123"
        assert call_args.title == "Test Title"
        assert call_args.description == "Test Description"
        assert call_args.assignees == ["test_user"]

    def test_add_subtask_request_creation_with_defaults(self, service, mock_add_subtask_response):
        """Test that AddSubtaskRequest is created with default values when data is missing"""
        service._add_subtask_use_case.execute.return_value = mock_add_subtask_response
        
        subtask_data = {"title": "Test Title"}

        service.manage_subtasks("task-123", "add", subtask_data)

        # Verify that the request was created with default values
        call_args = service._add_subtask_use_case.execute.call_args[0][0]
        assert call_args.task_id == "task-123"
        assert call_args.title == "Test Title"
        assert call_args.description == ""  # Default value
        assert call_args.assignees == []  # Default value

    def test_update_subtask_request_creation(self, service, mock_update_subtask_response):
        """Test that UpdateSubtaskRequest is created correctly"""
        service._update_subtask_use_case.execute.return_value = mock_update_subtask_response
        
        subtask_data = {
            "id": "subtask-123",
            "title": "Updated Title",
            "description": "Updated Description",
            "status": "completed",
            "assignees": ["updated_user"]
        }

        service.manage_subtasks("task-123", "update", subtask_data)

        # Verify that the request was created with correct parameters
        call_args = service._update_subtask_use_case.execute.call_args[0][0]
        assert isinstance(call_args, UpdateSubtaskRequest)
        assert call_args.task_id == "task-123"
        assert call_args.id == "subtask-123"
        assert call_args.title == "Updated Title"
        assert call_args.description == "Updated Description"
        assert call_args.status == "completed"
        assert call_args.assignees == ["updated_user"]

    def test_update_subtask_request_creation_partial(self, service, mock_update_subtask_response):
        """Test that UpdateSubtaskRequest is created with partial data"""
        service._update_subtask_use_case.execute.return_value = mock_update_subtask_response
        
        subtask_data = {
            "id": "subtask-123",
            "title": "Updated Title"
        }

        service.manage_subtasks("task-123", "update", subtask_data)

        # Verify that the request was created with provided and None values
        call_args = service._update_subtask_use_case.execute.call_args[0][0]
        assert call_args.task_id == "task-123"
        assert call_args.id == "subtask-123"
        assert call_args.title == "Updated Title"
        assert call_args.description is None
        assert call_args.status is None
        assert call_args.assignees is None