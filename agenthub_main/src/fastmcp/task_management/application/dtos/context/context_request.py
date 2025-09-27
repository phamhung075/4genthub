"""Context Request DTOs"""

from dataclasses import dataclass, field
from typing import Dict, Any, Optional, List
from datetime import datetime


@dataclass
class CreateContextRequest:
    """Request DTO for creating a new context following clean relationship chain"""
    task_id: str  # Primary key - contains all necessary context via task -> git_branch -> project -> user
    title: str
    description: str = ""
    status: Optional[str] = None
    priority: Optional[str] = None
    assignees: Optional[List[str]] = None
    labels: Optional[List[str]] = None
    estimated_effort: Optional[str] = None
    due_date: Optional[datetime] = None
    data: Optional[Dict[str, Any]] = None


@dataclass
class UpdateContextRequest:
    """Request DTO for updating a context following clean relationship chain"""
    task_id: str  # Primary key - contains all necessary context via task -> git_branch -> project -> user
    data: Optional[Dict[str, Any]] = None


@dataclass
class GetContextRequest:
    """Request DTO for getting a context following clean relationship chain"""
    task_id: str  # Primary key - contains all necessary context via task -> git_branch -> project -> user


@dataclass
class DeleteContextRequest:
    """Request DTO for deleting a context following clean relationship chain"""
    task_id: str  # Primary key - contains all necessary context via task -> git_branch -> project -> user


@dataclass
class ListContextsRequest:
    """Request DTO for listing contexts following clean relationship chain"""
    user_id: Optional[str] = None  # Only user_id needed since contexts are accessed via tasks
    project_id: str = ""  # Optional project_id for filtering contexts


@dataclass
class GetPropertyRequest:
    """Request DTO for getting a context property following clean relationship chain"""
    task_id: str  # Primary key - contains all necessary context via task -> git_branch -> project -> user
    property_path: str


@dataclass
class UpdatePropertyRequest:
    """Request DTO for updating a context property following clean relationship chain"""
    task_id: str  # Primary key - contains all necessary context via task -> git_branch -> project -> user
    property_path: str
    value: Any


@dataclass
class MergeContextRequest:
    """Request DTO for merging data into a context following clean relationship chain"""
    task_id: str  # Primary key - contains all necessary context via task -> git_branch -> project -> user
    data: Dict[str, Any]


@dataclass
class MergeDataRequest:
    """Request DTO for merging data into a context following clean relationship chain (alias for MergeContextRequest)"""
    task_id: str  # Primary key - contains all necessary context via task -> git_branch -> project -> user
    data: Dict[str, Any]


@dataclass
class AddInsightRequest:
    """Request DTO for adding an insight following clean relationship chain"""
    task_id: str  # Primary key - contains all necessary context via task -> git_branch -> project -> user
    agent: str
    category: str
    content: str
    importance: str = "medium"


@dataclass
class AddProgressRequest:
    """Request DTO for adding progress following clean relationship chain"""
    task_id: str  # Primary key - contains all necessary context via task -> git_branch -> project -> user
    action: str
    agent: str
    details: str = ""
    status: str = "completed"


@dataclass
class UpdateNextStepsRequest:
    """Request DTO for updating next steps following clean relationship chain"""
    task_id: str  # Primary key - contains all necessary context via task -> git_branch -> project -> user
    next_steps: List[str]