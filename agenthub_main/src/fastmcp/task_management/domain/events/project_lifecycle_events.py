"""
Project Lifecycle Domain Events

Clean implementation of project-related domain events.
NO backward compatibility, NO legacy code.
"""

from dataclasses import dataclass
from typing import Optional, Dict, Any, List
from datetime import datetime


@dataclass
class ProjectEvent:
    """Base class for project domain events"""
    project_id: str
    timestamp: datetime
    user_id: Optional[str] = None

    @classmethod
    def create(cls, **kwargs):
        """Factory method to create event with timestamp"""
        if 'timestamp' not in kwargs:
            kwargs['timestamp'] = datetime.utcnow()
        return cls(**kwargs)

    def to_dict(self) -> Dict[str, Any]:
        """Convert event to dictionary for serialization"""
        return {
            'project_id': self.project_id,
            'timestamp': self.timestamp.isoformat(),
            'user_id': self.user_id,
            'event_type': self.__class__.__name__
        }


@dataclass
class ProjectCreatedEvent(ProjectEvent):
    """Event raised when a project is created"""
    name: str
    description: Optional[str] = None
    status: str = 'active'

    def to_dict(self) -> Dict[str, Any]:
        data = super().to_dict()
        data.update({
            'name': self.name,
            'description': self.description,
            'status': self.status
        })
        return data


@dataclass
class ProjectUpdatedEvent(ProjectEvent):
    """Event raised when a project is updated"""
    old_name: Optional[str] = None
    new_name: Optional[str] = None
    old_status: Optional[str] = None
    new_status: Optional[str] = None
    old_description: Optional[str] = None
    new_description: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        data = super().to_dict()
        data.update({
            'old_name': self.old_name,
            'new_name': self.new_name,
            'old_status': self.old_status,
            'new_status': self.new_status,
            'old_description': self.old_description,
            'new_description': self.new_description
        })
        return data


@dataclass
class ProjectDeletedEvent(ProjectEvent):
    """Event raised when a project is deleted"""
    name: str
    branches_deleted: int = 0
    tasks_deleted: int = 0
    subtasks_deleted: int = 0
    contexts_deleted: int = 0

    def to_dict(self) -> Dict[str, Any]:
        data = super().to_dict()
        data.update({
            'name': self.name,
            'branches_deleted': self.branches_deleted,
            'tasks_deleted': self.tasks_deleted,
            'subtasks_deleted': self.subtasks_deleted,
            'contexts_deleted': self.contexts_deleted
        })
        return data


@dataclass
class ProjectStatisticsUpdatedEvent(ProjectEvent):
    """Event raised when project statistics are updated"""
    branch_count: int
    total_tasks: int
    completed_tasks: int
    in_progress_tasks: int
    todo_tasks: int
    overall_progress_percentage: float

    def to_dict(self) -> Dict[str, Any]:
        data = super().to_dict()
        data.update({
            'branch_count': self.branch_count,
            'total_tasks': self.total_tasks,
            'completed_tasks': self.completed_tasks,
            'in_progress_tasks': self.in_progress_tasks,
            'todo_tasks': self.todo_tasks,
            'overall_progress_percentage': self.overall_progress_percentage
        })
        return data