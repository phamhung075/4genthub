"""
Project Lifecycle Domain Events

Standardized implementation using BaseDomainEvent.
All project-related events follow consistent patterns.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from .base import BaseDomainEvent


@dataclass(frozen=True)
class ProjectCreatedEvent(BaseDomainEvent):
    """Event raised when a project is created"""
    project_id: str = ""
    name: str = ""
    description: str | None = None
    status: str = 'active'


@dataclass(frozen=True)
class ProjectUpdatedEvent(BaseDomainEvent):
    """Event raised when a project is updated"""
    project_id: str = ""
    old_name: str | None = None
    new_name: str | None = None
    old_status: str | None = None
    new_status: str | None = None
    old_description: str | None = None
    new_description: str | None = None


@dataclass(frozen=True)
class ProjectDeletedEvent(BaseDomainEvent):
    """Event raised when a project is deleted"""
    project_id: str = ""
    name: str = ""
    branches_deleted: int = 0
    tasks_deleted: int = 0
    subtasks_deleted: int = 0
    contexts_deleted: int = 0


@dataclass(frozen=True)
class ProjectStatisticsUpdatedEvent(BaseDomainEvent):
    """Event raised when project statistics are updated"""
    project_id: str = ""
    branch_count: int = 0
    total_tasks: int = 0
    completed_tasks: int = 0
    in_progress_tasks: int = 0
    todo_tasks: int = 0
    overall_progress_percentage: float = 0.0


@dataclass(frozen=True)
class ProjectHealthChanged(BaseDomainEvent):
    """
    Event raised when project health metrics change.

    This is a new event added in Phase 5 to track project health status.
    """
    project_id: str = ""
    old_health_status: str = ""
    new_health_status: str = ""
    health_metrics: dict[str, Any] = field(default_factory=dict)
    reason: str | None = None


@dataclass(frozen=True)
class ProjectArchived(BaseDomainEvent):
    """Event raised when a project is archived"""
    project_id: str = ""
    name: str = ""
    archived_by: str = ""
    reason: str | None = None


__all__ = [
    'ProjectCreatedEvent',
    'ProjectUpdatedEvent',
    'ProjectDeletedEvent',
    'ProjectStatisticsUpdatedEvent',
    'ProjectHealthChanged',
    'ProjectArchived',
]