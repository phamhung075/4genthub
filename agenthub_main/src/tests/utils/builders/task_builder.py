"""Task Builder for Test Data Creation"""

import uuid
from datetime import UTC, datetime
from typing import Any


class TaskBuilder:
    """Builder for creating test task data."""

    def __init__(self):
        """Initialize with default values."""
        self.task_id = str(uuid.uuid4())
        self.title = "Test Task"
        self.description = "Test task description"
        self.status = "todo"
        self.priority = "medium"
        self.details = ""
        self.estimated_effort = "2 hours"
        self.assignees = "coding-agent"
        self.labels: list[str] = []
        self.git_branch_id = str(uuid.uuid4())
        self.progress_percentage = 0
        self.created_at = datetime.now(UTC)
        self.updated_at = datetime.now(UTC)

    def with_id(self, task_id: str) -> "TaskBuilder":
        """Set task ID."""
        self.task_id = task_id
        return self

    def with_title(self, title: str) -> "TaskBuilder":
        """Set task title."""
        self.title = title
        return self

    def with_description(self, description: str) -> "TaskBuilder":
        """Set task description."""
        self.description = description
        return self

    def with_status(self, status: str) -> "TaskBuilder":
        """Set task status."""
        self.status = status
        return self

    def with_priority(self, priority: str) -> "TaskBuilder":
        """Set task priority."""
        self.priority = priority
        return self

    def with_details(self, details: str) -> "TaskBuilder":
        """Set task details."""
        self.details = details
        return self

    def with_assignee(self, assignee: str) -> "TaskBuilder":
        """Set task assignee."""
        self.assignees = assignee
        return self

    def with_assignees(self, assignees: str) -> "TaskBuilder":
        """Set multiple assignees (comma-separated)."""
        self.assignees = assignees
        return self

    def with_label(self, label: str) -> "TaskBuilder":
        """Add a label."""
        if label not in self.labels:
            self.labels.append(label)
        return self

    def with_labels(self, labels: list[str]) -> "TaskBuilder":
        """Set multiple labels."""
        self.labels = labels
        return self

    def with_git_branch_id(self, git_branch_id: str) -> "TaskBuilder":
        """Set git branch ID."""
        self.git_branch_id = git_branch_id
        return self

    def with_progress(self, percentage: int) -> "TaskBuilder":
        """Set progress percentage."""
        self.progress_percentage = percentage
        return self

    def build(self) -> dict[str, Any]:
        """Build and return the task data dictionary."""
        return {
            "id": self.task_id,
            "title": self.title,
            "description": self.description,
            "status": self.status,
            "priority": self.priority,
            "details": self.details,
            "estimated_effort": self.estimated_effort,
            "assignees": self.assignees,
            "labels": self.labels,
            "git_branch_id": self.git_branch_id,
            "progress_percentage": self.progress_percentage,
            "created_at": self.created_at.isoformat(),
            "updated_at": self.updated_at.isoformat(),
        }
