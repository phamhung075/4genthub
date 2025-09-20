"""
Unit tests for SubtaskMCPController parameter fixing
Tests the critical fix for task_id vs git_branch_id confusion
"""

import pytest
from unittest.mock import Mock, MagicMock, patch
from uuid import uuid4
import sys
from pathlib import Path

# Add the src directory to the path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from fastmcp.task_management.interface.mcp_controllers.subtask_mcp_controller.subtask_mcp_controller import (
    SubtaskMCPController
)


class TestSubtaskMCPController:
    """Unit tests for SubtaskMCPController to verify correct parameter handling"""

    @pytest.fixture
    def mock_facade_service(self):
        """Create a mock facade service"""
        mock_service = Mock()
        mock_service.get_task_facade = Mock()
        mock_service.get_subtask_facade = Mock()
        return mock_service

    @pytest.fixture
    def controller(self, mock_facade_service):
        """Create controller with mocked dependencies"""
        controller = SubtaskMCPController(
            facade_service=mock_facade_service,
            workflow_guidance=Mock()
        )
        return controller

    @pytest.fixture
    def sample_task_data(self):
        """Generate sample task data for testing"""
        return {
            "task_id": str(uuid4()),
            "git_branch_id": str(uuid4()),
            "project_id": str(uuid4()),
            "title": "Parent Task",
            "description": "Parent task description"
        }

    def test_get_facade_for_request_with_correct_git_branch_lookup(self, controller, mock_facade_service, sample_task_data):
        """
        CRITICAL TEST: Verify that _get_facade_for_request looks up git_branch_id correctly
        This tests the fix for the bug where task_id was incorrectly passed as git_branch_id
        """
        task_id = sample_task_data["task_id"]
        git_branch_id = sample_task_data["git_branch_id"]
        user_id = str(uuid4())

        # Setup mock task facade to return task data
        mock_task_facade = Mock()
        mock_task_facade.get_task.return_value = {
            "success": True,
            "data": {
                "task": {
                    "id": task_id,
                    "git_branch_id": git_branch_id,
                    "title": sample_task_data["title"]
                }
            }
        }
        mock_facade_service.get_task_facade.return_value = mock_task_facade

        # Setup mock subtask facade
        mock_subtask_facade = Mock()
        mock_facade_service.get_subtask_facade.return_value = mock_subtask_facade

        # Call the method being tested
        result = controller._get_facade_for_request(task_id=task_id, user_id=user_id)

        # CRITICAL ASSERTIONS:
        # 1. Should call get_task_facade to look up the task
        mock_facade_service.get_task_facade.assert_called_once_with(user_id=user_id)

        # 2. Should fetch task details to get git_branch_id
        mock_task_facade.get_task.assert_called_once_with(task_id=task_id)

        # 3. Should call get_subtask_facade with CORRECT git_branch_id (not task_id!)
        mock_facade_service.get_subtask_facade.assert_called_once_with(
            user_id=user_id,
            git_branch_id=git_branch_id  # This is the FIX - using actual git_branch_id
        )

        # 4. Verify task_id was NOT passed as git_branch_id
        call_args = mock_facade_service.get_subtask_facade.call_args
        assert call_args[1]["git_branch_id"] == git_branch_id
        assert call_args[1]["git_branch_id"] != task_id

        # 5. Should return the subtask facade
        assert result == mock_subtask_facade

    def test_get_facade_handles_missing_task_gracefully(self, controller, mock_facade_service):
        """Test that missing parent task is handled correctly"""
        task_id = str(uuid4())
        user_id = str(uuid4())

        # Setup mock to return no task
        mock_task_facade = Mock()
        mock_task_facade.get_task.return_value = {
            "success": False,
            "error": "Task not found"
        }
        mock_facade_service.get_task_facade.return_value = mock_task_facade

        # Should raise an appropriate error
        with pytest.raises(ValueError, match="Task .* not found"):
            controller._get_facade_for_request(task_id=task_id, user_id=user_id)

        # Should NOT call get_subtask_facade if task doesn't exist
        mock_facade_service.get_subtask_facade.assert_not_called()

    def test_get_facade_handles_task_without_git_branch_id(self, controller, mock_facade_service):
        """Test handling of task that's missing git_branch_id"""
        task_id = str(uuid4())
        user_id = str(uuid4())

        # Setup mock task without git_branch_id
        mock_task_facade = Mock()
        mock_task_facade.get_task.return_value = {
            "success": True,
            "data": {
                "task": {
                    "id": task_id,
                    "title": "Task without git_branch_id"
                    # Note: git_branch_id is missing
                }
            }
        }
        mock_facade_service.get_task_facade.return_value = mock_task_facade

        # Should raise an appropriate error
        with pytest.raises(ValueError, match="missing git_branch_id"):
            controller._get_facade_for_request(task_id=task_id, user_id=user_id)

    def test_create_subtask_validates_parent_before_creation(self, controller, mock_facade_service, sample_task_data):
        """Test that subtask creation validates parent task exists"""
        task_id = sample_task_data["task_id"]
        git_branch_id = sample_task_data["git_branch_id"]
        user_id = str(uuid4())

        # Setup successful task lookup
        mock_task_facade = Mock()
        mock_task_facade.get_task.return_value = {
            "success": True,
            "data": {
                "task": {
                    "id": task_id,
                    "git_branch_id": git_branch_id
                }
            }
        }
        mock_facade_service.get_task_facade.return_value = mock_task_facade

        # Setup subtask facade
        mock_subtask_facade = Mock()
        mock_subtask_facade.create_subtask.return_value = {
            "success": True,
            "subtask": {
                "id": str(uuid4()),
                "parent_task_id": task_id,  # Correct parent
                "title": "Test Subtask"
            }
        }
        mock_facade_service.get_subtask_facade.return_value = mock_subtask_facade

        # Create subtask
        result = controller.create(
            task_id=task_id,
            title="Test Subtask",
            description="Test Description",
            user_id=user_id
        )

        # Verify parent task was validated
        mock_facade_service.get_task_facade.assert_called()
        mock_task_facade.get_task.assert_called_with(task_id=task_id)

        # Verify subtask was created with correct parameters
        mock_subtask_facade.create_subtask.assert_called_once()
        create_args = mock_subtask_facade.create_subtask.call_args[1]

        # Critical: parent_task_id should be task_id, not git_branch_id
        assert create_args.get("parent_task_id") == task_id or create_args.get("task_id") == task_id

        # Result should indicate success
        assert result["success"] is True

    def test_update_subtask_uses_correct_context(self, controller, mock_facade_service, sample_task_data):
        """Test that subtask updates use correct task context"""
        task_id = sample_task_data["task_id"]
        git_branch_id = sample_task_data["git_branch_id"]
        subtask_id = str(uuid4())
        user_id = str(uuid4())

        # Setup task lookup
        mock_task_facade = Mock()
        mock_task_facade.get_task.return_value = {
            "success": True,
            "data": {
                "task": {
                    "id": task_id,
                    "git_branch_id": git_branch_id
                }
            }
        }
        mock_facade_service.get_task_facade.return_value = mock_task_facade

        # Setup subtask facade
        mock_subtask_facade = Mock()
        mock_subtask_facade.update_subtask.return_value = {
            "success": True,
            "subtask": {
                "id": subtask_id,
                "parent_task_id": task_id
            }
        }
        mock_facade_service.get_subtask_facade.return_value = mock_subtask_facade

        # Update subtask
        result = controller.update(
            task_id=task_id,
            subtask_id=subtask_id,
            title="Updated Title",
            user_id=user_id
        )

        # Verify correct facade was obtained
        mock_facade_service.get_subtask_facade.assert_called_with(
            user_id=user_id,
            git_branch_id=git_branch_id  # Should use git_branch_id from task
        )

        # Verify update was called
        mock_subtask_facade.update_subtask.assert_called_once()

    def test_list_subtasks_uses_correct_task_context(self, controller, mock_facade_service, sample_task_data):
        """Test that listing subtasks uses correct task context"""
        task_id = sample_task_data["task_id"]
        git_branch_id = sample_task_data["git_branch_id"]
        user_id = str(uuid4())

        # Setup task lookup
        mock_task_facade = Mock()
        mock_task_facade.get_task.return_value = {
            "success": True,
            "data": {
                "task": {
                    "id": task_id,
                    "git_branch_id": git_branch_id
                }
            }
        }
        mock_facade_service.get_task_facade.return_value = mock_task_facade

        # Setup subtask facade
        mock_subtask_facade = Mock()
        mock_subtask_facade.list_subtasks.return_value = {
            "success": True,
            "subtasks": [
                {
                    "id": str(uuid4()),
                    "parent_task_id": task_id,  # All should have correct parent
                    "title": "Subtask 1"
                },
                {
                    "id": str(uuid4()),
                    "parent_task_id": task_id,
                    "title": "Subtask 2"
                }
            ]
        }
        mock_facade_service.get_subtask_facade.return_value = mock_subtask_facade

        # List subtasks
        result = controller.list(task_id=task_id, user_id=user_id)

        # Verify correct context was used
        mock_facade_service.get_subtask_facade.assert_called_with(
            user_id=user_id,
            git_branch_id=git_branch_id
        )

        # All returned subtasks should have correct parent_task_id
        if "subtasks" in result:
            for subtask in result["subtasks"]:
                assert subtask.get("parent_task_id") == task_id

    def test_complete_subtask_uses_correct_context(self, controller, mock_facade_service, sample_task_data):
        """Test that completing a subtask uses correct context"""
        task_id = sample_task_data["task_id"]
        git_branch_id = sample_task_data["git_branch_id"]
        subtask_id = str(uuid4())
        user_id = str(uuid4())

        # Setup mocks
        mock_task_facade = Mock()
        mock_task_facade.get_task.return_value = {
            "success": True,
            "data": {
                "task": {
                    "id": task_id,
                    "git_branch_id": git_branch_id
                }
            }
        }
        mock_facade_service.get_task_facade.return_value = mock_task_facade

        mock_subtask_facade = Mock()
        mock_subtask_facade.complete_subtask.return_value = {
            "success": True,
            "subtask": {
                "id": subtask_id,
                "parent_task_id": task_id,
                "status": "completed"
            }
        }
        mock_facade_service.get_subtask_facade.return_value = mock_subtask_facade

        # Complete subtask
        result = controller.complete(
            task_id=task_id,
            subtask_id=subtask_id,
            completion_summary="Task completed successfully",
            user_id=user_id
        )

        # Verify correct facade context
        mock_facade_service.get_subtask_facade.assert_called_with(
            user_id=user_id,
            git_branch_id=git_branch_id
        )

        # Verify completion was called
        mock_subtask_facade.complete_subtask.assert_called_once()


if __name__ == "__main__":
    pytest.main([__file__, "-v"])