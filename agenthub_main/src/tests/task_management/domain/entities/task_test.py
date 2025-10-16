"""Test suite for Task entity."""

import pytest
from datetime import datetime, timedelta
from uuid import uuid4

from fastmcp.task_management.domain.entities.task import Task
from fastmcp.task_management.domain.value_objects.task_status import TaskStatus
from fastmcp.task_management.domain.value_objects.priority import Priority
from fastmcp.shared.domain.value_objects import UUID


class TestTaskEntity:
    """Test cases for Task entity."""
    
    @pytest.fixture
    def valid_task_data(self):
        """Provide valid data for creating a task."""
        return {
            "id": UUID.generate(),
            "title": "Test Task",
            "description": "Test Description",
            "status": TaskStatus.TODO,
            "priority": Priority.MEDIUM,
            "details": "Additional details",
            "assignees": ["user1", "user2"],
            "labels": ["backend", "feature"],
            "estimated_effort": "3 hours",
            "due_date": datetime.utcnow() + timedelta(days=7),
            "created_at": datetime.utcnow(),
            "updated_at": datetime.utcnow(),
            "git_branch_id": UUID.generate(),
            "project_id": UUID.generate(),
            "parent_task_id": None,
            "dependencies": [],
            "blocking_tasks": [],
            "subtask_ids": [],
            "subtask_count": 0,
            "context_id": None,
            "completion_summary": None
        }
    
    def test_task_creation_with_valid_data(self, valid_task_data):
        """Test creating a task with all valid data."""
        task = Task(**valid_task_data)
        
        assert task.id == valid_task_data["id"]
        assert task.title == "Test Task"
        assert task.description == "Test Description"
        assert task.status == TaskStatus.TODO
        assert task.priority == Priority.MEDIUM
        assert task.assignees == ["user1", "user2"]
        assert task.labels == ["backend", "feature"]
        assert task.subtask_count == 0
    
    def test_task_creation_with_minimal_data(self):
        """Test creating a task with only required fields."""
        task = Task(
            id=UUID.generate(),
            title="Minimal Task",
            status=TaskStatus.TODO,
            priority=Priority.LOW,
            created_at=datetime.utcnow(),
            updated_at=datetime.utcnow(),
            git_branch_id=UUID.generate(),
            project_id=UUID.generate()
        )
        
        assert task.title == "Minimal Task"
        assert task.description is None
        assert task.details is None
        assert task.assignees == []
        assert task.labels == []
        assert task.estimated_effort is None
        assert task.due_date is None
        assert task.subtask_count == 0
    
    def test_task_with_subtasks(self):
        """Test task with subtasks."""
        subtask_ids = [UUID.generate(), UUID.generate(), UUID.generate()]
        task = Task(
            id=UUID.generate(),
            title="Task with Subtasks",
            status=TaskStatus.IN_PROGRESS,
            priority=Priority.HIGH,
            created_at=datetime.utcnow(),
            updated_at=datetime.utcnow(),
            git_branch_id=UUID.generate(),
            project_id=UUID.generate(),
            subtask_ids=subtask_ids,
            subtask_count=3
        )
        
        assert len(task.subtask_ids) == 3
        assert task.subtask_count == 3
        assert all(isinstance(sid, UUID) for sid in task.subtask_ids)
    
    def test_task_with_dependencies(self):
        """Test task with dependencies and blocking tasks."""
        dep_ids = [UUID.generate(), UUID.generate()]
        blocking_ids = [UUID.generate()]
        
        task = Task(
            id=UUID.generate(),
            title="Task with Dependencies",
            status=TaskStatus.BLOCKED,
            priority=Priority.MEDIUM,
            created_at=datetime.utcnow(),
            updated_at=datetime.utcnow(),
            git_branch_id=UUID.generate(),
            project_id=UUID.generate(),
            dependencies=dep_ids,
            blocking_tasks=blocking_ids
        )
        
        assert len(task.dependencies) == 2
        assert len(task.blocking_tasks) == 1
        assert all(isinstance(d, UUID) for d in task.dependencies)
        assert all(isinstance(b, UUID) for b in task.blocking_tasks)
    
    def test_task_status_values(self):
        """Test all valid task status values."""
        base_data = {
            "id": UUID.generate(),
            "title": "Status Test",
            "priority": Priority.MEDIUM,
            "created_at": datetime.utcnow(),
            "updated_at": datetime.utcnow(),
            "git_branch_id": UUID.generate(),
            "project_id": UUID.generate()
        }
        
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
            task = Task(status=status, **base_data)
            assert task.status == status
    
    def test_task_priority_values(self):
        """Test all valid task priority values."""
        base_data = {
            "id": UUID.generate(),
            "title": "Priority Test",
            "status": TaskStatus.TODO,
            "created_at": datetime.utcnow(),
            "updated_at": datetime.utcnow(),
            "git_branch_id": UUID.generate(),
            "project_id": UUID.generate()
        }
        
        priorities = [
            Priority.LOW,
            Priority.MEDIUM,
            Priority.HIGH,
            Priority.URGENT,
            Priority.CRITICAL
        ]
        
        for priority in priorities:
            task = Task(priority=priority, **base_data)
            assert task.priority == priority
    
    def test_task_completion(self, valid_task_data):
        """Test task completion with summary."""
        valid_task_data["status"] = TaskStatus.DONE
        valid_task_data["completion_summary"] = "Successfully implemented the feature"
        
        task = Task(**valid_task_data)
        
        assert task.status == TaskStatus.DONE
        assert task.completion_summary == "Successfully implemented the feature"
    
    def test_task_with_parent(self):
        """Test creating a subtask with parent reference."""
        parent_id = UUID.generate()
        task = Task(
            id=UUID.generate(),
            title="Subtask",
            status=TaskStatus.TODO,
            priority=Priority.MEDIUM,
            created_at=datetime.utcnow(),
            updated_at=datetime.utcnow(),
            git_branch_id=UUID.generate(),
            project_id=UUID.generate(),
            parent_task_id=parent_id
        )
        
        assert task.parent_task_id == parent_id
    
    def test_task_with_context(self):
        """Test task with associated context."""
        context_id = UUID.generate()
        task = Task(
            id=UUID.generate(),
            title="Task with Context",
            status=TaskStatus.TODO,
            priority=Priority.MEDIUM,
            created_at=datetime.utcnow(),
            updated_at=datetime.utcnow(),
            git_branch_id=UUID.generate(),
            project_id=UUID.generate(),
            context_id=context_id
        )
        
        assert task.context_id == context_id
    
    def test_task_assignees_validation(self):
        """Test that assignees must be a list of strings."""
        task = Task(
            id=UUID.generate(),
            title="Test Task",
            status=TaskStatus.TODO,
            priority=Priority.MEDIUM,
            created_at=datetime.utcnow(),
            updated_at=datetime.utcnow(),
            git_branch_id=UUID.generate(),
            project_id=UUID.generate(),
            assignees=["user1", "user2", "user3"]
        )
        
        assert isinstance(task.assignees, list)
        assert all(isinstance(a, str) for a in task.assignees)
        assert len(task.assignees) == 3
    
    def test_task_labels_handling(self):
        """Test task labels as list of strings."""
        labels = ["frontend", "bug", "urgent", "security"]
        task = Task(
            id=UUID.generate(),
            title="Labeled Task",
            status=TaskStatus.TODO,
            priority=Priority.HIGH,
            created_at=datetime.utcnow(),
            updated_at=datetime.utcnow(),
            git_branch_id=UUID.generate(),
            project_id=UUID.generate(),
            labels=labels
        )
        
        assert task.labels == labels
        assert isinstance(task.labels, list)
        assert all(isinstance(l, str) for l in task.labels)
    
    def test_task_timestamps(self):
        """Test task creation and update timestamps."""
        now = datetime.utcnow()
        later = now + timedelta(hours=1)
        
        task = Task(
            id=UUID.generate(),
            title="Timestamped Task",
            status=TaskStatus.TODO,
            priority=Priority.MEDIUM,
            created_at=now,
            updated_at=later,
            git_branch_id=UUID.generate(),
            project_id=UUID.generate()
        )
        
        assert task.created_at == now
        assert task.updated_at == later
        assert task.updated_at > task.created_at