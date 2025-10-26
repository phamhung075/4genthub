"""Unit tests for Task datetime timezone handling."""

import pytest
from datetime import datetime, timezone
from uuid import uuid4

from fastmcp.task_management.domain.entities.task import Task, normalize_datetime
from fastmcp.task_management.domain.value_objects.task_id import TaskId
from fastmcp.task_management.domain.value_objects.task_status import TaskStatus
from fastmcp.task_management.domain.value_objects.priority import Priority


class TestNormalizeDatetime:
    """Test the normalize_datetime utility function."""

    def test_normalize_naive_datetime_string(self):
        """Test normalizing a naive datetime string."""
        result = normalize_datetime("2025-10-29")
        assert result.tzinfo == timezone.utc
        assert result.year == 2025
        assert result.month == 10
        assert result.day == 29

    def test_normalize_aware_datetime_string(self):
        """Test normalizing a timezone-aware datetime string."""
        result = normalize_datetime("2025-10-29T23:59:59+00:00")
        assert result.tzinfo == timezone.utc
        assert result.year == 2025
        assert result.month == 10
        assert result.day == 29
        assert result.hour == 23
        assert result.minute == 59

    def test_normalize_aware_datetime_string_with_offset(self):
        """Test normalizing a timezone-aware datetime with non-UTC offset."""
        # Input with +05:00 offset should be converted to UTC
        result = normalize_datetime("2025-10-29T23:59:59+05:00")
        assert result.tzinfo == timezone.utc
        # UTC time should be 5 hours earlier
        assert result.hour == 18
        assert result.minute == 59

    def test_normalize_naive_datetime_object(self):
        """Test normalizing a naive datetime object."""
        naive_dt = datetime(2025, 10, 29, 12, 0, 0)
        result = normalize_datetime(naive_dt)
        assert result.tzinfo == timezone.utc
        assert result.year == 2025
        assert result.month == 10
        assert result.day == 29
        assert result.hour == 12

    def test_normalize_aware_datetime_object(self):
        """Test normalizing an aware datetime object."""
        aware_dt = datetime(2025, 10, 29, 12, 0, 0, tzinfo=timezone.utc)
        result = normalize_datetime(aware_dt)
        assert result.tzinfo == timezone.utc
        assert result == aware_dt


class TestTaskDueDateHandling:
    """Test Task entity due_date handling with timezone normalization."""

    def test_update_due_date_with_naive_string(self):
        """Test updating task due_date with naive datetime string."""
        task = Task(
            id=TaskId(str(uuid4())),
            title="Test Task",
            description="Test description",
            status=TaskStatus.todo(),
            priority=Priority.medium(),
            git_branch_id=str(uuid4())
        )

        # Update with naive datetime format
        task.update_due_date("2025-10-29")

        # Should be stored as UTC-aware ISO string
        assert task.due_date is not None
        assert "+00:00" in task.due_date or "Z" in task.due_date or task.due_date.endswith("T00:00:00")

        # Should be parseable as UTC-aware datetime
        parsed = datetime.fromisoformat(task.due_date)
        assert parsed.tzinfo is not None

    def test_update_due_date_with_aware_string(self):
        """Test updating task due_date with timezone-aware datetime string."""
        task = Task(
            id=TaskId(str(uuid4())),
            title="Test Task",
            description="Test description",
            status=TaskStatus.todo(),
            priority=Priority.medium(),
            git_branch_id=str(uuid4())
        )

        # Update with aware datetime format
        task.update_due_date("2025-10-29T23:59:59+00:00")

        # Should be stored as UTC-aware ISO string
        assert task.due_date is not None
        parsed = datetime.fromisoformat(task.due_date)
        assert parsed.tzinfo == timezone.utc
        assert parsed.hour == 23
        assert parsed.minute == 59

    def test_update_due_date_with_none(self):
        """Test updating task due_date with None (clearing the date)."""
        task = Task(
            id=TaskId(str(uuid4())),
            title="Test Task",
            description="Test description",
            status=TaskStatus.todo(),
            priority=Priority.medium(),
            git_branch_id=str(uuid4()),
            due_date="2025-10-29"
        )

        # Clear due_date
        task.update_due_date(None)
        assert task.due_date is None

    def test_update_due_date_with_invalid_format(self):
        """Test updating task due_date with invalid format raises error."""
        task = Task(
            id=TaskId(str(uuid4())),
            title="Test Task",
            description="Test description",
            status=TaskStatus.todo(),
            priority=Priority.medium(),
            git_branch_id=str(uuid4())
        )

        # Invalid format should raise ValueError
        with pytest.raises(ValueError, match="Invalid due date format"):
            task.update_due_date("not-a-date")

    def test_due_date_comparison_no_error(self):
        """Test comparing tasks with different due_date formats doesn't crash."""
        task1 = Task(
            id=TaskId(str(uuid4())),
            title="Task 1",
            description="Test description 1",
            status=TaskStatus.todo(),
            priority=Priority.medium(),
            git_branch_id=str(uuid4())
        )
        task1.update_due_date("2025-10-29")

        task2 = Task(
            id=TaskId(str(uuid4())),
            title="Task 2",
            description="Test description 2",
            status=TaskStatus.todo(),
            priority=Priority.medium(),
            git_branch_id=str(uuid4())
        )
        task2.update_due_date("2025-10-30T00:00:00+00:00")

        # Should not crash on comparison
        date1 = datetime.fromisoformat(task1.due_date)
        date2 = datetime.fromisoformat(task2.due_date)
        assert date1 < date2

    def test_is_overdue_with_past_naive_date(self):
        """Test is_overdue returns True for past naive datetime."""
        task = Task(
            id=TaskId(str(uuid4())),
            title="Test Task",
            description="Test description",
            status=TaskStatus.todo(),
            priority=Priority.medium(),
            git_branch_id=str(uuid4())
        )

        # Set due_date to a past date
        task.update_due_date("2020-01-01")

        # Should be overdue
        assert task.is_overdue() is True

    def test_is_overdue_with_future_aware_date(self):
        """Test is_overdue returns False for future aware datetime."""
        task = Task(
            id=TaskId(str(uuid4())),
            title="Test Task",
            description="Test description",
            status=TaskStatus.todo(),
            priority=Priority.medium(),
            git_branch_id=str(uuid4())
        )

        # Set due_date to a future date
        task.update_due_date("2030-12-31T23:59:59+00:00")

        # Should not be overdue
        assert task.is_overdue() is False

    def test_is_overdue_with_completed_task(self):
        """Test is_overdue returns False for completed task even if past due."""
        task = Task(
            id=TaskId(str(uuid4())),
            title="Test Task",
            description="Test description",
            status=TaskStatus.done(),
            priority=Priority.medium(),
            git_branch_id=str(uuid4())
        )

        # Set due_date to a past date
        task.update_due_date("2020-01-01")

        # Should not be overdue because task is completed
        assert task.is_overdue() is False
