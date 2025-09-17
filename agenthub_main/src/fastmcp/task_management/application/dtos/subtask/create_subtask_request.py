"""
DTO for subtask creation requests.
"""

from dataclasses import dataclass
from typing import Optional, List


@dataclass
class CreateSubtaskRequest:
    """Request DTO for creating a new subtask."""
    
    task_id: str
    title: str
    description: Optional[str] = None
    status: Optional[str] = "todo"
    priority: Optional[str] = "medium"
    assignees: Optional[List[str]] = None
    
    def validate(self) -> None:
        """Validate the request data."""
        if not self.task_id:
            raise ValueError("task_id is required")
        if not self.title:
            raise ValueError("title is required")
        if self.status not in ["todo", "in_progress", "done"]:
            raise ValueError(f"Invalid status: {self.status}")