"""
Cascade Data Provider Protocol

This Protocol defines the data access interface needed by CascadeCalculator domain service.
By depending on this abstraction rather than concrete implementations, the domain layer
remains independent of infrastructure concerns (Dependency Inversion Principle).

Infrastructure implementations (e.g., SQLAlchemyCascadeDataProvider) provide the actual
data access logic using specific technologies.
"""

from dataclasses import dataclass
from typing import List, Optional, Protocol, Set
from ..cascade_calculator import EntityType


@dataclass
class TaskCascadeData:
    """Data transfer object for task cascade information"""

    id: str
    git_branch_id: str
    project_id: str
    context_id: Optional[str] = None


@dataclass
class SubtaskCascadeData:
    """Data transfer object for subtask cascade information"""

    id: str
    task_id: str
    git_branch_id: str
    project_id: str
    context_id: Optional[str] = None


@dataclass
class BranchCascadeData:
    """Data transfer object for branch cascade information"""

    id: str
    project_id: str
    task_ids: Set[str]
    subtask_ids: Set[str]


@dataclass
class ProjectCascadeData:
    """Data transfer object for project cascade information"""

    id: str
    branch_ids: Set[str]
    task_ids: Set[str]
    subtask_ids: Set[str]


@dataclass
class ContextCascadeData:
    """Data transfer object for context cascade information"""

    id: str
    task_ids: Set[str]
    branch_ids: Set[str]
    project_ids: Set[str]
    subtask_ids: Set[str]


class CascadeDataProvider(Protocol):
    """
    Protocol defining data access interface for cascade calculations.

    This Protocol uses Python's structural subtyping - any class implementing
    these methods will satisfy the Protocol without explicit inheritance.

    All methods are async to support efficient I/O operations.
    All methods return domain DTOs, never infrastructure-specific types.
    """

    async def get_task_cascade_data(self, task_id: str) -> Optional[TaskCascadeData]:
        """
        Get cascade-relevant data for a task.

        Args:
            task_id: UUID of the task

        Returns:
            TaskCascadeData if found, None if task doesn't exist
        """
        ...

    async def get_task_subtask_ids(self, task_id: str) -> Set[str]:
        """
        Get all subtask IDs for a task.

        Args:
            task_id: UUID of the task

        Returns:
            Set of subtask IDs (empty set if none)
        """
        ...

    async def get_task_parent_task_ids(self, task_id: str) -> Set[str]:
        """
        Get IDs of tasks that depend on this task.

        Args:
            task_id: UUID of the task

        Returns:
            Set of parent task IDs (empty set if none)
        """
        ...

    async def get_subtask_cascade_data(self, subtask_id: str) -> Optional[SubtaskCascadeData]:
        """
        Get cascade-relevant data for a subtask.

        Args:
            subtask_id: UUID of the subtask

        Returns:
            SubtaskCascadeData if found, None if subtask doesn't exist
        """
        ...

    async def get_branch_cascade_data(self, branch_id: str) -> Optional[BranchCascadeData]:
        """
        Get cascade-relevant data for a branch.

        Args:
            branch_id: UUID of the branch

        Returns:
            BranchCascadeData if found, None if branch doesn't exist
        """
        ...

    async def get_project_cascade_data(self, project_id: str) -> Optional[ProjectCascadeData]:
        """
        Get cascade-relevant data for a project.

        Args:
            project_id: UUID of the project

        Returns:
            ProjectCascadeData if found, None if project doesn't exist
        """
        ...

    async def get_context_cascade_data(self, context_id: str) -> Optional[ContextCascadeData]:
        """
        Get cascade-relevant data for a context.

        Args:
            context_id: UUID of the context

        Returns:
            ContextCascadeData if found, None if context doesn't exist
        """
        ...

    async def get_related_context_ids(self, branch_id: str, project_id: str) -> Set[str]:
        """
        Get context IDs related to a branch and project.

        Args:
            branch_id: UUID of the branch
            project_id: UUID of the project

        Returns:
            Set of context IDs (empty set if none)
        """
        ...

    async def detect_entity_type(self, entity_id: str) -> Optional[EntityType]:
        """
        Auto-detect the type of an entity by its ID.

        Args:
            entity_id: UUID of the entity

        Returns:
            EntityType if found, None if entity doesn't exist in any table
        """
        ...
