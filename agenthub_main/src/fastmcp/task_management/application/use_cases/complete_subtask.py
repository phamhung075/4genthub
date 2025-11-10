"""Complete Subtask Use Case"""

from __future__ import annotations

import logging
import time
from typing import Any

from ...domain import TaskId, TaskNotFoundError, TaskRepository
from ...domain.repositories.subtask_repository import SubtaskRepository


class CompleteSubtaskUseCase:
    def __init__(self, task_repository: TaskRepository, subtask_repository: SubtaskRepository = None):
        self._task_repository = task_repository
        self._subtask_repository = subtask_repository

    def execute(self, task_id: str | int, id: str | int,
                user_id: str = None, completion_summary: str = None,
                insights_found: list = None, testing_notes: str = None) -> dict[str, Any]:
        task_id_obj = self._convert_to_task_id(task_id)

        # Retry task lookup on concurrent access conflicts
        max_retries = 3
        retry_delay = 0.01  # 10ms
        task = None

        for attempt in range(max_retries):
            try:
                task = self._task_repository.find_by_id(task_id_obj)
                if not task:
                    raise TaskNotFoundError(f"Task {task_id} not found")
                break  # Success!
            except Exception as e:
                error_str = str(e).lower()
                # Check for SQLite concurrent access errors or enum validation issues during lookup
                is_retryable = (
                    "interfaceerror" in error_str or
                    "bad parameter" in error_str or
                    "database is locked" in error_str or
                    "api misuse" in error_str
                )
                if is_retryable and attempt < max_retries - 1:
                    # Exponential backoff for lookup retries too
                    delay = retry_delay * (2 ** attempt)
                    logging.warning(f"[CompleteSubtask] Concurrent access conflict on lookup attempt {attempt+1}/{max_retries}, retrying after {delay:.3f}s...")
                    time.sleep(delay)
                    continue
                # Re-raise if not a concurrent access issue or out of retries
                logging.error(f"[CompleteSubtask] Task lookup failed after {attempt+1} attempts: {e}")
                raise
        
        # Use dedicated subtask repository if available
        if self._subtask_repository:
            subtask = self._subtask_repository.find_by_id(id)
            if not subtask:
                raise ValueError(f"Subtask {id} not found in task {task_id}")

            # Store old status for event
            old_status = subtask.status

            subtask.complete()
            self._subtask_repository.save(subtask)
            success = True

            # Atomically increment parent task's completed_subtasks counter
            # This prevents lost updates in concurrent scenarios by using database-level atomic operation
            max_save_retries = 5  # Increased from 3 for higher concurrency
            save_retry_delay = 0.02  # 20ms base delay

            for save_attempt in range(max_save_retries):
                try:
                    # Use atomic increment at database level to prevent race conditions
                    increment_success = self._task_repository.atomic_increment_completed_subtasks(str(task_id))

                    if increment_success:
                        logging.info(f"Atomically incremented completed_subtasks for task {task_id}")
                        break  # Success!
                    else:
                        raise TaskNotFoundError(f"Task {task_id} not found for counter increment")

                except Exception as e:
                    error_str = str(e).lower()
                    # Check for concurrent update conflicts (database locked, etc.)
                    is_concurrent_conflict = (
                        "database is locked" in error_str or
                        "concurrent" in error_str or
                        "locked" in error_str
                    )

                    if is_concurrent_conflict and save_attempt < max_save_retries - 1:
                        # Exponential backoff
                        delay = save_retry_delay * (2 ** save_attempt)
                        logging.warning(
                            f"[CompleteSubtask] Concurrent update conflict on atomic increment attempt {save_attempt+1}/{max_save_retries}, "
                            f"retrying after {delay:.3f}s... Error: {e}"
                        )
                        time.sleep(delay)
                        continue

                    # Re-raise if not a concurrent conflict or out of retries
                    logging.error(f"[CompleteSubtask] Failed to atomically increment after {save_attempt+1} attempts: {e}")
                    raise

            # Dispatch domain event for subtask status change
            # This will trigger branch statistics update
            try:
                from ...domain.events.task_lifecycle_events import (
                    TaskStatusChangedEvent,
                )
                from ...domain.services.event_dispatcher import dispatch_domain_event

                branch_id = task.git_branch_id if hasattr(task, 'git_branch_id') else None
                if branch_id:
                    event = TaskStatusChangedEvent.create(
                        task_id=str(id),
                        branch_id=branch_id,
                        old_status=old_status,
                        new_status='done'
                    )

                    dispatch_domain_event("task_status_changed", event)
                    logging.info(f"Dispatched task_status_changed event for subtask {id} completion")
            except Exception as e:
                logging.warning(f"Failed to dispatch subtask completion event: {e}")
        else:
            # Fallback to existing task entity method for backward compatibility
            success = task.complete_subtask(id)
            if success:
                self._task_repository.save(task)
        
        # Reload task to get updated completed_subtasks count and calculate progress
        task = self._task_repository.find_by_id(task_id_obj)
        if not task:
            raise TaskNotFoundError(f"Task {task_id} not found after atomic increment")

        # Calculate parent progress after subtask completion
        # NOTE: get_subtask_progress() cannot determine actual progress without repository access
        # Instead, calculate progress from the task's completed_subtasks counter
        total_subtasks = len(task.subtasks) if hasattr(task, 'subtasks') and task.subtasks else 0
        completed_subtasks = task.completed_subtasks if hasattr(task, 'completed_subtasks') else 0

        if total_subtasks > 0:
            progress_percentage = (completed_subtasks / total_subtasks) * 100
        else:
            progress_percentage = 0

        parent_progress = {
            "total": total_subtasks,
            "completed": completed_subtasks,
            "percentage": progress_percentage
        }

        # Trigger parent task progress update
        try:
            self._update_parent_task_progress(task, parent_progress)
        except Exception as e:
            logging.warning(f"Failed to update parent task progress: {e}")

        # Add insights and completion details to parent task context if provided
        try:
            self._update_parent_task_context(task, completion_summary, insights_found, testing_notes)
        except Exception as e:
            logging.warning(f"Failed to update parent task context: {e}")

        return {
            "success": success,
            "task_id": str(task_id),
            "subtask_id": str(id),
            "progress": parent_progress,
            "parent_progress": parent_progress  # Include explicit parent progress
        }

    def _update_parent_task_progress(self, task, progress) -> None:
        """Update parent task with aggregated progress from subtasks.

        Args:
            task: The parent task entity
            progress: Either a dict with 'percentage' key or a numeric value
        """
        try:
            # Extract percentage from progress dict if needed
            if isinstance(progress, dict):
                progress_value = progress.get('percentage', 0)
            else:
                progress_value = progress

            # Update the task's overall progress if it has subtasks
            if hasattr(task, 'subtasks') and task.subtasks:
                # Set overall progress based on subtask completion
                progress_int = int(progress_value)
                task.set_progress_percentage(progress_int)

                # Save the updated task
                self._task_repository.save(task)

                logging.info(f"Updated parent task {task.id} progress to {progress_int}%")
        except Exception as e:
            logging.error(f"Failed to update parent task progress: {e}")

    def _update_parent_task_context(self, task, completion_summary: str = None,
                                   insights_found: list = None, testing_notes: str = None) -> None:
        """Update parent task context with subtask completion details."""
        if not completion_summary and not insights_found and not testing_notes:
            return  # Nothing to update

        try:
            # Initialize context_data if it doesn't exist
            if not hasattr(task, 'context_data') or task.context_data is None:
                task.context_data = {}

            # Ensure context_data is a dictionary
            if not isinstance(task.context_data, dict):
                task.context_data = {}

            # Add insights to context_data
            if insights_found:
                if 'subtask_insights' not in task.context_data:
                    task.context_data['subtask_insights'] = []

                # Add insights as list items
                if isinstance(insights_found, list):
                    task.context_data['subtask_insights'].extend(insights_found)
                else:
                    task.context_data['subtask_insights'].append(str(insights_found))

                logging.info(f"Added {len(insights_found) if isinstance(insights_found, list) else 1} insights to parent task {task.id}")

            # Add completion summary to context if provided
            if completion_summary:
                if 'subtask_completions' not in task.context_data:
                    task.context_data['subtask_completions'] = []
                task.context_data['subtask_completions'].append(completion_summary)

            # Add testing notes if provided
            if testing_notes:
                if 'subtask_testing_notes' not in task.context_data:
                    task.context_data['subtask_testing_notes'] = []
                task.context_data['subtask_testing_notes'].append(testing_notes)

            # Save the updated task with context
            self._task_repository.save(task)
            logging.info(f"Updated parent task {task.id} context with subtask completion details")
        except Exception as e:
            logging.error(f"Failed to update parent task context: {e}")

    def _convert_to_task_id(self, task_id: str | int) -> TaskId:
        if isinstance(task_id, int):
            return TaskId.from_int(task_id)
        else:
            return TaskId.from_string(str(task_id)) 