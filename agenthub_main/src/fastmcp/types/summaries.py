"""
Summary DTOs - Lightweight objects for list views
Matches frontend types in taskTypes.ts
"""

from typing import Optional, List, Dict, Any
from pydantic import BaseModel, Field


class TaskSummaryDTO(BaseModel):
    """Task summary matching frontend TaskSummary interface"""
    id: str
    title: str
    status: str
    priority: str
    subtask_count: int
    assignees_count: int
    assignees: Optional[List[str]] = None
    has_dependencies: bool
    dependency_count: Optional[int] = None
    has_context: bool
    created_at: Optional[str] = None
    updated_at: Optional[str] = None

    class Config:
        from_attributes = True


class SubtaskSummaryDTO(BaseModel):
    """Subtask summary matching frontend SubtaskSummary interface"""
    id: str
    title: str
    status: str
    priority: str
    assignees_count: int
    assignees: Optional[List[str]] = None
    progress_percentage: Optional[int] = None
    created_at: Optional[str] = None
    updated_at: Optional[str] = None

    class Config:
        from_attributes = True


class BranchSummaryDTO(BaseModel):
    """Branch summary matching frontend BranchSummary interface"""
    id: str
    project_id: str
    name: str
    git_branch_name: Optional[str] = None
    status: Optional[str] = None
    priority: Optional[str] = None
    task_count: int
    completed_tasks: int
    in_progress_tasks: int
    blocked_tasks: int
    todo_tasks: int
    progress_percentage: int
    last_activity: Optional[str] = None
    has_urgent_tasks: Optional[bool] = None
    is_completed: Optional[bool] = None
    task_counts: Optional[Dict[str, Any]] = None

    class Config:
        from_attributes = True


class ProjectSummaryDTO(BaseModel):
    """Project summary matching frontend ProjectSummary interface"""
    id: str
    name: str
    description: Optional[str] = None
    branchCount: int = Field(alias="branchCount")
    totalTasks: int = Field(alias="totalTasks")
    completedTasks: int = Field(alias="completedTasks")

    class Config:
        from_attributes = True
        populate_by_name = True