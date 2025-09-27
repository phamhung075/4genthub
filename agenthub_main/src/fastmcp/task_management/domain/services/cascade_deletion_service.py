"""
Domain Service for Cascade Deletion

This service handles cascade deletion of entities in the domain layer,
ensuring all related entities are properly deleted when a parent entity
is removed. It follows DDD principles and domain-driven logic.

Clean Code Requirements:
- NO backward compatibility code
- NO legacy patterns
- Direct implementation only
- Clean error handling
- Domain events for statistics updates
"""

import logging
from typing import Optional, List, Dict, Any
from enum import Enum

logger = logging.getLogger(__name__)


class DeleteScope(Enum):
    """Scope of cascade deletion"""
    TASK_ONLY = "task_only"
    TASK_WITH_SUBTASKS = "task_with_subtasks"
    TASK_FULL = "task_full"  # Task + Subtasks + Contexts
    BRANCH_FULL = "branch_full"  # Branch + All Tasks/Subtasks/Contexts
    PROJECT_FULL = "project_full"  # Project + All Branches/Tasks/Subtasks/Contexts


class CascadeDeletionService:
    """
    Domain service that handles cascade deletion of entities.

    This service ensures proper cleanup of all related entities when
    a parent entity is deleted, maintaining referential integrity and
    triggering appropriate domain events for statistics updates.
    """

    def __init__(self,
                 task_repository,
                 subtask_repository,
                 branch_repository,
                 project_repository,
                 context_repository=None):
        """
        Initialize the cascade deletion service with repositories.

        Args:
            task_repository: Repository for task operations
            subtask_repository: Repository for subtask operations
            branch_repository: Repository for branch operations
            project_repository: Repository for project operations
            context_repository: Optional repository for context operations
        """
        self._task_repository = task_repository
        self._subtask_repository = subtask_repository
        self._branch_repository = branch_repository
        self._project_repository = project_repository
        self._context_repository = context_repository

    def delete_task_cascade(self, task_id: str, scope: DeleteScope = DeleteScope.TASK_FULL) -> Dict[str, Any]:
        """
        Delete a task with cascade deletion of related entities.

        Args:
            task_id: ID of the task to delete
            scope: Scope of cascade deletion

        Returns:
            Dictionary with deletion statistics
        """
        logger.info(f"Starting cascade deletion for task {task_id} with scope {scope.value}")

        stats = {
            "task_deleted": False,
            "subtasks_deleted": 0,
            "contexts_deleted": 0,
            "events_dispatched": []
        }

        # Find the task first
        from ..value_objects.task_id import TaskId
        task_id_obj = TaskId.from_string(task_id) if isinstance(task_id, str) else task_id
        task = self._task_repository.find_by_id(task_id_obj)

        if not task:
            logger.warning(f"Task {task_id} not found for cascade deletion")
            return stats

        # Store task info for event dispatch
        branch_id = task.git_branch_id if hasattr(task, 'git_branch_id') else None
        task_status = str(task.status.value) if hasattr(task.status, 'value') else str(task.status)
        task_title = task.title

        # Delete subtasks if in scope
        if scope in [DeleteScope.TASK_WITH_SUBTASKS, DeleteScope.TASK_FULL]:
            deleted_count = self._delete_task_subtasks(task_id_obj)
            stats["subtasks_deleted"] = deleted_count
            logger.info(f"Deleted {deleted_count} subtasks for task {task_id}")

        # Delete task context if in scope
        if scope == DeleteScope.TASK_FULL and self._context_repository:
            if hasattr(task, 'context_id') and task.context_id:
                try:
                    self._context_repository.delete(task.context_id)
                    stats["contexts_deleted"] += 1
                    logger.info(f"Deleted context {task.context_id} for task {task_id}")
                except Exception as e:
                    logger.warning(f"Failed to delete context {task.context_id}: {e}")

        # Delete the task itself
        success = self._task_repository.delete(task_id_obj)
        stats["task_deleted"] = success

        if success:
            # Dispatch domain event for statistics update
            self._dispatch_task_deleted_event(task_id, branch_id, task_status, task_title)
            stats["events_dispatched"].append("task_deleted")
            logger.info(f"Successfully deleted task {task_id}")
        else:
            logger.error(f"Failed to delete task {task_id}")

        return stats

    def delete_branch_cascade(self, branch_id: str) -> Dict[str, Any]:
        """
        Delete a branch with cascade deletion of all tasks and related entities.

        Args:
            branch_id: ID of the branch to delete

        Returns:
            Dictionary with deletion statistics
        """
        logger.info(f"Starting cascade deletion for branch {branch_id}")

        stats = {
            "branch_deleted": False,
            "tasks_deleted": 0,
            "subtasks_deleted": 0,
            "contexts_deleted": 0,
            "events_dispatched": []
        }

        # Find the branch first
        branch = self._branch_repository.find_by_id(branch_id)
        if not branch:
            logger.warning(f"Branch {branch_id} not found for cascade deletion")
            return stats

        # Store branch info for event dispatch
        project_id = branch.project_id if hasattr(branch, 'project_id') else None
        branch_name = branch.name if hasattr(branch, 'name') else "Unknown"

        # Find and delete all tasks in the branch
        tasks = self._task_repository.find_by_git_branch_id(branch_id)
        for task in tasks:
            task_stats = self.delete_task_cascade(
                str(task.id.value) if hasattr(task.id, 'value') else str(task.id),
                scope=DeleteScope.TASK_FULL
            )
            if task_stats["task_deleted"]:
                stats["tasks_deleted"] += 1
                stats["subtasks_deleted"] += task_stats["subtasks_deleted"]
                stats["contexts_deleted"] += task_stats["contexts_deleted"]

        # Delete branch context if exists
        if self._context_repository and hasattr(branch, 'context_id') and branch.context_id:
            try:
                self._context_repository.delete(branch.context_id)
                stats["contexts_deleted"] += 1
                logger.info(f"Deleted context {branch.context_id} for branch {branch_id}")
            except Exception as e:
                logger.warning(f"Failed to delete branch context {branch.context_id}: {e}")

        # Delete the branch itself
        success = self._branch_repository.delete(branch_id)
        stats["branch_deleted"] = success

        if success:
            # Dispatch domain event for statistics update
            self._dispatch_branch_deleted_event(branch_id, project_id, branch_name)
            stats["events_dispatched"].append("branch_deleted")
            logger.info(f"Successfully deleted branch {branch_id} with {stats['tasks_deleted']} tasks")
        else:
            logger.error(f"Failed to delete branch {branch_id}")

        return stats

    def delete_project_cascade(self, project_id: str) -> Dict[str, Any]:
        """
        Delete a project with cascade deletion of all branches, tasks and related entities.

        Args:
            project_id: ID of the project to delete

        Returns:
            Dictionary with deletion statistics
        """
        logger.info(f"Starting cascade deletion for project {project_id}")

        stats = {
            "project_deleted": False,
            "branches_deleted": 0,
            "tasks_deleted": 0,
            "subtasks_deleted": 0,
            "contexts_deleted": 0,
            "events_dispatched": []
        }

        # Find the project first
        project = self._project_repository.find_by_id(project_id)
        if not project:
            logger.warning(f"Project {project_id} not found for cascade deletion")
            return stats

        # Store project info for event dispatch
        project_name = project.name if hasattr(project, 'name') else "Unknown"

        # Find and delete all branches in the project
        branches = self._branch_repository.find_by_project_id(project_id)
        for branch in branches:
            branch_id = str(branch.id) if hasattr(branch, 'id') else str(branch)
            branch_stats = self.delete_branch_cascade(branch_id)
            if branch_stats["branch_deleted"]:
                stats["branches_deleted"] += 1
                stats["tasks_deleted"] += branch_stats["tasks_deleted"]
                stats["subtasks_deleted"] += branch_stats["subtasks_deleted"]
                stats["contexts_deleted"] += branch_stats["contexts_deleted"]

        # Delete project context if exists
        if self._context_repository and hasattr(project, 'context_id') and project.context_id:
            try:
                self._context_repository.delete(project.context_id)
                stats["contexts_deleted"] += 1
                logger.info(f"Deleted context {project.context_id} for project {project_id}")
            except Exception as e:
                logger.warning(f"Failed to delete project context {project.context_id}: {e}")

        # Delete the project itself
        success = self._project_repository.delete(project_id)
        stats["project_deleted"] = success

        if success:
            # Dispatch domain event for statistics update
            self._dispatch_project_deleted_event(project_id, project_name)
            stats["events_dispatched"].append("project_deleted")
            logger.info(f"Successfully deleted project {project_id} with {stats['branches_deleted']} branches")
        else:
            logger.error(f"Failed to delete project {project_id}")

        return stats

    def _delete_task_subtasks(self, task_id) -> int:
        """
        Delete all subtasks for a task.

        Args:
            task_id: TaskId object

        Returns:
            Number of subtasks deleted
        """
        try:
            # Get count before deletion for statistics
            count = self._subtask_repository.count_by_parent_task_id(task_id)

            # Delete all subtasks
            success = self._subtask_repository.delete_by_parent_task_id(task_id)

            if success:
                logger.info(f"Deleted {count} subtasks for task {task_id}")
                return count
            else:
                logger.warning(f"Failed to delete subtasks for task {task_id}")
                return 0
        except Exception as e:
            logger.error(f"Error deleting subtasks for task {task_id}: {e}")
            return 0

    def _dispatch_task_deleted_event(self, task_id: str, branch_id: Optional[str],
                                    status: str, title: str) -> None:
        """Dispatch task deleted event for statistics update."""
        try:
            from ..services.event_dispatcher import dispatch_domain_event
            from ..events.task_lifecycle_events import TaskDeletedEvent

            if branch_id:
                event = TaskDeletedEvent.create(
                    task_id=task_id,
                    branch_id=branch_id,
                    status=status,
                    title=title
                )
                dispatch_domain_event("task_deleted", event)
                logger.info(f"Dispatched task_deleted event for task {task_id}")
        except Exception as e:
            logger.warning(f"Failed to dispatch task deleted event: {e}")

    def _dispatch_branch_deleted_event(self, branch_id: str, project_id: Optional[str],
                                      name: str) -> None:
        """Dispatch branch deleted event for statistics update."""
        try:
            from ..services.event_dispatcher import dispatch_domain_event
            from ..events.branch_lifecycle_events import BranchDeletedEvent

            if project_id:
                event = BranchDeletedEvent.create(
                    branch_id=branch_id,
                    project_id=project_id,
                    name=name
                )
                dispatch_domain_event("branch_deleted", event)
                logger.info(f"Dispatched branch_deleted event for branch {branch_id}")
        except Exception as e:
            logger.warning(f"Failed to dispatch branch deleted event: {e}")

    def _dispatch_project_deleted_event(self, project_id: str, name: str) -> None:
        """Dispatch project deleted event for statistics update."""
        try:
            from ..services.event_dispatcher import dispatch_domain_event
            from ..events.project_lifecycle_events import ProjectDeletedEvent

            event = ProjectDeletedEvent.create(
                project_id=project_id,
                name=name
            )
            dispatch_domain_event("project_deleted", event)
            logger.info(f"Dispatched project_deleted event for project {project_id}")
        except Exception as e:
            logger.warning(f"Failed to dispatch project deleted event: {e}")