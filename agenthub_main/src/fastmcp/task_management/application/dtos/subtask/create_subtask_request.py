"""
DTO for subtask creation requests.
"""

from __future__ import annotations

from dataclasses import dataclass


@dataclass
class CreateSubtaskRequest:
    """Request DTO for creating a new subtask."""
    
    task_id: str
    title: str
    description: str | None = None
    status: str | None = "todo"
    priority: str | None = "medium"
    assignees: list[str] | None = None
    
    def validate(self) -> None:
        """Validate the request data."""
        if not self.task_id:
            raise ValueError("task_id is required")
        if not self.title:
            raise ValueError("title is required")
        if self.status not in ["todo", "in_progress", "done"]:
            raise ValueError(f"Invalid status: {self.status}")