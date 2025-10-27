"""
Test suite for TaskResponse DTO

Tests the comprehensive task response structure after Phase 1
refactoring with streamlined subtask handling.
"""

import pytest
from datetime import datetime, timezone, timedelta
from uuid import uuid4

from fastmcp.task_management.application.dtos.task.task_response import TaskResponse
from fastmcp.task_management.domain.entities.task import Task
from fastmcp.task_management.domain.entities.subtask import Subtask
from fastmcp.task_management.domain.value_objects import (
    TaskID,
    SubtaskID,
    TaskTitle,
    TaskDescription,
    TaskStatus,
    TaskPriority,
    GitBranchID,
    UserID,
    TaskDetails,
    EstimatedEffort
)


class TestTaskResponse:
    """Test suite for TaskResponse DTO"""

    @pytest.fixture
    def sample_task(self):
        """Create a comprehensive sample task"""
        task_id = TaskID(str(uuid4()))
        git_branch_id = GitBranchID(str(uuid4()))
        
        task = Task(
            id=task_id,
            git_branch_id=git_branch_id,
            title=TaskTitle("Implement User Authentication"),
            description=TaskDescription("Add JWT-based authentication system"),
            status=TaskStatus.IN_PROGRESS,
            priority=TaskPriority.HIGH,
            assignees=[UserID("dev1"), UserID("dev2"), UserID("reviewer1")],
            labels=["security", "backend", "phase1"],
            details=TaskDetails("Full implementation including refresh tokens"),
            estimated_effort=EstimatedEffort("3 days"),
            dependencies=[TaskID(str(uuid4())), TaskID(str(uuid4()))],
            progress_percentage=65,
            due_date=datetime.now(timezone.utc) + timedelta(days=5)
        )
        
        # Set timestamps
        task.created_at = datetime.now(timezone.utc) - timedelta(days=2)
        task.updated_at = datetime.now(timezone.utc) - timedelta(hours=1)
        
        # Add some metadata
        task.blocked_reason = "Waiting for security review"
        task.completion_summary = None  # Not completed yet
        
        return task

    @pytest.fixture
    def sample_subtasks(self, sample_task):
        """Create sample subtasks for the task"""
        subtasks = []
        
        # Subtask 1 - Completed
        sub1 = Subtask(
            id=SubtaskID(str(uuid4())),
            task_id=sample_task.id,
            title="Design authentication schema",
            description="Create database models for users and tokens",
            status=TaskStatus.DONE,
            priority=TaskPriority.HIGH,
            assignees=[UserID("dev1")],
            progress_percentage=100
        )
        sub1.created_at = datetime.now(timezone.utc) - timedelta(days=2)
        sub1.updated_at = datetime.now(timezone.utc) - timedelta(days=1)
        subtasks.append(sub1)
        
        # Subtask 2 - In Progress
        sub2 = Subtask(
            id=SubtaskID(str(uuid4())),
            task_id=sample_task.id,
            title="Implement JWT generation",
            description="Create JWT token generation and validation",
            status=TaskStatus.IN_PROGRESS,
            priority=TaskPriority.HIGH,
            assignees=[UserID("dev1"), UserID("dev2")],
            progress_percentage=75
        )
        sub2.created_at = datetime.now(timezone.utc) - timedelta(days=1)
        sub2.updated_at = datetime.now(timezone.utc) - timedelta(hours=2)
        subtasks.append(sub2)
        
        # Subtask 3 - Todo
        sub3 = Subtask(
            id=SubtaskID(str(uuid4())),
            task_id=sample_task.id,
            title="Add refresh token support",
            status=TaskStatus.TODO,
            priority=TaskPriority.MEDIUM,
            assignees=[UserID("dev2")]
        )
        sub3.created_at = datetime.now(timezone.utc) - timedelta(hours=5)
        sub3.updated_at = datetime.now(timezone.utc) - timedelta(hours=5)
        subtasks.append(sub3)
        
        return subtasks

    def test_from_domain_complete_task(self, sample_task, sample_subtasks):
        """Test creating response from complete task with subtasks"""
        response = TaskResponse.from_domain(sample_task, subtasks=sample_subtasks)
        
        # Basic fields
        assert response.id == sample_task.id.value
        assert response.git_branch_id == sample_task.git_branch_id.value
        assert response.title == sample_task.title.value
        assert response.description == sample_task.description.value
        assert response.status == sample_task.status.value
        assert response.priority == sample_task.priority.value
        
        # Collections
        assert response.assignees == ["dev1", "dev2", "reviewer1"]
        assert response.labels == ["security", "backend", "phase1"]
        assert len(response.dependencies) == 2
        
        # Optional fields
        assert response.details == sample_task.details.value
        assert response.estimated_effort == sample_task.estimated_effort.value
        assert response.progress_percentage == 65
        assert response.blocked_reason == "Waiting for security review"
        
        # Subtasks
        assert len(response.subtasks) == 3
        assert response.subtasks[0]["title"] == "Design authentication schema"
        assert response.subtasks[1]["status"] == "in_progress"
        assert response.subtasks[2]["priority"] == "medium"

    def test_from_domain_minimal_task(self):
        """Test creating response from minimal task"""
        task = Task(
            id=TaskID(str(uuid4())),
            git_branch_id=GitBranchID(str(uuid4())),
            title=TaskTitle("Minimal Task"),
            status=TaskStatus.TODO,
            priority=TaskPriority.LOW,
            assignees=[],
            labels=[]
        )
        
        response = TaskResponse.from_domain(task)
        
        assert response.title == "Minimal Task"
        assert response.status == "todo"
        assert response.priority == "low"
        assert response.assignees == []
        assert response.labels == []
        assert response.subtasks == []
        assert response.description is None
        assert response.details is None
        assert response.progress_percentage is None

    def test_subtask_conversion(self, sample_task, sample_subtasks):
        """Test subtask entity to dict conversion"""
        response = TaskResponse.from_domain(sample_task, subtasks=sample_subtasks)
        
        # Check first subtask details
        sub1_dict = response.subtasks[0]
        sub1 = sample_subtasks[0]
        
        assert sub1_dict["id"] == sub1.id.value
        assert sub1_dict["title"] == sub1.title
        assert sub1_dict["description"] == sub1.description
        assert sub1_dict["status"] == sub1.status.value
        assert sub1_dict["priority"] == sub1.priority.value
        assert sub1_dict["assignees"] == ["dev1"]
        assert sub1_dict["progress_percentage"] == 100
        assert "created_at" in sub1_dict
        assert "updated_at" in sub1_dict

    def test_empty_subtasks_list(self, sample_task):
        """Test task with no subtasks"""
        response = TaskResponse.from_domain(sample_task, subtasks=[])
        assert response.subtasks == []

    def test_none_subtasks_defaults_to_empty(self, sample_task):
        """Test None subtasks defaults to empty list"""
        response = TaskResponse.from_domain(sample_task, subtasks=None)
        assert response.subtasks == []

    def test_model_dump_full_data(self, sample_task, sample_subtasks):
        """Test full data serialization"""
        response = TaskResponse.from_domain(sample_task, subtasks=sample_subtasks)
        data = response.model_dump()
        
        assert isinstance(data, dict)
        assert data["id"] == sample_task.id.value
        assert data["subtasks"] == response.subtasks
        assert len(data["subtasks"]) == 3

    def test_model_dump_json(self, sample_task, sample_subtasks):
        """Test JSON serialization with datetime handling"""
        response = TaskResponse.from_domain(sample_task, subtasks=sample_subtasks)
        json_str = response.model_dump_json()
        
        assert isinstance(json_str, str)
        assert sample_task.id.value in json_str
        assert "subtasks" in json_str
        # Should contain ISO format timestamps
        assert "T" in json_str  # ISO format indicator

    def test_model_dump_exclude_none(self, sample_task):
        """Test excluding None values"""
        # Create task without optional fields
        task = Task(
            id=TaskID(str(uuid4())),
            git_branch_id=GitBranchID(str(uuid4())),
            title=TaskTitle("No Optionals"),
            status=TaskStatus.TODO,
            priority=TaskPriority.MEDIUM,
            assignees=[],
            labels=[]
        )
        
        response = TaskResponse.from_domain(task)
        data = response.model_dump(exclude_none=True)
        
        # These should not be present
        assert "description" not in data
        assert "details" not in data
        assert "estimated_effort" not in data
        assert "progress_percentage" not in data
        assert "blocked_reason" not in data

    def test_completed_task_fields(self):
        """Test completed task specific fields"""
        task = Task(
            id=TaskID(str(uuid4())),
            git_branch_id=GitBranchID(str(uuid4())),
            title=TaskTitle("Completed Task"),
            status=TaskStatus.DONE,
            priority=TaskPriority.MEDIUM,
            assignees=[UserID("dev1")],
            labels=["completed"],
            progress_percentage=100
        )
        
        # Set completion fields
        task.completion_date = datetime.now(timezone.utc)
        task.completion_summary = "Successfully implemented all features"
        task.testing_notes = "All unit tests passing, integration tested"
        
        response = TaskResponse.from_domain(task)
        
        assert response.status == "done"
        assert response.progress_percentage == 100
        assert response.completion_date is not None
        assert response.completion_summary == "Successfully implemented all features"
        assert response.testing_notes == "All unit tests passing, integration tested"

    def test_blocked_task_fields(self):
        """Test blocked task specific fields"""
        task = Task(
            id=TaskID(str(uuid4())),
            git_branch_id=GitBranchID(str(uuid4())),
            title=TaskTitle("Blocked Task"),
            status=TaskStatus.BLOCKED,
            priority=TaskPriority.HIGH,
            assignees=[UserID("dev1")],
            labels=["blocked"]
        )
        
        task.blocked_reason = "Waiting for API documentation"
        task.blocked_at = datetime.now(timezone.utc)
        
        response = TaskResponse.from_domain(task)
        
        assert response.status == "blocked"
        assert response.blocked_reason == "Waiting for API documentation"
        assert response.blocked_at is not None

    def test_datetime_timezone_handling(self, sample_task):
        """Test all datetime fields maintain timezone"""
        response = TaskResponse.from_domain(sample_task)
        
        assert response.created_at.tzinfo is not None
        assert response.updated_at.tzinfo is not None
        if response.due_date:
            assert response.due_date.tzinfo is not None

    def test_large_number_of_subtasks(self, sample_task):
        """Test handling many subtasks"""
        # Create 50 subtasks
        subtasks = []
        for i in range(50):
            sub = Subtask(
                id=SubtaskID(str(uuid4())),
                task_id=sample_task.id,
                title=f"Subtask {i}",
                status=TaskStatus.TODO if i < 25 else TaskStatus.DONE,
                priority=TaskPriority.MEDIUM,
                assignees=[UserID(f"dev{i % 3}")]
            )
            subtasks.append(sub)
        
        response = TaskResponse.from_domain(sample_task, subtasks=subtasks)
        
        assert len(response.subtasks) == 50
        # Check some are todo and some are done
        todo_count = sum(1 for s in response.subtasks if s["status"] == "todo")
        done_count = sum(1 for s in response.subtasks if s["status"] == "done")
        assert todo_count == 25
        assert done_count == 25

    def test_all_status_values(self):
        """Test all possible status values"""
        statuses = [
            (TaskStatus.TODO, "todo"),
            (TaskStatus.IN_PROGRESS, "in_progress"),
            (TaskStatus.DONE, "done"),
            (TaskStatus.BLOCKED, "blocked"),
            (TaskStatus.REVIEW, "review"),
            (TaskStatus.TESTING, "testing"),
            (TaskStatus.CANCELLED, "cancelled")
        ]
        
        for status_enum, status_str in statuses:
            task = Task(
                id=TaskID(str(uuid4())),
                git_branch_id=GitBranchID(str(uuid4())),
                title=TaskTitle(f"Task {status_str}"),
                status=status_enum,
                priority=TaskPriority.MEDIUM,
                assignees=[],
                labels=[]
            )
            
            response = TaskResponse.from_domain(task)
            assert response.status == status_str

    def test_all_priority_values(self):
        """Test all possible priority values"""
        priorities = [
            (TaskPriority.LOW, "low"),
            (TaskPriority.MEDIUM, "medium"),
            (TaskPriority.HIGH, "high"),
            (TaskPriority.URGENT, "urgent"),
            (TaskPriority.CRITICAL, "critical")
        ]
        
        for priority_enum, priority_str in priorities:
            task = Task(
                id=TaskID(str(uuid4())),
                git_branch_id=GitBranchID(str(uuid4())),
                title=TaskTitle(f"Task {priority_str}"),
                status=TaskStatus.TODO,
                priority=priority_enum,
                assignees=[],
                labels=[]
            )
            
            response = TaskResponse.from_domain(task)
            assert response.priority == priority_str

    def test_dependency_string_conversion(self, sample_task):
        """Test dependencies are converted to string IDs"""
        response = TaskResponse.from_domain(sample_task)
        
        assert isinstance(response.dependencies, list)
        assert len(response.dependencies) == 2
        for dep_id in response.dependencies:
            assert isinstance(dep_id, str)
            # Should be valid UUID format
            uuid4(dep_id)  # This will raise if not valid UUID

    def test_context_and_insights(self, sample_task):
        """Test context and insight fields"""
        # Add context and insights to task
        sample_task.context_data = {"feature": "authentication", "phase": 1}
        sample_task.insights_found = ["JWT library is well-documented", "Consider rate limiting"]
        
        response = TaskResponse.from_domain(sample_task)
        
        assert response.context_data == {"feature": "authentication", "phase": 1}
        assert response.insights_found == ["JWT library is well-documented", "Consider rate limiting"]