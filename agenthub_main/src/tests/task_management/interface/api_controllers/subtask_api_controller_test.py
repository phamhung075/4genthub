"""Test suite for SubtaskApiController."""

import pytest
from unittest.mock import Mock, AsyncMock
from uuid import uuid4
from datetime import datetime

from fastmcp.task_management.interface.api_controllers.subtask_api_controller import SubtaskApiController
from fastmcp.task_management.application.facades.subtask_application_facade import SubtaskApplicationFacade
from fastmcp.task_management.application.dtos.subtask.subtask_response import SubtaskResponse
from fastmcp.types.entities import SubtaskEntity


class TestSubtaskApiController:
    """Test cases for SubtaskApiController."""
    
    @pytest.fixture
    def mock_facade(self):
        """Create mock SubtaskApplicationFacade."""
        return Mock(spec=SubtaskApplicationFacade)
    
    @pytest.fixture
    def controller(self, mock_facade):
        """Create SubtaskApiController instance."""
        return SubtaskApiController(facade=mock_facade)
    
    @pytest.fixture
    def sample_subtask(self):
        """Create sample subtask entity."""
        return SubtaskEntity(
            id=str(uuid4()),
            title="Test Subtask",
            description="Test Description",
            status="todo",
            priority="medium",
            assignees=["user1", "user2"],
            progress_notes="Initial setup",
            created_at="2024-01-01T00:00:00Z",
            updated_at="2024-01-01T00:00:00Z",
            task_id=str(uuid4()),
            parent_title="Parent Task Title"
        )
    
    @pytest.mark.asyncio
    async def test_list_subtasks_success(self, controller, mock_facade, sample_subtask):
        """Test successful listing of subtasks."""
        task_id = str(uuid4())
        user_id = str(uuid4())
        
        mock_facade.list_subtasks = AsyncMock(return_value=[sample_subtask])
        
        result = await controller.list_subtasks(
            task_id=task_id,
            user_id=user_id,
            offset=0,
            limit=10
        )
        
        assert result["success"] is True
        assert len(result["subtasks"]) == 1
        assert result["subtasks"][0]["id"] == sample_subtask.id
        assert result["total"] == 1
        
        mock_facade.list_subtasks.assert_called_once_with(
            task_id=task_id,
            user_id=user_id,
            offset=0,
            limit=10
        )
    
    @pytest.mark.asyncio
    async def test_list_subtasks_empty(self, controller, mock_facade):
        """Test listing subtasks when none exist."""
        task_id = str(uuid4())
        user_id = str(uuid4())
        
        mock_facade.list_subtasks = AsyncMock(return_value=[])
        
        result = await controller.list_subtasks(
            task_id=task_id,
            user_id=user_id
        )
        
        assert result["success"] is True
        assert result["subtasks"] == []
        assert result["total"] == 0
    
    @pytest.mark.asyncio
    async def test_list_subtasks_with_pagination(self, controller, mock_facade):
        """Test listing subtasks with pagination parameters."""
        task_id = str(uuid4())
        user_id = str(uuid4())
        
        # Create multiple subtasks
        subtasks = [
            SubtaskEntity(
                id=str(uuid4()),
                title=f"Subtask {i}",
                description=f"Description {i}",
                status="todo",
                priority="medium",
                assignees=[],
                progress_notes=None,
                created_at="2024-01-01T00:00:00Z",
                updated_at="2024-01-01T00:00:00Z",
                task_id=task_id,
                parent_title="Parent"
            )
            for i in range(5)
        ]
        
        mock_facade.list_subtasks = AsyncMock(return_value=subtasks[2:4])  # Return page
        
        result = await controller.list_subtasks(
            task_id=task_id,
            user_id=user_id,
            offset=2,
            limit=2
        )
        
        assert result["success"] is True
        assert len(result["subtasks"]) == 2
        assert result["subtasks"][0]["title"] == "Subtask 2"
        assert result["subtasks"][1]["title"] == "Subtask 3"
        assert result["total"] == 2
    
    @pytest.mark.asyncio
    async def test_get_subtask_success(self, controller, mock_facade, sample_subtask):
        """Test successful retrieval of a single subtask."""
        task_id = sample_subtask.task_id
        subtask_id = sample_subtask.id
        user_id = str(uuid4())
        
        mock_facade.get_subtask = AsyncMock(
            return_value=SubtaskResponse(subtask=sample_subtask, success=True)
        )
        
        result = await controller.get_subtask(
            task_id=task_id,
            subtask_id=subtask_id,
            user_id=user_id
        )
        
        assert isinstance(result, SubtaskResponse)
        assert result.success is True
        assert result.subtask.id == subtask_id
        assert result.subtask.title == "Test Subtask"
        
        mock_facade.get_subtask.assert_called_once_with(
            task_id=task_id,
            subtask_id=subtask_id,
            user_id=user_id
        )
    
    @pytest.mark.asyncio
    async def test_get_subtask_not_found(self, controller, mock_facade):
        """Test getting non-existent subtask."""
        task_id = str(uuid4())
        subtask_id = str(uuid4())
        user_id = str(uuid4())
        
        mock_facade.get_subtask = AsyncMock(
            return_value=SubtaskResponse(subtask=None, success=False)
        )
        
        result = await controller.get_subtask(
            task_id=task_id,
            subtask_id=subtask_id,
            user_id=user_id
        )
        
        assert isinstance(result, SubtaskResponse)
        assert result.success is False
        assert result.subtask is None
    
    @pytest.mark.asyncio
    async def test_list_subtasks_error_handling(self, controller, mock_facade):
        """Test error handling in list_subtasks."""
        task_id = str(uuid4())
        user_id = str(uuid4())
        
        mock_facade.list_subtasks = AsyncMock(side_effect=Exception("Database error"))
        
        with pytest.raises(Exception, match="Database error"):
            await controller.list_subtasks(
                task_id=task_id,
                user_id=user_id
            )
    
    @pytest.mark.asyncio
    async def test_get_subtask_error_handling(self, controller, mock_facade):
        """Test error handling in get_subtask."""
        task_id = str(uuid4())
        subtask_id = str(uuid4())
        user_id = str(uuid4())
        
        mock_facade.get_subtask = AsyncMock(side_effect=Exception("Not found"))
        
        with pytest.raises(Exception, match="Not found"):
            await controller.get_subtask(
                task_id=task_id,
                subtask_id=subtask_id,
                user_id=user_id
            )
    
    @pytest.mark.asyncio
    async def test_list_subtasks_default_pagination(self, controller, mock_facade):
        """Test list_subtasks with default pagination values."""
        task_id = str(uuid4())
        user_id = str(uuid4())
        
        mock_facade.list_subtasks = AsyncMock(return_value=[])
        
        # Call without offset and limit
        result = await controller.list_subtasks(
            task_id=task_id,
            user_id=user_id
        )
        
        # Should use default values
        mock_facade.list_subtasks.assert_called_once_with(
            task_id=task_id,
            user_id=user_id,
            offset=0,
            limit=50
        )
    
    @pytest.mark.asyncio
    async def test_subtask_data_format(self, controller, mock_facade):
        """Test that subtask data is properly formatted in responses."""
        subtask = SubtaskEntity(
            id=str(uuid4()),
            title="Formatted Subtask",
            description="Test formatting",
            status="in_progress",
            priority="high",
            assignees=["user1", "user2", "user3"],
            progress_notes="50% complete",
            created_at="2024-01-01T12:00:00Z",
            updated_at="2024-01-02T12:00:00Z",
            task_id=str(uuid4()),
            parent_title="Main Task"
        )
        
        mock_facade.list_subtasks = AsyncMock(return_value=[subtask])
        
        result = await controller.list_subtasks(
            task_id=subtask.task_id,
            user_id=str(uuid4())
        )
        
        subtask_data = result["subtasks"][0]
        
        # Verify all fields are present and properly formatted
        assert subtask_data["id"] == subtask.id
        assert subtask_data["title"] == "Formatted Subtask"
        assert subtask_data["description"] == "Test formatting"
        assert subtask_data["status"] == "in_progress"
        assert subtask_data["priority"] == "high"
        assert subtask_data["assignees"] == ["user1", "user2", "user3"]
        assert subtask_data["progress_notes"] == "50% complete"
        assert subtask_data["created_at"] == "2024-01-01T12:00:00Z"
        assert subtask_data["updated_at"] == "2024-01-02T12:00:00Z"
        assert subtask_data["task_id"] == subtask.task_id
        assert subtask_data["parent_title"] == "Main Task"