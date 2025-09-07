"""Minimal response DTO for task list operations"""

from dataclasses import dataclass
from typing import Optional, List
from datetime import datetime

@dataclass
class TaskListItemResponse:
    """Minimal task response for list operations - optimized for performance"""
    id: str
    title: str
    status: str
    priority: str
    progress_percentage: int = 0
    assignees_count: int = 0
    labels: List[str] = None
    due_date: Optional[str] = None
    updated_at: Optional[datetime] = None
    has_dependencies: bool = False
    is_blocked: bool = False
    
    def __init__(
        self,
        id: str,
        title: str,
        status: str,
        priority: str,
        progress_percentage: int = 0,
        assignees: List[str] = None,
        labels: List[str] = None,
        due_date: Optional[str] = None,
        updated_at: Optional[datetime] = None,
        dependencies: List[str] = None
    ):
        """Initialize minimal task list item"""
        self.id = id
        self.title = title
        self.status = status
        self.priority = priority
        self.progress_percentage = progress_percentage
        self.assignees_count = len(assignees) if assignees else 0
        self.labels = labels[:3] if labels else []  # Show first 3 labels only
        self.due_date = due_date
        self.updated_at = updated_at
        self.has_dependencies = bool(dependencies) if dependencies else False
        self.is_blocked = False  # Will be set based on dependency resolution if needed
    
    @classmethod
    def from_task_response(cls, task) -> 'TaskListItemResponse':
        """Create minimal response from full task response"""
        return cls(
            id=task.id,
            title=task.title,
            status=task.status,
            priority=task.priority,
            progress_percentage=getattr(task, 'progress_percentage', 0),
            assignees=getattr(task, 'assignees', []),
            labels=getattr(task, 'labels', []),
            due_date=getattr(task, 'due_date', None),
            updated_at=getattr(task, 'updated_at', None),
            dependencies=getattr(task, 'dependencies', [])
        )
    
    def to_dict(self):
        """Convert to dictionary for JSON serialization"""
        return {
            "id": self.id,
            "title": self.title,
            "status": self.status,
            "priority": self.priority,
            "progress_percentage": self.progress_percentage,
            "assignees_count": self.assignees_count,
            "labels": self.labels,
            "due_date": self.due_date,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
            "has_dependencies": self.has_dependencies,
            "is_blocked": self.is_blocked
        }