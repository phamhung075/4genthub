"""Tests for SubtaskApplicationService"""

import pytest
from unittest.mock import Mock, patch, MagicMock

from fastmcp.task_management.application.services.subtask_application_service import SubtaskApplicationService
from fastmcp.task_management.application.dtos.subtask import (
    AddSubtaskRequest,
    UpdateSubtaskRequest,
    SubtaskResponse
)


class TestSubtaskApplicationService:
    """Test cases for SubtaskApplicationService"""

    def setup_method(self):
        """Set up test fixtures"""
        self.mock_task_repository = Mock()
        self.mock_subtask_repository = Mock()
        self.user_id = "user-123"
        
        self.service = SubtaskApplicationService(
            task_repository=self.mock_task_repository,
            subtask_repository=self.mock_subtask_repository,
            user_id=self.user_id
        )

    def test_init(self):
        """Test service initialization"""
        assert self.service._task_repository == self.mock_task_repository
        assert self.service._subtask_repository == self.mock_subtask_repository
        assert self.service._user_id == self.user_id

    def test_init_without_subtask_repository(self):
        """Test service initialization without subtask repository"""
        service = SubtaskApplicationService(
            task_repository=self.mock_task_repository,
            user_id=self.user_id
        )
        
        assert service._task_repository == self.mock_task_repository
        assert service._subtask_repository is None

    def test_init_without_user_id(self):
        """Test service initialization without user_id"""
        service = SubtaskApplicationService(
            task_repository=self.mock_task_repository,
            subtask_repository=self.mock_subtask_repository
        )
        
        assert service._user_id is None

    def test_get_user_scoped_repository_with_user_method(self):
        """Test getting user-scoped repository when repository has with_user method"""
        mock_repo = Mock()
        mock_scoped_repo = Mock()
        mock_repo.with_user.return_value = mock_scoped_repo
        
        service = SubtaskApplicationService(self.mock_task_repository, user_id="test-user")
        result = service._get_user_scoped_repository(mock_repo)
        
        mock_repo.with_user.assert_called_once_with("test-user")
        assert result == mock_scoped_repo

    def test_get_user_scoped_repository_with_user_id_attribute(self):
        """Test getting user-scoped repository when repository has user_id attribute"""
        mock_repo = Mock()
        # Remove with_user method
        del mock_repo.with_user
        mock_repo.user_id = "different-user"
        mock_repo.session = Mock()
        
        # Mock repository class constructor
        with patch.object(type(mock_repo), '__call__') as mock_constructor:
            mock_new_repo = Mock()
            mock_constructor.return_value = mock_new_repo
            
            service = SubtaskApplicationService(self.mock_task_repository, user_id="test-user")
            result = service._get_user_scoped_repository(mock_repo)
            
            mock_constructor.assert_called_once_with(mock_repo.session, user_id="test-user")
            assert result == mock_new_repo

    def test_get_user_scoped_repository_no_user_support(self):
        """Test fallback when repository doesn't support user scoping"""
        mock_repo = Mock()
        # Remove with_user method
        del mock_repo.with_user
        
        service = SubtaskApplicationService(self.mock_task_repository, user_id="test-user")
        result = service._get_user_scoped_repository(mock_repo)
        
        assert result == mock_repo

    def test_get_user_scoped_repository_none_repository(self):
        """Test handling None repository"""
        service = SubtaskApplicationService(self.mock_task_repository)
        result = service._get_user_scoped_repository(None)
        
        assert result is None

    def test_with_user(self):
        """Test creating user-scoped service instance"""
        new_user_id = "new-user-456"
        
        new_service = self.service.with_user(new_user_id)
        
        assert isinstance(new_service, SubtaskApplicationService)
        assert new_service._task_repository == self.mock_task_repository
        assert new_service._subtask_repository == self.mock_subtask_repository
        assert new_service._user_id == new_user_id

    @patch('fastmcp.task_management.application.services.subtask_application_service.AddSubtaskUseCase')
    def test_add_subtask(self, mock_use_case_class):
        """Test adding subtask"""
        # Setup mock use case
        mock_use_case = Mock()
        mock_response = SubtaskResponse(
            id="subtask-123",
            task_id="task-456",
            title="Test Subtask",
            description="Test Description",
            status="todo",
            assignees=["user1"],
            priority="medium",
            progress_percentage=0
        )
        mock_use_case.execute.return_value = mock_response
        mock_use_case_class.return_value = mock_use_case
        
        request = AddSubtaskRequest(
            task_id="task-456",
            title="Test Subtask",
            description="Test Description",
            assignees=["user1"]
        )
        
        # Create new service to trigger use case creation
        service = SubtaskApplicationService(self.mock_task_repository, self.mock_subtask_repository)
        result = service.add_subtask(request)
        
        assert result == mock_response
        mock_use_case.execute.assert_called_once_with(request)

    @patch('fastmcp.task_management.application.services.subtask_application_service.RemoveSubtaskUseCase')
    def test_remove_subtask(self, mock_use_case_class):
        """Test removing subtask"""
        mock_use_case = Mock()
        mock_response = {"success": True, "message": "Subtask removed"}
        mock_use_case.execute.return_value = mock_response
        mock_use_case_class.return_value = mock_use_case
        
        service = SubtaskApplicationService(self.mock_task_repository, self.mock_subtask_repository)
        result = service.remove_subtask("task-456", "subtask-123")
        
        assert result == mock_response
        mock_use_case.execute.assert_called_once_with("task-456", "subtask-123")

    @patch('fastmcp.task_management.application.services.subtask_application_service.UpdateSubtaskUseCase')
    def test_update_subtask(self, mock_use_case_class):
        """Test updating subtask"""
        mock_use_case = Mock()
        mock_response = SubtaskResponse(
            id="subtask-123",
            task_id="task-456",
            title="Updated Subtask",
            description="Updated Description",
            status="in_progress",
            assignees=["user2"],
            priority="high",
            progress_percentage=50
        )
        mock_use_case.execute.return_value = mock_response
        mock_use_case_class.return_value = mock_use_case
        
        request = UpdateSubtaskRequest(
            task_id="task-456",
            id="subtask-123",
            title="Updated Subtask",
            description="Updated Description",
            status="in_progress",
            assignees=["user2"],
            priority="high",
            progress_percentage=50
        )
        
        service = SubtaskApplicationService(self.mock_task_repository, self.mock_subtask_repository)
        result = service.update_subtask(request)
        
        assert result == mock_response
        mock_use_case.execute.assert_called_once_with(request)

    @patch('fastmcp.task_management.application.services.subtask_application_service.CompleteSubtaskUseCase')
    def test_complete_subtask(self, mock_use_case_class):
        """Test completing subtask"""
        mock_use_case = Mock()
        mock_response = {"success": True, "message": "Subtask completed"}
        mock_use_case.execute.return_value = mock_response
        mock_use_case_class.return_value = mock_use_case
        
        service = SubtaskApplicationService(self.mock_task_repository, self.mock_subtask_repository)
        result = service.complete_subtask("task-456", "subtask-123")
        
        assert result == mock_response
        mock_use_case.execute.assert_called_once_with("task-456", "subtask-123")

    @patch('fastmcp.task_management.application.services.subtask_application_service.GetSubtasksUseCase')
    def test_get_subtasks(self, mock_use_case_class):
        """Test getting subtasks"""
        mock_use_case = Mock()
        mock_response = {
            "subtasks": [
                {"id": "subtask-1", "title": "Subtask 1"},
                {"id": "subtask-2", "title": "Subtask 2"}
            ]
        }
        mock_use_case.execute.return_value = mock_response
        mock_use_case_class.return_value = mock_use_case
        
        service = SubtaskApplicationService(self.mock_task_repository, self.mock_subtask_repository)
        result = service.get_subtasks("task-456")
        
        assert result == mock_response
        mock_use_case.execute.assert_called_once_with("task-456")

    @patch('fastmcp.task_management.application.services.subtask_application_service.GetSubtaskUseCase')
    def test_get_subtask(self, mock_use_case_class):
        """Test getting single subtask"""
        mock_use_case = Mock()
        mock_response = {"id": "subtask-123", "title": "Test Subtask"}
        mock_use_case.execute.return_value = mock_response
        mock_use_case_class.return_value = mock_use_case
        
        service = SubtaskApplicationService(self.mock_task_repository, self.mock_subtask_repository)
        result = service.get_subtask("task-456", "subtask-123")
        
        assert result == mock_response
        mock_use_case.execute.assert_called_once_with("task-456", "subtask-123")

    def test_manage_subtasks_add_action(self):
        """Test manage_subtasks with add action"""
        with patch.object(self.service, 'add_subtask') as mock_add:
            mock_response = SubtaskResponse(
                id="subtask-123",
                task_id="task-456",
                title="New Subtask",
                description="Description",
                status="todo",
                assignees=["user1"],
                priority="medium",
                progress_percentage=0
            )
            mock_add.return_value = mock_response
            
            subtask_data = {
                "title": "New Subtask",
                "description": "Description",
                "assignees": ["user1"]
            }
            
            result = self.service.manage_subtasks("task-456", "add_subtask", subtask_data)
            
            mock_add.assert_called_once()
            request = mock_add.call_args[0][0]
            assert isinstance(request, AddSubtaskRequest)
            assert request.task_id == "task-456"
            assert request.title == "New Subtask"
            assert request.assignees == ["user1"]
            assert result == mock_response.__dict__

    def test_manage_subtasks_add_action_single_assignee(self):
        """Test manage_subtasks add action with single assignee field"""
        with patch.object(self.service, 'add_subtask') as mock_add:
            mock_response = SubtaskResponse(
                id="subtask-123",
                task_id="task-456",
                title="New Subtask",
                description="Description",
                status="todo",
                assignees=["user1"],
                priority="medium",
                progress_percentage=0
            )
            mock_add.return_value = mock_response
            
            subtask_data = {
                "title": "New Subtask",
                "description": "Description",
                "assignee": "user1"  # Single assignee
            }
            
            result = self.service.manage_subtasks("task-456", "add", subtask_data)
            
            request = mock_add.call_args[0][0]
            assert request.assignees == ["user1"]

    def test_manage_subtasks_add_action_no_assignees(self):
        """Test manage_subtasks add action with no assignees"""
        with patch.object(self.service, 'add_subtask') as mock_add:
            mock_response = SubtaskResponse(
                id="subtask-123",
                task_id="task-456",
                title="New Subtask",
                description="Description",
                status="todo",
                assignees=[],
                priority="medium",
                progress_percentage=0
            )
            mock_add.return_value = mock_response
            
            subtask_data = {
                "title": "New Subtask",
                "description": "Description"
            }
            
            result = self.service.manage_subtasks("task-456", "add", subtask_data)
            
            request = mock_add.call_args[0][0]
            assert request.assignees == []

    def test_manage_subtasks_complete_action(self):
        """Test manage_subtasks with complete action"""
        with patch.object(self.service, 'complete_subtask') as mock_complete:
            mock_response = {"success": True, "message": "Completed"}
            mock_complete.return_value = mock_response
            
            subtask_data = {"id": "subtask-123"}
            
            result = self.service.manage_subtasks("task-456", "complete_subtask", subtask_data)
            
            mock_complete.assert_called_once_with("task-456", "subtask-123")
            assert result == mock_response

    def test_manage_subtasks_complete_action_missing_id(self):
        """Test manage_subtasks complete action with missing id"""
        subtask_data = {}
        
        with pytest.raises(ValueError, match="id is required for completing a subtask"):
            self.service.manage_subtasks("task-456", "complete", subtask_data)

    def test_manage_subtasks_update_action(self):
        """Test manage_subtasks with update action"""
        with patch.object(self.service, 'update_subtask') as mock_update:
            mock_response = SubtaskResponse(
                id="subtask-123",
                task_id="task-456",
                title="Updated Subtask",
                description="Updated Description",
                status="in_progress",
                assignees=["user2"],
                priority="high",
                progress_percentage=50
            )
            mock_update.return_value = mock_response
            
            subtask_data = {
                "id": "subtask-123",
                "title": "Updated Subtask",
                "description": "Updated Description",
                "status": "in_progress",
                "assignees": "user2",  # String instead of list
                "priority": "high",
                "progress_percentage": 50
            }
            
            result = self.service.manage_subtasks("task-456", "update_subtask", subtask_data)
            
            mock_update.assert_called_once()
            request = mock_update.call_args[0][0]
            assert isinstance(request, UpdateSubtaskRequest)
            assert request.id == "subtask-123"
            assert request.assignees == ["user2"]  # Should be converted to list
            assert result == mock_response.__dict__

    def test_manage_subtasks_update_action_completed_mapping(self):
        """Test manage_subtasks update action with completed field mapping"""
        with patch.object(self.service, 'update_subtask') as mock_update:
            mock_response = SubtaskResponse(
                id="subtask-123",
                task_id="task-456",
                title="Subtask",
                description="Description",
                status="completed",
                assignees=[],
                priority="medium",
                progress_percentage=100
            )
            mock_update.return_value = mock_response
            
            subtask_data = {
                "id": "subtask-123",
                "completed": True  # Should map to status="completed"
            }
            
            self.service.manage_subtasks("task-456", "update", subtask_data)
            
            request = mock_update.call_args[0][0]
            assert request.status == "completed"

    def test_manage_subtasks_remove_action(self):
        """Test manage_subtasks with remove action"""
        with patch.object(self.service, 'remove_subtask') as mock_remove:
            mock_response = {"success": True, "message": "Removed"}
            mock_remove.return_value = mock_response
            
            subtask_data = {"id": "subtask-123"}
            
            result = self.service.manage_subtasks("task-456", "remove_subtask", subtask_data)
            
            mock_remove.assert_called_once_with("task-456", "subtask-123")
            assert result == mock_response

    def test_manage_subtasks_remove_action_missing_id(self):
        """Test manage_subtasks remove action with missing id"""
        subtask_data = {}
        
        with pytest.raises(ValueError, match="id is required for removing a subtask"):
            self.service.manage_subtasks("task-456", "remove", subtask_data)

    def test_manage_subtasks_get_action(self):
        """Test manage_subtasks with get action"""
        with patch.object(self.service, 'get_subtask') as mock_get:
            mock_response = {"id": "subtask-123", "title": "Test Subtask"}
            mock_get.return_value = mock_response
            
            subtask_data = {"id": "subtask-123"}
            
            result = self.service.manage_subtasks("task-456", "get_subtask", subtask_data)
            
            mock_get.assert_called_once_with("task-456", "subtask-123")
            assert result == mock_response

    def test_manage_subtasks_get_action_missing_id(self):
        """Test manage_subtasks get action with missing id"""
        subtask_data = {}
        
        with pytest.raises(ValueError, match="id is required for getting a subtask"):
            self.service.manage_subtasks("task-456", "get", subtask_data)

    def test_manage_subtasks_list_action(self):
        """Test manage_subtasks with list action"""
        with patch.object(self.service, 'get_subtasks') as mock_get_subtasks:
            mock_response = {"subtasks": [{"id": "subtask-1"}, {"id": "subtask-2"}]}
            mock_get_subtasks.return_value = mock_response
            
            subtask_data = {}
            
            result = self.service.manage_subtasks("task-456", "list_subtasks", subtask_data)
            
            mock_get_subtasks.assert_called_once_with("task-456")
            assert result == mock_response

    def test_manage_subtasks_list_action_short_form(self):
        """Test manage_subtasks with list action (short form)"""
        with patch.object(self.service, 'get_subtasks') as mock_get_subtasks:
            mock_response = {"subtasks": []}
            mock_get_subtasks.return_value = mock_response
            
            result = self.service.manage_subtasks("task-456", "list", {})
            
            mock_get_subtasks.assert_called_once_with("task-456")
            assert result == mock_response

    def test_manage_subtasks_unknown_action(self):
        """Test manage_subtasks with unknown action"""
        with pytest.raises(ValueError, match="Unknown subtask action: unknown_action"):
            self.service.manage_subtasks("task-456", "unknown_action", {})

    def test_use_case_initialization(self):
        """Test that all use cases are properly initialized"""
        # Test that service has all required use cases
        assert hasattr(self.service, '_add_subtask_use_case')
        assert hasattr(self.service, '_update_subtask_use_case')
        assert hasattr(self.service, '_remove_subtask_use_case')
        assert hasattr(self.service, '_complete_subtask_use_case')
        assert hasattr(self.service, '_get_subtasks_use_case')
        assert hasattr(self.service, '_get_subtask_use_case')

    def test_action_aliases(self):
        """Test that action aliases work correctly"""
        # Test all action aliases
        action_mappings = {
            "add_subtask": "add",
            "complete_subtask": "complete",
            "update_subtask": "update",
            "remove_subtask": "remove",
            "get_subtask": "get",
            "list_subtasks": "list"
        }
        
        for full_action, short_action in action_mappings.items():
            with patch.object(self.service, full_action.replace("_subtask", "_subtask" if "_subtask" in full_action else "").replace("list_", "get_")) as mock_method:
                # Mock return value
                if full_action.startswith("add") or full_action.startswith("update"):
                    mock_response = SubtaskResponse(
                        id="test", task_id="test", title="test", description="test",
                        status="todo", assignees=[], priority="medium", progress_percentage=0
                    )
                    mock_method.return_value = mock_response
                else:
                    mock_method.return_value = {"success": True}
                
                # Test data based on action requirements
                if full_action in ["complete_subtask", "remove_subtask", "get_subtask"]:
                    subtask_data = {"id": "test-id"}
                else:
                    subtask_data = {"title": "Test"} if full_action == "add_subtask" else {}
                
                try:
                    result = self.service.manage_subtasks("task-456", short_action, subtask_data)
                    # If we get here, the alias worked
                    assert result is not None
                except ValueError as e:
                    # Some actions require specific fields, that's expected
                    if "required" in str(e):
                        continue
                    else:
                        raise

    def test_assignee_handling_variations(self):
        """Test different assignee field variations"""
        test_cases = [
            # (input, expected_output)
            ({"assignees": ["user1", "user2"]}, ["user1", "user2"]),
            ({"assignees": "user1"}, ["user1"]),
            ({"assignee": "user1"}, ["user1"]),
            ({"assignee": None}, []),
            ({}, [])
        ]
        
        for input_data, expected_assignees in test_cases:
            with patch.object(self.service, 'add_subtask') as mock_add:
                mock_response = SubtaskResponse(
                    id="test", task_id="test", title="test", description="test",
                    status="todo", assignees=expected_assignees, priority="medium", progress_percentage=0
                )
                mock_add.return_value = mock_response
                
                subtask_data = {"title": "Test Subtask", **input_data}
                
                self.service.manage_subtasks("task-456", "add", subtask_data)
                
                request = mock_add.call_args[0][0]
                assert request.assignees == expected_assignees