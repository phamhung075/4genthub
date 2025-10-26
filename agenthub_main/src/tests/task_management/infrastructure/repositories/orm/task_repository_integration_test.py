"""
Integration tests for Task Repository ORM implementation

These are proper integration tests using a real test database.
Focus on: CRUD operations, query building, data validation, repository patterns
"""

import pytest
import uuid
from datetime import datetime, timezone, timedelta
from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker, Session
from sqlalchemy.exc import IntegrityError

from fastmcp.task_management.infrastructure.repositories.orm.task_repository import (
    ORMTaskRepository, _ensure_estimated_effort_default
)
from fastmcp.task_management.infrastructure.database.models import (
    Task as TaskORM,
    TaskAssignee,
    TaskLabel,
    TaskDependency,
    Label,
    ProjectGitBranch,
    Project,
    Subtask,
    Base
)
from fastmcp.task_management.domain.entities.task import Task as TaskEntity
from fastmcp.task_management.domain.value_objects.task_id import TaskId
from fastmcp.task_management.domain.value_objects.task_status import TaskStatus
from fastmcp.task_management.domain.value_objects.priority import Priority


@pytest.fixture(scope='function')
def test_db_engine():
    """Create a test database engine"""
    # Use in-memory SQLite for fast tests
    engine = create_engine('sqlite:///:memory:', echo=False)
    Base.metadata.create_all(engine)
    yield engine
    engine.dispose()


@pytest.fixture(scope='function')
def test_session(test_db_engine):
    """Create a test database session"""
    SessionLocal = sessionmaker(bind=test_db_engine)
    session = SessionLocal()
    yield session
    session.close()


@pytest.fixture(scope='function')
def test_user_id():
    """Generate a consistent test user ID"""
    return str(uuid.uuid4())


@pytest.fixture(scope='function')
def test_project(test_session, test_user_id):
    """Create a test project"""
    project_id = str(uuid.uuid4())
    project = Project(
        id=project_id,
        name="Test Project",
        description="Project for testing",
        user_id=test_user_id,
        created_at=datetime.now(timezone.utc),
        updated_at=datetime.now(timezone.utc)
    )
    test_session.add(project)
    test_session.commit()
    return project


@pytest.fixture(scope='function')
def test_git_branch(test_session, test_project, test_user_id):
    """Create a test git branch"""
    branch_id = str(uuid.uuid4())
    branch = ProjectGitBranch(
        id=branch_id,
        project_id=test_project.id,
        name="test-branch",
        description="Branch for testing",
        user_id=test_user_id,
        task_count=0,
        completed_task_count=0,
        created_at=datetime.now(timezone.utc),
        updated_at=datetime.now(timezone.utc)
    )
    test_session.add(branch)
    test_session.commit()
    return branch


@pytest.fixture(scope='function')
def repository(test_session, test_git_branch, test_user_id):
    """Create a task repository instance"""
    return ORMTaskRepository(
        session=test_session,
        git_branch_id=test_git_branch.id,
        project_id=test_git_branch.project_id,
        user_id=test_user_id,
        performance_mode=False
    )


class TestTaskRepositoryCRUD:
    """Test basic CRUD operations"""

    def test_create_task_basic(self, repository, test_git_branch):
        """Test creating a basic task"""
        # Arrange
        title = "Implement authentication"
        description = "Add JWT authentication system"

        # Act
        task = repository.create_task(
            title=title,
            description=description,
            priority="high",
            assignee_ids=["coding-agent"]
        )

        # Assert
        assert task is not None
        assert task.title == title
        assert task.description == description
        assert str(task.priority) == "high"
        assert task.git_branch_id == test_git_branch.id
        assert "coding-agent" in task.assignees
        assert task.estimated_effort == "2 hours"  # default value

    def test_create_task_with_all_fields(self, repository, test_git_branch):
        """Test creating a task with all fields"""
        # Arrange
        due_date = datetime.now(timezone.utc) + timedelta(days=7)

        # Act
        task = repository.create_task(
            title="Complex Task",
            description="Task with all fields",
            priority="urgent",
            status="in_progress",
            assignee_ids=["coding-agent", "test-orchestrator-agent"],
            label_names=["backend", "security"],
            estimated_effort="5 days",
            due_date=due_date
        )

        # Assert
        assert task.title == "Complex Task"
        assert str(task.priority) == "urgent"
        assert str(task.status) == "in_progress"
        assert len(task.assignees) == 2
        assert len(task.labels) == 2
        assert task.estimated_effort == "5 days"
        assert task.due_date == due_date

    def test_get_task_by_id(self, repository):
        """Test retrieving task by ID"""
        # Arrange - create a task first
        created_task = repository.create_task(
            title="Get Test Task",
            description="Task to retrieve",
            assignee_ids=["coding-agent"]
        )

        # Act
        retrieved_task = repository.get_task(str(created_task.id))

        # Assert
        assert retrieved_task is not None
        assert str(retrieved_task.id) == str(created_task.id)
        assert retrieved_task.title == "Get Test Task"

    def test_get_task_not_found(self, repository):
        """Test retrieving non-existent task returns None"""
        # Act
        task = repository.get_task(str(uuid.uuid4()))

        # Assert
        assert task is None

    def test_update_task_basic_fields(self, repository):
        """Test updating task basic fields"""
        # Arrange
        task = repository.create_task(
            title="Original Title",
            description="Original description",
            assignee_ids=["coding-agent"]
        )

        # Act
        updated_task = repository.update_task(
            str(task.id),
            title="Updated Title",
            description="Updated description",
            priority="urgent"
        )

        # Assert
        assert updated_task.title == "Updated Title"
        assert updated_task.description == "Updated description"
        assert str(updated_task.priority) == "urgent"

    def test_update_task_status(self, repository):
        """Test updating task status"""
        # Arrange
        task = repository.create_task(
            title="Status Test",
            description="Test status updates",
            assignee_ids=["coding-agent"]
        )

        # Act
        updated_task = repository.update_task(
            str(task.id),
            status="in_progress"
        )

        # Assert
        assert str(updated_task.status) == "in_progress"

    def test_update_task_assignees(self, repository):
        """Test updating task assignees"""
        # Arrange
        task = repository.create_task(
            title="Assignee Test",
            description="Test assignee updates",
            assignee_ids=["coding-agent"]
        )

        # Act
        updated_task = repository.update_task(
            str(task.id),
            assignee_ids=["test-orchestrator-agent", "debugger-agent"]
        )

        # Assert
        assert len(updated_task.assignees) == 2
        assert "test-orchestrator-agent" in updated_task.assignees
        assert "debugger-agent" in updated_task.assignees

    def test_update_task_labels(self, repository):
        """Test updating task labels"""
        # Arrange
        task = repository.create_task(
            title="Label Test",
            description="Test label updates",
            assignee_ids=["coding-agent"],
            label_names=["frontend"]
        )

        # Act
        updated_task = repository.update_task(
            str(task.id),
            label_names=["backend", "api"]
        )

        # Assert
        assert len(updated_task.labels) == 2
        assert "backend" in updated_task.labels
        assert "api" in updated_task.labels

    def test_delete_task(self, repository):
        """Test deleting a task"""
        # Arrange
        task = repository.create_task(
            title="Delete Test",
            description="Task to delete",
            assignee_ids=["coding-agent"]
        )
        task_id = str(task.id)

        # Act
        result = repository.delete_task(task_id)

        # Assert
        assert result is True
        deleted_task = repository.get_task(task_id)
        assert deleted_task is None


class TestTaskRepositoryQuerying:
    """Test query building and filtering operations"""

    def test_list_tasks_basic(self, repository):
        """Test basic task listing"""
        # Arrange - create multiple tasks
        for i in range(5):
            repository.create_task(
                title=f"Task {i}",
                description=f"Description {i}",
                assignee_ids=["coding-agent"]
            )

        # Act
        tasks = repository.list_tasks(limit=100, offset=0)

        # Assert
        assert len(tasks) >= 5

    def test_list_tasks_with_status_filter(self, repository):
        """Test listing tasks filtered by status"""
        # Arrange
        repository.create_task(
            title="Todo Task",
            description="Should be in results",
            status="todo",
            assignee_ids=["coding-agent"]
        )
        repository.create_task(
            title="Done Task",
            description="Should not be in results",
            status="done",
            assignee_ids=["coding-agent"]
        )

        # Act
        todo_tasks = repository.list_tasks(status="todo")

        # Assert
        assert len(todo_tasks) >= 1
        assert all(str(t.status) == "todo" for t in todo_tasks)

    def test_list_tasks_with_priority_filter(self, repository):
        """Test listing tasks filtered by priority"""
        # Arrange
        repository.create_task(
            title="High Priority",
            description="High priority task",
            priority="high",
            assignee_ids=["coding-agent"]
        )
        repository.create_task(
            title="Low Priority",
            description="Low priority task",
            priority="low",
            assignee_ids=["coding-agent"]
        )

        # Act
        high_priority_tasks = repository.list_tasks(priority="high")

        # Assert
        assert len(high_priority_tasks) >= 1
        assert all(str(t.priority) == "high" for t in high_priority_tasks)

    def test_list_tasks_with_assignee_filter(self, repository):
        """Test listing tasks filtered by assignee"""
        # Arrange
        repository.create_task(
            title="Coding Task",
            description="For coding agent",
            assignee_ids=["coding-agent"]
        )
        repository.create_task(
            title="Test Task",
            description="For test agent",
            assignee_ids=["test-orchestrator-agent"]
        )

        # Act
        coding_tasks = repository.list_tasks(assignee_id="coding-agent")

        # Assert
        assert len(coding_tasks) >= 1
        assert all("coding-agent" in t.assignees for t in coding_tasks)

    def test_list_tasks_pagination(self, repository):
        """Test task listing with pagination"""
        # Arrange - create 10 tasks
        for i in range(10):
            repository.create_task(
                title=f"Task {i}",
                description=f"Description {i}",
                assignee_ids=["coding-agent"]
            )

        # Act
        page1 = repository.list_tasks(limit=5, offset=0)
        page2 = repository.list_tasks(limit=5, offset=5)

        # Assert
        assert len(page1) == 5
        assert len(page2) >= 5
        # Verify no overlap
        page1_ids = {str(t.id) for t in page1}
        page2_ids = {str(t.id) for t in page2}
        assert len(page1_ids & page2_ids) == 0  # No common IDs

    def test_search_tasks_by_title(self, repository):
        """Test searching tasks by title"""
        # Arrange
        repository.create_task(
            title="Authentication System",
            description="Build auth",
            assignee_ids=["coding-agent"]
        )
        repository.create_task(
            title="Database Migration",
            description="Update schema",
            assignee_ids=["coding-agent"]
        )

        # Act
        results = repository.search_tasks("authentication")

        # Assert
        assert len(results) >= 1
        assert any("authentication" in t.title.lower() for t in results)

    def test_search_tasks_by_description(self, repository):
        """Test searching tasks by description"""
        # Arrange
        repository.create_task(
            title="Task 1",
            description="This task involves JWT tokens",
            assignee_ids=["coding-agent"]
        )

        # Act
        results = repository.search_tasks("JWT")

        # Assert
        assert len(results) >= 1

    def test_get_task_count(self, repository):
        """Test getting total task count"""
        # Arrange
        initial_count = repository.get_task_count()
        repository.create_task(
            title="Count Test 1",
            description="Test",
            assignee_ids=["coding-agent"]
        )
        repository.create_task(
            title="Count Test 2",
            description="Test",
            assignee_ids=["coding-agent"]
        )

        # Act
        new_count = repository.get_task_count()

        # Assert
        assert new_count == initial_count + 2

    def test_get_task_count_with_status_filter(self, repository):
        """Test getting task count filtered by status"""
        # Arrange
        repository.create_task(
            title="Todo Task",
            description="Test",
            status="todo",
            assignee_ids=["coding-agent"]
        )
        repository.create_task(
            title="Done Task",
            description="Test",
            status="done",
            assignee_ids=["coding-agent"]
        )

        # Act
        todo_count = repository.get_task_count(status="todo")
        done_count = repository.get_task_count(status="done")

        # Assert
        assert todo_count >= 1
        assert done_count >= 1


class TestTaskRepositoryDataValidation:
    """Test data validation and constraints"""

    def test_ensure_estimated_effort_default_none(self):
        """Test _ensure_estimated_effort_default with None"""
        assert _ensure_estimated_effort_default(None) == "2 hours"

    def test_ensure_estimated_effort_default_empty_string(self):
        """Test _ensure_estimated_effort_default with empty string"""
        assert _ensure_estimated_effort_default("") == "2 hours"

    def test_ensure_estimated_effort_default_whitespace(self):
        """Test _ensure_estimated_effort_default with whitespace"""
        assert _ensure_estimated_effort_default("   ") == "2 hours"

    def test_ensure_estimated_effort_default_valid_value(self):
        """Test _ensure_estimated_effort_default with valid value"""
        assert _ensure_estimated_effort_default("5 days") == "5 days"

    def test_create_task_assigns_default_estimated_effort(self, repository):
        """Test that create_task assigns default estimated_effort"""
        # Act
        task = repository.create_task(
            title="Default Effort Test",
            description="Test default",
            assignee_ids=["coding-agent"]
        )

        # Assert
        assert task.estimated_effort == "2 hours"

    def test_create_task_with_custom_estimated_effort(self, repository):
        """Test that create_task respects custom estimated_effort"""
        # Act
        task = repository.create_task(
            title="Custom Effort Test",
            description="Test custom",
            estimated_effort="10 days",
            assignee_ids=["coding-agent"]
        )

        # Assert
        assert task.estimated_effort == "10 days"

    def test_model_to_entity_conversion(self, repository):
        """Test _model_to_entity conversion"""
        # Arrange
        task = repository.create_task(
            title="Conversion Test",
            description="Test model to entity conversion",
            priority="high",
            assignee_ids=["coding-agent"],
            label_names=["test"]
        )

        # Assert - verify entity properties
        assert isinstance(task.id, TaskId)
        assert isinstance(task.status, TaskStatus)
        assert isinstance(task.priority, Priority)
        assert isinstance(task.assignees, list)
        assert isinstance(task.labels, list)

    def test_entity_to_model_dict_conversion(self, repository):
        """Test _entity_to_model_dict conversion"""
        # Arrange
        task = repository.create_task(
            title="Dict Conversion Test",
            description="Test entity to model dict",
            assignee_ids=["coding-agent"]
        )

        # Act
        model_dict = repository._entity_to_model_dict(task)

        # Assert
        assert "id" in model_dict
        assert "title" in model_dict
        assert "description" in model_dict
        assert "status" in model_dict
        assert "priority" in model_dict
        assert model_dict["title"] == "Dict Conversion Test"


class TestTaskRepositoryRelationships:
    """Test task relationships and cascades"""

    def test_delete_task_cascades_assignees(self, repository, test_session):
        """Test that deleting task removes assignees"""
        # Arrange
        task = repository.create_task(
            title="Cascade Test",
            description="Test cascade delete",
            assignee_ids=["coding-agent", "test-orchestrator-agent"]
        )
        task_id = str(task.id)

        # Verify assignees exist
        assignee_count = test_session.query(TaskAssignee).filter(
            TaskAssignee.task_id == task_id
        ).count()
        assert assignee_count == 2

        # Act
        repository.delete_task(task_id)

        # Assert
        assignee_count_after = test_session.query(TaskAssignee).filter(
            TaskAssignee.task_id == task_id
        ).count()
        assert assignee_count_after == 0

    def test_delete_task_cascades_labels(self, repository, test_session):
        """Test that deleting task removes label relationships"""
        # Arrange
        task = repository.create_task(
            title="Label Cascade Test",
            description="Test label cascade",
            assignee_ids=["coding-agent"],
            label_names=["backend", "urgent"]
        )
        task_id = str(task.id)

        # Verify labels exist
        label_count = test_session.query(TaskLabel).filter(
            TaskLabel.task_id == task_id
        ).count()
        assert label_count == 2

        # Act
        repository.delete_task(task_id)

        # Assert
        label_count_after = test_session.query(TaskLabel).filter(
            TaskLabel.task_id == task_id
        ).count()
        assert label_count_after == 0

    def test_create_task_updates_branch_counter(self, repository, test_git_branch, test_session):
        """Test that creating task updates branch counter"""
        # Arrange
        initial_count = test_git_branch.task_count or 0

        # Act
        repository.create_task(
            title="Counter Test",
            description="Test branch counter update",
            assignee_ids=["coding-agent"]
        )

        # Refresh branch from database
        test_session.refresh(test_git_branch)

        # Assert
        assert test_git_branch.task_count == initial_count + 1

    def test_update_task_status_updates_completed_counter(self, repository, test_git_branch, test_session):
        """Test that changing task to done updates completed counter"""
        # Arrange
        task = repository.create_task(
            title="Status Counter Test",
            description="Test completed counter",
            status="in_progress",
            assignee_ids=["coding-agent"]
        )
        test_session.refresh(test_git_branch)
        initial_completed = test_git_branch.completed_task_count or 0

        # Act
        repository.update_task(str(task.id), status="done")

        # Refresh branch from database
        test_session.refresh(test_git_branch)

        # Assert
        assert test_git_branch.completed_task_count == initial_completed + 1


class TestTaskRepositoryPerformance:
    """Test performance-related features"""

    def test_list_tasks_minimal(self, repository):
        """Test list_tasks_minimal for lightweight queries"""
        # Arrange
        for i in range(5):
            repository.create_task(
                title=f"Minimal Task {i}",
                description=f"Test minimal query {i}",
                assignee_ids=["coding-agent"]
            )

        # Act
        tasks = repository.list_tasks_minimal(limit=10, offset=0)

        # Assert
        assert len(tasks) >= 5
        assert all(isinstance(t, dict) for t in tasks)
        assert all("id" in t and "title" in t for t in tasks)

    def test_performance_mode_initialization(self, test_session, test_git_branch, test_user_id):
        """Test repository initialization with performance mode"""
        # Act
        repo = ORMTaskRepository(
            session=test_session,
            git_branch_id=test_git_branch.id,
            project_id=test_git_branch.project_id,
            user_id=test_user_id,
            performance_mode=True
        )

        # Assert
        assert repo.performance_mode is True
        assert repo.optimizer is not None

    def test_with_user_creates_new_instance(self, repository):
        """Test with_user creates properly scoped repository"""
        # Arrange
        new_user_id = str(uuid.uuid4())

        # Act
        new_repo = repository.with_user(new_user_id)

        # Assert
        assert new_repo.user_id == new_user_id
        assert new_repo.git_branch_id == repository.git_branch_id
        assert new_repo is not repository  # Different instance


class TestTaskRepositoryEdgeCases:
    """Test edge cases and error handling"""

    def test_get_task_graceful_relationship_loading(self, repository):
        """Test that get_task handles relationship loading errors gracefully"""
        # Arrange
        task = repository.create_task(
            title="Graceful Loading Test",
            description="Test graceful error handling",
            assignee_ids=["coding-agent"]
        )

        # Act - this should not raise an exception
        retrieved = repository.get_task(str(task.id))

        # Assert
        assert retrieved is not None
        assert retrieved.title == "Graceful Loading Test"

    def test_search_tasks_empty_query(self, repository):
        """Test search with empty query returns empty list"""
        # Act
        results = repository.search_tasks("")

        # Assert
        assert results == []

    def test_search_tasks_with_whitespace(self, repository):
        """Test search with whitespace-only query"""
        # Act
        results = repository.search_tasks("   ")

        # Assert
        assert results == []

    def test_list_tasks_minimal_respects_limit(self, repository):
        """Test that list_tasks_minimal respects limit parameter"""
        # Arrange
        for i in range(10):
            repository.create_task(
                title=f"Limit Test {i}",
                description="Test limit",
                assignee_ids=["coding-agent"]
            )

        # Act
        tasks = repository.list_tasks_minimal(limit=3, offset=0)

        # Assert
        assert len(tasks) <= 3
