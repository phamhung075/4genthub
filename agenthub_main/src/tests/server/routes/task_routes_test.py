"""Test suite for task API routes."""

import pytest
from unittest.mock import Mock, patch, AsyncMock
from fastapi import HTTPException
from fastapi.testclient import TestClient
from uuid import uuid4

from fastmcp.server.routes.task_routes import router
from fastmcp.task_management.application.dtos.task.task_response import TaskResponse
from fastmcp.types.entities import TaskEntity
from fastmcp.auth.models.user import UserInfo


@pytest.fixture
def mock_task():
    """Create a mock task entity."""
    return TaskEntity(
        id=str(uuid4()),
        title="Test Task",
        description="Test Description",
        status="todo",
        priority="medium",
        details=None,
        assignees=["user1", "user2"],
        labels=["frontend", "bug"],
        estimated_effort="2 hours",
        due_date="2024-12-31T00:00:00Z",
        created_at="2024-01-01T00:00:00Z",
        updated_at="2024-01-01T00:00:00Z",
        git_branch_id=str(uuid4()),
        project_id=str(uuid4()),
        parent_task_id=None,
        dependencies=[],
        blocking_tasks=[],
        subtask_ids=[],
        subtask_count=0,
        context_id=None,
        completion_summary=None
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


class TestTaskRoutes:
    """Test cases for task routes."""
    
    @pytest.mark.asyncio
    async def test_list_tasks_success(self, client, mock_task, mock_user):
        """Test successful listing of tasks."""
        with patch('fastmcp.server.routes.task_routes.get_current_user') as mock_get_user:
            mock_get_user.return_value = mock_user
            
            with patch('fastmcp.server.routes.task_routes.get_task_api_controller') as mock_get_controller:
                mock_controller = Mock()
                mock_controller.list_tasks = AsyncMock(return_value={
                    "tasks": [mock_task.__dict__],
                    "total": 1,
                    "success": True
                })
                mock_get_controller.return_value = mock_controller
                
                response = client.get("/api/tasks")
                
                assert response.status_code == 200
                data = response.json()
                assert data["success"] is True
                assert len(data["tasks"]) == 1
                assert data["total"] == 1
    
    @pytest.mark.asyncio
    async def test_list_tasks_with_filters(self, client, mock_user):
        """Test listing tasks with various filters."""
        git_branch_id = str(uuid4())
        
        with patch('fastmcp.server.routes.task_routes.get_current_user') as mock_get_user:
            mock_get_user.return_value = mock_user
            
            with patch('fastmcp.server.routes.task_routes.get_task_api_controller') as mock_get_controller:
                mock_controller = Mock()
                mock_controller.list_tasks = AsyncMock()
                mock_get_controller.return_value = mock_controller
                
                response = client.get(
                    f"/api/tasks?git_branch_id={git_branch_id}&status=todo&priority=high&offset=10&limit=20"
                )
                
                mock_controller.list_tasks.assert_called_once_with(
                    user_id=mock_user.id,
                    git_branch_id=git_branch_id,
                    status="todo",
                    priority="high",
                    assignee=None,
                    label=None,
                    offset=10,
                    limit=20
                )
    
    @pytest.mark.asyncio
    async def test_get_task_success(self, client, mock_task, mock_user):
        """Test successful retrieval of a single task."""
        task_id = mock_task.id
        
        with patch('fastmcp.server.routes.task_routes.get_current_user') as mock_get_user:
            mock_get_user.return_value = mock_user
            
            with patch('fastmcp.server.routes.task_routes.get_task_api_controller') as mock_get_controller:
                mock_controller = Mock()
                mock_controller.get_task = AsyncMock(return_value=TaskResponse(
                    task=mock_task,
                    success=True
                ))
                mock_get_controller.return_value = mock_controller
                
                response = client.get(f"/api/tasks/{task_id}")
                
                assert response.status_code == 200
                data = response.json()
                assert data["success"] is True
                assert data["task"]["id"] == task_id
    
    @pytest.mark.asyncio
    async def test_get_task_not_found(self, client, mock_user):
        """Test getting non-existent task."""
        task_id = str(uuid4())
        
        with patch('fastmcp.server.routes.task_routes.get_current_user') as mock_get_user:
            mock_get_user.return_value = mock_user
            
            with patch('fastmcp.server.routes.task_routes.get_task_api_controller') as mock_get_controller:
                mock_controller = Mock()
                mock_controller.get_task = AsyncMock(side_effect=HTTPException(
                    status_code=404,
                    detail="Task not found"
                ))
                mock_get_controller.return_value = mock_controller
                
                response = client.get(f"/api/tasks/{task_id}")
                
                assert response.status_code == 404
    
    @pytest.mark.asyncio
    async def test_search_tasks_success(self, client, mock_task, mock_user):
        """Test successful task search."""
        with patch('fastmcp.server.routes.task_routes.get_current_user') as mock_get_user:
            mock_get_user.return_value = mock_user
            
            with patch('fastmcp.server.routes.task_routes.get_task_api_controller') as mock_get_controller:
                mock_controller = Mock()
                mock_controller.search_tasks = AsyncMock(return_value={
                    "tasks": [mock_task.__dict__],
                    "total": 1,
                    "success": True
                })
                mock_get_controller.return_value = mock_controller
                
                response = client.get("/api/tasks/search?q=test")
                
                assert response.status_code == 200
                data = response.json()
                assert data["success"] is True
                assert len(data["tasks"]) == 1
    
    @pytest.mark.asyncio
    async def test_search_tasks_empty_query(self, client, mock_user):
        """Test search with empty query."""
        with patch('fastmcp.server.routes.task_routes.get_current_user') as mock_get_user:
            mock_get_user.return_value = mock_user
            
            response = client.get("/api/tasks/search?q=")
            
            assert response.status_code == 400
            assert "Query parameter is required" in response.json()["detail"]
    
    @pytest.mark.asyncio
    async def test_list_tasks_unauthorized(self, client):
        """Test listing tasks without authentication."""
        with patch('fastmcp.server.routes.task_routes.get_current_user') as mock_get_user:
            mock_get_user.side_effect = HTTPException(status_code=401, detail="Unauthorized")
            
            response = client.get("/api/tasks")
            
            assert response.status_code == 401
    
    @pytest.mark.asyncio
    async def test_list_tasks_controller_error(self, client, mock_user):
        """Test handling of controller errors."""
        with patch('fastmcp.server.routes.task_routes.get_current_user') as mock_get_user:
            mock_get_user.return_value = mock_user
            
            with patch('fastmcp.server.routes.task_routes.get_task_api_controller') as mock_get_controller:
                mock_controller = Mock()
                mock_controller.list_tasks = AsyncMock(side_effect=Exception("Database error"))
                mock_get_controller.return_value = mock_controller
                
                response = client.get("/api/tasks")
                
                assert response.status_code == 500
    
    @pytest.mark.asyncio
    async def test_search_tasks_with_git_branch_filter(self, client, mock_user):
        """Test search with git branch filter."""
        git_branch_id = str(uuid4())
        
        with patch('fastmcp.server.routes.task_routes.get_current_user') as mock_get_user:
            mock_get_user.return_value = mock_user
            
            with patch('fastmcp.server.routes.task_routes.get_task_api_controller') as mock_get_controller:
                mock_controller = Mock()
                mock_controller.search_tasks = AsyncMock()
                mock_get_controller.return_value = mock_controller
                
                response = client.get(f"/api/tasks/search?q=test&git_branch_id={git_branch_id}&limit=50")
                
                mock_controller.search_tasks.assert_called_once_with(
                    user_id=mock_user.id,
                    query="test",
                    git_branch_id=git_branch_id,
                    limit=50
                )