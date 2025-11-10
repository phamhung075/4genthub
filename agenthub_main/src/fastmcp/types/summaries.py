"""
Summary DTOs - Lightweight objects for list views
Matches frontend types in taskTypes.ts
"""

from __future__ import annotations

from typing import Any

from pydantic import BaseModel, ConfigDict, Field


class TaskSummaryDTO(BaseModel):
    """Task summary matching frontend TaskSummary interface"""
    id: str
    title: str
    status: str
    priority: str
    subtask_count: int
    assignees_count: int
    assignees: list[str] | None = None
    has_dependencies: bool
    dependency_count: int | None = None
    has_context: bool
    git_branch_id: str | None = None  # Required by frontend Pydantic validation
    project_id: str | None = None  # Required by frontend Pydantic validation
    created_at: str | None = None
    updated_at: str | None = None

    model_config = ConfigDict(from_attributes=True)


class SubtaskSummaryDTO(BaseModel):
    """Subtask summary matching frontend SubtaskSummary interface"""
    id: str
    task_id: str  # Parent task ID - required by frontend validation
    title: str
    status: str
    priority: str
    assignees_count: int
    assignees: list[str] | None = None
    progress_percentage: int | None = None
    created_at: str | None = None
    updated_at: str | None = None

    model_config = ConfigDict(from_attributes=True)


class BranchSummaryDTO(BaseModel):
    """Branch summary matching frontend BranchSummary interface"""
    id: str
    project_id: str
    name: str
    git_branch_name: str | None = None
    status: str | None = None
    priority: str | None = None
    task_count: int
    completed_tasks: int
    in_progress_tasks: int
    blocked_tasks: int
    todo_tasks: int
    progress_percentage: int
    last_activity: str | None = None
    has_urgent_tasks: bool | None = None
    is_completed: bool | None = None
    task_counts: dict[str, Any] | None = None

    model_config = ConfigDict(from_attributes=True)


class ProjectSummaryDTO(BaseModel):
    """Project summary matching frontend ProjectSummary interface"""
    id: str
    name: str
    description: str | None = None
    branchCount: int = Field(alias="branchCount")
    totalTasks: int = Field(alias="totalTasks")
    completedTasks: int = Field(alias="completedTasks")

    model_config = ConfigDict(from_attributes=True, populate_by_name=True)


