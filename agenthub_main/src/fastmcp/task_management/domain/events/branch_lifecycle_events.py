"""
Branch Lifecycle Domain Events

Clean implementation of branch-related domain events.
NO backward compatibility, NO legacy code.
"""

from dataclasses import dataclass
from datetime import datetime
from typing import Any


@dataclass
class BranchEvent:
    """Base class for branch domain events"""
    branch_id: str = ""
    project_id: str | None
    timestamp: datetime
    user_id: str | None = None

    @classmethod
    def create(cls, **kwargs):
        """Factory method to create event with timestamp"""
        if 'timestamp' not in kwargs:
            kwargs['timestamp'] = datetime.utcnow()
        return cls(**kwargs)

    def to_dict(self) -> dict[str, Any]:
        """Convert event to dictionary for serialization"""
        return {
            'branch_id': self.branch_id,
            'project_id': self.project_id,
            'timestamp': self.timestamp.isoformat(),
            'user_id': self.user_id,
            'event_type': self.__class__.__name__
        }


@dataclass
class BranchCreatedEvent(BranchEvent):
    """Event raised when a branch is created"""
    name: str = ""
    description: str | None = None
    status: str = 'active'

    def to_dict(self) -> dict[str, Any]:
        data = super().to_dict()
        data.update({
            'name': self.name,
            'description': self.description,
            'status': self.status
        })
        return data


@dataclass
class BranchUpdatedEvent(BranchEvent):
    """Event raised when a branch is updated"""
    old_name: str | None = None
    new_name: str | None = None
    old_status: str | None = None
    new_status: str | None = None
    old_task_count: int | None = None
    new_task_count: int | None = None

    def to_dict(self) -> dict[str, Any]:
        data = super().to_dict()
        data.update({
            'old_name': self.old_name,
            'new_name': self.new_name,
            'old_status': self.old_status,
            'new_status': self.new_status,
            'old_task_count': self.old_task_count,
            'new_task_count': self.new_task_count
        })
        return data


@dataclass
class BranchDeletedEvent(BranchEvent):
    """Event raised when a branch is deleted"""
    name: str = ""
    tasks_deleted: int = 0
    subtasks_deleted: int = 0
    contexts_deleted: int = 0

    def to_dict(self) -> dict[str, Any]:
        data = super().to_dict()
        data.update({
            'name': self.name,
            'tasks_deleted': self.tasks_deleted,
            'subtasks_deleted': self.subtasks_deleted,
            'contexts_deleted': self.contexts_deleted
        })
        return data


@dataclass
class BranchStatisticsUpdatedEvent(BranchEvent):
    """Event raised when branch statistics are updated"""
    task_count: int = 0
    completed_task_count: int = 0
    in_progress_task_count: int = 0
    todo_task_count: int = 0
    progress_percentage: float = 0.0

    def to_dict(self) -> dict[str, Any]:
        data = super().to_dict()
        data.update({
            'task_count': self.task_count,
            'completed_task_count': self.completed_task_count,
            'in_progress_task_count': self.in_progress_task_count,
            'todo_task_count': self.todo_task_count,
            'progress_percentage': self.progress_percentage
        })
        return data