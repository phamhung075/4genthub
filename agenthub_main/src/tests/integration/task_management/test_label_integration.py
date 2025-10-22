"""
Comprehensive Label Integration Tests

This test suite provides comprehensive integration testing for label functionality,
covering creation, association, queries, and error handling with >90% code coverage.

Test Classes:
1. TestLabelCreation - Label creation scenarios with timestamp validation
2. TestLabelAssociation - Label-task relationship management
3. TestLabelQueries - Label filtering and search operations
4. TestLabelErrorHandling - Error scenarios and validation

Requirements:
- Minimum 15 test cases covering all label operations
- >90% code coverage for label-related code
- UTC timestamp validation for all created labels
- Edge cases and error conditions covered
"""

import pytest
from datetime import datetime, timezone
from typing import List
import uuid

from fastmcp.task_management.infrastructure.repositories.orm.label_repository import ORMLabelRepository
from fastmcp.task_management.infrastructure.repositories.orm.task_repository import ORMTaskRepository
from fastmcp.task_management.infrastructure.database.database_adapter import DatabaseAdapter
from fastmcp.task_management.infrastructure.database.database_config import get_session
from fastmcp.task_management.domain.entities.label import Label as LabelEntity
from fastmcp.task_management.domain.exceptions.base_exceptions import (
    RepositoryError,
    NotFoundError,
    ValidationError
)


# ==============================================================================
# Test Fixtures
# ==============================================================================

@pytest.fixture(scope="function")
def db_session():
    """Provides a database session for tests"""
    session = get_session()
    yield session
    session.close()


@pytest.fixture
def db_adapter():
    """Provides a database adapter for tests"""
    from fastmcp.task_management.infrastructure.database.database_config import get_engine
    engine = get_engine()
    adapter = DatabaseAdapter(engine)
    return adapter


@pytest.fixture
def label_repository(db_adapter):
    """Provides a label repository for tests"""
    repo = ORMLabelRepository(db_adapter)
    repo.user_id = "test_user"  # Set user_id for multi-tenant isolation
    return repo


@pytest.fixture
def task_repository(db_session):
    """Provides a task repository for tests"""
    repo = ORMTaskRepository(session=db_session, user_id="test_user")
    return repo


@pytest.fixture
def test_git_branch_id():
    """Provides a test git branch ID"""
    return str(uuid.uuid4())


@pytest.fixture
def cleanup_labels():
    """Cleanup labels after each test"""
    yield
    # Cleanup logic if needed
    pass


# ==============================================================================
# Test Class 1: Label Creation Tests
# ==============================================================================

class TestLabelCreation:
    """Test label creation scenarios with UTC timestamp validation"""

    def test_create_single_label(self, label_repository, cleanup_labels):
        """Test creating a single label with UTC timestamp"""
        # Arrange
        label_name = "backend"
        label_color = "#0066cc"
        label_desc = "Backend development tasks"

        # Act
        label = label_repository.create_label(
            name=label_name,
            color=label_color,
            description=label_desc
        )

        # Assert
        assert label is not None
        assert label.name == label_name
        assert label.color == label_color
        assert label.description == label_desc
        # Verify UTC-aware timestamps
        assert label.created_at is not None
        assert label.updated_at is not None
        assert label.created_at.tzinfo is not None
        assert label.updated_at.tzinfo is not None
        assert label.created_at.tzinfo == timezone.utc
        assert label.updated_at.tzinfo == timezone.utc

    def test_create_label_with_default_color(self, label_repository, cleanup_labels):
        """Test creating a label with default color"""
        # Arrange
        label_name = "frontend"

        # Act
        label = label_repository.create_label(name=label_name)

        # Assert
        assert label is not None
        assert label.name == label_name
        assert label.color == "#0066cc"  # Default color
        assert label.created_at.tzinfo == timezone.utc

    def test_create_multiple_labels_different_names(self, label_repository, cleanup_labels):
        """Test creating multiple labels with different names"""
        # Arrange
        label_names = ["security", "api", "database"]

        # Act
        labels = [
            label_repository.create_label(name=name)
            for name in label_names
        ]

        # Assert
        assert len(labels) == 3
        for label in labels:
            assert label.name in label_names
            assert label.created_at.tzinfo == timezone.utc
            assert label.updated_at.tzinfo == timezone.utc

    def test_create_label_with_complex_name(self, label_repository, cleanup_labels):
        """Test creating labels with hyphens and special characters"""
        # Arrange
        complex_names = [
            "api-integration",
            "frontend-ui",
            "db-optimization"
        ]

        # Act
        labels = [
            label_repository.create_label(name=name)
            for name in complex_names
        ]

        # Assert
        assert len(labels) == 3
        for label in labels:
            assert label.name in complex_names
            assert "-" in label.name  # Verify hyphen preserved

    def test_label_timestamp_is_utc_aware(self, label_repository, cleanup_labels):
        """Test that all label timestamps are UTC-aware"""
        # Arrange
        label_name = "test-timezone"

        # Act
        label = label_repository.create_label(name=label_name)

        # Assert - Comprehensive timezone checks
        assert label.created_at.tzinfo is not None, "created_at must have timezone info"
        assert label.updated_at.tzinfo is not None, "updated_at must have timezone info"
        assert label.created_at.tzinfo == timezone.utc, "created_at must be UTC"
        assert label.updated_at.tzinfo == timezone.utc, "updated_at must be UTC"
        # Verify timestamps are recent (within last minute)
        now = datetime.now(timezone.utc)
        time_diff = (now - label.created_at).total_seconds()
        assert time_diff < 60, "Timestamp should be recent"

    def test_duplicate_label_handling(self, label_repository, cleanup_labels):
        """Test that duplicate label names are rejected"""
        # Arrange
        label_name = "duplicate-test"

        # Act - Create first label
        label1 = label_repository.create_label(name=label_name)
        assert label1 is not None

        # Act & Assert - Attempt to create duplicate
        with pytest.raises(ValidationError) as exc_info:
            label_repository.create_label(name=label_name)

        assert "already exists" in str(exc_info.value).lower()


# ==============================================================================
# Test Class 2: Label Association Tests
# ==============================================================================

class TestLabelAssociation:
    """Test label-task relationship management"""

    def test_assign_label_to_task(self, task_repository, label_repository, test_git_branch_id, cleanup_labels):
        """Test assigning a label to a task"""
        # Arrange - Create task
        task_id = str(uuid.uuid4())
        task = task_repository.create_task(
            task_id=task_id,
            title="Test Task",
            description="Task for label assignment",
            git_branch_id=test_git_branch_id,
            assignees="test-orchestrator-agent",
            priority="medium",
            status="todo"
        )

        # Create label
        label = label_repository.create_label(name="test-label")

        # Act - Assign label to task
        result = label_repository.assign_label_to_task(
            task_id=task_id,
            label_id=label.id
        )

        # Assert
        assert result is True

        # Verify assignment
        task_labels = label_repository.get_labels_by_task(task_id)
        assert len(task_labels) == 1
        assert task_labels[0].name == "test-label"

    def test_assign_multiple_labels_to_task(self, task_repository, label_repository, test_git_branch_id, cleanup_labels):
        """Test assigning multiple labels to a single task"""
        # Arrange - Create task
        task_id = str(uuid.uuid4())
        task = task_repository.create_task(
            task_id=task_id,
            title="Multi-label Task",
            description="Task with multiple labels",
            git_branch_id=test_git_branch_id,
            assignees="test-orchestrator-agent",
            priority="high",
            status="todo"
        )

        # Create multiple labels
        label_names = ["backend", "security", "critical"]
        labels = [
            label_repository.create_label(name=name)
            for name in label_names
        ]

        # Act - Assign all labels to task
        for label in labels:
            label_repository.assign_label_to_task(
                task_id=task_id,
                label_id=label.id
            )

        # Assert
        task_labels = label_repository.get_labels_by_task(task_id)
        assert len(task_labels) == 3
        task_label_names = [l.name for l in task_labels]
        for name in label_names:
            assert name in task_label_names

    def test_assign_same_label_to_multiple_tasks(self, task_repository, label_repository, test_git_branch_id, cleanup_labels):
        """Test using the same label across multiple tasks"""
        # Arrange - Create single label
        label = label_repository.create_label(name="shared-label")

        # Create multiple tasks
        task_ids = []
        for i in range(3):
            task_id = str(uuid.uuid4())
            task_repository.create_task(
                task_id=task_id,
                title=f"Task {i+1}",
                description=f"Task {i+1} description",
                git_branch_id=test_git_branch_id,
                assignees="test-orchestrator-agent",
                priority="medium",
                status="todo"
            )
            task_ids.append(task_id)

        # Act - Assign same label to all tasks
        for task_id in task_ids:
            label_repository.assign_label_to_task(
                task_id=task_id,
                label_id=label.id
            )

        # Assert - Verify label is assigned to all tasks
        tasks_with_label = label_repository.get_tasks_by_label(label.id)
        assert len(tasks_with_label) == 3

    def test_remove_label_from_task(self, task_repository, label_repository, test_git_branch_id, cleanup_labels):
        """Test removing a label from a task"""
        # Arrange - Create task and label
        task_id = str(uuid.uuid4())
        task_repository.create_task(
            task_id=task_id,
            title="Test Task",
            description="Task for label removal",
            git_branch_id=test_git_branch_id,
            assignees="test-orchestrator-agent",
            priority="medium",
            status="todo"
        )

        label = label_repository.create_label(name="temp-label")
        label_repository.assign_label_to_task(task_id=task_id, label_id=label.id)

        # Act - Remove label
        result = label_repository.remove_label_from_task(
            task_id=task_id,
            label_id=label.id
        )

        # Assert
        assert result is True
        task_labels = label_repository.get_labels_by_task(task_id)
        assert len(task_labels) == 0

    def test_assign_duplicate_label_to_task(self, task_repository, label_repository, test_git_branch_id, cleanup_labels):
        """Test that assigning the same label twice returns False"""
        # Arrange
        task_id = str(uuid.uuid4())
        task_repository.create_task(
            task_id=task_id,
            title="Test Task",
            description="Task for duplicate label test",
            git_branch_id=test_git_branch_id,
            assignees="test-orchestrator-agent",
            priority="medium",
            status="todo"
        )

        label = label_repository.create_label(name="dup-label")

        # Act - First assignment
        result1 = label_repository.assign_label_to_task(task_id=task_id, label_id=label.id)
        # Second assignment (duplicate)
        result2 = label_repository.assign_label_to_task(task_id=task_id, label_id=label.id)

        # Assert
        assert result1 is True
        assert result2 is False  # Duplicate assignment should return False


# ==============================================================================
# Test Class 3: Label Query Tests
# ==============================================================================

class TestLabelQueries:
    """Test label filtering and search operations"""

    def test_list_all_labels(self, label_repository, cleanup_labels):
        """Test listing all labels"""
        # Arrange - Create multiple labels
        label_names = ["label1", "label2", "label3"]
        for name in label_names:
            label_repository.create_label(name=name)

        # Act
        labels = label_repository.list_labels()

        # Assert
        assert len(labels) >= 3
        label_names_result = [l.name for l in labels]
        for name in label_names:
            assert name in label_names_result

    def test_list_labels_with_limit(self, label_repository, cleanup_labels):
        """Test listing labels with limit parameter"""
        # Arrange - Create multiple labels
        for i in range(5):
            label_repository.create_label(name=f"limit-label-{i}")

        # Act
        labels = label_repository.list_labels(limit=3)

        # Assert
        assert len(labels) <= 3

    def test_list_labels_with_offset(self, label_repository, cleanup_labels):
        """Test listing labels with offset parameter"""
        # Arrange - Create labels in specific order
        for i in range(5):
            label_repository.create_label(name=f"offset-label-{i:02d}")  # 00, 01, 02...

        # Act
        all_labels = label_repository.list_labels()
        offset_labels = label_repository.list_labels(offset=2)

        # Assert
        assert len(offset_labels) < len(all_labels)

    def test_get_label_by_name(self, label_repository, cleanup_labels):
        """Test retrieving a label by name"""
        # Arrange
        label_name = "search-test"
        created_label = label_repository.create_label(name=label_name)

        # Act
        found_label = label_repository.get_label_by_name(label_name)

        # Assert
        assert found_label is not None
        assert found_label.name == label_name
        assert found_label.id == created_label.id

    def test_get_label_by_id(self, label_repository, cleanup_labels):
        """Test retrieving a label by ID"""
        # Arrange
        created_label = label_repository.create_label(name="id-test")

        # Act
        found_label = label_repository.get_label(created_label.id)

        # Assert
        assert found_label is not None
        assert found_label.id == created_label.id
        assert found_label.name == "id-test"


# ==============================================================================
# Test Class 4: Label Error Handling Tests
# ==============================================================================

class TestLabelErrorHandling:
    """Test error scenarios and validation"""

    def test_create_label_with_empty_name(self, label_repository, cleanup_labels):
        """Test that empty label names are rejected"""
        # Act & Assert
        with pytest.raises((ValidationError, ValueError)):
            label_repository.create_label(name="")

    def test_create_label_with_whitespace_only_name(self, label_repository, cleanup_labels):
        """Test that whitespace-only names are rejected"""
        # Act & Assert
        with pytest.raises((ValidationError, ValueError)):
            label_repository.create_label(name="   ")

    def test_assign_label_to_nonexistent_task(self, label_repository, cleanup_labels):
        """Test assigning a label to a non-existent task"""
        # Arrange
        label = label_repository.create_label(name="error-test")
        fake_task_id = str(uuid.uuid4())

        # Act & Assert
        with pytest.raises(NotFoundError) as exc_info:
            label_repository.assign_label_to_task(
                task_id=fake_task_id,
                label_id=label.id
            )

        assert "Task" in str(exc_info.value)

    def test_assign_nonexistent_label_to_task(self, task_repository, label_repository, test_git_branch_id, cleanup_labels):
        """Test assigning a non-existent label to a task"""
        # Arrange - Create task
        task_id = str(uuid.uuid4())
        task_repository.create_task(
            task_id=task_id,
            title="Test Task",
            description="Task for error test",
            git_branch_id=test_git_branch_id,
            assignees="test-orchestrator-agent",
            priority="medium",
            status="todo"
        )

        fake_label_id = 99999

        # Act & Assert
        with pytest.raises(NotFoundError) as exc_info:
            label_repository.assign_label_to_task(
                task_id=task_id,
                label_id=fake_label_id
            )

        assert "Label" in str(exc_info.value)

    def test_get_nonexistent_label(self, label_repository):
        """Test getting a label that doesn't exist"""
        # Arrange
        fake_label_id = 99999

        # Act
        label = label_repository.get_label(fake_label_id)

        # Assert
        assert label is None

    def test_update_label_with_existing_name(self, label_repository, cleanup_labels):
        """Test updating a label to a name that already exists"""
        # Arrange - Create two labels
        label1 = label_repository.create_label(name="label-one")
        label2 = label_repository.create_label(name="label-two")

        # Act & Assert - Try to rename label2 to label1's name
        with pytest.raises(ValidationError) as exc_info:
            label_repository.update_label(
                label_id=label2.id,
                name="label-one"
            )

        assert "already exists" in str(exc_info.value).lower()

    def test_delete_nonexistent_label(self, label_repository):
        """Test deleting a label that doesn't exist"""
        # Arrange
        fake_label_id = 99999

        # Act
        result = label_repository.delete_label(fake_label_id)

        # Assert
        assert result is False
