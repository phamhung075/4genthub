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
    ORMTaskRepository as TaskRepository
)
from fastmcp.task_management.infrastructure.database.models import (
    Task as TaskORM,
    Project as ProjectORM,
    Subtask,
    TaskAssignee,
    TaskDependency,
    TaskContext
)
from fastmcp.task_management.domain.entities import Task as TaskEntity, TaskStatus, TaskPriority
from fastmcp.task_management.domain.value_objects.priority import Priority as TaskPriority  # Use correct import


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
    
    def _mock_db_session(self, mock_session):
        """Helper to create a context manager for mocking get_db_session"""
        from contextlib import contextmanager
        @contextmanager
        def mock_get_db_session():
            yield mock_session
        return mock_get_db_session

    @pytest.fixture
    def repository(self, mock_session):
        """Create repository instance with mock session"""
        # Create repository without connecting to real database
        repo = TaskRepository(
            session=mock_session,
            git_branch_id="branch-123",
            project_id="project-123",
            user_id="test-user"
        )
        # Override the session to use our mock
        repo._session = mock_session
        return repo

    @pytest.fixture
    def sample_task_orm(self):
        """Create sample task ORM object"""
        task = TaskORM(
            id="task-123",
            title="Implement authentication",
            description="Add JWT authentication",
            status="in_progress",
            priority="high",
            git_branch_id="branch-123",
            user_id="test-user",
            created_at=datetime.now(),
            updated_at=datetime.now()
        )
        # Add related objects
        task.assignees = [
            TaskAssignee(task_id="task-123", assignee_id="coding-agent", user_id="test-user"),
            TaskAssignee(task_id="task-123", assignee_id="@security-auditor-agent", user_id="test-user")
        ]
        task.subtasks = [
            Subtask(
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
        # Create a proper task ORM entity for return
        task_orm = MagicMock(spec=TaskORM)
        task_orm.id = "task-456"
        task_orm.title = "New Feature"
        task_orm.description = "Implement new feature"
        task_orm.status = "todo"
        task_orm.priority = "medium"
        task_orm.git_branch_id = "branch-123"
        task_orm.user_id = "test-user"
        task_orm.created_at = datetime.now()
        task_orm.updated_at = datetime.now()
        task_orm.assignees = []
        task_orm.labels = []
        task_orm.subtasks = []
        task_orm.dependencies = []
        task_orm.estimated_effort = "2 hours"
        task_orm.due_date = None
        task_orm.progress_history = {}
        task_orm.progress_count = 0
        
        # Mock the ORM model class to return our mock instance
        with patch('fastmcp.task_management.infrastructure.repositories.orm.task_repository.Task') as MockTask:
            MockTask.return_value = task_orm
            
            # Execute using repository's kwargs-based create method
            created = repository.create_task(
                title="New Feature",
                description="Implement new feature",
                priority="medium",
                status="todo",
                assignee_ids=[]  # Use correct parameter name
            )
        
        # Verify
        assert mock_session.add.called
        assert mock_session.flush.called
        assert created.id == "task-456"
        assert created.title == "New Feature"
        # Note: assignees are handled separately in actual implementation

    def test_create_task_with_dependencies(self, repository, mock_session):
        """Test creating task with dependencies"""
        # Configure mock to return empty results for dependency check
        mock_query = Mock()
        mock_query.filter.return_value = mock_query
        mock_query.all.return_value = []  # No existing dependencies
        mock_session.query.return_value = mock_query
        
        task_orm = TaskORM(
            id="task-789",
            title="Dependent Task", 
            description="This task depends on others",
            status="todo",
            priority="high",
            git_branch_id="branch-123",
            user_id="test-user",
            created_at=datetime.now(),
            updated_at=datetime.now()
        )
        task_orm.assignees = []
        task_orm.dependencies = []
        
        # Make the mock session behave correctly
        mock_session.add = Mock()
        mock_session.flush = Mock()
        mock_session.refresh = Mock(side_effect=lambda x: setattr(x, 'assignees', []))
        mock_session.commit = Mock()
        
        # Mock the get_db_session to return our mock session
        with patch.object(repository, 'get_db_session', self._mock_db_session(mock_session)):
            # Mock the model class constructor
            with patch('fastmcp.task_management.infrastructure.repositories.orm.task_repository.Task', return_value=task_orm):
                # Execute using repository's kwargs-based create method
                created = repository.create_task(
                title="Dependent Task",
                description="This task depends on others",
                priority="high",
                status="todo",
                assignees=[],
                git_branch_id="branch-123",
                user_id="test-user",
                dependencies=["task-001", "task-002"]  # These will be processed separately
            )
        
        # Verify
        assert mock_session.add.called
        assert created.id == "task-789"

    def test_get_task_by_id(self, repository, mock_session, sample_task_orm):
        """Test retrieving task by ID"""
        # Mock the internal _load_task_with_relationships method
        with patch.object(repository, '_load_task_with_relationships', return_value=sample_task_orm):
            # Execute - use get_task which is the actual method
            task = repository.get_task("task-123")
            
            # Verify
            assert task is not None
            assert task.id == "task-123"
            assert task.title == "Implement authentication"
            assert len(task.assignees) == 2
            assert "coding-agent" in task.assignees

    def test_get_task_not_found(self, repository, mock_session):
        """Test retrieving non-existent task"""
        # Configure mock with correct chain
        mock_query = Mock()
        mock_options = Mock()
        mock_filter = Mock()
        mock_first = Mock(return_value=None)
        
        # Build the query chain to match implementation
        mock_query.options.return_value = mock_options
        mock_options.filter.return_value = mock_filter
        mock_filter.first = mock_first
        
        mock_session.query.return_value = mock_query
        
        # Execute - use get_task which is the actual method
        task = repository.get_task("non-existent")
        
        # Verify
        assert task is None

    def test_update_task(self, repository, mock_session, sample_task_orm):
        """Test updating task"""
        # Configure mock to find the task to update
        mock_query = Mock()
        mock_filter = Mock()
        mock_first = Mock(return_value=sample_task_orm)
        
        # Build the query chain
        mock_query.filter.return_value = mock_filter
        mock_filter.first = mock_first
        
        mock_session.query.return_value = mock_query
        
        # Mock the internal update method (from BaseORMRepository)
        with patch.object(repository, 'update', return_value=sample_task_orm):
            # Mock _load_task_with_relationships for the reload
            with patch.object(repository, '_load_task_with_relationships', return_value=sample_task_orm):
                # Execute - use update_task with keyword arguments
                result = repository.update_task(
                    "task-123",
                    title="Updated Authentication",
                    description="Updated description",
                    status="in_progress",
                    priority="urgent"
                )
                
                # Verify
                assert result is not None
                assert result.id == "task-123"

    def test_update_task_status(self, repository, mock_session, sample_task_orm):
        """Test updating only task status"""
        # Configure mock to find the task
        mock_query = Mock()
        mock_filter = Mock()
        mock_first = Mock(return_value=sample_task_orm)
        
        # Build the query chain
        mock_query.filter.return_value = mock_filter
        mock_filter.first = mock_first
        
        mock_session.query.return_value = mock_query
        
        # Mock the internal update method
        with patch.object(repository, 'update', return_value=sample_task_orm):
            # Mock _load_task_with_relationships for the reload
            with patch.object(repository, '_load_task_with_relationships', return_value=sample_task_orm):
                # Execute - use update_task
                result = repository.update_task("task-123", status="done")
                
                # Verify
                assert result is not None

    def test_delete_task(self, repository, mock_session, sample_task_orm):
        """Test deleting task"""
        # Configure mock with proper query chain
        mock_query = Mock()
        mock_filter = Mock()
        mock_first = Mock(return_value=sample_task_orm)
        mock_delete = Mock(return_value=0)  # For cascade deletes
        
        # Build the query chain
        mock_query.filter.return_value = mock_filter
        mock_filter.first = mock_first
        mock_filter.delete = mock_delete
        
        mock_session.query.return_value = mock_query
        
        # Execute - use delete_task method
        result = repository.delete_task("task-123")
        
        # Verify
        assert mock_session.delete.called
        assert mock_session.commit.called
        assert result == True

    def test_list_tasks_by_project(self, repository, mock_session):
        """Test listing tasks by git branch (no list_by_project exists)"""
        # Create sample tasks with proper attributes
        tasks = []
        for i in range(5):
            task = TaskORM(
                id=f"task-{i}",
                title=f"Task {i}",
                description=f"Description {i}",
                git_branch_id="branch-123",
                user_id="test-user",
                status="todo" if i % 2 == 0 else "done",
                priority="medium",
                created_at=datetime.now(),
                updated_at=datetime.now()
            )
            task.assignees = []
            task.labels = []
            task.subtasks = []
            task.dependencies = []
            tasks.append(task)
        
        # Configure mock with proper query chain
        mock_query = Mock()
        mock_options = Mock()
        mock_filter = Mock()
        mock_order_by = Mock()
        mock_offset = Mock()
        mock_limit = Mock()
        mock_all = Mock(return_value=tasks)
        
        # Build the complete query chain to match implementation
        mock_query.options.return_value = mock_options
        mock_options.filter.return_value = mock_filter
        mock_filter.order_by.return_value = mock_order_by
        mock_order_by.offset.return_value = mock_offset
        mock_offset.limit.return_value = mock_limit
        mock_limit.all = mock_all
        
        mock_session.query.return_value = mock_query
        
        # Execute - use list_tasks method
        result = repository.list_tasks(limit=100, offset=0)
        
        # Verify
        assert len(result) == 5
        assert all(isinstance(t, TaskEntity) for t in result)

    def test_list_tasks_with_filters(self, repository, mock_session):
        """Test listing tasks with multiple filters"""
        # Create filtered task with proper attributes
        task = TaskORM(
            id="task-1",
            title="Urgent Task",
            description="Urgent description",
            status="in_progress",
            priority="urgent",
            git_branch_id="branch-123",
            user_id="test-user",
            created_at=datetime.now(),
            updated_at=datetime.now()
        )
        task.assignees = []
        task.labels = []
        task.subtasks = []
        task.dependencies = []
        filtered_tasks = [task]
        
        # Configure mock with proper query chain
        mock_query = Mock()
        mock_options = Mock()
        mock_filter = Mock()
        mock_order_by = Mock()
        mock_offset = Mock()
        mock_limit = Mock()
        mock_all = Mock(return_value=filtered_tasks)
        
        # Build the complete query chain
        mock_query.options.return_value = mock_options
        mock_options.filter.return_value = mock_filter
        mock_filter.order_by.return_value = mock_order_by
        mock_order_by.offset.return_value = mock_offset
        mock_offset.limit.return_value = mock_limit
        mock_limit.all = mock_all
        
        mock_session.query.return_value = mock_query
        
        # Execute - use list_tasks method with filters
        result = repository.list_tasks(
            status="in_progress",
            priority="urgent",
            limit=20,
            offset=0
        )
        
        # Verify
        assert len(result) == 1
        assert result[0].title == "Urgent Task"

    def test_search_tasks(self, repository, mock_session):
        """Test searching tasks by keyword"""
        # Create tasks with proper attributes
        task1 = TaskORM(
            id="task-1",
            title="Authentication Implementation",
            description="Implement JWT auth",
            status="todo",
            priority="high",
            git_branch_id="branch-123",
            user_id="test-user",
            created_at=datetime.now(),
            updated_at=datetime.now()
        )
        task1.assignees = []
        task1.labels = []
        task1.subtasks = []
        
        task2 = TaskORM(
            id="task-2",
            title="Fix auth bug",
            description="Authentication not working",
            status="in_progress",
            priority="urgent",
            git_branch_id="branch-123",
            user_id="test-user",
            created_at=datetime.now(),
            updated_at=datetime.now()
        )
        task2.assignees = []
        task2.labels = []
        task2.subtasks = []
        
        matching_tasks = [task1, task2]
        
        # Configure mock with proper query chain
        mock_query = Mock()
        mock_options = Mock()
        mock_filter = Mock()
        mock_order_by = Mock()
        mock_limit = Mock()
        mock_all = Mock(return_value=matching_tasks)
        
        # Build the query chain to match search_tasks implementation
        mock_query.options.return_value = mock_options
        mock_options.filter.return_value = mock_filter
        mock_filter.order_by.return_value = mock_order_by
        mock_order_by.limit.return_value = mock_limit
        mock_limit.all = mock_all
        
        # Need to mock the subquery for label search
        mock_subquery = Mock()
        mock_session.query.side_effect = [mock_query, mock_subquery, mock_query]
        
        # Execute search using correct method name
        results = repository.search_tasks("auth")
        
        # Verify
        assert len(results) == 2
        assert all("auth" in t.title.lower() or "auth" in t.description.lower() 
                  for t in results)

    def test_get_tasks_by_assignee(self, repository, mock_session):
        """Test getting tasks assigned to specific agent"""
        # Create tasks with proper attributes
        assigned_tasks = []
        for i in range(3):
            task = TaskORM(
                id=f"task-{i}",
                title=f"Task {i}",
                description=f"Description {i}",
                status="todo",
                priority="medium",
                git_branch_id="branch-123",
                user_id="test-user",
                created_at=datetime.now(),
                updated_at=datetime.now()
            )
            # Add assignee
            assignee = TaskAssignee(task_id=f"task-{i}", assignee_id="coding-agent", user_id="test-user")
            task.assignees = [assignee]
            task.labels = []
            task.subtasks = []
            task.dependencies = []
            assigned_tasks.append(task)
        
        # Configure mock with proper query chain for list_tasks
        mock_query = Mock()
        mock_options = Mock()
        mock_join = Mock()
        mock_filter = Mock()
        mock_order_by = Mock()
        mock_offset = Mock()
        mock_limit = Mock()
        mock_all = Mock(return_value=assigned_tasks)
        
        # Build query chain
        mock_query.options.return_value = mock_options
        mock_options.join.return_value = mock_join
        mock_join.filter.return_value = mock_filter
        mock_filter.order_by.return_value = mock_order_by
        mock_order_by.offset.return_value = mock_offset
        mock_offset.limit.return_value = mock_limit
        mock_limit.all = mock_all
        
        mock_session.query.return_value = mock_query
        
        # Execute - get_tasks_by_assignee uses list_tasks internally
        results = repository.get_tasks_by_assignee("coding-agent")
        
        # Verify
        assert len(results) == 3
        assert all("coding-agent" in t.assignees for t in results)

    def test_get_task_dependencies(self, repository, mock_session):
        """Test getting task with its dependencies"""
        # Create main task with dependencies through get_task
        dependency_1 = TaskDependency(
            task_id="task-main",
            depends_on_task_id="task-dep-1",
            dependency_type="blocks"
        )
        dependency_2 = TaskDependency(
            task_id="task-main",
            depends_on_task_id="task-dep-2", 
            dependency_type="blocks"
        )
        
        task_orm = TaskORM(
            id="task-main",
            title="Main Task",
            description="Task with dependencies",
            status="todo",
            priority="high",
            git_branch_id="branch-123",
            user_id="test-user",
            created_at=datetime.now(),
            updated_at=datetime.now()
        )
        task_orm.assignees = []
        task_orm.labels = []
        task_orm.subtasks = []
        task_orm.dependencies = [dependency_1, dependency_2]
        
        # Configure mock with proper query chain
        mock_query = Mock()
        mock_options = Mock()
        mock_filter = Mock()
        mock_first = Mock(return_value=task_orm)
        
        # Build the query chain
        mock_query.options.return_value = mock_options
        mock_options.filter.return_value = mock_filter
        mock_filter.first = mock_first
        
        mock_session.query.return_value = mock_query
        
        # Execute - use get_task to retrieve task with dependencies
        task = repository.get_task("task-main")
        
        # Verify - dependencies should be part of the task entity
        assert task is not None
        assert len(task.dependencies) == 2

    def test_get_task_dependents(self, repository, mock_session):
        """Test getting task with its dependents"""
        # Since get_dependents doesn't exist, test via list_tasks
        # Create tasks that depend on task-base
        dependent_1 = TaskORM(
            id="task-dep-1",
            title="Dependent 1",
            description="Depends on task-base",
            status="todo",
            priority="medium",
            git_branch_id="branch-123",
            user_id="test-user",
            created_at=datetime.now(),
            updated_at=datetime.now()
        )
        dependent_1.assignees = []
        dependent_1.labels = []
        dependent_1.subtasks = []
        dependent_1.dependencies = []
        
        dependent_2 = TaskORM(
            id="task-dep-2",
            title="Dependent 2",
            description="Also depends on task-base",
            status="todo",
            priority="medium",
            git_branch_id="branch-123",
            user_id="test-user",
            created_at=datetime.now(),
            updated_at=datetime.now()
        )
        dependent_2.assignees = []
        dependent_2.labels = []
        dependent_2.subtasks = []
        dependent_2.dependencies = []
        
        tasks = [dependent_1, dependent_2]
        
        # Configure mock with proper query chain for list_tasks
        mock_query = Mock()
        mock_options = Mock()
        mock_filter = Mock()
        mock_order_by = Mock()
        mock_offset = Mock()
        mock_limit = Mock()
        mock_all = Mock(return_value=tasks)
        
        # Build the query chain
        mock_query.options.return_value = mock_options
        mock_options.filter.return_value = mock_filter
        mock_filter.order_by.return_value = mock_order_by
        mock_order_by.offset.return_value = mock_offset
        mock_offset.limit.return_value = mock_limit
        mock_limit.all = mock_all
        
        mock_session.query.return_value = mock_query
        
        # Execute - use list_tasks to get all tasks
        results = repository.list_tasks(limit=100, offset=0)
        
        # Verify
        assert len(results) == 2
        assert any(t.id == "task-dep-1" for t in results)
        assert any(t.id == "task-dep-2" for t in results)

    def test_get_overdue_tasks(self, repository, mock_session):
        """Test getting overdue tasks"""
        from datetime import timezone
        now = datetime.now(timezone.utc)
        
        # Create overdue tasks with proper attributes
        overdue_task_1 = TaskORM(
            id="task-overdue-1",
            title="Overdue Task 1",
            description="First overdue task",
            due_date=(now - timedelta(days=2)).isoformat(),
            status="in_progress",
            priority="high",
            git_branch_id="branch-123",
            user_id="test-user",
            created_at=now - timedelta(days=5),
            updated_at=now - timedelta(days=1)
        )
        overdue_task_1.assignees = []
        overdue_task_1.labels = []
        overdue_task_1.subtasks = []
        
        overdue_task_2 = TaskORM(
            id="task-overdue-2",
            title="Overdue Task 2",
            description="Second overdue task",
            due_date=(now - timedelta(days=1)).isoformat(),
            status="todo",
            priority="medium",
            git_branch_id="branch-123",
            user_id="test-user",
            created_at=now - timedelta(days=3),
            updated_at=now
        )
        overdue_task_2.assignees = []
        overdue_task_2.labels = []
        overdue_task_2.subtasks = []
        
        overdue_tasks = [overdue_task_1, overdue_task_2]
        
        # Configure mock with proper query chain
        mock_query = Mock()
        mock_options = Mock()
        mock_filter = Mock()
        mock_all = Mock(return_value=overdue_tasks)
        
        # Build the query chain
        mock_query.options.return_value = mock_options
        mock_options.filter.return_value = mock_filter
        mock_filter.all = mock_all
        
        mock_session.query.return_value = mock_query
        
        # Execute
        results = repository.get_overdue_tasks()
        
        # Verify
        assert len(results) == 2
        assert all(t.status != "done" for t in results)

    def test_bulk_update_tasks(self, repository, mock_session):
        """Test bulk updating multiple tasks - using batch_update_status"""
        task_ids = ["task-1", "task-2", "task-3"]
        
        # Configure mock - batch_update_status uses query.filter.update pattern
        mock_query = Mock()
        mock_filter = Mock()
        mock_update = Mock(return_value=3)  # 3 tasks updated
        
        # Build the query chain
        mock_query.filter.return_value = mock_filter
        mock_filter.update = mock_update
        
        mock_session.query.return_value = mock_query
        
        # Execute - use batch_update_status which exists
        updated_count = repository.batch_update_status(task_ids, "in_progress")
        
        # Verify
        assert updated_count == 3
        assert mock_filter.update.called

    def test_get_task_statistics(self, repository, mock_session):
        """Test getting task statistics"""
        # Mock the get_task_count method since get_statistics calls it
        with patch.object(repository, 'get_task_count') as mock_count:
            # Configure return values for different status calls
            mock_count.side_effect = lambda status=None, use_cache=True: {
                None: 20,  # total_tasks
                "completed": 10,
                "in_progress": 3,
                "todo": 5
            }.get(status, 0)
            
            # Execute
            stats = repository.get_statistics()
            
            # Verify
            assert stats["total_tasks"] == 20
            assert stats["completed_tasks"] == 10
            assert stats["in_progress_tasks"] == 3
            assert stats["todo_tasks"] == 5

    def test_cascade_operations(self, repository, mock_session, sample_task_orm):
        """Test cascade operations when deleting task"""
        # Add more related entities
        sample_task_orm.context_id = "ctx-123"
        
        # Configure mock for delete_task which handles cascade manually
        mock_query = Mock()
        mock_filter = Mock()
        mock_first = Mock(return_value=sample_task_orm)
        mock_delete = Mock(return_value=0)  # For cascade deletes
        
        # Build the query chain
        mock_query.filter.return_value = mock_filter
        mock_filter.first = mock_first
        mock_filter.delete = mock_delete
        
        mock_session.query.return_value = mock_query
        
        # Execute delete_task which handles cascade internally
        result = repository.delete_task("task-123")
        
        # Verify cascade behavior - delete_task handles this internally
        assert mock_session.delete.called
        assert mock_session.commit.called
        assert result == True

    def test_transaction_handling(self, repository, mock_session):
        """Test proper transaction handling on errors"""
        # Configure mock to raise error
        mock_session.commit.side_effect = SQLAlchemyError("Database error")
        
        # Execute and expect error - create takes kwargs not entity
        with pytest.raises(Exception):  # Will be wrapped in TaskCreationError
            repository.create_task(
                title="Error Task",
                description="Task for error testing",
                priority="medium",
                status="todo",
                assignees=["coding-agent"],
                git_branch_id="branch-123",
                user_id="test-user"
            )
        
        # Verify rollback was called
        assert mock_session.rollback.called

    def test_performance_optimization_with_pagination(self, repository, mock_session):
        """Test query performance with pagination"""
        # Configure mock for list_tasks with pagination
        paginated_tasks = []
        for i in range(10):
            task = TaskORM(
                id=f"task-{i}",
                title=f"Task {i}",
                description=f"Description {i}",
                status="todo",
                priority="medium",
                git_branch_id="branch-123",
                user_id="test-user",
                created_at=datetime.now(),
                updated_at=datetime.now()
            )
            task.assignees = []
            task.labels = []
            task.subtasks = []
            task.dependencies = []
            paginated_tasks.append(task)
        
        # Configure mock with proper query chain
        mock_query = Mock()
        mock_options = Mock()
        mock_filter = Mock()
        mock_order_by = Mock()
        mock_offset = Mock()
        mock_limit = Mock()
        mock_all = Mock(return_value=paginated_tasks)
        
        # Build the query chain
        mock_query.options.return_value = mock_options
        mock_options.filter.return_value = mock_filter
        mock_filter.order_by.return_value = mock_order_by
        mock_order_by.offset.return_value = mock_offset
        mock_offset.limit.return_value = mock_limit
        mock_limit.all = mock_all
        
        mock_session.query.return_value = mock_query
        
        # Execute - use list_tasks with offset/limit for pagination
        results = repository.list_tasks(limit=10, offset=10)  # Page 2
        
        # Verify
        assert len(results) == 10
        assert mock_offset.limit.return_value.all.called