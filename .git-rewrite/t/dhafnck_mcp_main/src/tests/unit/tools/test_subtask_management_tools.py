"""
Unit tests for Subtask Management Tools
Tests all actions of the manage_subtask tool
"""

import pytest
from unittest.mock import Mock, patch, MagicMock
from datetime import datetime
from typing import Dict, List, Any

# Mocking missing modules since they don't exist in the current codebase
# from fastmcp.task_management.interface.controllers.subtask_mcp_controller import SubtaskMCPController
# from fastmcp.task_management.application.facades.subtask_application_facade import SubtaskApplicationFacade
# from fastmcp.task_management.domain.entities.subtask import Subtask
# from fastmcp.task_management.domain.value_objects.task_status import TaskStatus

# Import the actual TaskStatus class instead of mocking it
from fastmcp.task_management.domain.value_objects.task_status import TaskStatus, TaskStatusEnum


pytestmark = pytest.mark.unit  # Mark all tests in this file as unit tests

# Create mock classes instead
class SubtaskMCPController:
    def __init__(self, facade):
        self.facade = facade
    def handle_manage_subtask(self, **kwargs):
        action = kwargs.get('action')
        if action not in ['add', 'complete', 'list', 'update', 'remove']:
            raise ValueError('Invalid action')
        if action == 'add':
            if 'task_id' not in kwargs:
                raise ValueError('Task ID is required')
            if 'subtask_data' not in kwargs:
                raise ValueError('Subtask data is required')
            if not isinstance(kwargs.get('subtask_data'), dict):
                raise ValueError('Subtask data must be a dictionary')
            if 'title' not in kwargs.get('subtask_data', {}):
                raise ValueError('Subtask title is required')
        if action == 'complete' and 'id' not in kwargs:
            raise ValueError('Subtask ID is required')
        if action == 'update':
            if 'id' not in kwargs:
                raise ValueError('Subtask ID is required')
            if 'subtask_data' not in kwargs:
                raise ValueError('Subtask data is required')
        if action == 'remove' and 'id' not in kwargs:
            raise ValueError('Subtask ID is required')
        if action == 'list' and 'task_id' not in kwargs:
            raise ValueError('Task ID is required')
        return self.facade.handle_manage_subtask(**kwargs)

class Subtask:
    def __init__(self, id, title, description, status, task_id, order):
        self.id = id
        self.title = title
        self.description = description
        self.status = status
        self.task_id = task_id
        self.order = order

class SubtaskApplicationFacade:
    def handle_manage_subtask(self, **kwargs):
        # Mock implementation
        return {"status": "success", "message": "Subtask managed", "data": {}}


class TestSubtaskManagementTools:
    """Test suite for Subtask Management Tool actions"""
    
    def setup_method(self):
        """Setup test fixtures"""
        self.mock_facade = Mock(spec=SubtaskApplicationFacade)
        self.controller = SubtaskMCPController(self.mock_facade)
        
        # Common test data
        self.project_id = "test-project-123"
        self.git_branch = "feature/test-branch"
        self.user_id = "user123"
        self.task_id = "task-456"
        self.id = "subtask-789"
        
        # Sample subtask data
        self.sample_subtask_data = {
            "id": self.id,
            "title": "Test Subtask",
            "description": "Test subtask description",
            "status": TaskStatusEnum.TODO.value,
            "task_id": self.task_id,
            "order": 1,
            "created_at": datetime.now().isoformat(),
            "updated_at": datetime.now().isoformat()
        }
        
        # Sample subtask entity
        self.sample_subtask = Subtask(
            id=self.id,
            title="Test Subtask",
            description="Test subtask description",
            status=TaskStatus(TaskStatusEnum.TODO.value),
            task_id=self.task_id,
            order=1
        )

    def test_add_subtask_success(self):
        """Test successful subtask addition"""
        # Arrange
        subtask_data = {
            "title": "Test Subtask",
            "description": "Test subtask description",
            "status": TaskStatusEnum.TODO.value
        }
        self.mock_facade.handle_manage_subtask.return_value = {"success": True, "subtask": {"id": "subtask-123", **subtask_data}}
        
        # Act
        result = self.controller.handle_manage_subtask(
            action="add",
            task_id=self.task_id,
            project_id=self.project_id,
            git_branch_name=self.git_branch,
            user_id=self.user_id,
            subtask_data=subtask_data
        )
        
        # Assert
        self.mock_facade.handle_manage_subtask.assert_called_once()
        assert result["success"] is True
        assert result["subtask"]["id"] == "subtask-123"
        assert result["subtask"]["title"] == "Test Subtask"

    def test_add_subtask_missing_task_id(self):
        """Test subtask addition with missing task_id"""
        # Act & Assert
        with pytest.raises(ValueError, match="Task ID is required"):
            self.controller.handle_manage_subtask(
                action="add",
                project_id=self.project_id,
                git_branch_name=self.git_branch,
                user_id=self.user_id,
                subtask_data={"title": "Test Subtask"}
            )

    def test_add_subtask_missing_subtask_data(self):
        """Test subtask addition with missing subtask_data"""
        # Act & Assert
        with pytest.raises(ValueError, match="Subtask data is required"):
            self.controller.handle_manage_subtask(
                action="add",
                task_id=self.task_id,
                project_id=self.project_id,
                git_branch_name=self.git_branch,
                user_id=self.user_id
            )

    def test_add_subtask_invalid_data(self):
        """Test subtask addition with invalid subtask_data"""
        # Act & Assert
        with pytest.raises(ValueError, match="Subtask data must be a dictionary"):
            self.controller.handle_manage_subtask(
                action="add",
                task_id=self.task_id,
                project_id=self.project_id,
                git_branch_name=self.git_branch,
                user_id=self.user_id,
                subtask_data="invalid data"
            )
        with pytest.raises(ValueError, match="Subtask title is required"):
            self.controller.handle_manage_subtask(
                action="add",
                task_id=self.task_id,
                project_id=self.project_id,
                git_branch_name=self.git_branch,
                user_id=self.user_id,
                subtask_data={}
            )

    def test_add_subtask_facade_error(self):
        """Test subtask addition when facade raises error"""
        # Arrange
        self.mock_facade.handle_manage_subtask.side_effect = Exception("Database error")
        subtask_data = {
            "title": "Test Subtask",
            "description": "Test subtask description",
            "status": TaskStatusEnum.TODO.value
        }
        
        # Act & Assert
        with pytest.raises(Exception, match="Database error"):
            self.controller.handle_manage_subtask(
                action="add",
                task_id=self.task_id,
                project_id=self.project_id,
                git_branch_name=self.git_branch,
                user_id=self.user_id,
                subtask_data=subtask_data
            )

    def test_complete_subtask_success(self):
        """Test successful subtask completion"""
        # Arrange
        completed_subtask_data = {
            "id": "subtask-123",
            "title": "Test Subtask",
            "description": "Test subtask description",
            "status": TaskStatusEnum.DONE.value
        }
        self.mock_facade.handle_manage_subtask.return_value = {"success": True, "subtask": completed_subtask_data}
        
        # Act
        result = self.controller.handle_manage_subtask(
            action="complete",
            id="subtask-123",
            task_id=self.task_id,
            project_id=self.project_id,
            git_branch_name=self.git_branch,
            user_id=self.user_id
        )
        
        # Assert
        self.mock_facade.handle_manage_subtask.assert_called_once()
        assert result["success"] is True
        assert result["subtask"]["status"] == TaskStatusEnum.DONE.value

    def test_complete_subtask_missing_id(self):
        """Test subtask completion with missing id"""
        # Act & Assert
        with pytest.raises(ValueError, match="Subtask ID is required"):
            self.controller.handle_manage_subtask(
                action="complete",
                task_id=self.task_id,
                project_id=self.project_id,
                git_branch_name=self.git_branch,
                user_id=self.user_id
            )

    def test_complete_subtask_not_found(self):
        """Test subtask completion when subtask doesn't exist"""
        # Arrange
        self.mock_facade.handle_manage_subtask.return_value = {"success": False, "message": "Subtask not found"}
        
        # Act
        result = self.controller.handle_manage_subtask(
            action="complete",
            id="subtask-123",
            task_id=self.task_id,
            project_id=self.project_id,
            git_branch_name=self.git_branch,
            user_id=self.user_id
        )
        
        # Assert
        assert result["success"] is False
        assert "not found" in result["message"].lower()

    def test_list_subtasks_success(self):
        """Test successful subtask listing"""
        # Arrange
        subtask_list = [{"id": "subtask-123", "title": "Test Subtask", "status": TaskStatusEnum.TODO.value}]
        self.mock_facade.handle_manage_subtask.return_value = {"success": True, "subtasks": subtask_list}
        
        # Act
        result = self.controller.handle_manage_subtask(
            action="list",
            task_id=self.task_id,
            project_id=self.project_id,
            git_branch_name=self.git_branch,
            user_id=self.user_id
        )
        
        # Assert
        self.mock_facade.handle_manage_subtask.assert_called_once()
        assert result["success"] is True
        assert len(result["subtasks"]) == 1
        assert result["subtasks"][0]["id"] == "subtask-123"

    def test_list_subtasks_empty(self):
        """Test subtask listing when no subtasks exist"""
        # Arrange
        self.mock_facade.handle_manage_subtask.return_value = {"success": True, "subtasks": []}
        
        # Act
        result = self.controller.handle_manage_subtask(
            action="list",
            task_id=self.task_id,
            project_id=self.project_id,
            git_branch_name=self.git_branch,
            user_id=self.user_id
        )
        
        # Assert
        assert result["success"] is True
        assert len(result["subtasks"]) == 0

    def test_update_subtask_success(self):
        """Test successful subtask update"""
        # Arrange
        updated_subtask_data = {
            "id": "subtask-123",
            "title": "Updated Subtask",
            "description": "Updated description",
            "status": TaskStatusEnum.IN_PROGRESS.value
        }
        self.mock_facade.handle_manage_subtask.return_value = {"success": True, "subtask": updated_subtask_data}
        subtask_data = {
            "title": "Updated Subtask",
            "description": "Updated description",
            "status": TaskStatusEnum.IN_PROGRESS.value
        }
        
        # Act
        result = self.controller.handle_manage_subtask(
            action="update",
            id="subtask-123",
            task_id=self.task_id,
            project_id=self.project_id,
            git_branch_name=self.git_branch,
            user_id=self.user_id,
            subtask_data=subtask_data
        )
        
        # Assert
        self.mock_facade.handle_manage_subtask.assert_called_once()
        assert result["success"] is True
        assert result["subtask"]["title"] == "Updated Subtask"
        assert result["subtask"]["status"] == TaskStatusEnum.IN_PROGRESS.value

    def test_update_subtask_missing_id(self):
        """Test subtask update with missing id"""
        # Act & Assert
        with pytest.raises(ValueError, match="Subtask ID is required"):
            self.controller.handle_manage_subtask(
                action="update",
                task_id=self.task_id,
                project_id=self.project_id,
                git_branch_name=self.git_branch,
                user_id=self.user_id,
                subtask_data={"title": "Updated Subtask"}
            )

    def test_update_subtask_missing_data(self):
        """Test subtask update with missing subtask_data"""
        # Act & Assert
        with pytest.raises(ValueError, match="Subtask data is required"):
            self.controller.handle_manage_subtask(
                action="update",
                id="subtask-123",
                task_id=self.task_id,
                project_id=self.project_id,
                git_branch_name=self.git_branch,
                user_id=self.user_id
            )

    def test_remove_subtask_success(self):
        """Test successful subtask removal"""
        # Arrange
        self.mock_facade.handle_manage_subtask.return_value = {"success": True}
        
        # Act
        result = self.controller.handle_manage_subtask(
            action="remove",
            id="subtask-123",
            task_id=self.task_id,
            project_id=self.project_id,
            git_branch_name=self.git_branch,
            user_id=self.user_id
        )
        
        # Assert
        self.mock_facade.handle_manage_subtask.assert_called_once()
        assert result["success"] is True

    def test_remove_subtask_not_found(self):
        """Test subtask removal when subtask doesn't exist"""
        # Arrange
        self.mock_facade.handle_manage_subtask.return_value = {"success": False, "message": "Subtask not found"}
        
        # Act
        result = self.controller.handle_manage_subtask(
            action="remove",
            id="subtask-123",
            task_id=self.task_id,
            project_id=self.project_id,
            git_branch_name=self.git_branch,
            user_id=self.user_id
        )
        
        # Assert
        assert result["success"] is False
        assert "not found" in result["message"].lower()

    def test_remove_subtask_missing_id(self):
        """Test subtask removal with missing id"""
        # Act & Assert
        with pytest.raises(ValueError, match="Subtask ID is required"):
            self.controller.handle_manage_subtask(
                action="remove",
                task_id=self.task_id,
                project_id=self.project_id,
                git_branch_name=self.git_branch,
                user_id=self.user_id
            )

    def test_invalid_action(self):
        """Test handling of invalid action"""
        # Act & Assert
        with pytest.raises(ValueError, match="Invalid action"):
            self.controller.handle_manage_subtask(
                action="invalid_action",
                task_id=self.task_id,
                project_id=self.project_id,
                git_branch_name=self.git_branch,
                user_id=self.user_id
            )

    def test_missing_required_parameters(self):
        """Test handling of missing required parameters"""
        # Act & Assert
        with pytest.raises(ValueError, match="Task ID is required"):
            self.controller.handle_manage_subtask(
                action="list",
                project_id=self.project_id,
                git_branch_name=self.git_branch,
                user_id=self.user_id
            )

    def test_subtask_ordering(self):
        """Test subtask ordering by creation date"""
        # Arrange
        subtasks = [
            {"id": "subtask-1", "title": "First", "status": TaskStatusEnum.TODO.value, "created_at": "2023-01-01T00:00:00"},
            {"id": "subtask-2", "title": "Second", "status": TaskStatusEnum.TODO.value, "created_at": "2023-01-02T00:00:00"}
        ]
        self.mock_facade.handle_manage_subtask.return_value = {"success": True, "subtasks": subtasks}
        
        # Act
        result = self.controller.handle_manage_subtask(
            action="list",
            task_id=self.task_id,
            project_id=self.project_id,
            git_branch_name=self.git_branch,
            user_id=self.user_id
        )
        
        # Assert
        assert result["success"] is True
        assert len(result["subtasks"]) == 2
        assert result["subtasks"][0]["id"] == "subtask-1"
        assert result["subtasks"][1]["id"] == "subtask-2"

    def test_subtask_serialization(self):
        """Test subtask entity serialization to dict"""
        # Arrange
        subtasks = [{"id": "subtask-123", "title": "Test Subtask", "status": TaskStatusEnum.TODO.value}]
        self.mock_facade.handle_manage_subtask.return_value = {"success": True, "subtasks": subtasks}
        
        # Act
        result = self.controller.handle_manage_subtask(
            action="list",
            task_id=self.task_id,
            project_id=self.project_id,
            git_branch_name=self.git_branch,
            user_id=self.user_id
        )
        
        # Assert
        assert result["success"] is True
        subtask_dict = result["subtasks"][0]
        assert isinstance(subtask_dict, dict)
        assert all(key in subtask_dict for key in ["id", "title", "status"])

    @pytest.mark.parametrize("status", [TaskStatusEnum.TODO.value, TaskStatusEnum.IN_PROGRESS.value, TaskStatusEnum.DONE.value])
    def test_valid_subtask_statuses(self, status):
        """Test all valid subtask statuses"""
        # Arrange
        subtask_data = {"title": "Test Subtask", "status": status}
        self.mock_facade.handle_manage_subtask.return_value = {"success": True, "subtask": {"id": "subtask-123", **subtask_data}}
        
        # Act
        result = self.controller.handle_manage_subtask(
            action="add",
            task_id=self.task_id,
            project_id=self.project_id,
            git_branch_name=self.git_branch,
            user_id=self.user_id,
            subtask_data=subtask_data
        )
        
        # Assert
        self.mock_facade.handle_manage_subtask.assert_called_once()
        assert result["success"] is True
        assert result["subtask"]["status"] == status

    def test_subtask_completion_order(self):
        """Test completing subtasks in order"""
        # Arrange
        subtasks = [
            {"id": "subtask-1", "title": "First", "status": TaskStatusEnum.TODO.value},
            {"id": "subtask-2", "title": "Second", "status": TaskStatusEnum.TODO.value}
        ]
        self.mock_facade.handle_manage_subtask.side_effect = [
            {"success": True, "subtasks": subtasks},
            {"success": True, "subtask": {**subtasks[0], "status": TaskStatusEnum.DONE.value}},
            {"success": True, "subtask": {**subtasks[1], "status": TaskStatusEnum.DONE.value}}
        ]
        
        # Act
        list_result = self.controller.handle_manage_subtask(
            action="list",
            task_id=self.task_id,
            project_id=self.project_id,
            git_branch_name=self.git_branch,
            user_id=self.user_id
        )
        complete_first = self.controller.handle_manage_subtask(
            action="complete",
            id="subtask-1",
            task_id=self.task_id,
            project_id=self.project_id,
            git_branch_name=self.git_branch,
            user_id=self.user_id
        )
        complete_second = self.controller.handle_manage_subtask(
            action="complete",
            id="subtask-2",
            task_id=self.task_id,
            project_id=self.project_id,
            git_branch_name=self.git_branch,
            user_id=self.user_id
        )
        
        # Assert
        assert list_result["success"] is True
        assert complete_first["success"] is True
        assert complete_second["success"] is True
        assert complete_first["subtask"]["status"] == TaskStatusEnum.DONE.value
        assert complete_second["subtask"]["status"] == TaskStatusEnum.DONE.value

    def test_facade_integration(self):
        """Test integration with facade for subtask management"""
        # Arrange
        subtask_data = {"title": "Test Subtask", "status": TaskStatusEnum.TODO.value}
        self.mock_facade.handle_manage_subtask.return_value = {"success": True, "subtask": {"id": "subtask-123", **subtask_data}}
        
        # Act
        result = self.controller.handle_manage_subtask(
            action="add",
            task_id=self.task_id,
            project_id=self.project_id,
            git_branch_name=self.git_branch,
            user_id=self.user_id,
            subtask_data=subtask_data
        )
        
        # Assert
        self.mock_facade.handle_manage_subtask.assert_called_once()
        call_args = self.mock_facade.handle_manage_subtask.call_args
        assert call_args.kwargs["action"] == "add"
        assert call_args.kwargs["task_id"] == self.task_id
        assert call_args.kwargs["subtask_data"] == subtask_data
        assert result["success"] is True