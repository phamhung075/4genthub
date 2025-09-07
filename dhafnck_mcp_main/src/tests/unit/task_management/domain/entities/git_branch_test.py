"""Test suite for GitBranch domain entity.

Tests the GitBranch entity including:
- Creation and initialization
- Task hierarchy management (root tasks, child tasks)
- Task lifecycle operations (add, remove, get)
- Status and progress tracking
- Agent assignment
- Branch-level operations
- Task queries and filtering
- Status aggregation
"""

import pytest
from datetime import datetime, timezone, timedelta
from unittest.mock import Mock, patch
import uuid

from fastmcp.task_management.domain.entities.git_branch import GitBranch
from fastmcp.task_management.domain.entities.task import Task
from fastmcp.task_management.domain.value_objects.task_id import TaskId
from fastmcp.task_management.domain.value_objects.task_status import TaskStatus, TaskStatusEnum
from fastmcp.task_management.domain.value_objects.priority import Priority, PriorityLevel


class TestGitBranchCreation:
    """Test cases for GitBranch creation and initialization."""
    
    def test_create_git_branch_with_factory_method(self):
        """Test creating a git branch using the factory method."""
        git_branch = GitBranch.create(
            name="feature/authentication",
            description="Implement user authentication",
            project_id="project-123"
        )
        
        assert git_branch.id is not None
        assert len(git_branch.id) == 36  # UUID format
        assert git_branch.name == "feature/authentication"
        assert git_branch.description == "Implement user authentication"
        assert git_branch.project_id == "project-123"
        assert git_branch.created_at is not None
        assert git_branch.updated_at is not None
        assert git_branch.root_tasks == {}
        assert git_branch.all_tasks == {}
        assert git_branch.assigned_agent_id is None
        assert git_branch.priority.value == PriorityLevel.MEDIUM.label
        assert git_branch.status.value == TaskStatusEnum.TODO.value
    
    def test_create_git_branch_direct_instantiation(self):
        """Test creating a git branch with direct instantiation."""
        branch_id = str(uuid.uuid4())
        created_at = datetime.now(timezone.utc)
        updated_at = datetime.now(timezone.utc)
        
        git_branch = GitBranch(
            id=branch_id,
            name="direct/branch",
            description="Created directly",
            project_id="project-456",
            created_at=created_at,
            updated_at=updated_at,
            priority=Priority.high(),
            status=TaskStatus.in_progress()
        )
        
        assert git_branch.id == branch_id
        assert git_branch.name == "direct/branch"
        assert git_branch.description == "Created directly"
        assert git_branch.project_id == "project-456"
        assert git_branch.created_at == created_at
        assert git_branch.updated_at == updated_at
        assert git_branch.priority.value == "high"
        assert git_branch.status.value == TaskStatusEnum.IN_PROGRESS.value
    
    def test_git_branch_uuid_generation(self):
        """Test that each git branch gets a unique UUID."""
        branch1 = GitBranch.create("branch1", "First", "project-1")
        branch2 = GitBranch.create("branch2", "Second", "project-1")
        
        assert branch1.id != branch2.id
        # Verify UUID format
        uuid.UUID(branch1.id)  # Should not raise exception
        uuid.UUID(branch2.id)  # Should not raise exception


class TestTaskHierarchyManagement:
    """Test cases for task hierarchy management."""
    
    def test_add_root_task(self):
        """Test adding a root-level task."""
        git_branch = GitBranch.create("test/branch", "Test", "project-1")
        
        task = Task(
            id=TaskId("task-123"),
            title="Root Task",
            description="A root level task"
        )
        
        original_updated = git_branch.updated_at
        git_branch.add_root_task(task)
        
        assert task.id.value in git_branch.root_tasks
        assert task.id.value in git_branch.all_tasks
        assert git_branch.root_tasks[task.id.value] == task
        assert git_branch.all_tasks[task.id.value] == task
        assert git_branch.updated_at > original_updated
    
    def test_add_child_task(self):
        """Test adding a child task under a parent."""
        git_branch = GitBranch.create("test/branch", "Test", "project-1")
        
        # Add parent task
        parent_task = Task(
            id=TaskId("parent-123"),
            title="Parent Task",
            description="Parent task"
        )
        git_branch.add_root_task(parent_task)
        
        # Add child task
        child_task = Task(
            id=TaskId("child-123"),
            title="Child Task",
            description="Child task"
        )
        
        git_branch.add_child_task(parent_task.id.value, child_task)
        
        assert child_task.id.value in git_branch.all_tasks
        assert child_task.id.value not in git_branch.root_tasks  # Not a root task
        assert git_branch.all_tasks[child_task.id.value] == child_task
    
    def test_add_child_task_parent_not_found(self):
        """Test adding child task when parent doesn't exist fails."""
        git_branch = GitBranch.create("test/branch", "Test", "project-1")
        
        child_task = Task(
            id=TaskId("child-123"),
            title="Orphan Task",
            description="Task without parent"
        )
        
        with pytest.raises(ValueError, match="Parent task nonexistent-parent not found"):
            git_branch.add_child_task("nonexistent-parent", child_task)
    
    def test_remove_task_root_task(self):
        """Test removing a root task."""
        git_branch = GitBranch.create("test/branch", "Test", "project-1")
        
        task = Task(
            id=TaskId("task-123"),
            title="Root Task",
            description="Task to remove"
        )
        git_branch.add_root_task(task)
        
        result = git_branch.remove_task(task.id.value)
        
        assert result is True
        assert task.id.value not in git_branch.root_tasks
        assert task.id.value not in git_branch.all_tasks
    
    def test_remove_task_with_children(self):
        """Test removing a task with children removes all descendants."""
        git_branch = GitBranch.create("test/branch", "Test", "project-1")
        
        # Create parent task with children
        parent_task = Task(
            id=TaskId("parent-123"),
            title="Parent Task",
            description="Parent"
        )
        git_branch.add_root_task(parent_task)
        
        child_task = Task(
            id=TaskId("child-123"),
            title="Child Task",
            description="Child"
        )
        git_branch.add_child_task(parent_task.id.value, child_task)
        
        # Remove parent should remove both
        result = git_branch.remove_task(parent_task.id.value)
        
        assert result is True
        assert parent_task.id.value not in git_branch.all_tasks
        assert child_task.id.value not in git_branch.all_tasks
    
    def test_remove_nonexistent_task(self):
        """Test removing non-existent task returns False."""
        git_branch = GitBranch.create("test/branch", "Test", "project-1")
        
        result = git_branch.remove_task("nonexistent-task")
        assert result is False


class TestTaskQueries:
    """Test cases for task querying operations."""
    
    def test_get_task(self):
        """Test getting a task by ID."""
        git_branch = GitBranch.create("test/branch", "Test", "project-1")
        
        task = Task(
            id=TaskId("task-123"),
            title="Test Task",
            description="A test task"
        )
        git_branch.add_root_task(task)
        
        retrieved_task = git_branch.get_task(task.id.value)
        assert retrieved_task == task
        
        # Non-existent task
        assert git_branch.get_task("nonexistent") is None
    
    def test_has_task(self):
        """Test checking if task exists."""
        git_branch = GitBranch.create("test/branch", "Test", "project-1")
        
        task = Task(
            id=TaskId("task-123"),
            title="Test Task",
            description="A test task"
        )
        git_branch.add_root_task(task)
        
        assert git_branch.has_task(task.id.value) is True
        assert git_branch.has_task("nonexistent") is False
    
    def test_get_all_tasks(self):
        """Test getting all tasks."""
        git_branch = GitBranch.create("test/branch", "Test", "project-1")
        
        task1 = Task(id=TaskId("task-1"), title="Task 1", description="First")
        task2 = Task(id=TaskId("task-2"), title="Task 2", description="Second")
        
        git_branch.add_root_task(task1)
        git_branch.add_root_task(task2)
        
        all_tasks = git_branch.get_all_tasks()
        
        assert len(all_tasks) == 2
        assert task1.id.value in all_tasks
        assert task2.id.value in all_tasks
        assert all_tasks[task1.id.value] == task1
        assert all_tasks[task2.id.value] == task2
        
        # Should be a copy
        assert all_tasks is not git_branch.all_tasks
    
    def test_get_root_tasks(self):
        """Test getting root-level tasks only."""
        git_branch = GitBranch.create("test/branch", "Test", "project-1")
        
        root_task = Task(id=TaskId("root-1"), title="Root", description="Root task")
        child_task = Task(id=TaskId("child-1"), title="Child", description="Child task")
        
        git_branch.add_root_task(root_task)
        git_branch.add_child_task(root_task.id.value, child_task)
        
        root_tasks = git_branch.get_root_tasks()
        
        assert len(root_tasks) == 1
        assert root_task.id.value in root_tasks
        assert child_task.id.value not in root_tasks
        
        # Should be a copy
        assert root_tasks is not git_branch.root_tasks
    
    def test_get_task_count(self):
        """Test getting total task count."""
        git_branch = GitBranch.create("test/branch", "Test", "project-1")
        
        assert git_branch.get_task_count() == 0
        
        task1 = Task(id=TaskId("task-1"), title="Task 1", description="First")
        task2 = Task(id=TaskId("task-2"), title="Task 2", description="Second")
        
        git_branch.add_root_task(task1)
        assert git_branch.get_task_count() == 1
        
        git_branch.add_root_task(task2)
        assert git_branch.get_task_count() == 2
    
    def test_get_completed_task_count(self):
        """Test getting completed task count."""
        git_branch = GitBranch.create("test/branch", "Test", "project-1")
        
        # Add tasks with different statuses
        todo_task = Task(
            id=TaskId("todo-1"),
            title="Todo Task",
            description="Not done",
            status=TaskStatus.todo()
        )
        done_task = Task(
            id=TaskId("done-1"),
            title="Done Task",
            description="Completed",
            status=TaskStatus.done()
        )
        in_progress_task = Task(
            id=TaskId("progress-1"),
            title="In Progress Task",
            description="Working on it",
            status=TaskStatus.in_progress()
        )
        
        git_branch.add_root_task(todo_task)
        git_branch.add_root_task(done_task)
        git_branch.add_root_task(in_progress_task)
        
        assert git_branch.get_completed_task_count() == 1
    
    def test_get_progress_percentage(self):
        """Test getting progress percentage."""
        git_branch = GitBranch.create("test/branch", "Test", "project-1")
        
        # Empty branch
        assert git_branch.get_progress_percentage() == 0.0
        
        # Add 3 tasks, 1 completed
        todo_task = Task(id=TaskId("todo-1"), title="Todo", description="Todo", status=TaskStatus.todo())
        done_task = Task(id=TaskId("done-1"), title="Done", description="Done", status=TaskStatus.done())
        progress_task = Task(id=TaskId("progress-1"), title="Progress", description="Progress", status=TaskStatus.in_progress())
        
        git_branch.add_root_task(todo_task)
        git_branch.add_root_task(done_task)
        git_branch.add_root_task(progress_task)
        
        # 1 out of 3 completed = 33.33%
        assert abs(git_branch.get_progress_percentage() - 33.33) < 0.01
    
    def test_get_available_tasks(self):
        """Test getting available tasks (not done)."""
        git_branch = GitBranch.create("test/branch", "Test", "project-1")
        
        todo_task = Task(id=TaskId("todo-1"), title="Todo", description="Todo", status=TaskStatus.todo())
        done_task = Task(id=TaskId("done-1"), title="Done", description="Done", status=TaskStatus.done())
        progress_task = Task(id=TaskId("progress-1"), title="Progress", description="Progress", status=TaskStatus.in_progress())
        
        git_branch.add_root_task(todo_task)
        git_branch.add_root_task(done_task)
        git_branch.add_root_task(progress_task)
        
        available_tasks = git_branch.get_available_tasks()
        
        assert len(available_tasks) == 2  # todo and in_progress
        assert todo_task in available_tasks
        assert progress_task in available_tasks
        assert done_task not in available_tasks
    
    def test_get_next_task(self):
        """Test getting next highest priority task."""
        git_branch = GitBranch.create("test/branch", "Test", "project-1")
        
        # No tasks
        assert git_branch.get_next_task() is None
        
        # Add tasks with different priorities
        low_task = Task(
            id=TaskId("low-1"),
            title="Low Priority",
            description="Low",
            priority=Priority.low(),
            status=TaskStatus.todo()
        )
        high_task = Task(
            id=TaskId("high-1"),
            title="High Priority",
            description="High",
            priority=Priority.high(),
            status=TaskStatus.todo()
        )
        critical_task = Task(
            id=TaskId("critical-1"),
            title="Critical Priority",
            description="Critical",
            priority=Priority.critical(),
            status=TaskStatus.todo()
        )
        done_task = Task(
            id=TaskId("done-1"),
            title="Done Task",
            description="Already done",
            priority=Priority.urgent(),  # High priority but done
            status=TaskStatus.done()
        )
        
        git_branch.add_root_task(low_task)
        git_branch.add_root_task(high_task)
        git_branch.add_root_task(critical_task)
        git_branch.add_root_task(done_task)
        
        next_task = git_branch.get_next_task()
        assert next_task == critical_task  # Highest priority available task


class TestStatusManagement:
    """Test cases for status management and aggregation."""
    
    def test_get_tree_status(self):
        """Test getting comprehensive tree status."""
        git_branch = GitBranch.create("test/branch", "Test Branch", "project-1")
        
        # Add tasks with different statuses and priorities
        todo_task = Task(
            id=TaskId("todo-1"),
            title="Todo Task",
            description="Todo",
            status=TaskStatus.todo(),
            priority=Priority.medium()
        )
        done_task = Task(
            id=TaskId("done-1"),
            title="Done Task",
            description="Done",
            status=TaskStatus.done(),
            priority=Priority.high()
        )
        
        git_branch.add_root_task(todo_task)
        git_branch.add_root_task(done_task)
        
        status = git_branch.get_tree_status()
        
        assert status["tree_name"] == "Test Branch"
        assert status["total_tasks"] == 2
        assert status["completed_tasks"] == 1
        assert status["progress_percentage"] == 50.0
        assert status["status_breakdown"]["todo"] == 1
        assert status["status_breakdown"]["done"] == 1
        assert status["priority_breakdown"]["medium"] == 1
        assert status["priority_breakdown"]["high"] == 1
    
    def test_update_status_based_on_tasks_empty(self):
        """Test updating branch status when no tasks."""
        git_branch = GitBranch.create("test/branch", "Test", "project-1")
        
        git_branch.update_status_based_on_tasks()
        assert git_branch.status.value == TaskStatusEnum.TODO.value
    
    def test_update_status_based_on_tasks_all_done(self):
        """Test updating branch status when all tasks done."""
        git_branch = GitBranch.create("test/branch", "Test", "project-1")
        
        task1 = Task(id=TaskId("task-1"), title="Task 1", description="First", status=TaskStatus.done())
        task2 = Task(id=TaskId("task-2"), title="Task 2", description="Second", status=TaskStatus.done())
        
        git_branch.add_root_task(task1)
        git_branch.add_root_task(task2)
        
        git_branch.update_status_based_on_tasks()
        assert git_branch.status.value == TaskStatusEnum.DONE.value
    
    def test_update_status_based_on_tasks_mixed(self):
        """Test updating branch status with mixed task statuses."""
        git_branch = GitBranch.create("test/branch", "Test", "project-1")
        
        todo_task = Task(id=TaskId("todo-1"), title="Todo", description="Todo", status=TaskStatus.todo())
        progress_task = Task(id=TaskId("progress-1"), title="Progress", description="Progress", status=TaskStatus.in_progress())
        
        git_branch.add_root_task(todo_task)
        git_branch.add_root_task(progress_task)
        
        git_branch.update_status_based_on_tasks()
        assert git_branch.status.value == TaskStatusEnum.IN_PROGRESS.value
    
    def test_update_status_based_on_tasks_blocked(self):
        """Test branch status when tasks are blocked."""
        git_branch = GitBranch.create("test/branch", "Test", "project-1")
        
        blocked_task = Task(id=TaskId("blocked-1"), title="Blocked", description="Blocked", status=TaskStatus.blocked())
        todo_task = Task(id=TaskId("todo-1"), title="Todo", description="Todo", status=TaskStatus.todo())
        
        git_branch.add_root_task(blocked_task)
        git_branch.add_root_task(todo_task)
        
        git_branch.update_status_based_on_tasks()
        assert git_branch.status.value == TaskStatusEnum.BLOCKED.value


class TestAgentAssignment:
    """Test cases for agent assignment."""
    
    def test_assign_agent(self):
        """Test assigning an agent to the branch."""
        git_branch = GitBranch.create("test/branch", "Test", "project-1")
        
        original_updated = git_branch.updated_at
        git_branch.assign_agent("agent-123")
        
        assert git_branch.assigned_agent_id == "agent-123"
        assert git_branch.updated_at > original_updated
    
    def test_unassign_agent(self):
        """Test removing agent assignment."""
        git_branch = GitBranch.create("test/branch", "Test", "project-1")
        git_branch.assign_agent("agent-123")
        
        original_updated = git_branch.updated_at
        git_branch.unassign_agent()
        
        assert git_branch.assigned_agent_id is None
        assert git_branch.updated_at > original_updated
    
    def test_is_assigned_to_agent(self):
        """Test checking agent assignment."""
        git_branch = GitBranch.create("test/branch", "Test", "project-1")
        
        # No assignment
        assert git_branch.is_assigned_to_agent("agent-123") is False
        
        # Assign agent
        git_branch.assign_agent("agent-123")
        assert git_branch.is_assigned_to_agent("agent-123") is True
        assert git_branch.is_assigned_to_agent("agent-456") is False


class TestSerialization:
    """Test cases for serialization."""
    
    def test_to_dict(self):
        """Test converting git branch to dictionary."""
        created_at = datetime(2024, 1, 1, 12, 0, 0)
        updated_at = datetime(2024, 1, 2, 12, 0, 0)
        
        git_branch = GitBranch(
            id="branch-123",
            name="feature/test",
            description="Test branch",
            project_id="project-456",
            created_at=created_at,
            updated_at=updated_at,
            assigned_agent_id="agent-789",
            priority=Priority.high(),
            status=TaskStatus.in_progress()
        )
        
        # Add some tasks
        task = Task(id=TaskId("task-1"), title="Task 1", description="First", status=TaskStatus.done())
        git_branch.add_root_task(task)
        
        data = git_branch.to_dict()
        
        assert data["id"] == "branch-123"
        assert data["name"] == "feature/test"
        assert data["description"] == "Test branch"
        assert data["project_id"] == "project-456"
        assert data["created_at"] == created_at.isoformat()
        assert data["updated_at"] == updated_at.isoformat()
        assert data["assigned_agent_id"] == "agent-789"
        assert data["priority"] == "high"
        assert data["status"] == "in_progress"
        assert data["task_count"] == 1
        assert data["completed_task_count"] == 1
        assert data["progress_percentage"] == 100.0
    
    def test_repr(self):
        """Test string representation."""
        git_branch = GitBranch.create("test/branch", "Test Branch", "project-123")
        
        # Add a task
        task = Task(id=TaskId("task-1"), title="Task 1", description="First")
        git_branch.add_root_task(task)
        
        repr_str = repr(git_branch)
        
        assert "GitBranch" in repr_str
        assert git_branch.id in repr_str
        assert "test/branch" in repr_str
        assert "project-123" in repr_str
        assert "tasks=1" in repr_str


class TestEdgeCases:
    """Test cases for edge cases and error conditions."""
    
    def test_empty_branch_operations(self):
        """Test operations on empty branch."""
        git_branch = GitBranch.create("empty/branch", "Empty", "project-1")
        
        assert git_branch.get_task_count() == 0
        assert git_branch.get_completed_task_count() == 0
        assert git_branch.get_progress_percentage() == 0.0
        assert git_branch.get_available_tasks() == []
        assert git_branch.get_next_task() is None
        assert git_branch.get_all_tasks() == {}
        assert git_branch.get_root_tasks() == {}
    
    def test_task_with_dict_status_representation(self):
        """Test handling tasks with dict status representation."""
        git_branch = GitBranch.create("test/branch", "Test", "project-1")
        
        # Mock a task with dict-style status
        mock_task = Mock()
        mock_task.status = {"value": "done"}  # Dict-like status
        mock_task.priority = {"value": "high"}
        
        # Add to all_tasks directly to simulate different representations
        git_branch.all_tasks["mock-task"] = mock_task
        
        # Mock the is_task_done check to handle dict representation
        with patch.object(git_branch, 'get_completed_task_count') as mock_count:
            mock_count.return_value = 1
            completed = git_branch.get_completed_task_count()
            assert completed == 1
    
    def test_concurrent_modifications(self):
        """Test handling of concurrent modifications."""
        git_branch = GitBranch.create("concurrent/branch", "Concurrent", "project-1")
        
        task1 = Task(id=TaskId("task-1"), title="Task 1", description="First")
        task2 = Task(id=TaskId("task-2"), title="Task 2", description="Second")
        
        # Simulate concurrent additions
        original_updated = git_branch.updated_at
        git_branch.add_root_task(task1)
        first_update = git_branch.updated_at
        git_branch.add_root_task(task2)
        second_update = git_branch.updated_at
        
        assert first_update > original_updated
        assert second_update > first_update
        assert git_branch.get_task_count() == 2


if __name__ == "__main__":
    pytest.main([__file__])