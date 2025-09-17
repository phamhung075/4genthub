"""Unit tests for TaskRepository interface."""

import pytest
from typing import List, Optional, Dict, Any
from unittest.mock import Mock, MagicMock
from datetime import datetime, timezone

from fastmcp.task_management.domain.repositories.task_repository import TaskRepository
from fastmcp.task_management.domain.entities.task import Task
from fastmcp.task_management.domain.value_objects.task_id import TaskId
from fastmcp.task_management.domain.value_objects.task_status import TaskStatus
from fastmcp.task_management.domain.value_objects.priority import Priority


class MockTaskRepository(TaskRepository):
    """Mock implementation of TaskRepository for testing."""
    
    def __init__(self):
        self.tasks: Dict[str, Task] = {}
        self.next_id_counter = 1
        
    def save(self, task: Task) -> bool:
        """Save a task."""
        if task.id is None:
            task.id = self.get_next_id()
        self.tasks[task.id.value] = task
        return True
    
    def find_by_id(self, task_id: TaskId) -> Optional[Task]:
        """Find task by ID."""
        return self.tasks.get(task_id.value)
    
    def find_all(self) -> List[Task]:
        """Find all tasks."""
        return list(self.tasks.values())
    
    def find_by_status(self, status: TaskStatus) -> List[Task]:
        """Find tasks by status."""
        return [task for task in self.tasks.values() if task.status.value == status.value]
    
    def find_by_priority(self, priority: Priority) -> List[Task]:
        """Find tasks by priority."""
        return [task for task in self.tasks.values() if task.priority.value == priority.value]
    
    def find_by_assignee(self, assignee: str) -> List[Task]:
        """Find tasks by assignee."""
        return [task for task in self.tasks.values() if assignee in task.assignees]
    
    def find_by_labels(self, labels: List[str]) -> List[Task]:
        """Find tasks containing any of the specified labels."""
        return [
            task for task in self.tasks.values()
            if any(label in task.labels for label in labels)
        ]
    
    def search(self, query: str, limit: int = 10) -> List[Task]:
        """Search tasks by query string."""
        query_lower = query.lower()
        results = []
        for task in self.tasks.values():
            if (query_lower in task.title.lower() or 
                query_lower in task.description.lower() or
                any(query_lower in label.lower() for label in task.labels)):
                results.append(task)
                if len(results) >= limit:
                    break
        return results
    
    def delete(self, task_id: TaskId) -> bool:
        """Delete a task."""
        if task_id.value in self.tasks:
            del self.tasks[task_id.value]
            return True
        return False
    
    def exists(self, task_id: TaskId) -> bool:
        """Check if task exists."""
        return task_id.value in self.tasks
    
    def get_next_id(self) -> TaskId:
        """Get next available task ID."""
        # Generate UUID-like format for consistency
        task_id = TaskId.from_string(f"550e8400-e29b-41d4-a716-{self.next_id_counter:012d}")
        self.next_id_counter += 1
        return task_id
    
    def count(self) -> int:
        """Get total number of tasks."""
        return len(self.tasks)
    
    def get_statistics(self) -> Dict[str, Any]:
        """Get task statistics."""
        status_counts = {}
        priority_counts = {}
        
        for task in self.tasks.values():
            # Count by status
            status = task.status.value
            status_counts[status] = status_counts.get(status, 0) + 1
            
            # Count by priority
            priority = task.priority.value
            priority_counts[priority] = priority_counts.get(priority, 0) + 1
        
        return {
            "total": len(self.tasks),
            "by_status": status_counts,
            "by_priority": priority_counts,
            "with_assignees": sum(1 for task in self.tasks.values() if task.assignees),
            "with_labels": sum(1 for task in self.tasks.values() if task.labels)
        }
    
    def find_by_criteria(self, filters: Dict[str, Any], limit: Optional[int] = None) -> List[Task]:
        """Find tasks by multiple criteria."""
        results = list(self.tasks.values())
        
        # Apply filters
        if 'status' in filters:
            status_value = filters['status'].value if hasattr(filters['status'], 'value') else filters['status']
            results = [t for t in results if t.status.value == status_value]
        
        if 'priority' in filters:
            priority_value = filters['priority'].value if hasattr(filters['priority'], 'value') else filters['priority']
            results = [t for t in results if t.priority.value == priority_value]
        
        if 'assignee' in filters:
            results = [t for t in results if filters['assignee'] in t.assignees]
        
        if 'label' in filters:
            results = [t for t in results if filters['label'] in t.labels]
        
        if 'git_branch_id' in filters:
            results = [t for t in results if t.git_branch_id == filters['git_branch_id']]
        
        # Apply limit if specified
        if limit is not None:
            results = results[:limit]
        
        return results
    
    def find_by_id_all_states(self, task_id: TaskId) -> Optional[Task]:
        """Find task by ID across all states (active, completed, archived)."""
        # In this mock implementation, we don't differentiate between states
        # so this is equivalent to find_by_id
        return self.find_by_id(task_id)


class TestTaskRepositoryInterface:
    
    def setup_method(self, method):
        """Clean up before each test"""
        from fastmcp.task_management.infrastructure.database.database_config import get_db_config
        from sqlalchemy import text
        
        db_config = get_db_config()
        with db_config.get_session() as session:
            # Clean test data but preserve defaults
            try:
                session.execute(text("DELETE FROM tasks WHERE id LIKE 'test-%'"))
                session.execute(text("DELETE FROM projects WHERE id LIKE 'test-%' AND id != 'default_project'"))
                session.commit()
            except:
                session.rollback()

    """Test the TaskRepository interface contract."""
    
    def test_repository_implements_all_abstract_methods(self):
        """Test that MockTaskRepository implements all abstract methods."""
        repo = MockTaskRepository()
        
        # Check all abstract methods are implemented
        assert hasattr(repo, 'save')
        assert hasattr(repo, 'find_by_id')
        assert hasattr(repo, 'find_all')
        assert hasattr(repo, 'find_by_status')
        assert hasattr(repo, 'find_by_priority')
        assert hasattr(repo, 'find_by_assignee')
        assert hasattr(repo, 'find_by_labels')
        assert hasattr(repo, 'search')
        assert hasattr(repo, 'delete')
        assert hasattr(repo, 'exists')
        assert hasattr(repo, 'get_next_id')
        assert hasattr(repo, 'count')
        assert hasattr(repo, 'get_statistics')
        assert hasattr(repo, 'find_by_criteria')
        assert hasattr(repo, 'find_by_id_all_states')
    
    def test_repository_is_abstract(self):
        """Test that TaskRepository cannot be instantiated directly."""
        with pytest.raises(TypeError):
            TaskRepository()


class TestTaskRepositorySaveOperation:
    
    def setup_method(self, method):
        """Clean up before each test"""
        from fastmcp.task_management.infrastructure.database.database_config import get_db_config
        from sqlalchemy import text
        
        db_config = get_db_config()
        with db_config.get_session() as session:
            # Clean test data but preserve defaults
            try:
                session.execute(text("DELETE FROM tasks WHERE id LIKE 'test-%'"))
                session.execute(text("DELETE FROM projects WHERE id LIKE 'test-%' AND id != 'default_project'"))
                session.commit()
            except:
                session.rollback()

    """Test repository save operations."""
    
    def test_save_new_task(self):
        """Test saving a new task."""
        repo = MockTaskRepository()
        task = Task.create(
            id=TaskId.from_string("550e8400-e29b-41d4-a716-446655440001"),
            title="Test Task",
            description="Test Description"
        )
        
        result = repo.save(task)
        assert result is True
        assert repo.count() == 1
        assert repo.exists(task.id)
    
    def test_save_task_without_id(self):
        """Test saving a task without ID auto-generates one."""
        repo = MockTaskRepository()
        task = Task(
            title="Test Task",
            description="Test Description"
        )
        
        result = repo.save(task)
        assert result is True
        assert task.id is not None
        assert repo.exists(task.id)
    
    def test_save_updates_existing_task(self):
        """Test saving an existing task updates it."""
        repo = MockTaskRepository()
        task_id = TaskId.from_string("550e8400-e29b-41d4-a716-446655440001")
        
        # Save initial task
        task = Task.create(
            id=task_id,
            title="Original Title",
            description="Original Description"
        )
        repo.save(task)
        
        # Update and save again
        task.title = "Updated Title"
        repo.save(task)
        
        # Verify update
        assert repo.count() == 1
        saved_task = repo.find_by_id(task_id)
        assert saved_task.title == "Updated Title"


class TestTaskRepositoryFindOperations:
    
    def setup_method(self, method):
        """Clean up before each test"""
        from fastmcp.task_management.infrastructure.database.database_config import get_db_config
        from sqlalchemy import text
        
        db_config = get_db_config()
        with db_config.get_session() as session:
            # Clean test data but preserve defaults
            try:
                session.execute(text("DELETE FROM tasks WHERE id LIKE 'test-%'"))
                session.execute(text("DELETE FROM projects WHERE id LIKE 'test-%' AND id != 'default_project'"))
                session.commit()
            except:
                session.rollback()

    """Test repository find operations."""
    
    @pytest.fixture
    def populated_repo(self):
        """Create a repository with test data."""
        repo = MockTaskRepository()
        
        # Add various tasks
        tasks = [
            Task.create(
                id=TaskId.from_string("550e8400-e29b-41d4-a716-446655440001"),
                title="High Priority Bug",
                description="Fix critical bug in payment system",
                status=TaskStatus.in_progress(),
                priority=Priority.high(),
                assignees=["devops-agent", "coding-agent"],
                labels=["bug", "critical"]
            ),
            Task.create(
                id=TaskId.from_string("550e8400-e29b-41d4-a716-446655440002"),
                title="Feature Request",
                description="Add dark mode to UI",
                status=TaskStatus.todo(),
                priority=Priority.medium(),
                assignees=["@ui_designer_agent"],
                labels=["feature", "ui"]
            ),
            Task.create(
                id=TaskId.from_string("550e8400-e29b-41d4-a716-446655440003"),
                title="Documentation Update",
                description="Update API documentation",
                status=TaskStatus.done(),
                priority=Priority.low(),
                assignees=["documentation-agent"],
                labels=["ai_docs"]
            ),
            Task.create(
                id=TaskId.from_string("550e8400-e29b-41d4-a716-446655440004"),
                title="Performance Optimization",
                description="Optimize database queries",
                status=TaskStatus.in_progress(),
                priority=Priority.high(),
                assignees=["coding-agent"],
                labels=["performance", "backend"]
            ),
            Task.create(
                id=TaskId.from_string("550e8400-e29b-41d4-a716-446655440005"),
                title="Security Audit",
                description="Conduct security review",
                status=TaskStatus.review(),
                priority=Priority.urgent(),
                assignees=["security-auditor-agent"],
                labels=["security", "audit"]
            )
        ]
        
        for task in tasks:
            repo.save(task)
        
        return repo
    
    def test_find_by_id_existing(self, populated_repo):
        """Test finding an existing task by ID."""
        task_id = TaskId.from_string("550e8400-e29b-41d4-a716-446655440001")
        task = populated_repo.find_by_id(task_id)
        
        assert task is not None
        assert task.id == task_id
        assert task.title == "High Priority Bug"
    
    def test_find_by_id_non_existing(self, populated_repo):
        """Test finding a non-existing task by ID returns None."""
        task_id = TaskId.from_string("550e8400-e29b-41d4-a716-446655440099")
        task = populated_repo.find_by_id(task_id)
        
        assert task is None
    
    def test_find_all(self, populated_repo):
        """Test finding all tasks."""
        tasks = populated_repo.find_all()
        
        assert len(tasks) == 5
        assert all(isinstance(task, Task) for task in tasks)
    
    def test_find_by_status(self, populated_repo):
        """Test finding tasks by status."""
        # Find in_progress tasks
        in_progress_tasks = populated_repo.find_by_status(TaskStatus.in_progress())
        assert len(in_progress_tasks) == 2
        assert all(task.status.value == "in_progress" for task in in_progress_tasks)
        
        # Find done tasks
        done_tasks = populated_repo.find_by_status(TaskStatus.done())
        assert len(done_tasks) == 1
        assert done_tasks[0].title == "Documentation Update"
        
        # Find cancelled tasks (should be empty)
        cancelled_tasks = populated_repo.find_by_status(TaskStatus.cancelled())
        assert len(cancelled_tasks) == 0
    
    def test_find_by_priority(self, populated_repo):
        """Test finding tasks by priority."""
        # Find high priority tasks
        high_priority_tasks = populated_repo.find_by_priority(Priority.high())
        assert len(high_priority_tasks) == 2
        assert all(task.priority.value == "high" for task in high_priority_tasks)
        
        # Find urgent priority tasks
        urgent_tasks = populated_repo.find_by_priority(Priority.urgent())
        assert len(urgent_tasks) == 1
        assert urgent_tasks[0].title == "Security Audit"
        
        # Find critical priority tasks (should be empty)
        critical_tasks = populated_repo.find_by_priority(Priority.critical())
        assert len(critical_tasks) == 0
    
    def test_find_by_assignee(self, populated_repo):
        """Test finding tasks by assignee."""
        # Find tasks assigned to coding-agent
        coding_tasks = populated_repo.find_by_assignee("coding-agent")
        assert len(coding_tasks) == 2
        
        # Find tasks assigned to ui_designer_agent
        ui_tasks = populated_repo.find_by_assignee("@ui_designer_agent")
        assert len(ui_tasks) == 1
        assert ui_tasks[0].title == "Feature Request"
        
        # Find tasks assigned to non-existent agent
        no_tasks = populated_repo.find_by_assignee("@non_existent_agent")
        assert len(no_tasks) == 0
    
    def test_find_by_labels(self, populated_repo):
        """Test finding tasks by labels."""
        # Find tasks with 'bug' label
        bug_tasks = populated_repo.find_by_labels(["bug"])
        assert len(bug_tasks) == 1
        assert bug_tasks[0].title == "High Priority Bug"
        
        # Find tasks with multiple labels (OR operation)
        ui_or_docs_tasks = populated_repo.find_by_labels(["ui", "ai_docs"])
        assert len(ui_or_docs_tasks) == 2
        
        # Find tasks with non-existent label
        no_tasks = populated_repo.find_by_labels(["non-existent"])
        assert len(no_tasks) == 0
    
    def test_find_by_id_all_states(self, populated_repo):
        """Test finding task by ID across all states."""
        task_id = TaskId.from_string("550e8400-e29b-41d4-a716-446655440001")
        task = populated_repo.find_by_id_all_states(task_id)
        
        assert task is not None
        assert task.id == task_id
        assert task.title == "High Priority Bug"
    
    def test_find_by_id_all_states_non_existing(self, populated_repo):
        """Test finding a non-existing task by ID across all states returns None."""
        task_id = TaskId.from_string("550e8400-e29b-41d4-a716-446655440099")
        task = populated_repo.find_by_id_all_states(task_id)
        
        assert task is None


class TestTaskRepositorySearchOperation:
    
    def setup_method(self, method):
        """Clean up before each test"""
        from fastmcp.task_management.infrastructure.database.database_config import get_db_config
        from sqlalchemy import text
        
        db_config = get_db_config()
        with db_config.get_session() as session:
            # Clean test data but preserve defaults
            try:
                session.execute(text("DELETE FROM tasks WHERE id LIKE 'test-%'"))
                session.execute(text("DELETE FROM projects WHERE id LIKE 'test-%' AND id != 'default_project'"))
                session.commit()
            except:
                session.rollback()

    """Test repository search operations."""
    
    @pytest.fixture
    def searchable_repo(self):
        """Create a repository with searchable test data."""
        repo = MockTaskRepository()
        
        tasks = [
            Task.create(
                id=TaskId.from_string("550e8400-e29b-41d4-a716-446655440001"),
                title="Fix payment processing bug",
                description="Payment gateway returns 500 error",
                labels=["bug", "payment", "critical"]
            ),
            Task.create(
                id=TaskId.from_string("550e8400-e29b-41d4-a716-446655440002"),
                title="Add payment history feature",
                description="Users should see their payment history",
                labels=["feature", "payment"]
            ),
            Task.create(
                id=TaskId.from_string("550e8400-e29b-41d4-a716-446655440003"),
                title="Update user documentation",
                description="Add section about new features",
                labels=["documentation"]
            ),
            Task.create(
                id=TaskId.from_string("550e8400-e29b-41d4-a716-446655440004"),
                title="Security review",
                description="Review authentication flow",
                labels=["security", "review"]
            )
        ]
        
        for task in tasks:
            repo.save(task)
        
        return repo
    
    def test_search_by_title(self, searchable_repo):
        """Test searching tasks by title."""
        results = searchable_repo.search("payment")
        assert len(results) == 2
        assert all("payment" in task.title.lower() or 
                  "payment" in task.description.lower() or
                  "payment" in task.labels for task in results)
    
    def test_search_by_description(self, searchable_repo):
        """Test searching tasks by description."""
        results = searchable_repo.search("error")
        assert len(results) == 1
        assert results[0].title == "Fix payment processing bug"
    
    def test_search_by_label(self, searchable_repo):
        """Test searching tasks by label."""
        results = searchable_repo.search("security")
        assert len(results) == 1
        assert "security" in results[0].labels
    
    def test_search_case_insensitive(self, searchable_repo):
        """Test search is case insensitive."""
        results_lower = searchable_repo.search("payment")
        results_upper = searchable_repo.search("PAYMENT")
        results_mixed = searchable_repo.search("PayMent")
        
        assert len(results_lower) == len(results_upper) == len(results_mixed) == 2
    
    def test_search_with_limit(self, searchable_repo):
        """Test search respects limit parameter."""
        # Add more tasks to ensure we have more than default limit
        for i in range(15):
            task = Task.create(
                id=TaskId.from_string(f"550e8400-e29b-41d4-a716-4466554400{i+10:02d}"),
                title=f"Task {i}",
                description="Common description for search"
            )
            searchable_repo.save(task)
        
        # Search with default limit
        results_default = searchable_repo.search("description")
        assert len(results_default) == 10
        
        # Search with custom limit
        results_custom = searchable_repo.search("description", limit=5)
        assert len(results_custom) == 5
    
    def test_search_no_results(self, searchable_repo):
        """Test search with no matching results."""
        results = searchable_repo.search("nonexistent")
        assert len(results) == 0


class TestTaskRepositoryDeleteOperation:
    
    def setup_method(self, method):
        """Clean up before each test"""
        from fastmcp.task_management.infrastructure.database.database_config import get_db_config
        from sqlalchemy import text
        
        db_config = get_db_config()
        with db_config.get_session() as session:
            # Clean test data but preserve defaults
            try:
                session.execute(text("DELETE FROM tasks WHERE id LIKE 'test-%'"))
                session.execute(text("DELETE FROM projects WHERE id LIKE 'test-%' AND id != 'default_project'"))
                session.commit()
            except:
                session.rollback()

    """Test repository delete operations."""
    
    def test_delete_existing_task(self):
        """Test deleting an existing task."""
        repo = MockTaskRepository()
        task_id = TaskId.from_string("550e8400-e29b-41d4-a716-446655440001")
        
        task = Task.create(
            id=task_id,
            title="Task to Delete",
            description="This will be deleted"
        )
        repo.save(task)
        
        # Verify task exists
        assert repo.exists(task_id)
        assert repo.count() == 1
        
        # Delete task
        result = repo.delete(task_id)
        assert result is True
        assert not repo.exists(task_id)
        assert repo.count() == 0
    
    def test_delete_non_existing_task(self):
        """Test deleting a non-existing task returns False."""
        repo = MockTaskRepository()
        task_id = TaskId.from_string("550e8400-e29b-41d4-a716-446655440001")
        
        result = repo.delete(task_id)
        assert result is False


class TestTaskRepositoryUtilityOperations:
    
    def setup_method(self, method):
        """Clean up before each test"""
        from fastmcp.task_management.infrastructure.database.database_config import get_db_config
        from sqlalchemy import text
        
        db_config = get_db_config()
        with db_config.get_session() as session:
            # Clean test data but preserve defaults
            try:
                session.execute(text("DELETE FROM tasks WHERE id LIKE 'test-%'"))
                session.execute(text("DELETE FROM projects WHERE id LIKE 'test-%' AND id != 'default_project'"))
                session.commit()
            except:
                session.rollback()

    """Test repository utility operations."""
    
    def test_exists_for_existing_task(self):
        """Test exists returns True for existing task."""
        repo = MockTaskRepository()
        task_id = TaskId.from_string("550e8400-e29b-41d4-a716-446655440001")
        
        task = Task.create(
            id=task_id,
            title="Existing Task",
            description="This exists"
        )
        repo.save(task)
        
        assert repo.exists(task_id) is True
    
    def test_exists_for_non_existing_task(self):
        """Test exists returns False for non-existing task."""
        repo = MockTaskRepository()
        task_id = TaskId.from_string("550e8400-e29b-41d4-a716-446655440001")
        
        assert repo.exists(task_id) is False
    
    def test_get_next_id_generates_unique_ids(self):
        """Test get_next_id generates unique IDs."""
        repo = MockTaskRepository()
        
        ids = []
        for _ in range(10):
            new_id = repo.get_next_id()
            assert isinstance(new_id, TaskId)
            assert new_id not in ids
            ids.append(new_id)
    
    def test_count_empty_repository(self):
        """Test count returns 0 for empty repository."""
        repo = MockTaskRepository()
        assert repo.count() == 0
    
    def test_count_with_tasks(self):
        """Test count returns correct number of tasks."""
        repo = MockTaskRepository()
        
        for i in range(5):
            task = Task.create(
                id=TaskId.from_string(f"550e8400-e29b-41d4-a716-4466554400{i+1:02d}"),
                title=f"Task {i+1}",
                description="Test task"
            )
            repo.save(task)
        
        assert repo.count() == 5
    
    def test_get_statistics_empty_repository(self):
        """Test statistics for empty repository."""
        repo = MockTaskRepository()
        stats = repo.get_statistics()
        
        assert stats["total"] == 0
        assert stats["by_status"] == {}
        assert stats["by_priority"] == {}
        assert stats["with_assignees"] == 0
        assert stats["with_labels"] == 0
    
    def test_get_statistics_with_tasks(self):
        """Test statistics for repository with tasks."""
        repo = MockTaskRepository()
        
        # Add tasks with various attributes
        tasks = [
            Task.create(
                id=TaskId.from_string("550e8400-e29b-41d4-a716-446655440001"),
                title="Task 1",
                description="Test",
                status=TaskStatus.todo(),
                priority=Priority.high(),
                assignees=["@agent1"],
                labels=["bug"]
            ),
            Task.create(
                id=TaskId.from_string("550e8400-e29b-41d4-a716-446655440002"),
                title="Task 2",
                description="Test",
                status=TaskStatus.in_progress(),
                priority=Priority.high(),
                assignees=["@agent1", "@agent2"],
                labels=[]
            ),
            Task.create(
                id=TaskId.from_string("550e8400-e29b-41d4-a716-446655440003"),
                title="Task 3",
                description="Test",
                status=TaskStatus.done(),
                priority=Priority.medium(),
                assignees=[],
                labels=["feature", "ui"]
            ),
            Task.create(
                id=TaskId.from_string("550e8400-e29b-41d4-a716-446655440004"),
                title="Task 4",
                description="Test",
                status=TaskStatus.todo(),
                priority=Priority.low(),
                assignees=["@agent3"],
                labels=[]
            )
        ]
        
        for task in tasks:
            repo.save(task)
        
        stats = repo.get_statistics()
        
        assert stats["total"] == 4
        assert stats["by_status"]["todo"] == 2
        assert stats["by_status"]["in_progress"] == 1
        assert stats["by_status"]["done"] == 1
        assert stats["by_priority"]["high"] == 2
        assert stats["by_priority"]["medium"] == 1
        assert stats["by_priority"]["low"] == 1
        assert stats["with_assignees"] == 3
        assert stats["with_labels"] == 2


class TestTaskRepositoryIntegration:
    
    def setup_method(self, method):
        """Clean up before each test"""
        from fastmcp.task_management.infrastructure.database.database_config import get_db_config
        from sqlalchemy import text
        
        db_config = get_db_config()
        with db_config.get_session() as session:
            # Clean test data but preserve defaults
            try:
                session.execute(text("DELETE FROM tasks WHERE id LIKE 'test-%'"))
                session.execute(text("DELETE FROM projects WHERE id LIKE 'test-%' AND id != 'default_project'"))
                session.commit()
            except:
                session.rollback()

    """Test repository integration scenarios."""
    
    def test_complete_task_lifecycle(self):
        """Test complete task lifecycle through repository."""
        repo = MockTaskRepository()
        
        # Create and save new task
        task = Task(
            title="Implement feature",
            description="Add new functionality"
        )
        repo.save(task)
        task_id = task.id
        
        # Verify task was saved
        assert repo.exists(task_id)
        saved_task = repo.find_by_id(task_id)
        assert saved_task.title == "Implement feature"
        
        # Update task
        saved_task.update_status(TaskStatus.in_progress())
        saved_task.update_priority(Priority.high())
        saved_task.assignees = ["coding-agent"]
        saved_task.labels = ["feature", "backend"]
        repo.save(saved_task)
        
        # Verify updates
        updated_task = repo.find_by_id(task_id)
        assert updated_task.status.value == "in_progress"
        assert updated_task.priority.value == "high"
        assert "coding-agent" in updated_task.assignees
        
        # Search for task
        search_results = repo.search("feature")
        assert len(search_results) == 1
        assert search_results[0].id == task_id
        
        # Find by various criteria
        assert len(repo.find_by_status(TaskStatus.in_progress())) == 1
        assert len(repo.find_by_priority(Priority.high())) == 1
        assert len(repo.find_by_assignee("coding-agent")) == 1
        assert len(repo.find_by_labels(["backend"])) == 1
        
        # Get statistics
        stats = repo.get_statistics()
        assert stats["total"] == 1
        assert stats["by_status"]["in_progress"] == 1
        
        # Delete task
        assert repo.delete(task_id) is True
        assert not repo.exists(task_id)
        assert repo.count() == 0
    
    def test_repository_isolation(self):
        """Test that repository operations don't affect each other."""
        repo1 = MockTaskRepository()
        repo2 = MockTaskRepository()
        
        # Add task to repo1
        task = Task.create(
            id=TaskId.from_string("550e8400-e29b-41d4-a716-446655440001"),
            title="Task in Repo 1",
            description="Test"
        )
        repo1.save(task)
        
        # Verify isolation
        assert repo1.count() == 1
        assert repo2.count() == 0
        assert repo1.exists(task.id)
        assert not repo2.exists(task.id)