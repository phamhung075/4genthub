"""
Project Lifecycle Domain Events

Standardized implementation using BaseDomainEvent.
All project-related events follow consistent patterns.
"""

from dataclasses import dataclass, field
from typing import Optional, Dict, Any, List
from datetime import datetime
from .base import BaseDomainEvent


@dataclass(frozen=True)
class ProjectCreatedEvent(BaseDomainEvent):
    """Event raised when a project is created"""
    project_id: str = ""
    name: str = ""
    description: Optional[str] = None
    status: str = 'active'


@dataclass(frozen=True)
class ProjectUpdatedEvent(BaseDomainEvent):
    """Event raised when a project is updated"""
    project_id: str = ""
    old_name: Optional[str] = None
    new_name: Optional[str] = None
    old_status: Optional[str] = None
    new_status: Optional[str] = None
    old_description: Optional[str] = None
    new_description: Optional[str] = None


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
    health_metrics: Dict[str, Any] = field(default_factory=dict)
    reason: Optional[str] = None


@dataclass(frozen=True)
class ProjectArchived(BaseDomainEvent):
    """Event raised when a project is archived"""
    project_id: str = ""
    name: str = ""
    archived_by: str = ""
    reason: Optional[str] = None


__all__ = [
    'ProjectCreatedEvent',
    'ProjectUpdatedEvent',
    'ProjectDeletedEvent',
    'ProjectStatisticsUpdatedEvent',
    'ProjectHealthChanged',
    'ProjectArchived',
]