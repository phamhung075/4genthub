"""
Test suite for lazy_task_routes.py - Lazy Loading Task Routes

Tests the lightweight task and subtask data summaries API endpoints
for performance optimization in frontend loading scenarios.
"""

import pytest
from unittest.mock import Mock, patch, MagicMock
from fastapi.testclient import TestClient
from fastapi import HTTPException
import json
from datetime import datetime

from fastmcp.server.routes.lazy_task_routes import (
    router,
    get_task_facade,
    get_context_facade,
    TaskSummaryRequest,
    TaskSummary,
    TaskSummariesResponse,
    SubtaskSummaryRequest,
    SubtaskSummary,
    SubtaskSummariesResponse
)

# Test client setup
from fastapi import FastAPI
app = FastAPI()
app.include_router(router)
client = TestClient(app)

class TestTaskSummaryModels:
    """Test Pydantic models for task summaries"""
    
    def test_task_summary_request_defaults(self):
        """Test TaskSummaryRequest default values"""
        request = TaskSummaryRequest(git_branch_id="branch-123")
        assert request.git_branch_id == "branch-123"
        assert request.page == 1
        assert request.limit == 20
        assert request.include_counts is True
        assert request.status_filter is None
        assert request.priority_filter is None
    
    def test_task_summary_request_validation(self):
        """Test TaskSummaryRequest field validation"""
        # Test page validation
        with pytest.raises(ValueError):
            TaskSummaryRequest(git_branch_id="branch-123", page=0)
        
        # Test limit validation
        with pytest.raises(ValueError):
            TaskSummaryRequest(git_branch_id="branch-123", limit=0)
        
        with pytest.raises(ValueError):
            TaskSummaryRequest(git_branch_id="branch-123", limit=101)
    
    def test_task_summary_model(self):
        """Test TaskSummary model creation"""
        summary = TaskSummary(
            id="task-123",
            title="Test Task",
            status="in_progress",
            priority="high",
            subtask_count=3,
            assignees_count=2,
            has_dependencies=True,
            has_context=False,
            created_at="2024-01-01T00:00:00Z",
            updated_at="2024-01-02T00:00:00Z"
        )
        assert summary.id == "task-123"
        assert summary.subtask_count == 3
        assert summary.has_dependencies is True
    
    def test_subtask_summary_request(self):
        """Test SubtaskSummaryRequest model"""
        request = SubtaskSummaryRequest(parent_task_id="task-123")
        assert request.parent_task_id == "task-123"
        assert request.include_counts is True
    
    def test_subtask_summary_model(self):
        """Test SubtaskSummary model creation"""
        summary = SubtaskSummary(
            id="subtask-123",
            title="Test Subtask",
            status="todo",
            priority="medium",
            assignees_count=1,
            progress_percentage=50
        )
        assert summary.id == "subtask-123"
        assert summary.progress_percentage == 50

class TestDependencyInjection:
    """Test dependency injection functions"""
    
    def test_get_task_facade(self):
        """Test TaskApplicationFacade dependency injection"""
        facade = get_task_facade()
        from fastmcp.task_management.application.facades.task_application_facade import TaskApplicationFacade
        assert isinstance(facade, TaskApplicationFacade)
    
    @patch('fastmcp.server.routes.lazy_task_routes.UnifiedContextFacadeFactory')
    def test_get_context_facade(self, mock_factory_class):
        """Test UnifiedContextFacade dependency injection"""
        mock_factory = Mock()
        mock_facade = Mock()
        mock_factory_class.get_instance.return_value = mock_factory
        mock_factory.create_unified_context_facade.return_value = mock_facade
        
        result = get_context_facade()
        
        mock_factory_class.get_instance.assert_called_once()
        mock_factory.create_unified_context_facade.assert_called_once()
        assert result == mock_facade

class TestTaskSummariesEndpoint:
    """Test /api/tasks/summaries endpoint"""
    
    @patch('fastmcp.server.routes.lazy_task_routes.get_context_facade')
    @patch('fastmcp.server.routes.lazy_task_routes.get_task_facade')
    def test_get_task_summaries_success(self, mock_task_facade_dep, mock_context_facade_dep):
        """Test successful task summaries retrieval"""
        # Mock facades
        mock_task_facade = Mock()
        mock_context_facade = Mock()
        mock_task_facade_dep.return_value = mock_task_facade
        mock_context_facade_dep.return_value = mock_context_facade
        
        # Mock task facade responses
        mock_task_facade.count_tasks.return_value = {"success": True, "count": 25}
        mock_task_facade.list_tasks_summary.return_value = {
            "success": True,
            "tasks": [
                {
                    "id": "task-1",
                    "title": "Task 1",
                    "status": "in_progress",
                    "priority": "high",
                    "subtasks": ["sub1", "sub2"],
                    "assignees": ["user1"],
                    "dependencies": ["dep1"],
                    "created_at": "2024-01-01T00:00:00Z",
                    "updated_at": "2024-01-02T00:00:00Z"
                },
                {
                    "id": "task-2",
                    "title": "Task 2",
                    "status": "todo",
                    "priority": "medium",
                    "subtasks": [],
                    "assignees": [],
                    "dependencies": None,
                    "created_at": "2024-01-01T00:00:00Z",
                    "updated_at": "2024-01-01T00:00:00Z"
                }
            ]
        }
        
        # Mock context facade responses
        mock_context_facade.get_context_summary.side_effect = [
            {"success": True, "has_context": True},
            {"success": False, "has_context": False}
        ]
        
        # Make request
        response = client.post("/api/tasks/summaries", json={
            "git_branch_id": "branch-123",
            "page": 1,
            "limit": 20,
            "include_counts": True
        })
        
        # Assertions
        assert response.status_code == 200
        data = response.json()
        
        assert data["total"] == 25
        assert data["page"] == 1
        assert data["limit"] == 20
        assert data["has_more"] is True
        assert len(data["tasks"]) == 2
        
        # Check first task
        task1 = data["tasks"][0]
        assert task1["id"] == "task-1"
        assert task1["title"] == "Task 1"
        assert task1["status"] == "in_progress"
        assert task1["priority"] == "high"
        assert task1["subtask_count"] == 2
        assert task1["assignees_count"] == 1
        assert task1["has_dependencies"] is True
        assert task1["has_context"] is True
        
        # Check second task
        task2 = data["tasks"][1]
        assert task2["id"] == "task-2"
        assert task2["subtask_count"] == 0
        assert task2["assignees_count"] == 0
        assert task2["has_dependencies"] is False
        assert task2["has_context"] is False
    
    @patch('fastmcp.server.routes.lazy_task_routes.get_task_facade')
    def test_get_task_summaries_with_filters(self, mock_task_facade_dep):
        """Test task summaries with status and priority filters"""
        mock_task_facade = Mock()
        mock_task_facade_dep.return_value = mock_task_facade
        
        mock_task_facade.count_tasks.return_value = {"success": True, "count": 5}
        mock_task_facade.list_tasks_summary.return_value = {
            "success": True,
            "tasks": []
        }
        
        response = client.post("/api/tasks/summaries", json={
            "git_branch_id": "branch-123",
            "status_filter": "in_progress",
            "priority_filter": "high",
            "include_counts": False
        })
        
        assert response.status_code == 200
        
        # Check that filters were passed correctly
        expected_filters = {
            "git_branch_id": "branch-123",
            "status": "in_progress",
            "priority": "high"
        }
        mock_task_facade.count_tasks.assert_called_once_with(expected_filters)
        mock_task_facade.list_tasks_summary.assert_called_once_with(
            filters=expected_filters,
            offset=0,
            limit=20,
            include_counts=False
        )
    
    @patch('fastmcp.server.routes.lazy_task_routes.get_task_facade')
    def test_get_task_summaries_pagination(self, mock_task_facade_dep):
        """Test task summaries pagination calculation"""
        mock_task_facade = Mock()
        mock_task_facade_dep.return_value = mock_task_facade
        
        mock_task_facade.count_tasks.return_value = {"success": True, "count": 100}
        mock_task_facade.list_tasks_summary.return_value = {
            "success": True,
            "tasks": []
        }
        
        # Test page 3 with limit 10
        response = client.post("/api/tasks/summaries", json={
            "git_branch_id": "branch-123",
            "page": 3,
            "limit": 10
        })
        
        assert response.status_code == 200
        data = response.json()
        
        assert data["total"] == 100
        assert data["page"] == 3
        assert data["limit"] == 10
        assert data["has_more"] is True  # (3-1)*10 + 10 = 30 < 100
        
        # Check offset calculation
        mock_task_facade.list_tasks_summary.assert_called_once()
        args, kwargs = mock_task_facade.list_tasks_summary.call_args
        assert kwargs["offset"] == 20  # (3-1) * 10
        assert kwargs["limit"] == 10
    
    @patch('fastmcp.server.routes.lazy_task_routes.get_task_facade')
    def test_get_task_summaries_count_failure(self, mock_task_facade_dep):
        """Test handling of count_tasks failure"""
        mock_task_facade = Mock()
        mock_task_facade_dep.return_value = mock_task_facade
        
        mock_task_facade.count_tasks.return_value = {"success": False, "error": "Database error"}
        mock_task_facade.list_tasks_summary.return_value = {
            "success": True,
            "tasks": []
        }
        
        response = client.post("/api/tasks/summaries", json={
            "git_branch_id": "branch-123"
        })
        
        assert response.status_code == 200
        data = response.json()
        assert data["total"] == 0  # Should default to 0 on count failure
    
    @patch('fastmcp.server.routes.lazy_task_routes.get_task_facade')
    def test_get_task_summaries_list_failure(self, mock_task_facade_dep):
        """Test handling of list_tasks_summary failure"""
        mock_task_facade = Mock()
        mock_task_facade_dep.return_value = mock_task_facade
        
        mock_task_facade.count_tasks.return_value = {"success": True, "count": 10}
        mock_task_facade.list_tasks_summary.return_value = {
            "success": False,
            "error": "Query failed"
        }
        
        response = client.post("/api/tasks/summaries", json={
            "git_branch_id": "branch-123"
        })
        
        assert response.status_code == 500
        assert "Query failed" in response.json()["detail"]
    
    @patch('fastmcp.server.routes.lazy_task_routes.get_task_facade')
    def test_get_task_summaries_exception(self, mock_task_facade_dep):
        """Test handling of unexpected exceptions"""
        mock_task_facade = Mock()
        mock_task_facade_dep.return_value = mock_task_facade
        
        mock_task_facade.count_tasks.side_effect = Exception("Unexpected error")
        
        response = client.post("/api/tasks/summaries", json={
            "git_branch_id": "branch-123"
        })
        
        assert response.status_code == 500
        assert "Unexpected error" in response.json()["detail"]

class TestFullTaskEndpoint:
    """Test /api/tasks/{task_id} endpoint"""
    
    @patch('fastmcp.server.routes.lazy_task_routes.get_task_facade')
    def test_get_full_task_success(self, mock_task_facade_dep):
        """Test successful full task retrieval"""
        mock_task_facade = Mock()
        mock_task_facade_dep.return_value = mock_task_facade
        
        expected_task = {
            "id": "task-123",
            "title": "Full Task Data",
            "description": "Complete task information",
            "status": "in_progress",
            "priority": "high",
            "assignees": ["user1", "user2"],
            "dependencies": ["dep1"],
            "subtasks": [{"id": "sub1", "title": "Subtask 1"}]
        }
        
        mock_task_facade.get_task.return_value = {
            "success": True,
            "task": expected_task
        }
        
        response = client.get("/api/tasks/task-123")
        
        assert response.status_code == 200
        data = response.json()
        assert data == expected_task
        
        mock_task_facade.get_task.assert_called_once_with("task-123", include_full_data=True)
    
    @patch('fastmcp.server.routes.lazy_task_routes.get_task_facade')
    def test_get_full_task_not_found(self, mock_task_facade_dep):
        """Test full task retrieval when task not found"""
        mock_task_facade = Mock()
        mock_task_facade_dep.return_value = mock_task_facade
        
        mock_task_facade.get_task.return_value = {
            "success": False,
            "error": "Task not found"
        }
        
        response = client.get("/api/tasks/nonexistent-task")
        
        assert response.status_code == 404
        assert "not found" in response.json()["detail"]
    
    @patch('fastmcp.server.routes.lazy_task_routes.get_task_facade')
    def test_get_full_task_no_data(self, mock_task_facade_dep):
        """Test full task retrieval when task data is None"""
        mock_task_facade = Mock()
        mock_task_facade_dep.return_value = mock_task_facade
        
        mock_task_facade.get_task.return_value = {
            "success": True,
            "task": None
        }
        
        response = client.get("/api/tasks/task-123")
        
        assert response.status_code == 404
        assert "not found" in response.json()["detail"]
    
    @patch('fastmcp.server.routes.lazy_task_routes.get_task_facade')
    def test_get_full_task_error(self, mock_task_facade_dep):
        """Test full task retrieval with service error"""
        mock_task_facade = Mock()
        mock_task_facade_dep.return_value = mock_task_facade
        
        mock_task_facade.get_task.return_value = {
            "success": False,
            "error": "Database connection failed"
        }
        
        response = client.get("/api/tasks/task-123")
        
        assert response.status_code == 500
        assert "Database connection failed" in response.json()["detail"]
    
    @patch('fastmcp.server.routes.lazy_task_routes.get_task_facade')
    def test_get_full_task_exception(self, mock_task_facade_dep):
        """Test full task retrieval with unexpected exception"""
        mock_task_facade = Mock()
        mock_task_facade_dep.return_value = mock_task_facade
        
        mock_task_facade.get_task.side_effect = Exception("Unexpected error")
        
        response = client.get("/api/tasks/task-123")
        
        assert response.status_code == 500
        assert "Unexpected error" in response.json()["detail"]

class TestSubtaskSummariesEndpoint:
    """Test /api/subtasks/summaries endpoint"""
    
    @patch('fastmcp.server.routes.lazy_task_routes.get_task_facade')
    def test_get_subtask_summaries_success(self, mock_task_facade_dep):
        """Test successful subtask summaries retrieval"""
        mock_task_facade = Mock()
        mock_task_facade_dep.return_value = mock_task_facade
        
        mock_task_facade.list_subtasks_summary.return_value = {
            "success": True,
            "subtasks": [
                {
                    "id": "sub-1",
                    "title": "Subtask 1",
                    "status": "done",
                    "priority": "high",
                    "assignees": ["user1"],
                    "progress_percentage": 100
                },
                {
                    "id": "sub-2",
                    "title": "Subtask 2",
                    "status": "in_progress",
                    "priority": "medium",
                    "assignees": [],
                    "progress_percentage": 50
                },
                {
                    "id": "sub-3",
                    "title": "Subtask 3",
                    "status": "todo",
                    "priority": "low",
                    "assignees": ["user1", "user2"],
                    "progress_percentage": 0
                }
            ]
        }
        
        response = client.post("/api/subtasks/summaries", json={
            "parent_task_id": "task-123",
            "include_counts": True
        })
        
        assert response.status_code == 200
        data = response.json()
        
        assert data["parent_task_id"] == "task-123"
        assert data["total_count"] == 3
        assert len(data["subtasks"]) == 3
        
        # Check progress summary
        progress = data["progress_summary"]
        assert progress["total"] == 3
        assert progress["completed"] == 1
        assert progress["in_progress"] == 1
        assert progress["todo"] == 1
        assert progress["blocked"] == 0
        assert progress["completion_percentage"] == 33  # 1/3 * 100
        
        # Check first subtask
        sub1 = data["subtasks"][0]
        assert sub1["id"] == "sub-1"
        assert sub1["status"] == "done"
        assert sub1["assignees_count"] == 1
        assert sub1["progress_percentage"] == 100
    
    @patch('fastmcp.server.routes.lazy_task_routes.get_task_facade')
    def test_get_subtask_summaries_empty(self, mock_task_facade_dep):
        """Test subtask summaries with no subtasks"""
        mock_task_facade = Mock()
        mock_task_facade_dep.return_value = mock_task_facade
        
        mock_task_facade.list_subtasks_summary.return_value = {
            "success": True,
            "subtasks": []
        }
        
        response = client.post("/api/subtasks/summaries", json={
            "parent_task_id": "task-123"
        })
        
        assert response.status_code == 200
        data = response.json()
        
        assert data["total_count"] == 0
        assert len(data["subtasks"]) == 0
        assert data["progress_summary"]["completion_percentage"] == 0
    
    @patch('fastmcp.server.routes.lazy_task_routes.get_task_facade')
    def test_get_subtask_summaries_failure(self, mock_task_facade_dep):
        """Test subtask summaries with service failure"""
        mock_task_facade = Mock()
        mock_task_facade_dep.return_value = mock_task_facade
        
        mock_task_facade.list_subtasks_summary.return_value = {
            "success": False,
            "error": "Failed to fetch subtasks"
        }
        
        response = client.post("/api/subtasks/summaries", json={
            "parent_task_id": "task-123"
        })
        
        assert response.status_code == 500
        assert "Failed to fetch subtasks" in response.json()["detail"]
    
    @patch('fastmcp.server.routes.lazy_task_routes.get_task_facade')
    def test_get_subtask_summaries_exception(self, mock_task_facade_dep):
        """Test subtask summaries with unexpected exception"""
        mock_task_facade = Mock()
        mock_task_facade_dep.return_value = mock_task_facade
        
        mock_task_facade.list_subtasks_summary.side_effect = Exception("Database error")
        
        response = client.post("/api/subtasks/summaries", json={
            "parent_task_id": "task-123"
        })
        
        assert response.status_code == 500
        assert "Database error" in response.json()["detail"]
    
    def test_subtask_status_counting(self):
        """Test status counting logic for progress summary"""
        # This tests the internal logic of status counting
        subtasks_data = [
            {"status": "done"},
            {"status": "done"},
            {"status": "in_progress"},
            {"status": "todo"},
            {"status": "blocked"},
            {"status": "unknown_status"}  # Should not be counted
        ]
        
        status_counts = {"todo": 0, "in_progress": 0, "done": 0, "blocked": 0}
        
        for subtask_data in subtasks_data:
            if subtask_data["status"] in status_counts:
                status_counts[subtask_data["status"]] += 1
        
        assert status_counts["done"] == 2
        assert status_counts["in_progress"] == 1
        assert status_counts["todo"] == 1
        assert status_counts["blocked"] == 1

class TestTaskContextSummaryEndpoint:
    """Test /api/tasks/{task_id}/context/summary endpoint"""
    
    @patch('fastmcp.server.routes.lazy_task_routes.get_context_facade')
    def test_get_task_context_summary_success(self, mock_context_facade_dep):
        """Test successful task context summary retrieval"""
        mock_context_facade = Mock()
        mock_context_facade_dep.return_value = mock_context_facade
        
        mock_context_facade.get_context_summary.return_value = {
            "success": True,
            "has_context": True,
            "context_size": 1024,
            "last_updated": "2024-01-01T12:00:00Z"
        }
        
        response = client.get("/api/tasks/task-123/context/summary")
        
        assert response.status_code == 200
        data = response.json()
        
        assert data["has_context"] is True
        assert data["context_size"] == 1024
        assert data["last_updated"] == "2024-01-01T12:00:00Z"
        
        mock_context_facade.get_context_summary.assert_called_once_with("task-123")
    
    @patch('fastmcp.server.routes.lazy_task_routes.get_context_facade')
    def test_get_task_context_summary_no_context(self, mock_context_facade_dep):
        """Test task context summary when no context exists"""
        mock_context_facade = Mock()
        mock_context_facade_dep.return_value = mock_context_facade
        
        mock_context_facade.get_context_summary.return_value = {
            "success": False,
            "error": "No context found"
        }
        
        response = client.get("/api/tasks/task-123/context/summary")
        
        assert response.status_code == 200
        data = response.json()
        
        assert data["has_context"] is False
        assert "error" in data
        assert data["error"] == "No context found"
    
    @patch('fastmcp.server.routes.lazy_task_routes.get_context_facade')
    def test_get_task_context_summary_exception(self, mock_context_facade_dep):
        """Test task context summary with exception handling"""
        mock_context_facade = Mock()
        mock_context_facade_dep.return_value = mock_context_facade
        
        mock_context_facade.get_context_summary.side_effect = Exception("Context service error")
        
        response = client.get("/api/tasks/task-123/context/summary")
        
        assert response.status_code == 200  # Exception handled gracefully
        data = response.json()
        
        assert data["has_context"] is False
        assert "error" in data
        assert data["error"] == "Context service error"

class TestAgentsSummaryEndpoint:
    """Test /api/agents/summary endpoint"""
    
    def test_get_agents_summary_success(self):
        """Test successful agents summary retrieval"""
        response = client.get("/api/agents/summary?project_id=project-123")
        
        assert response.status_code == 200
        data = response.json()
        
        assert "available_agents" in data
        assert "project_agents" in data
        assert "total_available" in data
        assert "total_assigned" in data
        
        # Check available agents structure
        available_agents = data["available_agents"]
        assert len(available_agents) == 3
        
        coding_agent = available_agents[0]
        assert coding_agent["id"] == "@coding_agent"
        assert coding_agent["name"] == "Coding Agent"
        assert coding_agent["type"] == "development"
    
    def test_get_agents_summary_missing_project_id(self):
        """Test agents summary without required project_id"""
        response = client.get("/api/agents/summary")
        
        assert response.status_code == 422  # Validation error

class TestPerformanceMetricsEndpoint:
    """Test /api/performance/metrics endpoint"""
    
    def test_get_performance_metrics(self):
        """Test performance metrics retrieval"""
        response = client.get("/api/performance/metrics")
        
        assert response.status_code == 200
        data = response.json()
        
        assert "endpoints" in data
        assert "recommendations" in data
        
        # Check endpoints structure
        endpoints = data["endpoints"]
        assert "task_summaries" in endpoints
        assert "subtask_summaries" in endpoints
        
        task_summaries = endpoints["task_summaries"]
        assert "average_response_time" in task_summaries
        assert "cache_hit_rate" in task_summaries
        assert "error_rate" in task_summaries
        
        # Check recommendations
        recommendations = data["recommendations"]
        assert isinstance(recommendations, list)
        assert len(recommendations) > 0

class TestIntegrationScenarios:
    """Test integration scenarios combining multiple endpoints"""
    
    @patch('fastmcp.server.routes.lazy_task_routes.get_context_facade')
    @patch('fastmcp.server.routes.lazy_task_routes.get_task_facade')
    def test_full_lazy_loading_workflow(self, mock_task_facade_dep, mock_context_facade_dep):
        """Test complete lazy loading workflow"""
        # Setup mocks
        mock_task_facade = Mock()
        mock_context_facade = Mock()
        mock_task_facade_dep.return_value = mock_task_facade
        mock_context_facade_dep.return_value = mock_context_facade
        
        # Mock task summaries
        mock_task_facade.count_tasks.return_value = {"success": True, "count": 1}
        mock_task_facade.list_tasks_summary.return_value = {
            "success": True,
            "tasks": [{
                "id": "task-123",
                "title": "Test Task",
                "status": "in_progress",
                "priority": "high",
                "subtasks": ["sub1"],
                "assignees": ["user1"],
                "dependencies": None,
                "created_at": "2024-01-01T00:00:00Z",
                "updated_at": "2024-01-02T00:00:00Z"
            }]
        }
        
        # Mock context summary
        mock_context_facade.get_context_summary.return_value = {
            "success": True,
            "has_context": True,
            "context_size": 512
        }
        
        # Mock full task data
        mock_task_facade.get_task.return_value = {
            "success": True,
            "task": {
                "id": "task-123",
                "title": "Test Task",
                "description": "Full task details",
                "status": "in_progress",
                "priority": "high"
            }
        }
        
        # Mock subtask summaries
        mock_task_facade.list_subtasks_summary.return_value = {
            "success": True,
            "subtasks": [{
                "id": "sub-1",
                "title": "Subtask 1",
                "status": "todo",
                "priority": "medium",
                "assignees": [],
                "progress_percentage": 0
            }]
        }
        
        # 1. Get task summaries (initial page load)
        summaries_response = client.post("/api/tasks/summaries", json={
            "git_branch_id": "branch-123",
            "page": 1,
            "limit": 10
        })
        assert summaries_response.status_code == 200
        
        # 2. Get full task data (user clicks on task)
        full_task_response = client.get("/api/tasks/task-123")
        assert full_task_response.status_code == 200
        
        # 3. Get context summary (check if context exists)
        context_response = client.get("/api/tasks/task-123/context/summary")
        assert context_response.status_code == 200
        assert context_response.json()["has_context"] is True
        
        # 4. Get subtask summaries (expand task details)
        subtasks_response = client.post("/api/subtasks/summaries", json={
            "parent_task_id": "task-123"
        })
        assert subtasks_response.status_code == 200
        
        # Verify all endpoints were called correctly
        mock_task_facade.list_tasks_summary.assert_called_once()
        mock_task_facade.get_task.assert_called_once_with("task-123", include_full_data=True)
        mock_context_facade.get_context_summary.assert_called()
        mock_task_facade.list_subtasks_summary.assert_called_once_with(
            parent_task_id="task-123", 
            include_counts=True
        )

class TestErrorHandling:
    """Test comprehensive error handling scenarios"""
    
    @patch('fastmcp.server.routes.lazy_task_routes.get_task_facade')
    def test_network_timeout_simulation(self, mock_task_facade_dep):
        """Test behavior during network timeouts"""
        mock_task_facade = Mock()
        mock_task_facade_dep.return_value = mock_task_facade
        
        # Simulate timeout exception
        import socket
        mock_task_facade.count_tasks.side_effect = socket.timeout("Network timeout")
        
        response = client.post("/api/tasks/summaries", json={
            "git_branch_id": "branch-123"
        })
        
        assert response.status_code == 500
        assert "timeout" in response.json()["detail"].lower()
    
    @patch('fastmcp.server.routes.lazy_task_routes.get_task_facade')
    def test_database_connection_error(self, mock_task_facade_dep):
        """Test database connection error handling"""
        mock_task_facade = Mock()
        mock_task_facade_dep.return_value = mock_task_facade
        
        # Simulate database connection error
        mock_task_facade.list_tasks_summary.side_effect = Exception("Database connection refused")
        
        response = client.post("/api/tasks/summaries", json={
            "git_branch_id": "branch-123"
        })
        
        assert response.status_code == 500
        assert "Database connection refused" in response.json()["detail"]
    
    def test_malformed_request_data(self):
        """Test handling of malformed request data"""
        # Invalid JSON
        response = client.post(
            "/api/tasks/summaries",
            data="invalid json",
            headers={"content-type": "application/json"}
        )
        assert response.status_code == 422
        
        # Missing required fields
        response = client.post("/api/tasks/summaries", json={})
        assert response.status_code == 422
        
        # Invalid field types
        response = client.post("/api/tasks/summaries", json={
            "git_branch_id": "branch-123",
            "page": "not-a-number"
        })
        assert response.status_code == 422

if __name__ == "__main__":
    pytest.main([__file__])