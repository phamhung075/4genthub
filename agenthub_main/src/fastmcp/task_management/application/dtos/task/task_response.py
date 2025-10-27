"""Response DTO for task operations"""

from dataclasses import dataclass
from typing import List, Optional, Dict, Any
from datetime import datetime
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
    assignees: List[str]
    labels: List[str]
    dependencies: List[str]
    subtasks: List[Dict[str, Any]]
    due_date: Optional[str]
    created_at: Optional[datetime]
    updated_at: Optional[datetime]
    git_branch_id: Optional[str] = None  # Links to git_branch which contains project and user info
    project_id: Optional[str] = None  # Project ID fetched via repository join (maintains normalization)
    context_id: Optional[str] = None
    context_data: Optional[Dict[str, Any]] = None
    dependency_relationships: Optional[DependencyRelationships] = None  # Enhanced dependency information
    progress_percentage: int = 0  # Task completion progress (0-100)
    progress_history: Optional[Dict[str, Any]] = None  # Full progress history structure
    progress_count: int = 0  # Number of progress entries
    subtask_count: int = 0  # Total number of subtasks
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
            assignees: List[str],
            labels: List[str],
            dependencies: List[str],
            subtasks: List[Dict[str, Any]],
            due_date: Optional[str],
            created_at: Optional[datetime],
            updated_at: Optional[datetime],
            git_branch_id: Optional[str] = None,  # Following clean relationship chain
            project_id: Optional[str] = None,  # Project ID from repository join
            context_id: Optional[str] = None,
            context_data: Optional[Dict[str, Any]] = None,
            dependency_relationships: Optional[DependencyRelationships] = None,
            progress_percentage: int = 0,
            progress_history: Optional[Dict[str, Any]] = None,
            progress_count: int = 0,
            subtask_count: int = 0,
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
        self.subtask_count = subtask_count
        self.completed_subtasks = completed_subtasks

    @classmethod
    def from_domain(cls, task, git_branch_repository=None, context_data: Optional[Dict[str, Any]] = None,
                   dependency_relationships: Optional[DependencyRelationships] = None) -> 'TaskResponse':
        """Create response DTO from domain entity with optional context data.

        Args:
            task: Domain task entity
            git_branch_repository: Repository for fetching project_id via join (Option 1 - Pure DDD)
            context_data: Optional context data
            dependency_relationships: Optional dependency information

        Returns:
            TaskResponse with project_id populated via repository join
        """
        task_dict = task.to_dict()

        # Fetch project_id via repository join (maintains database normalization)
        project_id = None
        if git_branch_repository and task_dict.get("git_branch_id"):
            try:
                git_branch = git_branch_repository.get_by_id(task_dict["git_branch_id"])
                project_id = git_branch.project_id if git_branch else None
            except Exception as e:
                # Log but don't fail - project_id is optional
                import logging
                logging.warning(f"Failed to fetch project_id for git_branch {task_dict.get('git_branch_id')}: {e}")
        
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

        # Fix 1 & 2: Compute subtask counts
        # Note: task.subtasks is a list of subtask IDs (strings), not subtask objects
        # We can count total subtasks, but cannot determine completion without loading subtask objects
        subtask_count = len(task.subtasks) if task.subtasks else 0
        # TODO: To calculate completed_subtasks, we need to query subtask repository
        # For now, frontend can query subtasks separately if needed
        completed_subtasks = 0  # Cannot determine from IDs alone

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
            subtask_count=subtask_count,  # Fix 1: Total subtask count
            completed_subtasks=completed_subtasks  # Fix 2: Completed subtask count
        )
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert TaskResponse to dictionary representation with JSON-safe datetime serialization"""
        # OPTIMIZATION: Serialize context_data with embedded=True to remove duplicates
        context_data_serialized = self.context_data
        if self.context_data and isinstance(self.context_data, dict):
            # Context data is already a dict - check if it has to_dict method through TaskContext
            # For now, keep as-is since it's already serialized
            context_data_serialized = self.context_data

        return {
            "id": self.id,
            "title": self.title,
            "description": self.description,
            "status": self.status,
            "priority": self.priority,
            "details": self.details,  # Formatted progress history text for backward compatibility
            "estimatedEffort": self.estimated_effort,
            "assignees": self.assignees,
            "labels": self.labels,
            "dependencies": self.dependencies,
            "subtasks": self.subtasks,
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