"""
Task Lifecycle Domain Events

Standardized implementation using BaseDomainEvent.
All task-related events follow consistent patterns with immutable frozen dataclasses.
"""

from dataclasses import dataclass, field
from typing import Any

from .base import BaseDomainEvent


@dataclass(frozen=True)
class TaskCreatedEvent(BaseDomainEvent):
    """Event raised when a task is created"""
    task_id: str = ""
    branch_id: str = ""
    title: str = ""
    status: str = ""
    priority: str = ""
    assignees: list[str] = field(default_factory=list)
    user_id: str | None = None


@dataclass(frozen=True)
class TaskUpdatedEvent(BaseDomainEvent):
    """Event raised when a task is updated"""
    task_id: str = ""
    branch_id: str = ""
    old_status: str | None = None
    new_status: str | None = None
    old_branch_id: str | None = None
    new_branch_id: str | None = None
    changes: dict[str, Any] = field(default_factory=dict)
    user_id: str | None = None


@dataclass(frozen=True)
class TaskDeletedEvent(BaseDomainEvent):
    """Event raised when a task is deleted"""
    task_id: str = ""
    branch_id: str = ""
    status: str = ""
    title: str = ""
    user_id: str | None = None


@dataclass(frozen=True)
class TaskStatusChangedEvent(BaseDomainEvent):
    """Event raised when task status changes"""
    task_id: str = ""
    branch_id: str = ""
    old_status: str = ""
    new_status: str = ""
    user_id: str | None = None


@dataclass(frozen=True)
class TaskCompletedEvent(BaseDomainEvent):
    """
    Event raised when a task is completed.

    This is a new event added in Phase 5 to distinguish task completion
    from generic status changes. Provides rich context about what was accomplished.
    """
    task_id: str = ""
    branch_id: str = ""
    title: str = ""
    completion_summary: str = ""
    testing_notes: str | None = None
    completed_by: str | None = None
    time_spent_minutes: int | None = None
    insights_found: list[str] = field(default_factory=list)


@dataclass(frozen=True)
class TaskRetrievedEvent(BaseDomainEvent):
    """Event raised when a task is retrieved from repository"""
    task_id: str = ""
    branch_id: str | None = None
    user_id: str | None = None


@dataclass(frozen=True)
class TaskMovedToBranchEvent(BaseDomainEvent):
    """Event raised when task is moved to a different branch"""
    task_id: str = ""
    old_branch_id: str = ""
    new_branch_id: str = ""
    user_id: str | None = None


__all__ = [
    'TaskCreatedEvent',
    'TaskUpdatedEvent',
    'TaskDeletedEvent',
    'TaskStatusChangedEvent',
    'TaskCompletedEvent',
    'TaskRetrievedEvent',
    'TaskMovedToBranchEvent',
]