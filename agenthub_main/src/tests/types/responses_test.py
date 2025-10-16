"""Test suite for response types."""

import pytest
from uuid import uuid4

from fastmcp.types.responses import (
    TaskListResponse,
    SubtaskListResponse,
    SearchResponse,
    ErrorResponse,
    SuccessResponse,
    PaginatedResponse
)
from fastmcp.types.entities import TaskEntity, SubtaskEntity


class TestTaskListResponse:
    """Test cases for TaskListResponse."""
    
    def test_task_list_response_success(self):
        """Test successful TaskListResponse."""
        tasks = [
            TaskEntity(
                id=str(uuid4()),
                title=f"Task {i}",
                description=f"Description {i}",
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
            for i in range(3)
        ]
        
        response = TaskListResponse(
            success=True,
            tasks=tasks,
            total=3
        )
        
        assert response.success is True
        assert len(response.tasks) == 3
        assert response.total == 3
        assert all(isinstance(task, TaskEntity) for task in response.tasks)
    
    def test_task_list_response_empty(self):
        """Test empty TaskListResponse."""
        response = TaskListResponse(
            success=True,
            tasks=[],
            total=0
        )
        
        assert response.success is True
        assert response.tasks == []
        assert response.total == 0
    
    def test_task_list_response_failure(self):
        """Test failed TaskListResponse."""
        response = TaskListResponse(
            success=False,
            tasks=[],
            total=0,
            error="Failed to fetch tasks"
        )
        
        assert response.success is False
        assert response.tasks == []
        assert response.error == "Failed to fetch tasks"


class TestSubtaskListResponse:
    """Test cases for SubtaskListResponse."""
    
    def test_subtask_list_response_success(self):
        """Test successful SubtaskListResponse."""
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
                task_id=str(uuid4()),
                parent_title="Parent Task"
            )
            for i in range(2)
        ]
        
        response = SubtaskListResponse(
            success=True,
            subtasks=subtasks,
            total=2
        )
        
        assert response.success is True
        assert len(response.subtasks) == 2
        assert response.total == 2
        assert all(isinstance(subtask, SubtaskEntity) for subtask in response.subtasks)
    
    def test_subtask_list_response_with_parent_info(self):
        """Test SubtaskListResponse includes parent information."""
        task_id = str(uuid4())
        subtasks = [
            SubtaskEntity(
                id=str(uuid4()),
                title="Subtask with parent",
                description="Test",
                status="todo",
                priority="low",
                assignees=[],
                progress_notes=None,
                created_at="2024-01-01T00:00:00Z",
                updated_at="2024-01-01T00:00:00Z",
                task_id=task_id,
                parent_title="Main Task Title"
            )
        ]
        
        response = SubtaskListResponse(
            success=True,
            subtasks=subtasks,
            total=1
        )
        
        assert response.subtasks[0].task_id == task_id
        assert response.subtasks[0].parent_title == "Main Task Title"


class TestSearchResponse:
    """Test cases for SearchResponse."""
    
    def test_search_response_with_results(self):
        """Test SearchResponse with search results."""
        tasks = [
            TaskEntity(
                id=str(uuid4()),
                title="Search Result Task",
                description="Contains search term",
                status="todo",
                priority="medium",
                details=None,
                assignees=[],
                labels=["searchable"],
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
        
        response = SearchResponse(
            success=True,
            tasks=tasks,
            total=1,
            query="search term",
            filters={"status": "todo"}
        )
        
        assert response.success is True
        assert len(response.tasks) == 1
        assert response.total == 1
        assert response.query == "search term"
        assert response.filters == {"status": "todo"}
    
    def test_search_response_no_results(self):
        """Test SearchResponse with no results."""
        response = SearchResponse(
            success=True,
            tasks=[],
            total=0,
            query="nonexistent",
            filters={}
        )
        
        assert response.success is True
        assert response.tasks == []
        assert response.total == 0
        assert response.query == "nonexistent"


class TestErrorResponse:
    """Test cases for ErrorResponse."""
    
    def test_error_response_basic(self):
        """Test basic ErrorResponse."""
        response = ErrorResponse(
            success=False,
            error="Something went wrong",
            code="GENERIC_ERROR"
        )
        
        assert response.success is False
        assert response.error == "Something went wrong"
        assert response.code == "GENERIC_ERROR"
    
    def test_error_response_with_details(self):
        """Test ErrorResponse with additional details."""
        response = ErrorResponse(
            success=False,
            error="Validation failed",
            code="VALIDATION_ERROR",
            details={
                "fields": ["title", "status"],
                "messages": ["Title is required", "Invalid status value"]
            }
        )
        
        assert response.success is False
        assert response.error == "Validation failed"
        assert response.code == "VALIDATION_ERROR"
        assert response.details["fields"] == ["title", "status"]
        assert len(response.details["messages"]) == 2


class TestSuccessResponse:
    """Test cases for SuccessResponse."""
    
    def test_success_response_simple(self):
        """Test simple SuccessResponse."""
        response = SuccessResponse(
            success=True,
            message="Operation completed successfully"
        )
        
        assert response.success is True
        assert response.message == "Operation completed successfully"
    
    def test_success_response_with_data(self):
        """Test SuccessResponse with additional data."""
        response = SuccessResponse(
            success=True,
            message="Task created",
            data={
                "task_id": str(uuid4()),
                "created_at": "2024-01-01T00:00:00Z"
            }
        )
        
        assert response.success is True
        assert response.message == "Task created"
        assert "task_id" in response.data
        assert "created_at" in response.data


class TestPaginatedResponse:
    """Test cases for PaginatedResponse."""
    
    def test_paginated_response(self):
        """Test PaginatedResponse with pagination metadata."""
        tasks = [
            TaskEntity(
                id=str(uuid4()),
                title=f"Task {i}",
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
            for i in range(10)
        ]
        
        response = PaginatedResponse(
            success=True,
            items=tasks,
            total=50,
            offset=10,
            limit=10,
            has_next=True,
            has_previous=True
        )
        
        assert response.success is True
        assert len(response.items) == 10
        assert response.total == 50
        assert response.offset == 10
        assert response.limit == 10
        assert response.has_next is True
        assert response.has_previous is True
    
    def test_paginated_response_first_page(self):
        """Test PaginatedResponse for first page."""
        response = PaginatedResponse(
            success=True,
            items=[],
            total=100,
            offset=0,
            limit=20,
            has_next=True,
            has_previous=False
        )
        
        assert response.offset == 0
        assert response.has_next is True
        assert response.has_previous is False
    
    def test_paginated_response_last_page(self):
        """Test PaginatedResponse for last page."""
        response = PaginatedResponse(
            success=True,
            items=[],
            total=100,
            offset=80,
            limit=20,
            has_next=False,
            has_previous=True
        )
        
        assert response.offset == 80
        assert response.has_next is False
        assert response.has_previous is True