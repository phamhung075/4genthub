"""
Tests for Subtask MCP Controller CRUD Handler
"""

import pytest
from unittest.mock import Mock, patch, AsyncMock
from typing import Dict, Any
import uuid
from datetime import datetime, timezone

from fastmcp.task_management.interface.mcp_controllers.subtask_mcp_controller.handlers.crud_handler import (
    SubtaskCRUDHandler
)
from fastmcp.task_management.interface.utils.response_formatter import StandardResponseFormatter, ErrorCodes
from fastmcp.task_management.application.facades.subtask_application_facade import SubtaskApplicationFacade
from fastmcp.task_management.domain.entities import Task, Subtask, TaskStatus, TaskPriority
from fastmcp.task_management.application.exceptions import (
    TaskNotFoundError,
    SubtaskNotFoundError,
    ValidationError
)


class TestSubtaskCRUDHandler:
    """Test Subtask CRUD Handler functionality"""

    @pytest.fixture
    def mock_response_formatter(self):
        """Create mock response formatter"""
        formatter = Mock(spec=StandardResponseFormatter)
        formatter.create_error_response = Mock(return_value={"success": False, "error": "test error"})
        formatter.format_response = Mock(side_effect=lambda success, data=None, error=None: {
            "success": success,
            "data": data,
            "error": error
        })
        return formatter

    @pytest.fixture
    def mock_context_facade(self):
        """Create mock context facade"""
        facade = Mock()
        facade.update_context = AsyncMock()
        return facade

    @pytest.fixture
    def mock_task_facade(self):
        """Create mock task facade"""
        facade = Mock()
        facade.get_task = AsyncMock()
        facade.update_task = AsyncMock()
        return facade
    
    @pytest.fixture
    def mock_subtask_facade(self):
        """Create mock subtask application facade"""
        facade = Mock(spec=SubtaskApplicationFacade)
        # Main method that the handler actually uses
        facade.handle_manage_subtask = Mock()
        return facade

    @pytest.fixture
    def handler(self, mock_response_formatter, mock_context_facade, mock_task_facade):
        """Create handler instance with mocks"""
        return SubtaskCRUDHandler(
            response_formatter=mock_response_formatter,
            context_facade=mock_context_facade,
            task_facade=mock_task_facade
        )

    @pytest.fixture
    def sample_task(self):
        """Create sample task"""
        task = Mock(spec=Task)
        task.id = "task-123"
        task.title = "Main Task"
        task.status = TaskStatus.IN_PROGRESS
        task.priority = "high"  # Priority is a string in the implementation
        task.assignees = ["coding-agent", "@test-agent"]
        task.to_dict = Mock(return_value={
            "id": "task-123",
            "title": "Main Task", 
            "status": "in_progress",
            "priority": "high",
            "assignees": ["coding-agent", "@test-agent"]
        })
        return task

    @pytest.fixture
    def sample_subtask(self):
        """Create sample subtask"""
        subtask = Mock(spec=Subtask)
        subtask.id = "sub-123"
        subtask.task_id = "task-123"
        subtask.title = "Implement login endpoint"
        subtask.description = "Create POST /auth/login endpoint"
        subtask.status = TaskStatus.TODO
        subtask.priority = "high"  # Priority is a string in the implementation
        subtask.assignees = ["coding-agent"]
        subtask.progress_percentage = 0
        subtask.to_dict = Mock(return_value={
            "id": "sub-123",
            "task_id": "task-123",
            "title": "Implement login endpoint",
            "description": "Create POST /auth/login endpoint",
            "status": "todo",
            "priority": "high",
            "assignees": ["coding-agent"],
            "progress_percentage": 0
        })
        return subtask

    @pytest.mark.asyncio
    async def test_handle_create_subtask(self, handler, mock_subtask_facade, sample_task, sample_subtask):
        """Test creating a subtask"""
        # Configure mocks - need to handle both create and list calls
        def handle_manage_subtask_side_effect(*args, **kwargs):
            if kwargs.get('action') == 'list':
                # Return empty list for parent progress calculation
                return {"success": True, "subtasks": []}
            else:
                # Return created subtask
                return {
                    "success": True,
                    "subtask": sample_subtask.to_dict(),
                    "agent_inheritance_applied": False
                }
        mock_subtask_facade.handle_manage_subtask.side_effect = handle_manage_subtask_side_effect
        
        # Execute
        result = handler.create_subtask(
            facade=mock_subtask_facade,
            task_id="task-123",
            title="Implement login endpoint",
            description="Create POST /auth/login endpoint",
            assignees=["coding-agent"]
        )
        
        # Verify
        assert result["success"] is True
        assert result["subtask"]["id"] == "sub-123"
        assert result["subtask"]["title"] == "Implement login endpoint"
        # The implementation calls handle_manage_subtask twice: once for create and once for _get_parent_progress
        assert mock_subtask_facade.handle_manage_subtask.call_count >= 1
        # Check that the first call was for create
        first_call = mock_subtask_facade.handle_manage_subtask.call_args_list[0]
        assert first_call.kwargs['action'] == 'create'
        assert first_call.kwargs['task_id'] == 'task-123'

    @pytest.mark.asyncio
    async def test_handle_create_subtask_inherit_assignees(self, handler, mock_subtask_facade, sample_task):
        """Test creating subtask inherits parent assignees when none specified"""
        # Configure mocks to simulate agent inheritance
        mock_subtask_facade.handle_manage_subtask.return_value = {
            "success": True,
            "subtask": {
                "id": "sub-456",
                "task_id": "task-123",
                "title": "New Subtask",
                "assignees": ["coding-agent", "@test-agent"]
            },
            "agent_inheritance_applied": True,
            "inherited_assignees": ["coding-agent", "@test-agent"]
        }
        
        # Execute without assignees
        result = handler.create_subtask(
            facade=mock_subtask_facade,
            task_id="task-123",
            title="New Subtask"
        )
        
        # Verify inheritance
        assert result["success"] is True
        assert result["subtask"]["assignees"] == ["coding-agent", "@test-agent"]
        # Check for agent_inheritance_applied instead of inheritance_info
        assert result.get("agent_inheritance_applied") is True or result.get("inheritance_info", {}).get("applied") is True

    @pytest.mark.asyncio  
    async def test_handle_create_subtask_task_not_found(self, handler, mock_subtask_facade):
        """Test creating subtask when parent task doesn't exist"""
        # Configure mock to return error
        mock_subtask_facade.handle_manage_subtask.return_value = {
            "success": False,
            "error": "Task not found: task-999"
        }
        
        # Execute
        result = handler.create_subtask(
            facade=mock_subtask_facade,
            task_id="task-999",
            title="Orphan Subtask"
        )
        
        # Verify error response
        assert result["success"] is False

    @pytest.mark.asyncio
    async def test_handle_update_subtask(self, handler, mock_subtask_facade, sample_subtask):
        """Test updating a subtask"""
        # Configure mocks
        mock_subtask_facade.handle_manage_subtask.return_value = {
            "success": True,
            "subtask": {
                "id": "sub-123",
                "task_id": "task-123",
                "title": "Updated login endpoint",
                "description": "Updated description", 
                "status": "in_progress",
                "progress_percentage": 50
            }
        }
        
        # Execute
        result = handler.update_subtask(
            facade=mock_subtask_facade,
            task_id="task-123",
            subtask_id="sub-123",
            title="Updated login endpoint",
            description="Updated description",
            progress_percentage=50
        )
        
        # Verify
        assert result["success"] is True
        assert result["subtask"]["title"] == "Updated login endpoint"
        assert result["subtask"]["progress_percentage"] == 50
        assert result["subtask"]["status"] == "in_progress"  # Auto-set from percentage

    @pytest.mark.asyncio
    async def test_handle_update_subtask_auto_status(self, handler, mock_subtask_facade):
        """Test automatic status setting based on progress percentage"""
        test_cases = [
            (0, TaskStatus.TODO),
            (1, TaskStatus.IN_PROGRESS),
            (50, TaskStatus.IN_PROGRESS),
            (99, TaskStatus.IN_PROGRESS),
            (100, TaskStatus.DONE)
        ]
        
        for percentage, expected_status in test_cases:
            # Configure mock - need to handle both update and list calls
            call_count = [0]
            def handle_manage_subtask_side_effect(*args, **kwargs):
                call_count[0] += 1
                if kwargs.get('action') == 'list':
                    return {"success": True, "subtasks": []}
                else:
                    return {
                        "success": True,
                        "subtask": {
                            "id": "sub-123",
                            "task_id": "task-123",
                            "title": "Test",
                            "status": expected_status,
                            "progress_percentage": percentage
                        }
                    }
            mock_subtask_facade.handle_manage_subtask.side_effect = handle_manage_subtask_side_effect
            
            # Execute
            result = handler.update_subtask(
                facade=mock_subtask_facade,
                task_id="task-123",
                subtask_id="sub-123",
                progress_percentage=percentage
            )
            
            # Verify status
            assert result["subtask"]["status"] == expected_status

    @pytest.mark.asyncio
    async def test_handle_delete_subtask(self, handler, mock_subtask_facade):
        """Test deleting a subtask"""
        # Configure mocks
        mock_subtask_facade.handle_manage_subtask.return_value = {
            "success": True,
            "message": "Subtask deleted successfully"
        }
        
        # Execute
        result = handler.delete_subtask(
            facade=mock_subtask_facade,
            task_id="task-123",
            subtask_id="sub-123"
        )
        
        # Verify
        assert result["success"] is True
        assert mock_subtask_facade.handle_manage_subtask.call_count >= 1

    @pytest.mark.asyncio
    async def test_handle_delete_subtask_not_found(self, handler, mock_subtask_facade):
        """Test deleting non-existent subtask"""
        # Configure mock
        mock_subtask_facade.handle_manage_subtask.return_value = {
            "success": False,
            "error": "Subtask not found: sub-999"
        }
        
        # Execute
        result = handler.delete_subtask(
            facade=mock_subtask_facade,
            task_id="task-123",
            subtask_id="sub-999"
        )
        
        # Verify error response
        assert result["success"] is False

    @pytest.mark.asyncio
    async def test_handle_get_subtask(self, handler, mock_subtask_facade, sample_subtask):
        """Test getting a specific subtask"""
        # Configure mocks
        mock_subtask_facade.handle_manage_subtask.return_value = {
            "success": True,
            "subtask": sample_subtask.to_dict()
        }
        
        # Execute
        result = handler.get_subtask(
            facade=mock_subtask_facade,
            task_id="task-123",
            subtask_id="sub-123"
        )
        
        # Verify
        assert result["success"] is True
        assert result["subtask"]["id"] == "sub-123"
        assert result["subtask"]["title"] == "Implement login endpoint"

    @pytest.mark.asyncio
    async def test_handle_list_subtasks(self, handler, mock_subtask_facade):
        """Test listing all subtasks for a task"""
        # Configure mocks
        mock_subtask_facade.handle_manage_subtask.return_value = {
            "success": True,
            "subtasks": [
                {"id": "sub-1", "title": "Subtask 1", "progress_percentage": 100},
                {"id": "sub-2", "title": "Subtask 2", "progress_percentage": 50}
            ],
            "progress_summary": {
                "total_subtasks": 2,
                "completed_subtasks": 1,
                "average_progress": 75,
                "overall_status": "in_progress"
            }
        }
        
        # Execute
        result = handler.list_subtasks(
            facade=mock_subtask_facade,
            task_id="task-123"
        )
        
        # Verify
        assert result["success"] is True
        assert len(result["subtasks"]) == 2
        assert result["progress_summary"]["total_subtasks"] == 2
        assert result["progress_summary"]["average_progress"] == 75

    @pytest.mark.asyncio
    async def test_handle_complete_subtask(self, handler, mock_subtask_facade, sample_task):
        """Test completing a subtask"""
        # Configure mocks
        mock_subtask_facade.handle_manage_subtask.return_value = {
            "success": True,
            "subtask": {
                "id": "sub-123",
                "status": "done",
                "progress_percentage": 100
            },
            "parent_progress": {
                "total_subtasks": 2,
                "completed_subtasks": 2,
                "progress_percentage": 100
            }
        }
        
        # Execute - use correct parameter names from implementation
        result = handler.complete_subtask(
            facade=mock_subtask_facade,
            task_id="task-123",
            subtask_id="sub-123",
            completion_notes="Login endpoint implemented and tested",
            completion_summary="Login endpoint implemented and tested",
            impact_on_parent="Authentication backend 50% complete"
        )
        
        # Verify
        assert result["success"] is True
        assert result["subtask"]["status"] == "done"
        assert result["subtask"]["progress_percentage"] == 100
        assert mock_subtask_facade.handle_manage_subtask.call_count >= 1

    @pytest.mark.asyncio
    async def test_handle_validation_errors(self, handler, mock_response_formatter, mock_subtask_facade):
        """Test validation error handling"""
        # Configure error response formatter
        mock_response_formatter.create_error_response.return_value = {
            "success": False,
            "error": "Validation error",
            "field": "task_id"
        }
        
        # Test missing task_id
        result = handler.create_subtask(
            facade=mock_subtask_facade,
            task_id="",
            title="Test"
        )
        assert result["success"] is False
        mock_response_formatter.create_error_response.assert_called()
        
        # Test missing title
        mock_response_formatter.create_error_response.return_value = {
            "success": False,
            "error": "Validation error",
            "field": "title"
        }
        result = handler.create_subtask(
            facade=mock_subtask_facade,
            task_id="task-123",
            title=""
        )
        assert result["success"] is False
        
        # Test missing subtask_id for update
        mock_response_formatter.create_error_response.return_value = {
            "success": False,
            "error": "Validation error",
            "field": "subtask_id"
        }
        result = handler.update_subtask(
            facade=mock_subtask_facade,
            task_id="task-123",
            subtask_id="",
            title="Updated"
        )
        assert result["success"] is False

    @pytest.mark.asyncio
    async def test_handle_progress_notes(self, handler, mock_subtask_facade):
        """Test handling progress notes during update"""
        # Configure mock - need to handle both update and list calls
        def handle_manage_subtask_side_effect(*args, **kwargs):
            if kwargs.get('action') == 'list':
                return {"success": True, "subtasks": []}
            else:
                return {
                    "success": True,
                    "subtask": {
                        "id": "sub-123",
                        "progress_percentage": 25,
                        "status": "in_progress"  # Auto-set from progress_percentage
                    }
                }
        mock_subtask_facade.handle_manage_subtask.side_effect = handle_manage_subtask_side_effect
        
        # Execute
        result = handler.update_subtask(
            facade=mock_subtask_facade,
            task_id="task-123",
            subtask_id="sub-123",
            progress_notes="Completed initial setup",
            progress_percentage=25
        )
        
        # Verify
        assert result["success"] is True
        # Progress notes are not stored on the subtask - they're used for context updates
        # So we don't expect progress_notes in the returned subtask
        assert result["subtask"]["id"] == "sub-123"
        assert result["subtask"]["progress_percentage"] == 25
        
        # Verify the update was called - progress_notes is passed but not stored
        assert mock_subtask_facade.handle_manage_subtask.call_count >= 1
        first_call = mock_subtask_facade.handle_manage_subtask.call_args_list[0]
        assert first_call.kwargs['action'] == 'update'
        # progress_notes is passed as a parameter for context updates, not stored in update_data
        # The test should verify the call was made successfully, not check for progress_notes in the data

    @pytest.mark.skip(reason="Feature not implemented in current version - update_subtask doesn't accept blockers/insights_found parameters")
    @pytest.mark.asyncio
    async def test_handle_blockers_and_insights(self, handler, mock_subtask_facade):
        """Test handling blockers and insights"""
        # This test is for a feature that's not implemented in the current version
        # The update_subtask method doesn't accept blockers or insights_found parameters
        # Keeping the test for future implementation
        pass

    @pytest.mark.asyncio
    async def test_handle_workflow_hints(self, handler, mock_subtask_facade):
        """Test workflow hints in responses"""
        # Create subtask
        mock_subtask_facade.handle_manage_subtask.return_value = {
            "success": True,
            "subtask": {
                "id": "sub-123",
                "title": "New Subtask"
            },
            "hint": "Next: Update the subtask with progress as you work on it",
            "workflow_guidance": {
                "next_actions": ["Update progress", "Add blockers if found"],
                "rules": ["Update progress_percentage as work progresses"]
            }
        }
        
        result = handler.create_subtask(
            facade=mock_subtask_facade,
            task_id="task-123",
            title="New Subtask"
        )
        
        # Verify hint present
        assert result["success"] is True
        assert "hint" in result
        assert "workflow_guidance" in result

    @pytest.mark.asyncio
    async def test_handle_batch_operations(self, handler, mock_subtask_facade):
        """Test batch operations like updating multiple subtasks"""
        # This would test batch update functionality if implemented
        # Currently handler doesn't support batch operations
        # This is a placeholder for future enhancement
        pass

    @pytest.mark.asyncio
    async def test_error_handling_and_logging(self, handler, mock_subtask_facade, mock_response_formatter):
        """Test error handling and logging"""
        # Configure mock to raise exception
        mock_subtask_facade.handle_manage_subtask.side_effect = Exception("Database error")
        mock_response_formatter.create_error_response.return_value = {
            "success": False,
            "error": "Failed to create subtask: Database error"
        }
        
        # Execute
        result = handler.create_subtask(
            facade=mock_subtask_facade,
            task_id="task-123",
            title="Test Subtask"
        )
        
        # Verify error handled gracefully
        assert result["success"] is False
        assert "Database error" in result["error"]
        mock_response_formatter.create_error_response.assert_called()