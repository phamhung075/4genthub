"""
Entity DTOs - Core domain objects
Matches frontend types in api.types.ts
"""

from typing import Optional, List, Dict, Any
from pydantic import BaseModel, Field, ConfigDict


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
    git_branch_id: Optional[str] = None
    project_id: Optional[str] = None
    created_at: Optional[str] = None
    updated_at: Optional[str] = None
    due_date: Optional[str] = None
    estimated_effort: Optional[str] = None
    labels: Optional[List[str]] = None
    details: Optional[str] = None
    progress_percentage: Optional[int] = None
    progress_history: Optional[Dict[str, Any]] = None
    progress_count: Optional[int] = None
    subtasks: Optional[List['SubtaskDTO']] = None

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

    model_config = ConfigDict(from_attributes=True)


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

    model_config = ConfigDict(from_attributes=True)


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

    model_config = ConfigDict(from_attributes=True)


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

    model_config = ConfigDict(from_attributes=True)


