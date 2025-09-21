"""Tests for append-only progress history functionality"""

import pytest
from datetime import datetime, timezone
from fastmcp.task_management.domain.entities.task import Task
from fastmcp.task_management.domain.value_objects.task_id import TaskId
from fastmcp.task_management.domain.value_objects.task_status import TaskStatus
from fastmcp.task_management.domain.value_objects.priority import Priority


class TestAppendProgress:
    """Test append-only progress history functionality"""

    def test_append_progress_creates_numbered_headers(self):
        """Test that append_progress creates numbered headers"""
        # Arrange
        task = Task(
            id=TaskId("test-id"),
            title="Test Task",
            description="Test Description",
            status=TaskStatus.todo(),
            priority=Priority.medium()
        )

        # Act
        task.append_progress("First progress update")

        # Assert
        assert task.progress_count == 1
        assert "progress_1" in task.progress_history
        assert "=== Progress 1 ===" in task.progress_history["progress_1"]["content"]
        assert "First progress update" in task.progress_history["progress_1"]["content"]

    def test_append_progress_increments_counter(self):
        """Test that multiple append_progress calls increment the counter"""
        # Arrange
        task = Task(
            id=TaskId("test-id"),
            title="Test Task",
            description="Test Description",
            status=TaskStatus.todo(),
            priority=Priority.medium()
        )

        # Act
        task.append_progress("First update")
        task.append_progress("Second update")
        task.append_progress("Third update")

        # Assert
        assert task.progress_count == 3
        assert len(task.progress_history) == 3
        assert "=== Progress 1 ===" in task.progress_history["progress_1"]["content"]
        assert "=== Progress 2 ===" in task.progress_history["progress_2"]["content"]
        assert "=== Progress 3 ===" in task.progress_history["progress_3"]["content"]

    def test_append_progress_preserves_order(self):
        """Test that progress entries maintain their order"""
        # Arrange
        task = Task(
            id=TaskId("test-id"),
            title="Test Task",
            description="Test Description",
            status=TaskStatus.todo(),
            priority=Priority.medium()
        )

        # Act
        task.append_progress("Step 1: Analysis")
        task.append_progress("Step 2: Implementation")
        task.append_progress("Step 3: Testing")

        # Assert
        assert task.progress_history["progress_1"]["progress_number"] == 1
        assert task.progress_history["progress_2"]["progress_number"] == 2
        assert task.progress_history["progress_3"]["progress_number"] == 3

    def test_get_progress_history_text_formats_correctly(self):
        """Test that get_progress_history_text returns properly formatted text"""
        # Arrange
        task = Task(
            id=TaskId("test-id"),
            title="Test Task",
            description="Test Description",
            status=TaskStatus.todo(),
            priority=Priority.medium()
        )

        # Act
        task.append_progress("First update")
        task.append_progress("Second update")
        formatted_text = task.get_progress_history_text()

        # Assert
        assert "=== Progress 1 ===" in formatted_text
        assert "=== Progress 2 ===" in formatted_text
        assert "First update" in formatted_text
        assert "Second update" in formatted_text
        # Should be separated by double newlines
        assert "\n\n" in formatted_text

    def test_get_progress_history_text_empty_when_no_history(self):
        """Test that get_progress_history_text returns empty string when no history"""
        # Arrange
        task = Task(
            id=TaskId("test-id"),
            title="Test Task",
            description="Test Description",
            status=TaskStatus.todo(),
            priority=Priority.medium()
        )

        # Act
        formatted_text = task.get_progress_history_text()

        # Assert
        assert formatted_text == ""

    def test_append_progress_clears_context_id(self):
        """Test that append_progress clears context_id to indicate context needs updating"""
        # Arrange
        task = Task(
            id=TaskId("test-id"),
            title="Test Task",
            description="Test Description",
            status=TaskStatus.todo(),
            priority=Priority.medium(),
            context_id="some-context-id"
        )

        # Act
        task.append_progress("Progress update")

        # Assert
        assert task.context_id is None

    def test_append_progress_updates_timestamp(self):
        """Test that append_progress updates the task's updated_at timestamp"""
        # Arrange
        task = Task(
            id=TaskId("test-id"),
            title="Test Task",
            description="Test Description",
            status=TaskStatus.todo(),
            priority=Priority.medium()
        )
        initial_time = task.updated_at

        # Act
        task.append_progress("Progress update")

        # Assert
        assert task.updated_at > initial_time

    def test_append_progress_handles_none_progress_history(self):
        """Test that append_progress works even if progress_history is None"""
        # Arrange
        task = Task(
            id=TaskId("test-id"),
            title="Test Task",
            description="Test Description",
            status=TaskStatus.todo(),
            priority=Priority.medium()
        )
        # Simulate case where progress_history might be None
        task.progress_history = None

        # Act
        task.append_progress("First update")

        # Assert
        assert task.progress_count == 1
        assert task.progress_history is not None
        assert "progress_1" in task.progress_history

    def test_to_dict_includes_progress_fields(self):
        """Test that to_dict includes the new progress fields"""
        # Arrange
        task = Task(
            id=TaskId("test-id"),
            title="Test Task",
            description="Test Description",
            status=TaskStatus.todo(),
            priority=Priority.medium()
        )
        task.append_progress("Test progress")

        # Act
        task_dict = task.to_dict()

        # Assert
        assert "progress_history" in task_dict
        assert "progress_count" in task_dict
        assert task_dict["progress_count"] == 1
        assert "progress_1" in task_dict["progress_history"]