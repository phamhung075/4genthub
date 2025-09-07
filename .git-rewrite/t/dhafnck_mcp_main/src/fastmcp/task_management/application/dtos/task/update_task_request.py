"""Request DTO for updating a task with hierarchical storage support"""

from dataclasses import dataclass
from typing import Any, Optional, List

@dataclass
class UpdateTaskRequest:
    """Request DTO for updating a task with hierarchical storage support"""
    task_id: Any
    title: Optional[str] = None
    description: Optional[str] = None
    status: Optional[str] = None
    priority: Optional[str] = None
    details: Optional[str] = None
    estimated_effort: Optional[str] = None
    assignees: Optional[List[str]] = None
    labels: Optional[List[str]] = None
    due_date: Optional[str] = None
    context_id: Optional[str] = None 