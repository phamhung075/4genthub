"""Test suite for TaskApiController SearchHandler."""

import pytest
from unittest.mock import Mock, AsyncMock
from uuid import uuid4

from fastmcp.task_management.interface.api_controllers.task_api_controller.handlers.search_handler import SearchHandler
from fastmcp.task_management.application.facades.task_application_facade import TaskApplicationFacade
from fastmcp.types.entities import TaskEntity


class TestSearchHandler:
    """Test cases for SearchHandler."""
    
    @pytest.fixture
    def mock_facade(self):
        """Create mock TaskApplicationFacade."""
        return Mock(spec=TaskApplicationFacade)
    
    @pytest.fixture
    def handler(self, mock_facade):
        """Create SearchHandler instance."""
        return SearchHandler(facade=mock_facade)
    
    @pytest.fixture
    def sample_task(self):
        """Create sample task entity."""
        return TaskEntity(
            id=str(uuid4()),
            title="Test Task",
            description="Test Description with searchable content",
            status="todo",
            priority="medium",
            details="Additional searchable details",
            assignees=["user1", "user2"],
            labels=["frontend", "search"],
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
    
    @pytest.mark.asyncio
    async def test_search_tasks_success(self, handler, mock_facade, sample_task):
        """Test successful task search."""
        user_id = str(uuid4())
        query = "searchable"
        
        mock_facade.search_tasks = AsyncMock(return_value=[sample_task])
        
        result = await handler.search_tasks(
            user_id=user_id,
            query=query,
            git_branch_id=None,
            limit=10
        )
        
        assert result["success"] is True
        assert len(result["tasks"]) == 1
        assert result["tasks"][0]["id"] == sample_task.id
        assert result["tasks"][0]["title"] == "Test Task"
        assert result["total"] == 1
        
        mock_facade.search_tasks.assert_called_once_with(
            user_id=user_id,
            query=query,
            git_branch_id=None,
            limit=10
        )
    
    @pytest.mark.asyncio
    async def test_search_tasks_empty_results(self, handler, mock_facade):
        """Test search with no matching results."""
        user_id = str(uuid4())
        query = "nonexistent"
        
        mock_facade.search_tasks = AsyncMock(return_value=[])
        
        result = await handler.search_tasks(
            user_id=user_id,
            query=query
        )
        
        assert result["success"] is True
        assert result["tasks"] == []
        assert result["total"] == 0
    
    @pytest.mark.asyncio
    async def test_search_with_git_branch_filter(self, handler, mock_facade):
        """Test search with git branch filter."""
        user_id = str(uuid4())
        git_branch_id = str(uuid4())
        query = "feature"
        
        # Create tasks in specific branch
        tasks = [
            TaskEntity(
                id=str(uuid4()),
                title=f"Feature Task {i}",
                description="Feature implementation",
                status="todo",
                priority="medium",
                details=None,
                assignees=[],
                labels=["feature"],
                estimated_effort=None,
                due_date=None,
                created_at="2024-01-01T00:00:00Z",
                updated_at="2024-01-01T00:00:00Z",
                git_branch_id=git_branch_id,
                project_id=str(uuid4()),
                parent_task_id=None,
                dependencies=[],
                blocking_tasks=[],
                subtask_ids=[],
                subtask_count=0,
                context_id=None,
                completion_summary=None
            )
            for i in range(3)
        ]
        
        mock_facade.search_tasks = AsyncMock(return_value=tasks)
        
        result = await handler.search_tasks(
            user_id=user_id,
            query=query,
            git_branch_id=git_branch_id,
            limit=50
        )
        
        assert result["success"] is True
        assert len(result["tasks"]) == 3
        assert all(task["git_branch_id"] == git_branch_id for task in result["tasks"])
        
        mock_facade.search_tasks.assert_called_once_with(
            user_id=user_id,
            query=query,
            git_branch_id=git_branch_id,
            limit=50
        )
    
    @pytest.mark.asyncio
    async def test_search_with_custom_limit(self, handler, mock_facade):
        """Test search with custom result limit."""
        user_id = str(uuid4())
        query = "test"
        limit = 100
        
        # Create many tasks
        tasks = [
            TaskEntity(
                id=str(uuid4()),
                title=f"Test Task {i}",
                description="Test",
                status="todo",
                priority="medium",
                details=None,
                assignees=[],
                labels=[],
                estimated_effort=None,
                due_date=None,
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
            for i in range(25)
        ]
        
        mock_facade.search_tasks = AsyncMock(return_value=tasks)
        
        result = await handler.search_tasks(
            user_id=user_id,
            query=query,
            limit=limit
        )
        
        assert result["success"] is True
        assert len(result["tasks"]) == 25
        assert result["total"] == 25
        
        mock_facade.search_tasks.assert_called_once_with(
            user_id=user_id,
            query=query,
            git_branch_id=None,
            limit=100
        )
    
    @pytest.mark.asyncio
    async def test_search_case_insensitive(self, handler, mock_facade):
        """Test that search is case insensitive."""
        user_id = str(uuid4())
        
        task = TaskEntity(
            id=str(uuid4()),
            title="UPPERCASE TITLE",
            description="MixedCase Description",
            status="todo",
            priority="medium",
            details=None,
            assignees=[],
            labels=[],
            estimated_effort=None,
            due_date=None,
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
        
        # Test various case queries
        queries = ["uppercase", "UPPERCASE", "UpPeRcAsE"]
        
        for query in queries:
            mock_facade.search_tasks = AsyncMock(return_value=[task])
            
            result = await handler.search_tasks(
                user_id=user_id,
                query=query
            )
            
            assert result["success"] is True
            assert len(result["tasks"]) == 1
    
    @pytest.mark.asyncio
    async def test_search_partial_match(self, handler, mock_facade):
        """Test search with partial string matching."""
        user_id = str(uuid4())
        
        tasks = [
            TaskEntity(
                id=str(uuid4()),
                title="Authentication System",
                description="Implement user authentication",
                status="todo",
                priority="high",
                details=None,
                assignees=[],
                labels=["auth"],
                estimated_effort=None,
                due_date=None,
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
        ]
        
        # Search for partial match
        mock_facade.search_tasks = AsyncMock(return_value=tasks)
        
        result = await handler.search_tasks(
            user_id=user_id,
            query="auth"  # Should match "Authentication" and "authentication"
        )
        
        assert result["success"] is True
        assert len(result["tasks"]) == 1
        assert "Authentication" in result["tasks"][0]["title"]
    
    @pytest.mark.asyncio
    async def test_search_error_handling(self, handler, mock_facade):
        """Test error handling during search."""
        user_id = str(uuid4())
        query = "test"
        
        mock_facade.search_tasks = AsyncMock(side_effect=Exception("Search failed"))
        
        with pytest.raises(Exception, match="Search failed"):
            await handler.search_tasks(
                user_id=user_id,
                query=query
            )
    
    @pytest.mark.asyncio
    async def test_search_special_characters(self, handler, mock_facade):
        """Test search with special characters."""
        user_id = str(uuid4())
        
        task = TaskEntity(
            id=str(uuid4()),
            title="Task with @special #characters!",
            description="Contains $pecial ch@racters",
            status="todo",
            priority="medium",
            details=None,
            assignees=[],
            labels=[],
            estimated_effort=None,
            due_date=None,
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
        
        mock_facade.search_tasks = AsyncMock(return_value=[task])
        
        # Search with special characters
        result = await handler.search_tasks(
            user_id=user_id,
            query="@special"
        )
        
        assert result["success"] is True
        assert len(result["tasks"]) == 1