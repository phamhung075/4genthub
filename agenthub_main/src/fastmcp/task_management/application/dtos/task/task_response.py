"""Response DTO for task operations"""

import logging
from dataclasses import dataclass
from datetime import datetime
from typing import Any

from ...exceptions import RepositoryProviderError
from .dependency_info import DependencyRelationships


@dataclass
class TaskResponse:
    """Response DTO for task operations following clean relationship chain"""
    id: str
    title: str
    description: str
    status: str
    priority: str
    details: str  # Backward compatibility - formatted progress_history text
    estimated_effort: str
    assignees: list[str]
    labels: list[str]
    dependencies: list[str]
    subtasks: list[dict[str, Any]]
    due_date: str | None
    created_at: datetime | None
    updated_at: datetime | None
    git_branch_id: str | None = None  # Links to git_branch which contains project and user info
    project_id: str | None = None  # Project ID fetched via repository join (maintains normalization)
    context_id: str | None = None
    context_data: dict[str, Any] | None = None
    dependency_relationships: DependencyRelationships | None = None  # Enhanced dependency information
    progress_percentage: int = 0  # Task completion progress (0-100)
    progress_history: dict[str, Any] | None = None  # Full progress history structure
    progress_count: int = 0  # Number of progress entries
    # subtask_count is now a derived @property - see below
    completed_subtasks: int = 0  # Number of completed subtasks

    def __init__(
            self,
            id: str,
            title: str,
            description: str,
            status: str,
            priority: str,
            details: str,
            estimated_effort: str,
            assignees: list[str],
            labels: list[str],
            dependencies: list[str],
            subtasks: list[dict[str, Any]],
            due_date: str | None,
            created_at: datetime | None,
            updated_at: datetime | None,
            git_branch_id: str | None = None,  # Following clean relationship chain
            project_id: str | None = None,  # Project ID from repository join
            context_id: str | None = None,
            context_data: dict[str, Any] | None = None,
            dependency_relationships: DependencyRelationships | None = None,
            progress_percentage: int = 0,
            progress_history: dict[str, Any] | None = None,
            progress_count: int = 0,
            completed_subtasks: int = 0
        ):
        """Initialize TaskResponse following clean relationship chain with git_branch_id, context_id, and context_data"""
        self.id = id
        self.title = title
        self.description = description
        self.git_branch_id = git_branch_id
        self.project_id = project_id
        self.status = status
        self.priority = priority
        self.details = details
        self.estimated_effort = estimated_effort
        self.assignees = assignees
        self.labels = labels
        self.dependencies = dependencies
        self.subtasks = subtasks
        self.due_date = due_date
        self.created_at = created_at
        self.updated_at = updated_at
        self.context_id = context_id
        self.context_data = context_data
        self.dependency_relationships = dependency_relationships
        self.progress_percentage = progress_percentage
        self.progress_history = progress_history or {}
        self.progress_count = progress_count
        # subtask_count is now a derived property - not stored
        self.completed_subtasks = completed_subtasks

    @property
    def subtask_count(self) -> int:
        """Total number of subtasks (derived from subtasks array length).

        This is a derived property that automatically reflects the current
        number of subtasks by computing len(self.subtasks). This ensures
        the count is always accurate even when subtasks are added/removed.

        Returns:
            int: Number of subtasks in the subtasks array
        """
        return len(self.subtasks) if self.subtasks else 0

    @classmethod
    def from_domain(cls, task, git_branch_repository=None, context_data: dict[str, Any] | None = None,
                   dependency_relationships: DependencyRelationships | None = None,
                   project_id: str | None = None,
                   completed_subtasks: int | None = None) -> 'TaskResponse':
        """Create response DTO from domain entity with optional context data.

        Args:
            task: Domain task entity
            git_branch_repository: Repository for fetching project_id via join (Option 1 - Pure DDD)
            context_data: Optional context data
            dependency_relationships: Optional dependency information
            project_id: Optional pre-fetched project_id (batch loading optimization)
            completed_subtasks: Optional pre-fetched completed subtask count (batch loading optimization)

        Returns:
            TaskResponse with project_id populated via repository join or batch loading
        """
        task_dict = task.to_dict()

        # BATCH LOADING OPTIMIZATION: Use provided project_id if available
        # This eliminates N+1 query problem when processing lists of tasks
        if project_id is not None:
            # Fast path: project_id already provided via batch loading
            pass
        elif git_branch_repository and task_dict.get("git_branch_id"):
            # Slow path: fetch individually (backward compatibility for single task operations)
            try:
                git_branch = git_branch_repository.get_by_id(task_dict["git_branch_id"])
                project_id = git_branch.project_id if git_branch else None
            except Exception as e:
                # CRITICAL: project_id is required by frontend TypeScript contract
                logging.error(
                    f"CRITICAL: Failed to fetch project_id for git_branch {task_dict.get('git_branch_id')}: {e}",
                    exc_info=True
                )
                raise RepositoryProviderError(
                    f"Failed to fetch required project_id: {e}"
                ) from e
        else:
            # No repository and no pre-fetched project_id
            project_id = None

        # Parse datetime strings back to datetime objects if they're strings
        created_at = task_dict["created_at"]
        if isinstance(created_at, str):
            created_at = datetime.fromisoformat(created_at)

        updated_at = task_dict["updated_at"]
        if isinstance(updated_at, str):
            updated_at = datetime.fromisoformat(updated_at)


        # Get progress_history and format details for backward compatibility
        progress_history = task_dict.get("progress_history", {})
        progress_count = task_dict.get("progress_count", 0)

        # Use task's get_progress_history_text() method for details field (backward compatibility)
        details = task.get_progress_history_text() if hasattr(task, 'get_progress_history_text') else ""

        # Fix 3: Add @ prefix to assignees if not present
        assignees_with_prefix = [f"@{a}" if not a.startswith("@") else a for a in task_dict["assignees"]]

        # Fix 2: Get completed_subtasks count
        # Note: subtask_count is now a derived @property, not computed here
        # BATCH LOADING OPTIMIZATION: Use provided completed_subtasks if available
        # This eliminates N+1 query problem when processing lists of tasks
        if completed_subtasks is not None:
            # Fast path: count provided via batch query
            actual_completed = completed_subtasks
        else:
            # Fallback: Extract from task entity if available
            actual_completed = task_dict.get("completed_subtasks", 0)

        return cls(
            id=task_dict["id"],
            title=task_dict["title"],
            description=task_dict["description"],
            status=task_dict["status"],
            priority=task_dict["priority"],
            details=details,  # Formatted progress history text for backward compatibility
            estimated_effort=task_dict["estimatedEffort"],
            assignees=assignees_with_prefix,  # Fix 3: Use assignees with @ prefix
            labels=task_dict["labels"],
            dependencies=task_dict["dependencies"],
            subtasks=task_dict["subtasks"],
            due_date=task_dict["dueDate"],
            created_at=created_at,
            updated_at=updated_at,
            git_branch_id=task_dict.get("git_branch_id"),  # Following clean relationship chain
            project_id=project_id,  # Fix 4: Project ID via repository join (maintains normalization)
            context_id=task_dict.get("context_id"),
            context_data=context_data,
            dependency_relationships=dependency_relationships,
            progress_percentage=task_dict.get("progress_percentage", 0),
            progress_history=progress_history,
            progress_count=progress_count,
            # subtask_count is now a derived @property - not passed to constructor
            completed_subtasks=actual_completed  # Fix 2: Accurate completed subtask count from batch query
        )
    
    def to_dict(self) -> dict[str, Any]:
        """Convert TaskResponse to dictionary representation with JSON-safe datetime serialization"""
        # OPTIMIZATION: Serialize context_data with embedded=True to remove duplicates
        context_data_serialized = self.context_data
        if self.context_data and isinstance(self.context_data, dict):
            # Context data is already a dict - check if it has to_dict method through TaskContext
            # For now, keep as-is since it's already serialized
            context_data_serialized = self.context_data
        elif not context_data_serialized:
            # Ensure context_data is never None - always return empty dict
            context_data_serialized = {}

        # Ensure assignees is always a list, never a string
        assignees_list = self.assignees
        if assignees_list is None:
            assignees_list = []
        elif isinstance(assignees_list, str):
            # Handle case where assignees might be a string instead of list
            assignees_list = [assignees_list] if assignees_list else []

        return {
            "id": self.id,
            "title": self.title,
            "description": self.description,
            "status": self.status,
            "priority": self.priority,
            "details": self.details,  # Formatted progress history text for backward compatibility
            "estimatedEffort": self.estimated_effort,
            "assignees": assignees_list,
            "labels": self.labels if self.labels else [],
            "dependencies": self.dependencies if self.dependencies else [],
            "subtasks": self.subtasks if self.subtasks else [],
            "dueDate": self.due_date,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
            "git_branch_id": self.git_branch_id,
            "project_id": self.project_id,
            "context_id": self.context_id,
            "context_data": context_data_serialized,
            "dependency_relationships": self.dependency_relationships.to_dict() if self.dependency_relationships else None,
            "progress_percentage": self.progress_percentage,
            "progress_history": self.progress_history,  # Full progress history structure
            "progress_count": self.progress_count,  # Number of progress entries
            "subtask_count": self.subtask_count,  # Total number of subtasks
            "completed_subtasks": self.completed_subtasks  # Number of completed subtasks
        } 