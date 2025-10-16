"""Test suite for subtask API routes."""

import pytest
from unittest.mock import Mock, patch, AsyncMock
from fastapi import HTTPException
from fastapi.testclient import TestClient
from uuid import uuid4

from fastmcp.server.routes.subtask_routes import router
from fastmcp.task_management.application.dtos.subtask.subtask_response import SubtaskResponse
from fastmcp.types.entities import SubtaskEntity
from fastmcp.auth.models.user import UserInfo


@pytest.fixture
def mock_subtask():
    """Create a mock subtask entity."""
    return SubtaskEntity(
        id=str(uuid4()),
        title="Test Subtask",
        description="Test Description",
        status="todo",
        priority="medium",
        assignees=["user1"],
        progress_notes="Initial progress",
        created_at="2024-01-01T00:00:00Z",
        updated_at="2024-01-01T00:00:00Z",
        task_id=str(uuid4()),
        parent_title="Parent Task"
    )


@pytest.fixture
def mock_user():
    """Create a mock user info."""
    return UserInfo(
        id=str(uuid4()),
        email="test@example.com",
        is_authenticated=True
    )


@pytest.fixture
def client():
    """Create test client."""
    from fastapi import FastAPI
    app = FastAPI()
    app.include_router(router)
    return TestClient(app)


class TestSubtaskRoutes:
    """Test cases for subtask routes."""
    
    @pytest.mark.asyncio
    async def test_list_subtasks_success(self, client, mock_subtask, mock_user):
        """Test successful listing of subtasks."""
        task_id = str(uuid4())
        
        with patch('fastmcp.server.routes.subtask_routes.get_current_user') as mock_get_user:
            mock_get_user.return_value = mock_user
            
            with patch('fastmcp.server.routes.subtask_routes.get_subtask_api_controller') as mock_get_controller:
                mock_controller = Mock()
                mock_controller.list_subtasks = AsyncMock(return_value={
                    "subtasks": [mock_subtask.__dict__],
                    "total": 1,
                    "success": True
                })
                mock_get_controller.return_value = mock_controller
                
                response = client.get(f"/api/tasks/{task_id}/subtasks")
                
                assert response.status_code == 200
                data = response.json()
                assert data["success"] is True
                assert len(data["subtasks"]) == 1
                assert data["total"] == 1
    
    @pytest.mark.asyncio
    async def test_list_subtasks_with_pagination(self, client, mock_user):
        """Test listing subtasks with pagination."""
        task_id = str(uuid4())
        
        with patch('fastmcp.server.routes.subtask_routes.get_current_user') as mock_get_user:
            mock_get_user.return_value = mock_user
            
            with patch('fastmcp.server.routes.subtask_routes.get_subtask_api_controller') as mock_get_controller:
                mock_controller = Mock()
                mock_controller.list_subtasks = AsyncMock()
                mock_get_controller.return_value = mock_controller
                
                response = client.get(f"/api/tasks/{task_id}/subtasks?offset=10&limit=20")
                
                mock_controller.list_subtasks.assert_called_once_with(
                    task_id=task_id,
                    user_id=mock_user.id,
                    offset=10,
                    limit=20
                )
    
    @pytest.mark.asyncio
    async def test_get_subtask_success(self, client, mock_subtask, mock_user):
        """Test successful retrieval of a single subtask."""
        task_id = str(uuid4())
        subtask_id = mock_subtask.id
        
        with patch('fastmcp.server.routes.subtask_routes.get_current_user') as mock_get_user:
            mock_get_user.return_value = mock_user
            
            with patch('fastmcp.server.routes.subtask_routes.get_subtask_api_controller') as mock_get_controller:
                mock_controller = Mock()
                mock_controller.get_subtask = AsyncMock(return_value=SubtaskResponse(
                    subtask=mock_subtask,
                    success=True
                ))
                mock_get_controller.return_value = mock_controller
                
                response = client.get(f"/api/tasks/{task_id}/subtasks/{subtask_id}")
                
                assert response.status_code == 200
                data = response.json()
                assert data["success"] is True
                assert data["subtask"]["id"] == subtask_id
    
    @pytest.mark.asyncio
    async def test_get_subtask_not_found(self, client, mock_user):
        """Test getting non-existent subtask."""
        task_id = str(uuid4())
        subtask_id = str(uuid4())
        
        with patch('fastmcp.server.routes.subtask_routes.get_current_user') as mock_get_user:
            mock_get_user.return_value = mock_user
            
            with patch('fastmcp.server.routes.subtask_routes.get_subtask_api_controller') as mock_get_controller:
                mock_controller = Mock()
                mock_controller.get_subtask = AsyncMock(side_effect=HTTPException(
                    status_code=404,
                    detail="Subtask not found"
                ))
                mock_get_controller.return_value = mock_controller
                
                response = client.get(f"/api/tasks/{task_id}/subtasks/{subtask_id}")
                
                assert response.status_code == 404
    
    @pytest.mark.asyncio
    async def test_list_subtasks_unauthorized(self, client):
        """Test listing subtasks without authentication."""
        task_id = str(uuid4())
        
        with patch('fastmcp.server.routes.subtask_routes.get_current_user') as mock_get_user:
            mock_get_user.side_effect = HTTPException(status_code=401, detail="Unauthorized")
            
            response = client.get(f"/api/tasks/{task_id}/subtasks")
            
            assert response.status_code == 401
    
    @pytest.mark.asyncio
    async def test_list_subtasks_controller_error(self, client, mock_user):
        """Test handling of controller errors."""
        task_id = str(uuid4())
        
        with patch('fastmcp.server.routes.subtask_routes.get_current_user') as mock_get_user:
            mock_get_user.return_value = mock_user
            
            with patch('fastmcp.server.routes.subtask_routes.get_subtask_api_controller') as mock_get_controller:
                mock_controller = Mock()
                mock_controller.list_subtasks = AsyncMock(side_effect=Exception("Database error"))
                mock_get_controller.return_value = mock_controller
                
                response = client.get(f"/api/tasks/{task_id}/subtasks")
                
                assert response.status_code == 500