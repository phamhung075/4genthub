"""
Entity DTOs - Core domain objects
Matches frontend types in api.types.ts
"""

from __future__ import annotations

from typing import Any

from pydantic import BaseModel, ConfigDict


class TaskDTO(BaseModel):
    """
    TaskDTO - Complete task entity for API responses

    Matches frontend Task interface in api.types.ts for type-safe API contracts.
    Contains full task data including relationships and metadata.

    Fields:
        id: Unique task identifier (UUID string)
        title: Task title (max 200 characters per ORM)
        description: Optional detailed description (max 2000 characters per ORM)
        status: Current task status ('todo', 'in_progress', 'done', etc.)
        priority: Priority level ('low', 'medium', 'high', 'urgent', 'critical')
        assignees: List of assigned agent identifiers
        assignees_count: Denormalized count of assignees for performance
        subtask_count: Denormalized count of subtasks (updated atomically via domain methods)

    Note: subtask_count is maintained through Task.add_subtask() and Task.remove_subtask()
          domain methods to ensure atomicity and consistency.

    Example:
        {
            "id": "123e4567-e89b-12d3-a456-426614174000",
            "title": "Implement authentication",
            "status": "in_progress",
            "priority": "high",
            "subtask_count": 3,
            "assignees_count": 2
        }
    """

    id: str
    title: str
    description: str | None = None
    status: str
    priority: str
    assignees: list[str] | None = None
    assignees_count: int
    subtask_count: int
    has_dependencies: bool
    dependency_count: int | None = None
    dependencies: list[str] | None = None
    has_context: bool
    context_id: str | None = None
    context_data: Any | None = None
    git_branch_id: str | None = None
    project_id: str | None = None
    created_at: str | None = None
    updated_at: str | None = None
    due_date: str | None = None
    estimated_effort: str | None = None
    labels: list[str] | None = None
    details: str | None = None
    progress_percentage: int | None = None
    progress_history: dict[str, Any] | None = None
    progress_count: int | None = None
    subtasks: list[SubtaskDTO] | None = None

    model_config = ConfigDict(from_attributes=True)


class SubtaskDTO(BaseModel):
    """
    SubtaskDTO - Complete subtask entity for API responses

    Matches frontend Subtask interface in api.types.ts.
    Represents a decomposed piece of work within a parent task.

    Fields:
        id: Unique subtask identifier (UUID string)
        task_id: Parent task identifier (called parent_task_id in frontend)
        title: Subtask title
        description: Optional detailed description
        status: Current status ('todo', 'in_progress', 'done', etc.)
        priority: Priority level (inherits from parent if not set)
        assignees: List of assigned agent IDs (inherits from parent if empty)
        assignees_count: Count of assigned agents
        progress_percentage: Completion percentage (0-100)

    Note: Subtasks inherit assignees from parent task if none specified,
          implementing the Agent Inheritance pattern for workflow efficiency.

    Example:
        {
            "id": "456e7890-e89b-12d3-a456-426614174001",
            "task_id": "123e4567-e89b-12d3-a456-426614174000",
            "title": "Design login UI",
            "status": "done",
            "priority": "high",
            "assignees_count": 1,
            "progress_percentage": 100
        }
    """

    id: str
    task_id: str  # In frontend this is parent_task_id
    title: str
    description: str | None = None
    status: str
    priority: str
    assignees: list[str] | None = None
    assignees_count: int
    progress_percentage: int | None = None
    progress_history: dict[str, Any] | None = (
        None  # Detailed progress tracking with timestamped entries
    )
    progress_count: int | None = None  # Number of progress entries
    created_at: str | None = None
    updated_at: str | None = None
    progress_notes: str | None = None
    completion_summary: str | None = None

    model_config = ConfigDict(from_attributes=True)


class ProjectDTO(BaseModel):
    """Project model matching frontend Project interface"""

    id: str
    name: str
    description: str | None = None
    created_at: str | None = None
    updated_at: str | None = None
    owner_id: str | None = None
    status: str | None = None
    branch_count: int | None = None
    task_count: int | None = None
    git_branchs: dict[str, BranchDTO] | None = (
        None  # API returns Record<string, Branch>
    )
    branches: list[BranchDTO] | None = None  # Legacy array format

    model_config = ConfigDict(from_attributes=True)


class BranchDTO(BaseModel):
    """Branch model matching frontend Branch interface"""

    id: str
    project_id: str
    name: str
    git_branch_name: str
    description: str | None = None
    status: str | None = None
    is_active: bool | None = None
    created_at: str | None = None
    updated_at: str | None = None
    task_count: int | None = None
    completed_tasks: int | None = None

    model_config = ConfigDict(from_attributes=True)


class RuleDTO(BaseModel):
    """Rule model matching frontend Rule interface"""

    id: str
    name: str
    description: str | None = None
    category: str | None = None
    content: str | None = None
    enabled: bool | None = None
    created_at: str | None = None
    updated_at: str | None = None

    model_config = ConfigDict(from_attributes=True)
