"""Update Subtask Use Case"""

import logging
from typing import Union
from ...application.dtos.subtask import (
    UpdateSubtaskRequest,
    SubtaskResponse
)

from ...domain import TaskRepository, TaskId, TaskNotFoundError
from ...domain.repositories.subtask_repository import SubtaskRepository
from ...domain.entities.subtask import Subtask
from ...domain.value_objects.priority import Priority
from ...domain.value_objects.task_status import TaskStatus

logger = logging.getLogger(__name__)


class UpdateSubtaskUseCase:
    def __init__(self, task_repository: TaskRepository, subtask_repository: SubtaskRepository = None):
        self._task_repository = task_repository
        self._subtask_repository = subtask_repository
        self._context_sync_service = None  # Lazy initialization to avoid circular imports

    def execute(self, request: UpdateSubtaskRequest) -> SubtaskResponse:
        task_id = self._convert_to_task_id(request.task_id)
        task = self._task_repository.find_by_id(task_id)
        if not task:
            raise TaskNotFoundError(f"Task {request.task_id} not found")
        
        # Use dedicated subtask repository if available
        if self._subtask_repository:
            subtask = self._subtask_repository.find_by_id(request.id)
            if not subtask:
                raise ValueError(f"Subtask {request.id} not found in task {request.task_id}")
            
            # Update subtask using domain entity methods
            if request.title is not None:
                subtask.update_title(request.title)
            if request.description is not None:
                subtask.update_description(request.description)
            if request.status is not None:
                if request.status == "done":
                    subtask.complete()
                elif request.status == "todo":
                    subtask.reopen()
                else:
                    # For other statuses, update directly
                    status_obj = TaskStatus.from_string(request.status)
                    subtask.update_status(status_obj)
            if request.priority is not None:
                priority_obj = Priority.from_string(request.priority)
                subtask.update_priority(priority_obj)
            if request.assignees is not None:
                subtask.update_assignees(request.assignees)
            if request.progress_percentage is not None:
                # Update subtask progress percentage using domain method
                subtask.update_progress_percentage(request.progress_percentage)
            
            self._subtask_repository.save(subtask)
            updated_subtask = subtask.to_dict()
            
            # Update parent task progress
            self._update_parent_task_progress(str(request.task_id))
            
            # Sync parent task context after subtask update (Fix for Issue #3)
            try:
                self._sync_parent_task_context_after_subtask_update(task)
            except Exception as e:
                # Don't fail the subtask update if context sync fails
                logger.warning(f"Parent task context sync failed for task {task.id} but subtask update succeeded: {e}")
        else:
            # Fallback to existing task entity method for backward compatibility
            updates = {}
            if request.title is not None:
                updates["title"] = request.title
            if request.description is not None:
                updates["description"] = request.description
            if request.status is not None:
                updates["status"] = request.status
            if request.priority is not None:
                updates["priority"] = request.priority
            if request.assignees is not None:
                updates["assignees"] = request.assignees
            
            success = task.update_subtask(request.id, updates)
            if not success:
                raise ValueError(f"Subtask {request.id} not found in task {request.task_id}")
            self._task_repository.save(task)
            updated_subtask = task.get_subtask(request.id)
            
            # Sync parent task context after subtask update (Fix for Issue #3)
            try:
                self._sync_parent_task_context_after_subtask_update(task)
            except Exception as e:
                # Don't fail the subtask update if context sync fails
                logger.warning(f"Parent task context sync failed for task {task.id} but subtask update succeeded: {e}")
        
        return SubtaskResponse(
            task_id=str(request.task_id),
            subtask=updated_subtask,
            progress=task.get_subtask_progress()
        )

    def _convert_to_task_id(self, task_id: Union[str, int]) -> TaskId:
        if isinstance(task_id, int):
            return TaskId.from_int(task_id)
        else:
            return TaskId.from_string(str(task_id))
    
    def _update_parent_task_progress(self, task_id: str) -> None:
        """Update parent task progress based on subtask completion."""
        try:
            from ..services.task_progress_service import TaskProgressService
            progress_service = TaskProgressService(self._task_repository, self._subtask_repository)
            progress_service.update_task_progress_from_subtasks(task_id)
        except Exception as e:
            logger.warning(f"Failed to update parent task progress: {e}")
    
    def _sync_parent_task_context_after_subtask_update(self, parent_task) -> None:
        """Sync parent task context after subtask update to capture progress changes.
        
        This method implements automatic context synchronization as part of
        Fix for Issue #3: Automatic Context Updates for Task State Changes.
        When a subtask is updated, the parent task's context should be updated
        to reflect the new progress and status.
        
        Args:
            parent_task: The parent task domain entity
        """
        try:
            # Extract task ID and git_branch_id for context sync
            task_id_str = str(parent_task.id.value if hasattr(parent_task.id, 'value') else parent_task.id)
            git_branch_id = getattr(parent_task, 'git_branch_id', None)
            project_id = getattr(parent_task, 'project_id', None)
            
            # Get git_branch_name if needed (fallback to 'main')
            git_branch_name = "main"
            
            logger.info(f"[UpdateSubtaskUseCase] Auto-syncing parent task context for task {task_id_str} after subtask update")
            logger.debug(f"[UpdateSubtaskUseCase] Parent task details - status: {parent_task.status}, git_branch_id: {git_branch_id}")
            
            # Lazy initialization of context sync service to avoid circular imports
            if self._context_sync_service is None:
                from ..services.task_context_sync_service import TaskContextSyncService
                self._context_sync_service = TaskContextSyncService(self._task_repository)
            
            # Use TaskContextSyncService to sync context asynchronously
            import asyncio
            
            # Check if we're already in an async context
            try:
                loop = asyncio.get_running_loop()
                # We're in an async context, but this is a sync method
                logger.debug(f"[UpdateSubtaskUseCase] Running in async context, context sync triggered for parent task {task_id_str}")
                logger.info(f"[UpdateSubtaskUseCase] Parent task context sync triggered for task {task_id_str}")
                
            except RuntimeError:
                # No event loop, we can create one
                logger.debug(f"[UpdateSubtaskUseCase] No async context, creating new event loop for parent task context sync")
                
                async def sync_context():
                    return await self._context_sync_service.sync_context_and_get_task(
                        task_id=task_id_str,
                        user_id="system_subtask_update",
                        project_id=project_id or "default_project",
                        git_branch_name=git_branch_name
                    )
                
                # Run the async context sync
                result = asyncio.run(sync_context())
                
                if result:
                    logger.info(f"[UpdateSubtaskUseCase] Successfully synced parent task context for task {task_id_str}")
                else:
                    logger.warning(f"[UpdateSubtaskUseCase] Parent task context sync returned None for task {task_id_str}")
                
        except Exception as e:
            # Don't fail the subtask update operation if context sync fails
            logger.warning(f"[UpdateSubtaskUseCase] Failed to sync parent task context for task {parent_task.id} after subtask update: {e}")
            logger.debug(f"[UpdateSubtaskUseCase] Parent task context sync error details", exc_info=True) 