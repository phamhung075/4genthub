"""Add Subtask Use Case"""

from __future__ import annotations

import logging
import time

from ...application.dtos.subtask.add_subtask_request import AddSubtaskRequest
from ...application.dtos.subtask.subtask_response import SubtaskResponse
from ...domain import TaskId, TaskNotFoundError, TaskRepository
from ...domain.entities.subtask import Subtask
from ...domain.repositories.subtask_repository import SubtaskRepository
from ...domain.value_objects.priority import Priority


class AddSubtaskUseCase:
    def __init__(
        self,
        task_repository: TaskRepository,
        subtask_repository: SubtaskRepository = None,
    ):
        self._task_repository = task_repository
        self._subtask_repository = subtask_repository

    def execute(self, request: AddSubtaskRequest) -> SubtaskResponse:
        logging.debug(f"[AddSubtask] Request received - priority: {request.priority}")
        task_id = self._convert_to_task_id(request.task_id)

        # Retry task lookup on concurrent access conflicts
        max_retries = 3
        retry_delay = 0.01  # 10ms
        task = None

        for attempt in range(max_retries):
            try:
                task = self._task_repository.find_by_id(task_id)
                if not task:
                    raise TaskNotFoundError(f"Task {request.task_id} not found")
                break  # Success!
            except Exception as e:
                error_str = str(e).lower()
                # Check for SQLite concurrent access errors or enum validation issues during lookup
                is_retryable = (
                    "interfaceerror" in error_str
                    or "bad parameter" in error_str
                    or "database is locked" in error_str
                    or "api misuse" in error_str
                )
                if is_retryable and attempt < max_retries - 1:
                    # Exponential backoff for lookup retries too
                    delay = retry_delay * (2**attempt)
                    logging.warning(
                        f"[AddSubtask] Concurrent access conflict on lookup attempt {attempt + 1}/{max_retries}, retrying after {delay:.3f}s..."
                    )
                    time.sleep(delay)
                    continue
                # Re-raise if not a concurrent access issue or out of retries
                logging.error(
                    f"[AddSubtask] Task lookup failed after {attempt + 1} attempts: {e}"
                )
                raise

        agent_inheritance_applied = False
        inherited_assignees = []

        # Create subtask using the new domain entity
        if self._subtask_repository:
            # Use dedicated subtask repository if available
            logging.debug("[AddSubtask] Using subtask repository path")
            subtask_id = self._subtask_repository.get_next_id(task_id)

            # Convert string priority to Priority value object
            priority = None
            if request.priority:
                priority = Priority.from_string(request.priority)
                logging.debug(
                    f"[AddSubtask] Creating subtask with priority: {request.priority} -> {priority}"
                )

            # Convert string status to TaskStatus value object if provided
            status = None
            if request.status:
                from ...domain.value_objects.task_status import TaskStatus

                status = TaskStatus.from_string(request.status)
                logging.debug(
                    f"[AddSubtask] Creating subtask with status: {request.status} -> {status}"
                )

            # Get progress_percentage if provided
            progress_percentage = (
                request.progress_percentage
                if hasattr(request, "progress_percentage")
                and request.progress_percentage is not None
                else 0
            )

            # Auto-adjust status based on progress_percentage if not explicitly set
            if progress_percentage >= 100 and not status:
                from ...domain.value_objects.task_status import TaskStatus

                status = TaskStatus.done()
                logging.debug(
                    "[AddSubtask] Auto-setting status to 'done' due to progress_percentage=100"
                )
            elif progress_percentage > 0 and not status:
                from ...domain.value_objects.task_status import TaskStatus

                status = TaskStatus.in_progress()
                logging.debug(
                    f"[AddSubtask] Auto-setting status to 'in_progress' due to progress_percentage={progress_percentage}"
                )

            subtask = Subtask.create(
                id=subtask_id,
                title=request.title,
                description=request.description,
                parent_task_id=task_id,
                assignees=request.assignees,
                priority=priority,
                status=status,
                progress_percentage=progress_percentage,
            )

            # Apply agent inheritance if subtask has no assignees
            if subtask.should_inherit_assignees():
                parent_assignees = task.get_inherited_assignees_for_subtasks()
                if parent_assignees:
                    logging.info(
                        f"Applying agent inheritance: subtask {subtask.id} inheriting {len(parent_assignees)} assignees from parent task {task.id}"
                    )
                    subtask.inherit_assignees_from_parent(parent_assignees)
                    agent_inheritance_applied = True
                    inherited_assignees = parent_assignees.copy()
                    logging.info(f"Agent inheritance applied: {inherited_assignees}")
                else:
                    logging.info(
                        f"No assignees to inherit: parent task {task.id} has no assignees"
                    )

            self._subtask_repository.save(subtask)
            # Standalone subtask response - include parent_task_id
            added_subtask = subtask.to_dict(include_parent_id=True)

            # Add subtask ID to parent task's subtasks list and increment count
            # This calls the domain method which does both operations atomically
            # Retry the save operation to handle concurrent updates
            max_save_retries = 5  # Increased from 3 for higher concurrency
            save_retry_delay = 0.02  # 20ms base delay

            for save_attempt in range(max_save_retries):
                try:
                    # Add subtask to the task - this modifies the task entity
                    task.add_subtask(str(subtask_id))
                    self._task_repository.save(task)
                    logging.info(
                        f"Added subtask {subtask_id} to parent task {task_id}, subtask_count now {len(task.subtasks)}"
                    )
                    break  # Success!
                except Exception as e:
                    error_str = str(e).lower()
                    # Check for concurrent update conflicts (SQLAlchemy StaleDataError or refresh errors)
                    is_concurrent_conflict = (
                        "expected to update" in error_str
                        or "stale" in error_str
                        or "concurrent" in error_str
                        or "could not refresh" in error_str
                        or "detached" in error_str
                    )

                    if is_concurrent_conflict and save_attempt < max_save_retries - 1:
                        # Exponential backoff
                        delay = save_retry_delay * (2**save_attempt)
                        logging.warning(
                            f"[AddSubtask] Concurrent update conflict on save attempt {save_attempt + 1}/{max_save_retries}, "
                            f"retrying after {delay:.3f}s... Error: {e}"
                        )
                        time.sleep(delay)

                        # Reload fresh task - the previous add_subtask call modified the old task
                        # We need a completely fresh instance from the database
                        task = self._task_repository.find_by_id(task_id)
                        if not task:
                            raise TaskNotFoundError(
                                f"Task {request.task_id} not found during retry"
                            )

                        # Important: The subtask is already saved, so if we retry we're just
                        # updating the parent task's subtask list. The subtask itself is persisted.
                        continue

                    # Re-raise if not a concurrent conflict or out of retries
                    logging.error(
                        f"[AddSubtask] Failed to save parent task after {save_attempt + 1} attempts: {e}"
                    )
                    raise

            # Update parent task progress
            self._update_parent_task_progress(str(task_id))

            # Dispatch domain event for subtask creation
            # This will trigger branch statistics update
            try:
                from ...domain.events.task_lifecycle_events import TaskCreatedEvent
                from ...domain.services.event_dispatcher import dispatch_domain_event

                # Subtasks affect the same branch as their parent task
                event = TaskCreatedEvent.create(
                    task_id=str(subtask.id),
                    branch_id=task.git_branch_id
                    if hasattr(task, "git_branch_id")
                    else None,
                    title=subtask.title,
                    status="todo",
                    priority=str(subtask.priority),
                    assignees=subtask.assignees,
                    user_id=getattr(request, "user_id", None),
                )

                if event.branch_id:
                    dispatch_domain_event("task_created", event)
                    logging.info(
                        f"Dispatched task_created event for subtask {subtask.id}"
                    )
            except Exception as e:
                logging.warning(f"Failed to dispatch subtask creation event: {e}")
        else:
            # Fallback to existing task entity method for backward compatibility
            logging.debug("[AddSubtask] Using legacy task entity path")
            subtask = {
                "title": request.title,
                "description": request.description,
                "completed": False,
                "assignees": request.assignees,
            }
            added_subtask = task.add_subtask(subtask)
            self._task_repository.save(task)

        logging.debug(
            f"[AddSubtask] Creating subtask for task_id={task_id} (following clean relationship chain)"
        )

        # Handle potential async/sync method issue
        try:
            progress = task.get_subtask_progress()
            # Check if it's a coroutine (async method result)
            if hasattr(progress, "__await__"):
                # If it's a coroutine, we can't await it in sync context
                # Fall back to a basic progress calculation
                logging.warning(
                    "[AddSubtask] get_subtask_progress returned coroutine, using fallback"
                )
                progress = {
                    "total": len(task.subtasks) if task.subtasks else 0,
                    "completed": 0,
                    "percentage": 0,
                }
        except Exception as e:
            logging.error(
                f"[AddSubtask] Error getting subtask progress: {e}, using fallback"
            )
            progress = {
                "total": len(task.subtasks) if task.subtasks else 0,
                "completed": 0,
                "percentage": 0,
            }

        response = SubtaskResponse(
            task_id=str(request.task_id), subtask=added_subtask, progress=progress
        )

        # Add inheritance information to the response
        if agent_inheritance_applied:
            response.agent_inheritance_applied = True
            response.inherited_assignees = inherited_assignees

        return response

    def _convert_to_task_id(self, task_id: str | int) -> TaskId:
        if isinstance(task_id, int):
            return TaskId.from_int(task_id)
        else:
            return TaskId.from_string(str(task_id))

    def _update_parent_task_progress(self, task_id: str) -> None:
        """Update parent task progress based on subtask completion."""
        try:
            from ..services.task_progress_service import TaskProgressService

            progress_service = TaskProgressService(
                self._task_repository, self._subtask_repository
            )
            progress_service.update_task_progress_from_subtasks(task_id)
        except Exception as e:
            logging.warning(f"Failed to update parent task progress: {e}")
