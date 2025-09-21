"""
Tests for Task Repository ORM implementation
"""

import pytest
from unittest.mock import Mock, patch, MagicMock
from datetime import datetime, timedelta
from sqlalchemy.orm import Session
from sqlalchemy.exc import IntegrityError, SQLAlchemyError
from sqlalchemy import func

from fastmcp.task_management.infrastructure.repositories.orm.task_repository import (
    TaskRepository
)
from fastmcp.task_management.infrastructure.orm.models import (
    Task as TaskORM,
    Project as ProjectORM,
    Subtask,
    TaskAssignee,
    TaskDependency,
    TaskContext
)
from fastmcp.task_management.domain.entities import Task as TaskEntity, TaskStatus, TaskPriority


class TestTaskRepository:
    """Test Task Repository functionality"""

    @pytest.fixture
    def mock_session(self):
        """Create mock database session"""
        session = Mock(spec=Session)
        session.query = Mock()
        session.add = Mock()
        session.commit = Mock()
        session.rollback = Mock()
        session.flush = Mock()
        session.refresh = Mock()
        session.execute = Mock()
        return session

    @pytest.fixture
    def repository(self, mock_session):
        """Create repository instance with mock session"""
        return TaskRepository(session=mock_session)

    @pytest.fixture
    def sample_task_orm(self):
        """Create sample task ORM object"""
        task = TaskORM(
            id="task-123",
            title="Implement authentication",
            description="Add JWT authentication",
            status="in_progress",
            priority="high",
            project_id="proj-123",
            git_branch_id="branch-123",
            created_at=datetime.now(),
            updated_at=datetime.now()
        )
        # Add related objects
        task.assignees = [
            TaskAssigneeORM(task_id="task-123", agent_id="coding-agent"),
            TaskAssigneeORM(task_id="task-123", agent_id="@security-auditor-agent")
        ]
        task.subtasks = [
            SubtaskORM(
                id="sub-1",
                task_id="task-123",
                title="Create login endpoint",
                status="done"
            )
        ]
        task.dependencies = []
        task.dependents = []
        return task

    def test_create_task(self, repository, mock_session):
        """Test creating a new task"""
        task = Task(
            id="task-456",
            title="New Feature",
            description="Implement new feature",
            status=TaskStatus.TODO,
            priority=TaskPriority.MEDIUM,
            project_id="proj-123",
            git_branch_id="branch-123",
            assignees=["coding-agent", "@test-agent"]
        )
        
        # Configure mock
        mock_session.query().filter().first.return_value = None  # No conflicts
        
        # Execute
        created = repository.create(task)
        
        # Verify
        assert mock_session.add.called
        assert mock_session.commit.called
        assert created.id == task.id
        assert created.title == task.title
        assert len(created.assignees) == 2

    def test_create_task_with_dependencies(self, repository, mock_session):
        """Test creating task with dependencies"""
        task = Task(
            id="task-789",
            title="Dependent Task",
            description="This task depends on others",
            status=TaskStatus.TODO,
            priority=TaskPriority.HIGH,
            project_id="proj-123",
            git_branch_id="branch-123",
            dependencies=["task-001", "task-002"]
        )
        
        # Configure mock to return existing tasks for dependencies
        existing_tasks = [
            TaskORM(id="task-001"),
            TaskORM(id="task-002")
        ]
        mock_session.query().filter().all.return_value = existing_tasks
        
        # Execute
        created = repository.create(task)
        
        # Verify dependencies were handled
        assert mock_session.add.called
        assert created.dependencies == ["task-001", "task-002"]

    def test_get_task_by_id(self, repository, mock_session, sample_task_orm):
        """Test retrieving task by ID"""
        # Configure mock
        mock_query = Mock()
        mock_query.options().filter().first.return_value = sample_task_orm
        mock_session.query.return_value = mock_query
        
        # Execute
        task = repository.get_by_id("task-123")
        
        # Verify
        assert task is not None
        assert task.id == "task-123"
        assert task.title == "Implement authentication"
        assert len(task.assignees) == 2
        assert "coding-agent" in task.assignees

    def test_get_task_not_found(self, repository, mock_session):
        """Test retrieving non-existent task"""
        # Configure mock
        mock_query = Mock()
        mock_query.options().filter().first.return_value = None
        mock_session.query.return_value = mock_query
        
        # Execute
        task = repository.get_by_id("non-existent")
        
        # Verify
        assert task is None

    def test_update_task(self, repository, mock_session, sample_task_orm):
        """Test updating task"""
        # Configure mock
        mock_query = Mock()
        mock_query.filter().first.return_value = sample_task_orm
        mock_session.query.return_value = mock_query
        
        # Create updated task
        updated_task = Task(
            id="task-123",
            title="Updated Authentication",
            description="Updated description",
            status=TaskStatus.IN_PROGRESS,
            priority=TaskPriority.URGENT,
            project_id="proj-123",
            git_branch_id="branch-123",
            assignees=["coding-agent", "@new-agent"]
        )
        
        # Execute
        result = repository.update(updated_task)
        
        # Verify
        assert mock_session.commit.called
        assert result.title == "Updated Authentication"
        assert result.priority == TaskPriority.URGENT

    def test_update_task_status(self, repository, mock_session, sample_task_orm):
        """Test updating only task status"""
        # Configure mock
        mock_query = Mock()
        mock_query.filter().first.return_value = sample_task_orm
        mock_session.query.return_value = mock_query
        
        # Execute
        result = repository.update_status("task-123", TaskStatus.DONE)
        
        # Verify
        assert sample_task_orm.status == "done"
        assert mock_session.commit.called
        assert result.status == TaskStatus.DONE

    def test_delete_task(self, repository, mock_session, sample_task_orm):
        """Test deleting task"""
        # Configure mock
        mock_query = Mock()
        mock_query.filter().first.return_value = sample_task_orm
        mock_session.query.return_value = mock_query
        
        # Execute
        repository.delete("task-123")
        
        # Verify
        assert mock_session.delete.called_with(sample_task_orm)
        assert mock_session.commit.called

    def test_list_tasks_by_project(self, repository, mock_session):
        """Test listing tasks by project"""
        # Create sample tasks
        tasks = [
            TaskORM(
                id=f"task-{i}",
                title=f"Task {i}",
                project_id="proj-123",
                status="todo" if i % 2 == 0 else "done"
            ) for i in range(5)
        ]
        
        # Configure mock
        mock_query = Mock()
        mock_query.filter().all.return_value = tasks
        mock_session.query.return_value = mock_query
        
        # Execute
        result = repository.list_by_project("proj-123")
        
        # Verify
        assert len(result) == 5
        assert all(isinstance(t, Task) for t in result)
        assert all(t.project_id == "proj-123" for t in result)

    def test_list_tasks_with_filters(self, repository, mock_session):
        """Test listing tasks with multiple filters"""
        # Create filtered tasks
        filtered_tasks = [
            TaskORM(
                id="task-1",
                title="Urgent Task",
                status="in_progress",
                priority="urgent",
                project_id="proj-123"
            )
        ]
        
        # Configure mock with chained filters
        mock_query = Mock()
        mock_filter = Mock()
        mock_query.filter.return_value = mock_filter
        mock_filter.filter.return_value = mock_filter
        mock_filter.all.return_value = filtered_tasks
        mock_session.query.return_value = mock_query
        
        # Execute
        result = repository.list(
            filters={
                "project_id": "proj-123",
                "status": TaskStatus.IN_PROGRESS,
                "priority": TaskPriority.URGENT
            }
        )
        
        # Verify
        assert len(result) == 1
        assert result[0].title == "Urgent Task"

    def test_search_tasks(self, repository, mock_session):
        """Test searching tasks by keyword"""
        matching_tasks = [
            TaskORM(
                id="task-1",
                title="Authentication Implementation",
                description="Implement JWT auth"
            ),
            TaskORM(
                id="task-2",
                title="Fix auth bug",
                description="Authentication not working"
            )
        ]
        
        # Configure mock for search
        mock_query = Mock()
        mock_query.filter().all.return_value = matching_tasks
        mock_session.query.return_value = mock_query
        
        # Execute search
        results = repository.search("auth")
        
        # Verify
        assert len(results) == 2
        assert all("auth" in t.title.lower() or "auth" in t.description.lower() 
                  for t in results)

    def test_get_tasks_by_assignee(self, repository, mock_session):
        """Test getting tasks assigned to specific agent"""
        # Create tasks with assignee
        assigned_tasks = [
            TaskORM(
                id=f"task-{i}",
                title=f"Task {i}",
                assignees=[TaskAssigneeORM(agent_id="coding-agent")]
            ) for i in range(3)
        ]
        
        # Configure mock
        mock_query = Mock()
        mock_query.join().filter().all.return_value = assigned_tasks
        mock_session.query.return_value = mock_query
        
        # Execute
        results = repository.get_by_assignee("coding-agent")
        
        # Verify
        assert len(results) == 3
        assert all("coding-agent" in t.assignees for t in results)

    def test_get_task_dependencies(self, repository, mock_session):
        """Test getting task dependencies"""
        # Create task with dependencies
        task_orm = TaskORM(id="task-main")
        dependency_1 = TaskORM(id="task-dep-1", title="Dependency 1")
        dependency_2 = TaskORM(id="task-dep-2", title="Dependency 2")
        
        task_orm.dependencies = [
            TaskDependencyORM(
                task_id="task-main",
                dependency_id="task-dep-1",
                dependency_task=dependency_1
            ),
            TaskDependencyORM(
                task_id="task-main",
                dependency_id="task-dep-2",
                dependency_task=dependency_2
            )
        ]
        
        # Configure mock
        mock_query = Mock()
        mock_query.options().filter().first.return_value = task_orm
        mock_session.query.return_value = mock_query
        
        # Execute
        dependencies = repository.get_dependencies("task-main")
        
        # Verify
        assert len(dependencies) == 2
        assert dependencies[0].id == "task-dep-1"
        assert dependencies[1].id == "task-dep-2"

    def test_get_task_dependents(self, repository, mock_session):
        """Test getting tasks that depend on a task"""
        # Create task with dependents
        task_orm = TaskORM(id="task-base")
        dependent_1 = TaskORM(id="task-dep-1", title="Dependent 1")
        dependent_2 = TaskORM(id="task-dep-2", title="Dependent 2")
        
        task_orm.dependents = [
            TaskDependencyORM(
                task_id="task-dep-1",
                dependency_id="task-base",
                task=dependent_1
            ),
            TaskDependencyORM(
                task_id="task-dep-2",
                dependency_id="task-base",
                task=dependent_2
            )
        ]
        
        # Configure mock
        mock_query = Mock()
        mock_query.options().filter().first.return_value = task_orm
        mock_session.query.return_value = mock_query
        
        # Execute
        dependents = repository.get_dependents("task-base")
        
        # Verify
        assert len(dependents) == 2
        assert any(d.id == "task-dep-1" for d in dependents)
        assert any(d.id == "task-dep-2" for d in dependents)

    def test_get_overdue_tasks(self, repository, mock_session):
        """Test getting overdue tasks"""
        now = datetime.now()
        overdue_tasks = [
            TaskORM(
                id="task-overdue-1",
                title="Overdue Task 1",
                due_date=now - timedelta(days=2),
                status="in_progress"
            ),
            TaskORM(
                id="task-overdue-2",
                title="Overdue Task 2",
                due_date=now - timedelta(days=1),
                status="todo"
            )
        ]
        
        # Configure mock
        mock_query = Mock()
        mock_query.filter().filter().filter().all.return_value = overdue_tasks
        mock_session.query.return_value = mock_query
        
        # Execute
        results = repository.get_overdue_tasks()
        
        # Verify
        assert len(results) == 2
        assert all(t.due_date < now for t in results)
        assert all(t.status != TaskStatus.DONE for t in results)

    def test_bulk_update_tasks(self, repository, mock_session):
        """Test bulk updating multiple tasks"""
        task_ids = ["task-1", "task-2", "task-3"]
        updates = {"status": "in_progress", "priority": "high"}
        
        # Configure mock
        mock_session.execute = Mock()
        
        # Execute
        updated_count = repository.bulk_update(task_ids, updates)
        
        # Verify
        assert mock_session.execute.called
        assert mock_session.commit.called
        assert updated_count == 3

    def test_get_task_statistics(self, repository, mock_session):
        """Test getting task statistics for a project"""
        # Configure mock for statistics queries
        stats_results = [
            ("todo", 5),
            ("in_progress", 3),
            ("done", 10),
            ("blocked", 2)
        ]
        
        mock_query = Mock()
        mock_query.filter().group_by().all.return_value = stats_results
        mock_session.query.return_value = mock_query
        
        # Execute
        stats = repository.get_project_statistics("proj-123")
        
        # Verify
        assert stats["total"] == 20
        assert stats["todo"] == 5
        assert stats["in_progress"] == 3
        assert stats["done"] == 10
        assert stats["blocked"] == 2
        assert stats["completion_rate"] == 0.5  # 10/20

    def test_cascade_operations(self, repository, mock_session, sample_task_orm):
        """Test cascade operations when deleting task"""
        # Add more related entities
        sample_task_orm.contexts = [
            ContextORM(id="ctx-1", level="task", context_id="task-123")
        ]
        
        # Configure mock
        mock_query = Mock()
        mock_query.filter().first.return_value = sample_task_orm
        mock_session.query.return_value = mock_query
        
        # Execute delete with cascade
        repository.delete("task-123", cascade=True)
        
        # Verify cascade behavior
        assert mock_session.delete.called
        # Related entities would be deleted via SQLAlchemy cascade

    def test_transaction_handling(self, repository, mock_session):
        """Test proper transaction handling on errors"""
        task = Task(
            id="task-error",
            title="Error Task",
            status=TaskStatus.TODO,
            priority=TaskPriority.MEDIUM,
            project_id="proj-123",
            git_branch_id="branch-123"
        )
        
        # Configure mock to raise error
        mock_session.commit.side_effect = SQLAlchemyError("Database error")
        
        # Execute and expect error
        with pytest.raises(SQLAlchemyError):
            repository.create(task)
        
        # Verify rollback was called
        assert mock_session.rollback.called

    def test_performance_optimization_with_pagination(self, repository, mock_session):
        """Test query performance with pagination"""
        # Configure mock for paginated query
        mock_query = Mock()
        paginated_tasks = [TaskORM(id=f"task-{i}") for i in range(10)]
        mock_query.filter().order_by().limit().offset().all.return_value = paginated_tasks
        mock_query.filter().count.return_value = 100  # Total count
        mock_session.query.return_value = mock_query
        
        # Execute paginated query
        results, total = repository.list_paginated(
            filters={"project_id": "proj-123"},
            page=2,
            per_page=10
        )
        
        # Verify
        assert len(results) == 10
        assert total == 100
        assert mock_query.filter().order_by().limit().offset().all.called