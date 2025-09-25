"""Task Domain Events - Legacy compatibility"""

from dataclasses import dataclass
from typing import Dict, Any
from .base import DomainEvent, create_event_metadata


@dataclass(frozen=True)
class TaskCreated(DomainEvent):
    """Event raised when a task is created."""
    task_id: str
    title: str
    description: str = ""

    @property
    def event_type(self) -> str:
        return "task_created"

    def to_dict(self) -> Dict[str, Any]:
        return {
            "event_type": self.event_type,
            "task_id": self.task_id,
            "title": self.title,
            "description": self.description
        }


@dataclass(frozen=True)
class TaskUpdated(DomainEvent):
    """Event raised when a task is updated."""
    task_id: str
    changes: Dict[str, Any]

    @property
    def event_type(self) -> str:
        return "task_updated"

    def to_dict(self) -> Dict[str, Any]:
        return {
            "event_type": self.event_type,
            "task_id": self.task_id,
            "changes": self.changes
        }


@dataclass(frozen=True)
class TaskRetrieved(DomainEvent):
    """Event raised when a task is retrieved."""
    task_id: str

    @property
    def event_type(self) -> str:
        return "task_retrieved"

    def to_dict(self) -> Dict[str, Any]:
        return {
            "event_type": self.event_type,
            "task_id": self.task_id
        }


@dataclass(frozen=True)
class TaskDeleted(DomainEvent):
    """Event raised when a task is deleted."""
    task_id: str

    @property
    def event_type(self) -> str:
        return "task_deleted"

    def to_dict(self) -> Dict[str, Any]:
        return {
            "event_type": self.event_type,
            "task_id": self.task_id
        }


# Re-export DomainEvent for compatibility
__all__ = ['DomainEvent', 'TaskCreated', 'TaskUpdated', 'TaskRetrieved', 'TaskDeleted']