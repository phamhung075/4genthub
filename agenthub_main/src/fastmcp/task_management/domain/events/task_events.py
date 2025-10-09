"""
Task Domain Events - DEPRECATED

⚠️ DEPRECATION NOTICE (Phase 5 - 2025-10-09):
This file is deprecated and will be removed in a future release.
Use task_lifecycle_events.py instead for all task-related events.

Migration path:
- TaskCreated → TaskCreatedEvent (from task_lifecycle_events)
- TaskUpdated → TaskUpdatedEvent (from task_lifecycle_events)
- TaskDeleted → TaskDeletedEvent (from task_lifecycle_events)
- TaskCompleted → TaskCompletedEvent (from task_lifecycle_events)
- TaskRetrieved → TaskRetrievedEvent (from task_lifecycle_events)

Backward compatibility aliases are provided in __init__.py for existing code.
"""

from dataclasses import dataclass
from typing import Dict, Any, Optional
from .base import BaseDomainEvent, DomainEvent


@dataclass(frozen=True)
class TaskCreated(BaseDomainEvent):
    """Event raised when a task is created."""
    task_id: str = ""
    title: str = ""
    description: str = ""
    status: str = "todo"
    priority: str = "medium"


@dataclass(frozen=True)
class TaskUpdated(BaseDomainEvent):
    """Event raised when a task is updated."""
    task_id: str = ""
    changes: Dict[str, Any] = None

    def __post_init__(self):
        """Ensure changes dict is not None."""
        if self.changes is None:
            object.__setattr__(self, 'changes', {})


@dataclass(frozen=True)
class TaskRetrieved(BaseDomainEvent):
    """Event raised when a task is retrieved."""
    task_id: str = ""


@dataclass(frozen=True)
class TaskDeleted(BaseDomainEvent):
    """Event raised when a task is deleted."""
    task_id: str = ""
    title: Optional[str] = None
    status: Optional[str] = None


@dataclass(frozen=True)
class TaskCompleted(BaseDomainEvent):
    """
    Event raised when a task is completed.

    This is a dedicated completion event separate from TaskUpdated to allow
    specialized handling of task completion workflows.
    """
    task_id: str = ""
    title: str = ""
    completion_summary: Optional[str] = None
    testing_notes: Optional[str] = None


# Re-export for compatibility
__all__ = [
    'DomainEvent',
    'BaseDomainEvent',
    'TaskCreated',
    'TaskUpdated',
    'TaskRetrieved',
    'TaskDeleted',
    'TaskCompleted'
]