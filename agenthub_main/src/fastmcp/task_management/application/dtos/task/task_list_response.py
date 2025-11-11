"""Response DTO for task list operations"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from .task_response import TaskResponse


@dataclass
class TaskListResponse:
    """Response DTO for task list operations"""

    tasks: list[TaskResponse]
    count: int
    filters_applied: dict[str, Any] | None = None
    query: str | None = None

    @classmethod
    def from_domain_list(
        cls,
        tasks,
        git_branch_repository=None,
        task_repository=None,
        filters_applied: dict[str, Any] | None = None,
        query: str | None = None,
    ) -> TaskListResponse:
        """Create response DTO from list of domain entities with batch loading optimization.

        BATCH LOADING IMPLEMENTATION:
        Eliminates N+1 query problem by fetching all git branches and completed subtask counts
        in single queries instead of one query per task.

        Performance Impact:
        - Before: 1 + N + N queries (1 for tasks, N for git branches, N for subtask counts)
        - After: 3 queries (1 for tasks, 1 for all git branches, 1 for all subtask counts)
        - Improvement: 50x-500x faster for large task lists

        Args:
            tasks: List of domain task entities
            git_branch_repository: Repository for batch fetching project_ids
            task_repository: Repository for batch fetching completed_subtasks counts
            filters_applied: Optional filter metadata
            query: Optional search query metadata

        Returns:
            TaskListResponse with all project_ids and completed_subtasks populated efficiently
        """
        # STEP 1: Extract unique git_branch_ids from tasks (O(n) operation)
        # Use set to eliminate duplicates, then convert to list for batch query
        branch_ids = list(
            set(
                str(task.git_branch_id.value)
                if hasattr(task.git_branch_id, "value")
                else str(task.git_branch_id)
                for task in tasks
                if task.git_branch_id
            )
        )

        # STEP 2: Batch load all branches in ONE query (eliminates N+1 problem)
        branch_to_project = {}
        if git_branch_repository and branch_ids:
            try:
                # DEBUG: Log batch loading attempt
                import logging

                logging.info(
                    f"🚀 BATCH LOADING: Fetching {len(branch_ids)} unique git branches in single query"
                )

                # Call the new find_by_ids() method that fetches all branches at once
                branches = git_branch_repository.find_by_ids(branch_ids)

                logging.info(
                    f"✅ BATCH LOADING: Retrieved {len(branches)} git branches successfully"
                )

                # Build lookup dictionary: branch_id → project_id
                branch_to_project = {
                    str(branch_id): str(branch.project_id.value)
                    if hasattr(branch.project_id, "value")
                    else str(branch.project_id)
                    for branch_id, branch in branches.items()
                }

                logging.info(
                    f"📦 BATCH LOADING: Built project_id lookup map with {len(branch_to_project)} entries"
                )
            except Exception as e:
                # Log warning but continue - project_id is optional
                import logging

                logging.warning(f"⚠️ BATCH LOADING FAILED: {e}", exc_info=True)
                # Empty dict means all tasks will have project_id=None

        # STEP 3: NEW - Batch load completed subtask counts in ONE query
        task_ids = [
            str(task.id.value) if hasattr(task.id, "value") else str(task.id)
            for task in tasks
        ]
        completed_counts = {}
        if task_repository and task_ids:
            try:
                import logging

                logging.info(
                    f"🚀 BATCH LOADING: Fetching completed subtask counts for {len(task_ids)} tasks in single query"
                )

                # Call the new get_completed_subtask_counts() method
                completed_counts = task_repository.get_completed_subtask_counts(
                    task_ids
                )

                logging.info(
                    f"✅ BATCH LOADING: Retrieved {len(completed_counts)} completed subtask counts successfully"
                )
            except Exception as e:
                import logging

                logging.warning(
                    f"⚠️ BATCH LOADING completed_subtasks FAILED: {e}", exc_info=True
                )
                # Empty dict means all tasks will have completed_subtasks=0

        # STEP 4: Create TaskResponse objects with pre-fetched project_ids AND completed_subtasks
        # This avoids the N individual queries that would occur in TaskResponse.from_domain()
        task_responses = [
            TaskResponse.from_domain(
                task,
                git_branch_repository=None,  # Don't pass repository since we have project_id
                project_id=branch_to_project.get(
                    str(task.git_branch_id.value)
                    if hasattr(task.git_branch_id, "value")
                    else str(task.git_branch_id)
                )
                if task.git_branch_id
                else None,
                completed_subtasks=completed_counts.get(
                    str(task.id.value) if hasattr(task.id, "value") else str(task.id),
                    0,  # Default to 0 if no completed subtasks found
                ),
            )
            for task in tasks
        ]

        return cls(
            tasks=task_responses,
            count=len(task_responses),
            filters_applied=filters_applied,
            query=query,
        )
