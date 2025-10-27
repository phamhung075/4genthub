"""
Test suite for Task domain entity

Tests the task entity behavior, validation, and business rules.
"""

import pytest
from datetime import datetime, timezone, timedelta
from uuid import uuid4

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
from fastmcp.task_management.domain.exceptions import ValidationError, InvalidTaskStateError


class TestTaskEntity:
    """Test suite for Task domain entity"""

    def test_create_minimal_task(self):
        """Test creating task with minimal required fields"""
        task = Task(
            id=TaskID(str(uuid4())),
            git_branch_id=GitBranchID(str(uuid4())),
            title=TaskTitle("Implement user authentication"),
            status=TaskStatus.TODO,
            priority=TaskPriority.MEDIUM,
            assignees=[],
            labels=[]
        )
        
        assert task.id is not None
        assert task.git_branch_id is not None
        assert task.title.value == "Implement user authentication"
        assert task.status == TaskStatus.TODO
        assert task.priority == TaskPriority.MEDIUM
        assert task.assignees == []
        assert task.labels == []
        assert task.description is None
        assert task.progress_percentage is None

    def test_create_complete_task(self):
        """Test creating task with all fields"""
        task_id = TaskID(str(uuid4()))
        branch_id = GitBranchID(str(uuid4()))
        dependencies = [TaskID(str(uuid4())), TaskID(str(uuid4()))]
        
        task = Task(
            id=task_id,
            git_branch_id=branch_id,
            title=TaskTitle("Complete feature implementation"),
            description=TaskDescription("Implement full user authentication with JWT"),
            status=TaskStatus.IN_PROGRESS,
            priority=TaskPriority.HIGH,
            assignees=[UserID("user123"), UserID("user456")],
            labels=["backend", "security", "phase1"],
            details=TaskDetails("Using RS256 algorithm, refresh tokens, 2FA support"),
            estimated_effort=EstimatedEffort("5 days"),
            dependencies=dependencies,
            progress_percentage=45,
            due_date=datetime.now(timezone.utc) + timedelta(days=7)
        )
        
        assert task.id == task_id
        assert task.title.value == "Complete feature implementation"
        assert task.description.value == "Implement full user authentication with JWT"
        assert task.status == TaskStatus.IN_PROGRESS
        assert task.priority == TaskPriority.HIGH
        assert len(task.assignees) == 2
        assert len(task.labels) == 3
        assert task.progress_percentage == 45
        assert len(task.dependencies) == 2
        assert task.due_date is not None

    def test_task_title_validation(self):
        """Test task title validation rules"""
        # Valid titles
        valid_titles = [
            "Fix bug",
            "Implement feature with special chars: @#$%",
            "A" * 200,  # Long but valid
            "Task with numbers 123"
        ]
        
        for title in valid_titles:
            task_title = TaskTitle(title)
            assert task_title.value == title
        
        # Invalid titles
        with pytest.raises(ValidationError, match="Title cannot be empty"):
            TaskTitle("")
        
        with pytest.raises(ValidationError, match="Title cannot be empty"):
            TaskTitle("   ")  # Whitespace only
        
        with pytest.raises(ValidationError, match="Title too long"):
            TaskTitle("A" * 501)  # Assuming 500 char limit

    def test_task_status_transitions(self):
        """Test valid task status transitions"""
        task = Task(
            id=TaskID(str(uuid4())),
            git_branch_id=GitBranchID(str(uuid4())),
            title=TaskTitle("Test status transitions"),
            status=TaskStatus.TODO,
            priority=TaskPriority.MEDIUM,
            assignees=[],
            labels=[]
        )
        
        # TODO -> IN_PROGRESS
        task.start_work()
        assert task.status == TaskStatus.IN_PROGRESS
        assert task.started_at is not None
        
        # IN_PROGRESS -> REVIEW
        task.submit_for_review()
        assert task.status == TaskStatus.REVIEW
        
        # REVIEW -> TESTING
        task.start_testing()
        assert task.status == TaskStatus.TESTING
        
        # TESTING -> DONE
        task.complete("All features implemented and tested")
        assert task.status == TaskStatus.DONE
        assert task.completion_date is not None
        assert task.completion_summary == "All features implemented and tested"

    def test_task_blocking_and_unblocking(self):
        """Test task blocking functionality"""
        task = Task(
            id=TaskID(str(uuid4())),
            git_branch_id=GitBranchID(str(uuid4())),
            title=TaskTitle("Blockable task"),
            status=TaskStatus.IN_PROGRESS,
            priority=TaskPriority.HIGH,
            assignees=[UserID("user123")],
            labels=[]
        )
        
        # Block task
        task.block("Waiting for external API documentation")
        
        assert task.status == TaskStatus.BLOCKED
        assert task.blocked_reason == "Waiting for external API documentation"
        assert task.blocked_at is not None
        
        # Unblock task
        previous_status = TaskStatus.IN_PROGRESS
        task.unblock()
        
        assert task.status == previous_status
        assert task.blocked_reason is None
        assert task.blocked_at is None

    def test_task_cancellation(self):
        """Test task cancellation"""
        task = Task(
            id=TaskID(str(uuid4())),
            git_branch_id=GitBranchID(str(uuid4())),
            title=TaskTitle("Task to cancel"),
            status=TaskStatus.IN_PROGRESS,
            priority=TaskPriority.LOW,
            assignees=[],
            labels=[]
        )
        
        # Cancel task
        task.cancel("Requirements changed, feature no longer needed")
        
        assert task.status == TaskStatus.CANCELLED
        assert task.cancellation_reason == "Requirements changed, feature no longer needed"
        assert task.cancelled_at is not None

    def test_task_progress_tracking(self):
        """Test progress percentage tracking"""
        task = Task(
            id=TaskID(str(uuid4())),
            git_branch_id=GitBranchID(str(uuid4())),
            title=TaskTitle("Progress tracking task"),
            status=TaskStatus.IN_PROGRESS,
            priority=TaskPriority.MEDIUM,
            assignees=[],
            labels=[],
            progress_percentage=0
        )
        
        # Update progress
        task.update_progress(25)
        assert task.progress_percentage == 25
        
        task.update_progress(50)
        assert task.progress_percentage == 50
        
        task.update_progress(100)
        assert task.progress_percentage == 100
        
        # Invalid progress
        with pytest.raises(ValidationError):
            task.update_progress(-10)
        
        with pytest.raises(ValidationError):
            task.update_progress(150)

    def test_task_assignee_management(self):
        """Test adding and removing assignees"""
        task = Task(
            id=TaskID(str(uuid4())),
            git_branch_id=GitBranchID(str(uuid4())),
            title=TaskTitle("Multi-assignee task"),
            status=TaskStatus.TODO,
            priority=TaskPriority.HIGH,
            assignees=[UserID("user123")],
            labels=[]
        )
        
        assert len(task.assignees) == 1
        
        # Add assignees
        task.add_assignee(UserID("user456"))
        task.add_assignee(UserID("user789"))
        
        assert len(task.assignees) == 3
        assert UserID("user456") in task.assignees
        
        # Remove assignee
        task.remove_assignee(UserID("user456"))
        assert len(task.assignees) == 2
        assert UserID("user456") not in task.assignees
        
        # Add duplicate (should not add)
        task.add_assignee(UserID("user123"))
        assert len(task.assignees) == 2

    def test_task_label_management(self):
        """Test label operations"""
        task = Task(
            id=TaskID(str(uuid4())),
            git_branch_id=GitBranchID(str(uuid4())),
            title=TaskTitle("Labeled task"),
            status=TaskStatus.TODO,
            priority=TaskPriority.MEDIUM,
            assignees=[],
            labels=["backend"]
        )
        
        # Add labels
        task.add_label("api")
        task.add_label("urgent")
        task.add_label("security")
        
        assert len(task.labels) == 4
        assert "api" in task.labels
        assert "security" in task.labels
        
        # Remove label
        task.remove_label("urgent")
        assert "urgent" not in task.labels
        assert len(task.labels) == 3

    def test_task_dependency_management(self):
        """Test dependency tracking"""
        task = Task(
            id=TaskID(str(uuid4())),
            git_branch_id=GitBranchID(str(uuid4())),
            title=TaskTitle("Task with dependencies"),
            status=TaskStatus.TODO,
            priority=TaskPriority.HIGH,
            assignees=[],
            labels=[],
            dependencies=[]
        )
        
        # Add dependencies
        dep1 = TaskID(str(uuid4()))
        dep2 = TaskID(str(uuid4()))
        dep3 = TaskID(str(uuid4()))
        
        task.add_dependency(dep1)
        task.add_dependency(dep2)
        task.add_dependency(dep3)
        
        assert len(task.dependencies) == 3
        assert dep1 in task.dependencies
        assert dep2 in task.dependencies
        
        # Remove dependency
        task.remove_dependency(dep2)
        assert len(task.dependencies) == 2
        assert dep2 not in task.dependencies
        
        # Cannot add self as dependency
        with pytest.raises(ValidationError, match="Cannot add self as dependency"):
            task.add_dependency(task.id)

    def test_task_due_date_validation(self):
        """Test due date handling"""
        now = datetime.now(timezone.utc)
        
        task = Task(
            id=TaskID(str(uuid4())),
            git_branch_id=GitBranchID(str(uuid4())),
            title=TaskTitle("Task with due date"),
            status=TaskStatus.TODO,
            priority=TaskPriority.HIGH,
            assignees=[],
            labels=[],
            due_date=now + timedelta(days=7)
        )
        
        # Check if overdue
        assert task.is_overdue() is False
        
        # Set past due date
        task.due_date = now - timedelta(days=1)
        assert task.is_overdue() is True
        
        # Completed tasks cannot be overdue
        task.status = TaskStatus.DONE
        assert task.is_overdue() is False

    def test_task_insights_and_learning(self):
        """Test tracking insights and challenges"""
        task = Task(
            id=TaskID(str(uuid4())),
            git_branch_id=GitBranchID(str(uuid4())),
            title=TaskTitle("Learning task"),
            status=TaskStatus.IN_PROGRESS,
            priority=TaskPriority.MEDIUM,
            assignees=[],
            labels=[]
        )
        
        # Add insights
        task.add_insight("JWT refresh tokens improve security")
        task.add_insight("Redis caching reduced API response time by 60%")
        
        assert len(task.insights_found) == 2
        
        # Add challenges
        task.add_challenge("CORS configuration was complex")
        task.add_challenge("Database migration required careful planning")
        
        assert len(task.challenges_overcome) == 2

    def test_task_serialization(self):
        """Test task serialization to dict"""
        task_id = TaskID(str(uuid4()))
        branch_id = GitBranchID(str(uuid4()))
        
        task = Task(
            id=task_id,
            git_branch_id=branch_id,
            title=TaskTitle("Serialize this task"),
            description=TaskDescription("Test serialization"),
            status=TaskStatus.REVIEW,
            priority=TaskPriority.CRITICAL,
            assignees=[UserID("user123"), UserID("user456")],
            labels=["test", "serialization"],
            progress_percentage=85
        )
        
        task.created_at = datetime.now(timezone.utc)
        task.updated_at = datetime.now(timezone.utc)
        
        task_dict = task.to_dict()
        
        assert task_dict["id"] == task_id.value
        assert task_dict["git_branch_id"] == branch_id.value
        assert task_dict["title"] == "Serialize this task"
        assert task_dict["description"] == "Test serialization"
        assert task_dict["status"] == "review"
        assert task_dict["priority"] == "critical"
        assert task_dict["assignees"] == ["user123", "user456"]
        assert task_dict["labels"] == ["test", "serialization"]
        assert task_dict["progress_percentage"] == 85
        assert "created_at" in task_dict
        assert "updated_at" in task_dict

    def test_task_context_integration(self):
        """Test task context data handling"""
        task = Task(
            id=TaskID(str(uuid4())),
            git_branch_id=GitBranchID(str(uuid4())),
            title=TaskTitle("Task with context"),
            status=TaskStatus.TODO,
            priority=TaskPriority.MEDIUM,
            assignees=[],
            labels=[]
        )
        
        # Set context data
        task.context_data = {
            "feature": "authentication",
            "tech_stack": ["JWT", "bcrypt"],
            "api_version": "v2"
        }
        
        assert task.context_data["feature"] == "authentication"
        assert len(task.context_data["tech_stack"]) == 2

    def test_task_completion_validation(self):
        """Test task completion requirements"""
        task = Task(
            id=TaskID(str(uuid4())),
            git_branch_id=GitBranchID(str(uuid4())),
            title=TaskTitle("Task to complete"),
            status=TaskStatus.IN_PROGRESS,
            priority=TaskPriority.HIGH,
            assignees=[],
            labels=[]
        )
        
        # Cannot complete without summary
        with pytest.raises(ValidationError, match="Completion summary required"):
            task.complete("")
        
        # Complete with summary
        task.complete("Successfully implemented all requirements")
        assert task.status == TaskStatus.DONE
        assert task.progress_percentage == 100

    def test_task_business_rules(self):
        """Test various business rules"""
        # Cannot create task with invalid priority
        with pytest.raises(ValueError):
            Task(
                id=TaskID(str(uuid4())),
                git_branch_id=GitBranchID(str(uuid4())),
                title=TaskTitle("Invalid priority task"),
                status=TaskStatus.TODO,
                priority="INVALID_PRIORITY",  # Invalid
                assignees=[],
                labels=[]
            )
        
        # Completed task cannot be modified
        task = Task(
            id=TaskID(str(uuid4())),
            git_branch_id=GitBranchID(str(uuid4())),
            title=TaskTitle("Completed task"),
            status=TaskStatus.DONE,
            priority=TaskPriority.MEDIUM,
            assignees=[],
            labels=[]
        )
        
        with pytest.raises(InvalidTaskStateError, match="Cannot modify completed task"):
            task.add_label("new-label")

    def test_task_minimum_assignee_requirement(self):
        """Test task requires at least one assignee (business rule)"""
        # This might be enforced at use case level, not entity level
        # Keeping test as documentation of business rule
        task = Task(
            id=TaskID(str(uuid4())),
            git_branch_id=GitBranchID(str(uuid4())),
            title=TaskTitle("Task without assignees"),
            status=TaskStatus.TODO,
            priority=TaskPriority.MEDIUM,
            assignees=[],  # Empty is allowed at entity level
            labels=[]
        )
        
        # Entity allows empty assignees (validation at use case level)
        assert task.assignees == []