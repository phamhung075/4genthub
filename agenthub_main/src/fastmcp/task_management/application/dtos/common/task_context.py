"""Context for current development task"""

from dataclasses import asdict, dataclass
from datetime import datetime
from typing import Literal

from .task_progress_info import TaskProgressInfo


@dataclass
class TaskContext:
    """Context for current development task"""

    id: str
    title: str
    description: str
    requirements: list[str]
    current_phase: Literal["planning", "coding", "testing", "review", "completed"]
    assigned_roles: list[str]
    primary_role: str
    context_data: dict
    created_at: datetime
    updated_at: datetime
    progress: TaskProgressInfo

    def to_dict(self) -> dict:
        result = asdict(self)
        result["created_at"] = self.created_at.isoformat()
        result["updated_at"] = self.updated_at.isoformat()
        return result
