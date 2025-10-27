"""
Test suite for Subtask domain entity

Tests the subtask entity behavior and validation.
"""

import pytest
from datetime import datetime, timezone
from uuid import uuid4

from fastmcp.task_management.domain.entities.subtask import Subtask
from fastmcp.task_management.domain.value_objects import (
    TaskID,
    SubtaskID,
    TaskStatus,
    TaskPriority,
    UserID
)
from fastmcp.task_management.domain.exceptions import ValidationError


class TestSubtaskEntity:
    """Test suite for Subtask domain entity"""

    def test_create_minimal_subtask(self):
        """Test creating subtask with minimal required fields"""
        parent_task_id = TaskID(str(uuid4()))
        
        subtask = Subtask(
            id=SubtaskID(str(uuid4())),
            task_id=parent_task_id,
            title="Implement login form",
            status=TaskStatus.TODO,
            priority=TaskPriority.MEDIUM,
            assignees=[]
        )
        
        assert subtask.id is not None
        assert subtask.task_id == parent_task_id
        assert subtask.title == "Implement login form"
        assert subtask.status == TaskStatus.TODO
        assert subtask.priority == TaskPriority.MEDIUM
        assert subtask.assignees == []
        assert subtask.description is None
        assert subtask.progress_percentage is None

    def test_create_complete_subtask(self):
        """Test creating subtask with all fields"""
        parent_task_id = TaskID(str(uuid4()))
        
        subtask = Subtask(
            id=SubtaskID(str(uuid4())),
            task_id=parent_task_id,
            title="Add input validation",
            description="Validate email and password fields",
            status=TaskStatus.IN_PROGRESS,
            priority=TaskPriority.HIGH,
            assignees=[UserID("user123"), UserID("user456")],
            labels=["frontend", "validation"],
            progress_percentage=60,
            details="Using zod for schema validation",
            estimated_effort="3 hours",
            progress_notes="Email validation complete, working on password",
            blockers="Waiting for password complexity requirements",
            order=1
        )
        
        assert subtask.title == "Add input validation"
        assert subtask.description == "Validate email and password fields"
        assert subtask.status == TaskStatus.IN_PROGRESS
        assert subtask.priority == TaskPriority.HIGH
        assert len(subtask.assignees) == 2
        assert subtask.labels == ["frontend", "validation"]
        assert subtask.progress_percentage == 60
        assert subtask.details == "Using zod for schema validation"
        assert subtask.estimated_effort == "3 hours"
        assert subtask.blockers == "Waiting for password complexity requirements"
        assert subtask.order == 1

    def test_subtask_status_transitions(self):
        """Test valid status transitions"""
        subtask = Subtask(
            id=SubtaskID(str(uuid4())),
            task_id=TaskID(str(uuid4())),
            title="Test subtask",
            status=TaskStatus.TODO,
            priority=TaskPriority.MEDIUM,
            assignees=[]
        )
        
        # TODO -> IN_PROGRESS
        subtask.status = TaskStatus.IN_PROGRESS
        assert subtask.status == TaskStatus.IN_PROGRESS
        
        # IN_PROGRESS -> REVIEW
        subtask.status = TaskStatus.REVIEW
        assert subtask.status == TaskStatus.REVIEW
        
        # REVIEW -> TESTING
        subtask.status = TaskStatus.TESTING
        assert subtask.status == TaskStatus.TESTING
        
        # TESTING -> DONE
        subtask.status = TaskStatus.DONE
        assert subtask.status == TaskStatus.DONE

    def test_subtask_progress_percentage_validation(self):
        """Test progress percentage validation"""
        subtask = Subtask(
            id=SubtaskID(str(uuid4())),
            task_id=TaskID(str(uuid4())),
            title="Test progress",
            status=TaskStatus.IN_PROGRESS,
            priority=TaskPriority.MEDIUM,
            assignees=[]
        )
        
        # Valid percentages
        for percentage in [0, 25, 50, 75, 100]:
            subtask.progress_percentage = percentage
            assert subtask.progress_percentage == percentage
        
        # Invalid percentages
        with pytest.raises(ValidationError):
            subtask.progress_percentage = -10
        
        with pytest.raises(ValidationError):
            subtask.progress_percentage = 150

    def test_subtask_completion(self):
        """Test marking subtask as complete"""
        subtask = Subtask(
            id=SubtaskID(str(uuid4())),
            task_id=TaskID(str(uuid4())),
            title="Complete this",
            status=TaskStatus.IN_PROGRESS,
            priority=TaskPriority.HIGH,
            assignees=[UserID("user123")],
            progress_percentage=80
        )
        
        # Complete the subtask
        subtask.complete("Successfully implemented feature with tests")
        
        assert subtask.status == TaskStatus.DONE
        assert subtask.progress_percentage == 100
        assert subtask.completion_date is not None
        assert subtask.completion_summary == "Successfully implemented feature with tests"

    def test_subtask_blocking(self):
        """Test blocking and unblocking subtask"""
        subtask = Subtask(
            id=SubtaskID(str(uuid4())),
            task_id=TaskID(str(uuid4())),
            title="Blockable subtask",
            status=TaskStatus.IN_PROGRESS,
            priority=TaskPriority.MEDIUM,
            assignees=[]
        )
        
        # Block subtask
        subtask.block("Waiting for API documentation")
        
        assert subtask.status == TaskStatus.BLOCKED
        assert subtask.blockers == "Waiting for API documentation"
        assert subtask.blocked_at is not None
        
        # Unblock subtask
        subtask.unblock()
        
        assert subtask.status == TaskStatus.IN_PROGRESS  # Returns to previous
        assert subtask.blockers is None
        assert subtask.blocked_at is None

    def test_subtask_insights_tracking(self):
        """Test tracking insights and challenges"""
        subtask = Subtask(
            id=SubtaskID(str(uuid4())),
            task_id=TaskID(str(uuid4())),
            title="Learning subtask",
            status=TaskStatus.IN_PROGRESS,
            priority=TaskPriority.MEDIUM,
            assignees=[]
        )
        
        # Add insights
        subtask.add_insight("React hooks simplify state management")
        subtask.add_insight("useEffect cleanup prevents memory leaks")
        
        assert len(subtask.insights_found) == 2
        assert "React hooks" in subtask.insights_found[0]
        
        # Add challenges
        subtask.add_challenge("TypeScript generics were complex to implement")
        
        assert len(subtask.challenges_overcome) == 1

    def test_subtask_serialization(self):
        """Test subtask serialization to dict"""
        parent_id = TaskID(str(uuid4()))
        subtask = Subtask(
            id=SubtaskID(str(uuid4())),
            task_id=parent_id,
            title="Serialize me",
            description="Test serialization",
            status=TaskStatus.REVIEW,
            priority=TaskPriority.URGENT,
            assignees=[UserID("user123")],
            labels=["test", "serialization"],
            progress_percentage=90
        )
        
        # Add timestamps
        subtask.created_at = datetime.now(timezone.utc)
        subtask.updated_at = datetime.now(timezone.utc)
        
        # Default serialization (without parent_id for nested context)
        data = subtask.to_dict()
        
        assert data["id"] == subtask.id.value
        assert "parent_task_id" not in data  # Phase 2 optimization
        assert data["title"] == "Serialize me"
        assert data["description"] == "Test serialization"
        assert data["status"] == "review"
        assert data["priority"] == "urgent"
        assert data["assignees"] == ["user123"]
        assert data["labels"] == ["test", "serialization"]
        assert data["progress_percentage"] == 90
        
        # Standalone serialization (with parent_id)
        data_standalone = subtask.to_dict(include_parent_id=True)
        assert data_standalone["parent_task_id"] == parent_id.value

    def test_subtask_priority_inheritance(self):
        """Test priority handling and inheritance"""
        # Test all priority levels
        for priority in TaskPriority:
            subtask = Subtask(
                id=SubtaskID(str(uuid4())),
                task_id=TaskID(str(uuid4())),
                title=f"{priority.value} priority subtask",
                status=TaskStatus.TODO,
                priority=priority,
                assignees=[]
            )
            assert subtask.priority == priority

    def test_subtask_assignee_management(self):
        """Test assignee addition and removal"""
        subtask = Subtask(
            id=SubtaskID(str(uuid4())),
            task_id=TaskID(str(uuid4())),
            title="Multi-assignee subtask",
            status=TaskStatus.TODO,
            priority=TaskPriority.MEDIUM,
            assignees=[UserID("user123")]
        )
        
        # Add assignees
        subtask.add_assignee(UserID("user456"))
        subtask.add_assignee(UserID("user789"))
        
        assert len(subtask.assignees) == 3
        assert UserID("user456") in subtask.assignees
        
        # Remove assignee
        subtask.remove_assignee(UserID("user456"))
        assert len(subtask.assignees) == 2
        assert UserID("user456") not in subtask.assignees
        
        # Try to add duplicate
        subtask.add_assignee(UserID("user123"))
        assert len(subtask.assignees) == 2  # No duplicate

    def test_subtask_label_management(self):
        """Test label operations"""
        subtask = Subtask(
            id=SubtaskID(str(uuid4())),
            task_id=TaskID(str(uuid4())),
            title="Labeled subtask",
            status=TaskStatus.TODO,
            priority=TaskPriority.LOW,
            assignees=[],
            labels=["backend"]
        )
        
        # Add labels
        subtask.add_label("api")
        subtask.add_label("urgent")
        
        assert len(subtask.labels) == 3
        assert "api" in subtask.labels
        assert "urgent" in subtask.labels
        
        # Remove label
        subtask.remove_label("backend")
        assert "backend" not in subtask.labels
        assert len(subtask.labels) == 2

    def test_subtask_time_tracking(self):
        """Test time tracking fields"""
        subtask = Subtask(
            id=SubtaskID(str(uuid4())),
            task_id=TaskID(str(uuid4())),
            title="Timed subtask",
            status=TaskStatus.TODO,
            priority=TaskPriority.MEDIUM,
            assignees=[],
            estimated_effort="4 hours"
        )
        
        assert subtask.estimated_effort == "4 hours"
        
        # Start work
        subtask.start_work()
        assert subtask.status == TaskStatus.IN_PROGRESS
        assert subtask.started_at is not None
        
        # Track actual effort
        subtask.actual_effort = "3.5 hours"
        assert subtask.actual_effort == "3.5 hours"

    def test_subtask_ordering(self):
        """Test subtask ordering within task"""
        task_id = TaskID(str(uuid4()))
        
        subtasks = []
        for i in range(5):
            subtask = Subtask(
                id=SubtaskID(str(uuid4())),
                task_id=task_id,
                title=f"Subtask {i}",
                status=TaskStatus.TODO,
                priority=TaskPriority.MEDIUM,
                assignees=[],
                order=i
            )
            subtasks.append(subtask)
        
        # Verify ordering
        for i, subtask in enumerate(subtasks):
            assert subtask.order == i

    def test_subtask_deliverables(self):
        """Test tracking deliverables"""
        subtask = Subtask(
            id=SubtaskID(str(uuid4())),
            task_id=TaskID(str(uuid4())),
            title="Deliverable subtask",
            status=TaskStatus.IN_PROGRESS,
            priority=TaskPriority.HIGH,
            assignees=[]
        )
        
        # Add deliverables
        subtask.add_deliverable("Login component implemented")
        subtask.add_deliverable("Unit tests written")
        subtask.add_deliverable("Documentation updated")
        
        assert len(subtask.deliverables) == 3
        assert "Login component implemented" in subtask.deliverables

    def test_subtask_quality_metrics(self):
        """Test quality tracking"""
        subtask = Subtask(
            id=SubtaskID(str(uuid4())),
            task_id=TaskID(str(uuid4())),
            title="Quality subtask",
            status=TaskStatus.TESTING,
            priority=TaskPriority.HIGH,
            assignees=[]
        )
        
        # Set quality metrics
        subtask.completion_quality = "High - All tests passing, well documented"
        subtask.testing_notes = "100% code coverage, edge cases handled"
        subtask.review_comments = ["Good error handling", "Consider caching"]
        
        assert subtask.completion_quality.startswith("High")
        assert "100% code coverage" in subtask.testing_notes
        assert len(subtask.review_comments) == 2

    def test_subtask_parent_validation(self):
        """Test parent task ID is required and immutable"""
        # Cannot create without parent
        with pytest.raises(TypeError):
            Subtask(
                id=SubtaskID(str(uuid4())),
                # Missing task_id
                title="Orphan subtask",
                status=TaskStatus.TODO,
                priority=TaskPriority.MEDIUM,
                assignees=[]
            )
        
        # Parent ID is set at creation
        parent_id = TaskID(str(uuid4()))
        subtask = Subtask(
            id=SubtaskID(str(uuid4())),
            task_id=parent_id,
            title="Child subtask",
            status=TaskStatus.TODO,
            priority=TaskPriority.MEDIUM,
            assignees=[]
        )
        
        assert subtask.task_id == parent_id