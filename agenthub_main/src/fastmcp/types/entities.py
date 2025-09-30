"""
Entity DTOs - Core domain objects
Matches frontend types in api.types.ts
"""

from typing import Optional, List, Dict, Any
from pydantic import BaseModel


class TaskDTO(BaseModel):
    """Task model matching frontend Task interface"""
    id: str
    title: str
    description: Optional[str] = None
    status: str
    priority: str
    assignees: Optional[List[str]] = None
    assignees_count: int
    subtask_count: int
    has_dependencies: bool
    dependency_count: Optional[int] = None
    dependencies: Optional[List[str]] = None
    has_context: bool
    context_id: Optional[str] = None
    context_data: Optional[Any] = None
    git_branch_id: str
    project_id: str
    created_at: Optional[str] = None
    updated_at: Optional[str] = None
    due_date: Optional[str] = None
    estimated_effort: Optional[str] = None
    labels: Optional[List[str]] = None
    details: Optional[str] = None
    progress_percentage: Optional[int] = None
    subtasks: Optional[List['SubtaskDTO']] = None

    class Config:
        from_attributes = True


class SubtaskDTO(BaseModel):
    """Subtask model matching frontend Subtask interface"""
    id: str
    task_id: str  # In frontend this is parent_task_id
    title: str
    description: Optional[str] = None
    status: str
    priority: str
    assignees: Optional[List[str]] = None
    assignees_count: int
    progress_percentage: Optional[int] = None
    created_at: Optional[str] = None
    updated_at: Optional[str] = None
    progress_notes: Optional[str] = None
    completion_summary: Optional[str] = None

    class Config:
        from_attributes = True


class ProjectDTO(BaseModel):
    """Project model matching frontend Project interface"""
    id: str
    name: str
    description: Optional[str] = None
    created_at: Optional[str] = None
    updated_at: Optional[str] = None
    owner_id: Optional[str] = None
    status: Optional[str] = None
    branch_count: Optional[int] = None
    task_count: Optional[int] = None
    git_branchs: Optional[Dict[str, 'BranchDTO']] = None  # API returns Record<string, Branch>
    branches: Optional[List['BranchDTO']] = None  # Legacy array format

    class Config:
        from_attributes = True


class BranchDTO(BaseModel):
    """Branch model matching frontend Branch interface"""
    id: str
    project_id: str
    name: str
    git_branch_name: str
    description: Optional[str] = None
    status: Optional[str] = None
    is_active: Optional[bool] = None
    created_at: Optional[str] = None
    updated_at: Optional[str] = None
    task_count: Optional[int] = None
    completed_tasks: Optional[int] = None

    class Config:
        from_attributes = True


class RuleDTO(BaseModel):
    """Rule model matching frontend Rule interface"""
    id: str
    name: str
    description: Optional[str] = None
    category: Optional[str] = None
    content: Optional[str] = None
    enabled: Optional[bool] = None
    created_at: Optional[str] = None
    updated_at: Optional[str] = None

    class Config:
        from_attributes = True