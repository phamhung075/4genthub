"""Request DTO for adding a subtask to a task"""

from __future__ import annotations

from dataclasses import dataclass, field


@dataclass
class AddSubtaskRequest:
    task_id: str | int
    title: str
    description: str = ""
    assignees: list[str] = field(default_factory=list)
    priority: str | None = None
    status: str | None = None
    progress_percentage: int | None = None
    
    def __post_init__(self):
        """Validate request data"""
        if not self.title or self.title.strip() == "":
            raise ValueError("Title cannot be empty")
        
        if len(self.title) > 255:
            raise ValueError("Title too long (maximum 255 characters)")
        
        if self.description and len(self.description) > 2000:
            raise ValueError("Description too long (maximum 2000 characters)")
        
        # Validate assignees
        if self.assignees:
            for assignee in self.assignees:
                if not assignee or assignee.strip() == "":
                    raise ValueError("Assignee cannot be empty") 