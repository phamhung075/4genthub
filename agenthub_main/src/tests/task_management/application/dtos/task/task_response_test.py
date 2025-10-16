"""Test suite for TaskResponse DTO."""

import pytest
from uuid import uuid4
from datetime import datetime

from fastmcp.task_management.application.dtos.task.task_response import TaskResponse
from fastmcp.types.entities import TaskEntity
from fastmcp.shared.domain.value_objects import UUID


class TestTaskResponse:
    """Test cases for TaskResponse DTO."""
    
    @pytest.fixture
    def sample_task_entity(self):
        """Create a sample task entity."""
        task_id = str(uuid4())
        return TaskEntity(
            id=task_id,
            title="Test Task",
            description="Test Description",
            status="todo",
            priority="medium",
            details="Additional details",
            assignees=["user1", "user2"],
            labels=["frontend", "urgent"],
            estimated_effort="3 hours",
            due_date="2024-12-31T00:00:00Z",
            created_at="2024-01-01T00:00:00Z",
            updated_at="2024-01-01T00:00:00Z",
            git_branch_id=str(uuid4()),
            project_id=str(uuid4()),
            parent_task_id=None,
            dependencies=[str(uuid4())],
            blocking_tasks=[str(uuid4())],
            subtask_ids=[str(uuid4()), str(uuid4())],
            subtask_count=2,
            context_id=str(uuid4()),
            completion_summary=None
        )
    
    def test_task_response_creation_with_entity(self, sample_task_entity):
        """Test creating TaskResponse with a task entity."""
        response = TaskResponse(task=sample_task_entity)
        
        assert response.success is True
        assert response.task == sample_task_entity
        assert response.task.id == sample_task_entity.id
        assert response.task.title == "Test Task"
        assert response.task.subtask_count == 2
    
    def test_task_response_creation_without_task(self):
        """Test creating TaskResponse without a task."""
        response = TaskResponse()
        
        assert response.success is True
        assert response.task is None
    
    def test_task_response_creation_with_success_false(self):
        """Test creating TaskResponse with success=False."""
        response = TaskResponse(success=False, task=None)
        
        assert response.success is False
        assert response.task is None
    
    def test_task_response_to_dict(self, sample_task_entity):
        """Test converting TaskResponse to dictionary."""
        response = TaskResponse(task=sample_task_entity)
        result_dict = response.model_dump()
        
        assert isinstance(result_dict, dict)
        assert result_dict["success"] is True
        assert result_dict["task"]["id"] == sample_task_entity.id
        assert result_dict["task"]["title"] == "Test Task"
        assert result_dict["task"]["subtask_count"] == 2
        assert result_dict["task"]["assignees"] == ["user1", "user2"]
        assert result_dict["task"]["labels"] == ["frontend", "urgent"]
    
    def test_task_response_json_serialization(self, sample_task_entity):
        """Test JSON serialization of TaskResponse."""
        response = TaskResponse(task=sample_task_entity)
        json_str = response.model_dump_json()
        
        assert isinstance(json_str, str)
        assert sample_task_entity.id in json_str
        assert "Test Task" in json_str
        assert '"success":true' in json_str
    
    def test_task_response_with_completed_task(self, sample_task_entity):
        """Test TaskResponse with a completed task."""
        sample_task_entity.status = "done"
        sample_task_entity.completion_summary = "Task completed successfully"
        
        response = TaskResponse(task=sample_task_entity)
        
        assert response.task.status == "done"
        assert response.task.completion_summary == "Task completed successfully"
    
    def test_task_response_with_null_fields(self):
        """Test TaskResponse with task having null fields."""
        task = TaskEntity(
            id=str(uuid4()),
            title="Minimal Task",
            description=None,
            status="todo",
            priority="low",
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
        
        response = TaskResponse(task=task)
        
        assert response.success is True
        assert response.task.description is None
        assert response.task.details is None
        assert response.task.estimated_effort is None
        assert response.task.due_date is None
        assert len(response.task.assignees) == 0
        assert len(response.task.labels) == 0
    
    def test_task_response_field_validation(self, sample_task_entity):
        """Test that TaskResponse properly validates task fields."""
        response = TaskResponse(task=sample_task_entity)
        
        # Verify all fields are properly typed
        assert isinstance(response.success, bool)
        assert isinstance(response.task.id, str)
        assert isinstance(response.task.title, str)
        assert isinstance(response.task.assignees, list)
        assert isinstance(response.task.labels, list)
        assert isinstance(response.task.subtask_count, int)
        assert isinstance(response.task.dependencies, list)
    
    def test_task_response_model_copy(self, sample_task_entity):
        """Test creating a copy of TaskResponse."""
        original = TaskResponse(task=sample_task_entity)
        copy = original.model_copy()
        
        assert copy.success == original.success
        assert copy.task.id == original.task.id
        assert copy.task.title == original.task.title
        assert copy is not original  # Different instances
    
    def test_task_response_model_validate(self, sample_task_entity):
        """Test model validation."""
        # Valid data
        data = {
            "success": True,
            "task": sample_task_entity.model_dump() if hasattr(sample_task_entity, 'model_dump') else sample_task_entity.__dict__
        }
        
        response = TaskResponse.model_validate(data)
        
        assert response.success is True
        assert response.task.id == sample_task_entity.id