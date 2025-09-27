"""Branch Statistics Service - Domain Service for Managing Branch Task Counts"""

import logging
from typing import Optional, Dict, Any, Protocol
from dataclasses import dataclass

logger = logging.getLogger(__name__)


@dataclass
class BranchStatistics:
    """Value object for branch statistics"""
    branch_id: str
    task_count: int
    completed_task_count: int
    in_progress_count: int
    blocked_count: int
    progress_percentage: float


class TaskRepositoryProtocol(Protocol):
    """Protocol for task repository to avoid infrastructure dependency."""
    def find_by_git_branch_id(self, branch_id: str) -> list:
        pass


class GitBranchRepositoryProtocol(Protocol):
    """Protocol for git branch repository to avoid infrastructure dependency."""
    def get(self, branch_id: str) -> Optional[Any]:
        pass

    def update(self, branch_id: str, updates: dict) -> bool:
        pass

    def find_by_project_id(self, project_id: str) -> list:
        pass

    def get_all(self) -> list:
        pass


class BranchStatisticsService:
    """
    Domain service responsible for maintaining branch statistics.
    This service ensures branch task counts are always synchronized
    with actual task states.
    """

    def __init__(self, task_repository, git_branch_repository):
        """
        Initialize the branch statistics service.

        Args:
            task_repository: Repository for accessing tasks
            git_branch_repository: Repository for accessing and updating branches
        """
        self._task_repository = task_repository
        self._git_branch_repository = git_branch_repository

    def on_task_created(self, task_id: str, branch_id: str, status: str) -> None:
        """
        Handle task creation event - update branch counts.

        Args:
            task_id: ID of the created task
            branch_id: ID of the branch the task belongs to
            status: Initial status of the task
        """
        if not branch_id:
            return

        try:
            logger.info(f"Updating branch {branch_id} statistics after task {task_id} creation")
            self._recalculate_branch_statistics(branch_id)
        except Exception as e:
            logger.error(f"Failed to update branch statistics on task creation: {e}")

    def on_task_updated(self, task_id: str, old_branch_id: Optional[str],
                       new_branch_id: Optional[str], old_status: str, new_status: str) -> None:
        """
        Handle task update event - update branch counts.

        Args:
            task_id: ID of the updated task
            old_branch_id: Previous branch ID (if changed)
            new_branch_id: New branch ID
            old_status: Previous task status
            new_status: New task status
        """
        branches_to_update = set()

        # If branch changed, update both branches
        if old_branch_id and old_branch_id != new_branch_id:
            branches_to_update.add(old_branch_id)

        if new_branch_id:
            branches_to_update.add(new_branch_id)

        for branch_id in branches_to_update:
            try:
                logger.info(f"Updating branch {branch_id} statistics after task {task_id} update")
                self._recalculate_branch_statistics(branch_id)
            except Exception as e:
                logger.error(f"Failed to update branch {branch_id} statistics: {e}")

    def on_task_deleted(self, task_id: str, branch_id: str, status: str) -> None:
        """
        Handle task deletion event - update branch counts.

        Args:
            task_id: ID of the deleted task
            branch_id: ID of the branch the task belonged to
            status: Status of the deleted task
        """
        if not branch_id:
            return

        try:
            logger.info(f"Updating branch {branch_id} statistics after task {task_id} deletion")
            self._recalculate_branch_statistics(branch_id)
        except Exception as e:
            logger.error(f"Failed to update branch statistics on task deletion: {e}")

    def _recalculate_branch_statistics(self, branch_id: str) -> BranchStatistics:
        """
        Recalculate all statistics for a branch.

        Args:
            branch_id: ID of the branch to recalculate

        Returns:
            Updated branch statistics
        """
        # Get all tasks for this branch
        tasks = self._task_repository.find_by_git_branch_id(branch_id)

        # Calculate statistics
        task_count = len(tasks)
        completed_count = sum(1 for task in tasks if task.status == 'done')
        in_progress_count = sum(1 for task in tasks if task.status == 'in_progress')
        blocked_count = sum(1 for task in tasks if task.status == 'blocked')

        progress_percentage = 0.0
        if task_count > 0:
            progress_percentage = (completed_count / task_count) * 100.0

        # Update branch in repository
        branch = self._git_branch_repository.get(branch_id)
        if branch:
            # Update branch statistics
            updates = {
                'task_count': task_count,
                'completed_task_count': completed_count,
                'progress_percentage': progress_percentage
            }

            self._git_branch_repository.update(branch_id, updates)

            logger.info(
                f"Updated branch {branch_id} statistics: "
                f"total={task_count}, completed={completed_count}, "
                f"in_progress={in_progress_count}, blocked={blocked_count}, "
                f"progress={progress_percentage:.1f}%"
            )
        else:
            logger.warning(f"Branch {branch_id} not found for statistics update")

        return BranchStatistics(
            branch_id=branch_id,
            task_count=task_count,
            completed_task_count=completed_count,
            in_progress_count=in_progress_count,
            blocked_count=blocked_count,
            progress_percentage=progress_percentage
        )

    def recalculate_all_branches(self, project_id: Optional[str] = None) -> Dict[str, BranchStatistics]:
        """
        Recalculate statistics for all branches in a project or all branches.

        Args:
            project_id: Optional project ID to limit recalculation

        Returns:
            Dictionary of branch IDs to their updated statistics
        """
        if project_id:
            branches = self._git_branch_repository.find_by_project_id(project_id)
        else:
            branches = self._git_branch_repository.get_all()

        results = {}
        for branch in branches:
            try:
                stats = self._recalculate_branch_statistics(branch.id)
                results[branch.id] = stats
            except Exception as e:
                logger.error(f"Failed to recalculate statistics for branch {branch.id}: {e}")

        logger.info(f"Recalculated statistics for {len(results)} branches")
        return results

    def get_branch_statistics(self, branch_id: str) -> Optional[BranchStatistics]:
        """
        Get current statistics for a branch.

        Args:
            branch_id: ID of the branch

        Returns:
            Branch statistics or None if branch not found
        """
        branch = self._git_branch_repository.get(branch_id)
        if not branch:
            return None

        # Get fresh counts from tasks
        tasks = self._task_repository.find_by_git_branch_id(branch_id)

        task_count = len(tasks)
        completed_count = sum(1 for task in tasks if task.status == 'done')
        in_progress_count = sum(1 for task in tasks if task.status == 'in_progress')
        blocked_count = sum(1 for task in tasks if task.status == 'blocked')

        progress_percentage = 0.0
        if task_count > 0:
            progress_percentage = (completed_count / task_count) * 100.0

        return BranchStatistics(
            branch_id=branch_id,
            task_count=task_count,
            completed_task_count=completed_count,
            in_progress_count=in_progress_count,
            blocked_count=blocked_count,
            progress_percentage=progress_percentage
        )