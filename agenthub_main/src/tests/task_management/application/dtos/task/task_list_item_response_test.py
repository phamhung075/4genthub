"""
Test suite for TaskListItemResponse DTO

Tests the streamlined task list item response structure
after Phase 1 refactoring to remove denormalized subtask_count.
"""

import pytest
from datetime import datetime, timezone
from uuid import uuid4

from fastmcp.task_management.application.dtos.task.task_list_item_response import TaskListItemResponse
from fastmcp.task_management.domain.entities.task import Task
from fastmcp.task_management.domain.value_objects import (
    TaskID,
    TaskTitle,
    TaskDescription,
    TaskStatus,
    TaskPriority,
    GitBranchID,
    UserID,
    TaskDetails,
    EstimatedEffort
)


class TestTaskListItemResponse:
    """Test suite for TaskListItemResponse DTO"""

    @pytest.fixture
    def sample_task(self):
        """Create a sample task for testing"""
        task = Task(
            id=TaskID(str(uuid4())),
            git_branch_id=GitBranchID(str(uuid4())),
            title=TaskTitle("Test Task"),
            description=TaskDescription("Test Description"),
            status=TaskStatus.TODO,
            priority=TaskPriority.HIGH,
            assignees=[UserID("user1"), UserID("user2")],
            labels=["backend", "feature"],
            details=TaskDetails("Detailed information"),
            estimated_effort=EstimatedEffort("2 days"),
            dependencies=[TaskID(str(uuid4())), TaskID(str(uuid4()))],
            progress_percentage=45
        )
        # Set timestamps
        task.created_at = datetime.now(timezone.utc)
        task.updated_at = datetime.now(timezone.utc)
        return task

    def test_from_domain_basic(self, sample_task):
        """Test creating response from domain entity"""
        response = TaskListItemResponse.from_domain(sample_task)
        
        assert response.id == sample_task.id.value
        assert response.title == sample_task.title.value
        assert response.description == sample_task.description.value
        assert response.status == sample_task.status.value
        assert response.priority == sample_task.priority.value
        assert response.assignees == ["user1", "user2"]
        assert response.labels == ["backend", "feature"]
        assert response.details == sample_task.details.value
        assert response.estimated_effort == sample_task.estimated_effort.value
        assert response.progress_percentage == 45
        assert response.created_at == sample_task.created_at
        assert response.updated_at == sample_task.updated_at

    def test_from_domain_with_subtasks(self, sample_task):
        """Test response includes subtasks array when provided"""
        # Add mock subtasks to task
        subtasks = [
            {"id": str(uuid4()), "title": "Subtask 1", "status": "done"},
            {"id": str(uuid4()), "title": "Subtask 2", "status": "in_progress"}
        ]
        
        # In real usage, subtasks would be loaded via repository
        # For testing, we'll pass them directly
        response = TaskListItemResponse.from_domain(sample_task, subtasks=subtasks)
        
        assert response.subtasks == subtasks
        assert len(response.subtasks) == 2

    def test_from_domain_no_subtasks(self, sample_task):
        """Test response with no subtasks"""
        response = TaskListItemResponse.from_domain(sample_task)
        
        assert response.subtasks == []

    def test_from_domain_empty_collections(self):
        """Test with empty collections"""
        task = Task(
            id=TaskID(str(uuid4())),
            git_branch_id=GitBranchID(str(uuid4())),
            title=TaskTitle("Minimal Task"),
            status=TaskStatus.TODO,
            priority=TaskPriority.MEDIUM,
            assignees=[],  # Empty
            labels=[],     # Empty
            dependencies=[] # Empty
        )
        
        response = TaskListItemResponse.from_domain(task)
        
        assert response.assignees == []
        assert response.labels == []
        assert response.dependencies == []
        assert response.subtasks == []

    def test_from_domain_optional_fields(self, sample_task):
        """Test optional fields handling"""
        # Create task without optional fields
        task = Task(
            id=TaskID(str(uuid4())),
            git_branch_id=GitBranchID(str(uuid4())),
            title=TaskTitle("Task without optionals"),
            status=TaskStatus.TODO,
            priority=TaskPriority.LOW,
            assignees=[],
            labels=[]
        )
        # Don't set optional fields
        
        response = TaskListItemResponse.from_domain(task)
        
        assert response.description is None
        assert response.details is None
        assert response.estimated_effort is None
        assert response.due_date is None
        assert response.completion_date is None
        assert response.progress_percentage is None

    def test_model_dump_serialization(self, sample_task):
        """Test serialization to dict"""
        response = TaskListItemResponse.from_domain(sample_task)
        data = response.model_dump()
        
        assert isinstance(data, dict)
        assert data["id"] == sample_task.id.value
        assert data["title"] == sample_task.title.value
        assert data["status"] == "todo"
        assert data["priority"] == "high"
        assert "subtasks" in data
        assert data["subtasks"] == []

    def test_model_dump_json_serialization(self, sample_task):
        """Test JSON serialization"""
        response = TaskListItemResponse.from_domain(sample_task)
        json_str = response.model_dump_json()
        
        assert isinstance(json_str, str)
        assert sample_task.id.value in json_str
        assert sample_task.title.value in json_str

    def test_model_dump_exclude_none(self, sample_task):
        """Test excluding None values in serialization"""
        # Create minimal task
        task = Task(
            id=TaskID(str(uuid4())),
            git_branch_id=GitBranchID(str(uuid4())),
            title=TaskTitle("Minimal"),
            status=TaskStatus.TODO,
            priority=TaskPriority.MEDIUM,
            assignees=[],
            labels=[]
        )
        
        response = TaskListItemResponse.from_domain(task)
        data = response.model_dump(exclude_none=True)
        
        # These should not be in the dict
        assert "description" not in data
        assert "details" not in data
        assert "estimated_effort" not in data
        assert "due_date" not in data

    def test_progress_percentage_boundaries(self):
        """Test progress percentage boundary values"""
        for progress in [0, 50, 100]:
            task = Task(
                id=TaskID(str(uuid4())),
                git_branch_id=GitBranchID(str(uuid4())),
                title=TaskTitle(f"Task {progress}%"),
                status=TaskStatus.IN_PROGRESS,
                priority=TaskPriority.MEDIUM,
                assignees=[],
                labels=[],
                progress_percentage=progress
            )
            
            response = TaskListItemResponse.from_domain(task)
            assert response.progress_percentage == progress

    def test_dependencies_conversion(self, sample_task):
        """Test dependencies are converted to strings"""
        response = TaskListItemResponse.from_domain(sample_task)
        
        assert len(response.dependencies) == 2
        assert all(isinstance(dep_id, str) for dep_id in response.dependencies)

    def test_timestamp_timezone_handling(self, sample_task):
        """Test timestamps maintain timezone info"""
        response = TaskListItemResponse.from_domain(sample_task)
        
        assert response.created_at.tzinfo is not None
        assert response.updated_at.tzinfo is not None

    def test_large_subtask_list(self, sample_task):
        """Test handling of many subtasks"""
        # Create 100 subtasks
        subtasks = [
            {"id": str(uuid4()), "title": f"Subtask {i}", "status": "todo"}
            for i in range(100)
        ]
        
        response = TaskListItemResponse.from_domain(sample_task, subtasks=subtasks)
        
        assert len(response.subtasks) == 100
        assert response.subtasks[0]["title"] == "Subtask 0"
        assert response.subtasks[99]["title"] == "Subtask 99"

    def test_status_enum_values(self):
        """Test all status enum values"""
        statuses = [
            TaskStatus.TODO,
            TaskStatus.IN_PROGRESS,
            TaskStatus.DONE,
            TaskStatus.BLOCKED,
            TaskStatus.REVIEW,
            TaskStatus.TESTING,
            TaskStatus.CANCELLED
        ]
        
        for status in statuses:
            task = Task(
                id=TaskID(str(uuid4())),
                git_branch_id=GitBranchID(str(uuid4())),
                title=TaskTitle(f"Task {status.value}"),
                status=status,
                priority=TaskPriority.MEDIUM,
                assignees=[],
                labels=[]
            )
            
            response = TaskListItemResponse.from_domain(task)
            assert response.status == status.value

    def test_priority_enum_values(self):
        """Test all priority enum values"""
        priorities = [
            TaskPriority.LOW,
            TaskPriority.MEDIUM,
            TaskPriority.HIGH,
            TaskPriority.URGENT,
            TaskPriority.CRITICAL
        ]
        
        for priority in priorities:
            task = Task(
                id=TaskID(str(uuid4())),
                git_branch_id=GitBranchID(str(uuid4())),
                title=TaskTitle(f"Task {priority.value}"),
                status=TaskStatus.TODO,
                priority=priority,
                assignees=[],
                labels=[]
            )
            
            response = TaskListItemResponse.from_domain(task)
            assert response.priority == priority.value

    def test_field_types(self, sample_task):
        """Verify all field types in response"""
        response = TaskListItemResponse.from_domain(sample_task)
        
        # String fields
        assert isinstance(response.id, str)
        assert isinstance(response.title, str)
        assert isinstance(response.status, str)
        assert isinstance(response.priority, str)
        
        # Optional string fields
        assert response.description is None or isinstance(response.description, str)
        assert response.details is None or isinstance(response.details, str)
        assert response.estimated_effort is None or isinstance(response.estimated_effort, str)
        
        # List fields
        assert isinstance(response.assignees, list)
        assert isinstance(response.labels, list)
        assert isinstance(response.dependencies, list)
        assert isinstance(response.subtasks, list)
        
        # Numeric fields
        assert response.progress_percentage is None or isinstance(response.progress_percentage, int)
        
        # Datetime fields
        assert isinstance(response.created_at, datetime)
        assert isinstance(response.updated_at, datetime)