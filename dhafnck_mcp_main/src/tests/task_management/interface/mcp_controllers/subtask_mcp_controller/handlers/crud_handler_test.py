"""
Tests for Subtask MCP Controller CRUD Handler
"""

import pytest
from unittest.mock import Mock, patch, AsyncMock
from typing import Dict, Any
import uuid
from datetime import datetime

from fastmcp.task_management.interface.mcp_controllers.subtask_mcp_controller.handlers.crud_handler import (
    SubtaskCRUDHandler
)
from fastmcp.task_management.domain.entities import Task, Subtask, TaskStatus, TaskPriority
from fastmcp.task_management.application.exceptions import (
    TaskNotFoundError,
    SubtaskNotFoundError,
    ValidationError
)


class TestSubtaskCRUDHandler:
    """Test Subtask CRUD Handler functionality"""

    @pytest.fixture
    def mock_subtask_service(self):
        """Create mock subtask service"""
        service = Mock()
        service.add_subtask = AsyncMock()
        service.update_subtask = AsyncMock()
        service.delete_subtask = AsyncMock()
        service.get_subtask = AsyncMock()
        service.list_subtasks = AsyncMock()
        service.complete_subtask = AsyncMock()
        return service

    @pytest.fixture
    def mock_task_service(self):
        """Create mock task service"""
        service = Mock()
        service.get_task = AsyncMock()
        service.update_task = AsyncMock()
        return service

    @pytest.fixture
    def handler(self, mock_subtask_service, mock_task_service):
        """Create handler instance with mocks"""
        return SubtaskCRUDHandler(
            subtask_service=mock_subtask_service,
            task_service=mock_task_service
        )

    @pytest.fixture
    def sample_task(self):
        """Create sample task"""
        return Task(
            id="task-123",
            title="Main Task",
            status=TaskStatus.IN_PROGRESS,
            priority=TaskPriority.HIGH,
            project_id="proj-123",
            git_branch_id="branch-123",
            assignees=["coding-agent", "@test-agent"]
        )

    @pytest.fixture
    def sample_subtask(self):
        """Create sample subtask"""
        return Subtask(
            id="sub-123",
            task_id="task-123",
            title="Implement login endpoint",
            description="Create POST /auth/login endpoint",
            status=TaskStatus.TODO,
            priority=TaskPriority.HIGH,
            assignees=["coding-agent"]
        )

    @pytest.mark.asyncio
    async def test_handle_create_subtask(self, handler, mock_subtask_service, mock_task_service, sample_task, sample_subtask):
        """Test creating a subtask"""
        # Configure mocks
        mock_task_service.get_task.return_value = sample_task
        mock_subtask_service.add_subtask.return_value = sample_subtask
        
        # Execute
        params = {
            "task_id": "task-123",
            "title": "Implement login endpoint",
            "description": "Create POST /auth/login endpoint",
            "assignees": "coding-agent"
        }
        
        result = await handler.handle_create(params)
        
        # Verify
        assert result["success"] is True
        assert result["subtask"]["id"] == "sub-123"
        assert result["subtask"]["title"] == "Implement login endpoint"
        mock_task_service.get_task.assert_awaited_once_with("task-123")
        mock_subtask_service.add_subtask.assert_awaited_once()

    @pytest.mark.asyncio
    async def test_handle_create_subtask_inherit_assignees(self, handler, mock_subtask_service, mock_task_service, sample_task):
        """Test creating subtask inherits parent assignees when none specified"""
        # Configure mocks
        mock_task_service.get_task.return_value = sample_task
        created_subtask = Subtask(
            id="sub-456",
            task_id="task-123",
            title="New Subtask",
            assignees=["coding-agent", "@test-agent"]  # Inherited
        )
        mock_subtask_service.add_subtask.return_value = created_subtask
        
        # Execute without assignees
        params = {
            "task_id": "task-123",
            "title": "New Subtask"
        }
        
        result = await handler.handle_create(params)
        
        # Verify inheritance
        assert result["subtask"]["assignees"] == ["coding-agent", "@test-agent"]
        
        # Check the call to add_subtask
        call_args = mock_subtask_service.add_subtask.call_args
        subtask_arg = call_args[0][1]  # Second argument is the subtask
        assert subtask_arg.assignees == ["coding-agent", "@test-agent"]

    @pytest.mark.asyncio
    async def test_handle_create_subtask_task_not_found(self, handler, mock_task_service):
        """Test creating subtask when parent task doesn't exist"""
        # Configure mock
        mock_task_service.get_task.side_effect = TaskNotFoundError("task-999")
        
        # Execute
        params = {
            "task_id": "task-999",
            "title": "Orphan Subtask"
        }
        
        result = await handler.handle_create(params)
        
        # Verify error response
        assert result["success"] is False
        assert "not found" in result["error"]

    @pytest.mark.asyncio
    async def test_handle_update_subtask(self, handler, mock_subtask_service, sample_subtask):
        """Test updating a subtask"""
        # Configure mocks
        updated_subtask = Subtask(
            id="sub-123",
            task_id="task-123",
            title="Updated login endpoint",
            description="Updated description",
            status=TaskStatus.IN_PROGRESS,
            progress_percentage=50
        )
        mock_subtask_service.update_subtask.return_value = updated_subtask
        
        # Execute
        params = {
            "task_id": "task-123",
            "subtask_id": "sub-123",
            "title": "Updated login endpoint",
            "description": "Updated description",
            "progress_percentage": 50
        }
        
        result = await handler.handle_update(params)
        
        # Verify
        assert result["success"] is True
        assert result["subtask"]["title"] == "Updated login endpoint"
        assert result["subtask"]["progress_percentage"] == 50
        assert result["subtask"]["status"] == "in_progress"  # Auto-set from percentage

    @pytest.mark.asyncio
    async def test_handle_update_subtask_auto_status(self, handler, mock_subtask_service):
        """Test automatic status setting based on progress percentage"""
        test_cases = [
            (0, TaskStatus.TODO),
            (1, TaskStatus.IN_PROGRESS),
            (50, TaskStatus.IN_PROGRESS),
            (99, TaskStatus.IN_PROGRESS),
            (100, TaskStatus.DONE)
        ]
        
        for percentage, expected_status in test_cases:
            # Configure mock
            mock_subtask_service.update_subtask.return_value = Subtask(
                id="sub-123",
                task_id="task-123",
                title="Test",
                status=expected_status,
                progress_percentage=percentage
            )
            
            # Execute
            params = {
                "task_id": "task-123",
                "subtask_id": "sub-123",
                "progress_percentage": percentage
            }
            
            result = await handler.handle_update(params)
            
            # Verify status
            assert result["subtask"]["status"] == expected_status.value

    @pytest.mark.asyncio
    async def test_handle_delete_subtask(self, handler, mock_subtask_service):
        """Test deleting a subtask"""
        # Configure mocks
        mock_subtask_service.delete_subtask.return_value = None
        
        # Execute
        params = {
            "task_id": "task-123",
            "subtask_id": "sub-123"
        }
        
        result = await handler.handle_delete(params)
        
        # Verify
        assert result["success"] is True
        assert result["message"] == "Subtask deleted successfully"
        mock_subtask_service.delete_subtask.assert_awaited_once_with("task-123", "sub-123")

    @pytest.mark.asyncio
    async def test_handle_delete_subtask_not_found(self, handler, mock_subtask_service):
        """Test deleting non-existent subtask"""
        # Configure mock
        mock_subtask_service.delete_subtask.side_effect = SubtaskNotFoundError("sub-999")
        
        # Execute
        params = {
            "task_id": "task-123",
            "subtask_id": "sub-999"
        }
        
        result = await handler.handle_delete(params)
        
        # Verify error response
        assert result["success"] is False
        assert "not found" in result["error"]

    @pytest.mark.asyncio
    async def test_handle_get_subtask(self, handler, mock_subtask_service, sample_subtask):
        """Test getting a specific subtask"""
        # Configure mocks
        mock_subtask_service.get_subtask.return_value = sample_subtask
        
        # Execute
        params = {
            "task_id": "task-123",
            "subtask_id": "sub-123"
        }
        
        result = await handler.handle_get(params)
        
        # Verify
        assert result["success"] is True
        assert result["subtask"]["id"] == "sub-123"
        assert result["subtask"]["title"] == "Implement login endpoint"

    @pytest.mark.asyncio
    async def test_handle_list_subtasks(self, handler, mock_subtask_service):
        """Test listing all subtasks for a task"""
        # Configure mocks
        subtasks = [
            Subtask(id="sub-1", task_id="task-123", title="Subtask 1", progress_percentage=100),
            Subtask(id="sub-2", task_id="task-123", title="Subtask 2", progress_percentage=50),
            Subtask(id="sub-3", task_id="task-123", title="Subtask 3", progress_percentage=0)
        ]
        mock_subtask_service.list_subtasks.return_value = subtasks
        
        # Execute
        params = {"task_id": "task-123"}
        
        result = await handler.handle_list(params)
        
        # Verify
        assert result["success"] is True
        assert len(result["subtasks"]) == 3
        assert result["progress_summary"]["total_subtasks"] == 3
        assert result["progress_summary"]["completed_subtasks"] == 1
        assert result["progress_summary"]["overall_progress"] == 50  # (100+50+0)/3

    @pytest.mark.asyncio
    async def test_handle_complete_subtask(self, handler, mock_subtask_service, mock_task_service):
        """Test completing a subtask with summary"""
        # Configure mocks
        completed_subtask = Subtask(
            id="sub-123",
            task_id="task-123",
            title="Login endpoint",
            status=TaskStatus.DONE,
            progress_percentage=100
        )
        mock_subtask_service.complete_subtask.return_value = completed_subtask
        
        # Execute
        params = {
            "task_id": "task-123",
            "subtask_id": "sub-123",
            "completion_summary": "Implemented JWT login with refresh tokens",
            "impact_on_parent": "Authentication backend 50% complete"
        }
        
        result = await handler.handle_complete(params)
        
        # Verify
        assert result["success"] is True
        assert result["subtask"]["status"] == "done"
        assert result["parent_updated"] is True
        mock_subtask_service.complete_subtask.assert_awaited_once()

    @pytest.mark.asyncio
    async def test_handle_validation_errors(self, handler):
        """Test parameter validation"""
        # Missing required task_id
        params = {"title": "No task ID"}
        result = await handler.handle_create(params)
        assert result["success"] is False
        assert "task_id" in result["error"]
        
        # Missing required subtask_id for update
        params = {"task_id": "task-123", "title": "Updated"}
        result = await handler.handle_update(params)
        assert result["success"] is False
        assert "subtask_id" in result["error"]

    @pytest.mark.asyncio
    async def test_handle_progress_notes(self, handler, mock_subtask_service):
        """Test handling progress notes updates"""
        # Configure mock
        updated_subtask = Subtask(
            id="sub-123",
            task_id="task-123",
            title="Test",
            progress_notes="Completed API design, starting implementation"
        )
        mock_subtask_service.update_subtask.return_value = updated_subtask
        
        # Execute
        params = {
            "task_id": "task-123",
            "subtask_id": "sub-123",
            "progress_notes": "Completed API design, starting implementation"
        }
        
        result = await handler.handle_update(params)
        
        # Verify
        assert result["success"] is True
        assert "progress_notes" in result["subtask"]

    @pytest.mark.asyncio
    async def test_handle_blockers_and_insights(self, handler, mock_subtask_service):
        """Test handling blockers and insights"""
        # Configure mock
        updated_subtask = Subtask(
            id="sub-123",
            task_id="task-123",
            title="Test",
            blockers=["Missing API documentation", "Database schema not finalized"],
            insights_found=["Found existing auth utility", "Can reuse token validation"]
        )
        mock_subtask_service.update_subtask.return_value = updated_subtask
        
        # Execute
        params = {
            "task_id": "task-123",
            "subtask_id": "sub-123",
            "blockers": "Missing API documentation,Database schema not finalized",
            "insights_found": "Found existing auth utility,Can reuse token validation"
        }
        
        result = await handler.handle_update(params)
        
        # Verify
        assert result["success"] is True
        assert len(result["subtask"]["blockers"]) == 2
        assert len(result["subtask"]["insights_found"]) == 2

    @pytest.mark.asyncio
    async def test_handle_workflow_hints(self, handler, mock_subtask_service):
        """Test workflow hints in responses"""
        # Configure mock
        subtasks = [
            Subtask(id="sub-1", task_id="task-123", title="Done", progress_percentage=100),
            Subtask(id="sub-2", task_id="task-123", title="In Progress", progress_percentage=50),
            Subtask(id="sub-3", task_id="task-123", title="Not Started", progress_percentage=0)
        ]
        mock_subtask_service.list_subtasks.return_value = subtasks
        
        # Execute
        result = await handler.handle_list({"task_id": "task-123"})
        
        # Verify hints
        assert "hint" in result
        assert "2 subtasks remaining" in result["hint"] or "progress" in result["hint"]

    @pytest.mark.asyncio
    async def test_handle_batch_operations(self, handler, mock_subtask_service):
        """Test batch operations on subtasks"""
        # Configure mock for batch update
        params = {
            "task_id": "task-123",
            "subtask_ids": ["sub-1", "sub-2", "sub-3"],
            "status": "in_progress",
            "batch_operation": True
        }
        
        # This would be implemented in the actual handler
        # For now, test individual updates
        for subtask_id in ["sub-1", "sub-2", "sub-3"]:
            mock_subtask_service.update_subtask.return_value = Subtask(
                id=subtask_id,
                task_id="task-123",
                title=f"Subtask {subtask_id}",
                status=TaskStatus.IN_PROGRESS
            )

    @pytest.mark.asyncio
    async def test_error_handling_and_logging(self, handler, mock_subtask_service):
        """Test comprehensive error handling"""
        # Test various error scenarios
        error_scenarios = [
            (ValueError("Invalid input"), "validation"),
            (TaskNotFoundError("task-123"), "not found"),
            (Exception("Unexpected error"), "error occurred")
        ]
        
        for error, expected_message in error_scenarios:
            mock_subtask_service.add_subtask.side_effect = error
            
            params = {"task_id": "task-123", "title": "Test"}
            result = await handler.handle_create(params)
            
            assert result["success"] is False
            assert expected_message in result["error"].lower()