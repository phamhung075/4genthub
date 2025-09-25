"""Task Domain Events"""

from dataclasses import dataclass
from datetime import datetime
from typing import Optional
from enum import Enum


class TaskEventType(Enum):
    """Types of task domain events"""
    CREATED = "task_created"
    UPDATED = "task_updated"
    DELETED = "task_deleted"
    STATUS_CHANGED = "task_status_changed"
    ASSIGNED = "task_assigned"
    UNASSIGNED = "task_unassigned"
    MOVED_TO_BRANCH = "task_moved_to_branch"


@dataclass
class TaskEvent:
    """Base class for task domain events"""
    event_type: TaskEventType
    task_id: str
    branch_id: Optional[str]
    user_id: Optional[str]
    timestamp: datetime

    @classmethod
    def now(cls):
        """Get current timestamp"""
        return datetime.utcnow()


@dataclass
class TaskCreatedEvent(TaskEvent):
    """Event raised when a task is created"""
    title: str
    status: str
    priority: str
    assignees: list

    @classmethod
    def create(cls, task_id: str, branch_id: str, title: str, status: str,
              priority: str, assignees: list, user_id: Optional[str] = None):
        return cls(
            event_type=TaskEventType.CREATED,
            task_id=task_id,
            branch_id=branch_id,
            user_id=user_id,
            timestamp=cls.now(),
            title=title,
            status=status,
            priority=priority,
            assignees=assignees
        )


@dataclass
class TaskUpdatedEvent(TaskEvent):
    """Event raised when a task is updated"""
    old_status: Optional[str]
    new_status: Optional[str]
    old_branch_id: Optional[str]
    new_branch_id: Optional[str]
    changes: dict

    @classmethod
    def create(cls, task_id: str, branch_id: str, old_status: Optional[str],
              new_status: Optional[str], old_branch_id: Optional[str] = None,
              new_branch_id: Optional[str] = None, changes: dict = None,
              user_id: Optional[str] = None):
        return cls(
            event_type=TaskEventType.UPDATED,
            task_id=task_id,
            branch_id=new_branch_id or branch_id,
            user_id=user_id,
            timestamp=cls.now(),
            old_status=old_status,
            new_status=new_status,
            old_branch_id=old_branch_id,
            new_branch_id=new_branch_id,
            changes=changes or {}
        )


@dataclass
class TaskDeletedEvent(TaskEvent):
    """Event raised when a task is deleted"""
    status: str
    title: str

    @classmethod
    def create(cls, task_id: str, branch_id: str, status: str, title: str,
              user_id: Optional[str] = None):
        return cls(
            event_type=TaskEventType.DELETED,
            task_id=task_id,
            branch_id=branch_id,
            user_id=user_id,
            timestamp=cls.now(),
            status=status,
            title=title
        )


@dataclass
class TaskStatusChangedEvent(TaskEvent):
    """Event raised when task status changes"""
    old_status: str
    new_status: str

    @classmethod
    def create(cls, task_id: str, branch_id: str, old_status: str,
              new_status: str, user_id: Optional[str] = None):
        return cls(
            event_type=TaskEventType.STATUS_CHANGED,
            task_id=task_id,
            branch_id=branch_id,
            user_id=user_id,
            timestamp=cls.now(),
            old_status=old_status,
            new_status=new_status
        )


@dataclass
class TaskMovedToBranchEvent(TaskEvent):
    """Event raised when task is moved to a different branch"""
    old_branch_id: str
    new_branch_id: str

    @classmethod
    def create(cls, task_id: str, old_branch_id: str, new_branch_id: str,
              user_id: Optional[str] = None):
        return cls(
            event_type=TaskEventType.MOVED_TO_BRANCH,
            task_id=task_id,
            branch_id=new_branch_id,
            user_id=user_id,
            timestamp=cls.now(),
            old_branch_id=old_branch_id,
            new_branch_id=new_branch_id
        )