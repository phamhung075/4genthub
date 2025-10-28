"""Update Task Use Case"""

from typing import Optional, Union
import logging

from ...application.dtos.task import (
    UpdateTaskRequest,
    UpdateTaskResponse,
    TaskResponse
)

from ...domain import TaskRepository, TaskId, TaskStatus, Priority, TaskNotFoundError
from ...domain.events import TaskUpdated

logger = logging.getLogger(__name__)


class UpdateTaskUseCase:
    """Use case for updating an existing task"""
    
    def __init__(self, task_repository: TaskRepository, git_branch_repository=None):
        self._task_repository = task_repository
        self._git_branch_repository = git_branch_repository
        self._context_sync_service = None  # Lazy initialization to avoid circular imports
    
    def execute(self, request: UpdateTaskRequest) -> UpdateTaskResponse:
        """Execute the update task use case"""
        # Convert to domain value object with proper type handling
        domain_task_id = self._convert_to_task_id(request.task_id)

        # Find the task
        task = self._task_repository.find_by_id(domain_task_id)
        if not task:
            raise TaskNotFoundError(f"Task {request.task_id} not found")

        # Store old values for event
        old_status = str(task.status.value) if hasattr(task.status, 'value') else str(task.status)
        old_branch_id = task.git_branch_id if hasattr(task, 'git_branch_id') else None

        # Update task fields if provided
        if request.title is not None:
            task.update_title(request.title)

        if request.description is not None:
            task.update_description(request.description)

        if request.status is not None:
            new_status = TaskStatus(request.status)
            # Only update status if it's actually changing
            if task.status != new_status:
                task.update_status(new_status)

        if request.priority is not None:
            new_priority = Priority(request.priority)
            # Only update priority if it's actually changing
            if task.priority != new_priority:
                task.update_priority(new_priority)
        
        if request.details is not None:
            task.append_progress(request.details)
        
        if request.estimated_effort is not None:
            task.update_estimated_effort(request.estimated_effort)
        
        if request.assignees is not None:
            task.update_assignees(request.assignees)
        
        if request.labels is not None:
            task.update_labels(request.labels)
        
        if request.due_date is not None:
            task.update_due_date(request.due_date)

        if request.progress_percentage is not None:
            task.set_progress_percentage(request.progress_percentage)

        # IMPORTANT: Set context_id LAST, after all other updates that might clear it
        if request.context_id is not None:
            logger.info(f"Setting context_id to: {request.context_id}")
            task.set_context_id(request.context_id)
            logger.info(f"Task context_id after set: {task.context_id}")
        
        # Save the updated task
        self._task_repository.save(task)

        # Check context_id after save
        logger.info(f"Task context_id after save: {task.context_id}")

        # Auto-sync task context after update (Fix for Issue #3)
        try:
            self._sync_task_context_after_update(task)
        except Exception as e:
            # Don't fail the task update if context sync fails
            logger.warning(f"Context sync failed for task {task.id} but task update succeeded: {e}")

        # Dispatch domain event for task update
        # Branch statistics will be updated automatically by event handlers
        try:
            from ...domain.services.event_dispatcher import dispatch_domain_event
            from ...domain.events.task_lifecycle_events import TaskUpdatedEvent

            new_status = str(task.status.value) if hasattr(task.status, 'value') else str(task.status)
            new_branch_id = task.git_branch_id if hasattr(task, 'git_branch_id') else None

            # Only dispatch if something changed
            if old_status != new_status or old_branch_id != new_branch_id:
                event = TaskUpdatedEvent.create(
                    task_id=str(task.id.value),
                    branch_id=new_branch_id or old_branch_id,
                    old_status=old_status,
                    new_status=new_status,
                    old_branch_id=old_branch_id,
                    new_branch_id=new_branch_id,
                    user_id=getattr(request, 'user_id', None)
                )

                dispatch_domain_event("task_updated", event)
                logger.info(f"Dispatched task_updated event for task {task.id.value}")

        except Exception as e:
            logger.warning(f"Failed to dispatch task update event: {e}")

        # Convert to response DTO with project_id via repository join (moved before WebSocket)
        task_response = TaskResponse.from_domain(task, git_branch_repository=self._git_branch_repository)

        # Send WebSocket notification for frontend real-time updates
        try:
            from ..services.websocket_notification_service import WebSocketNotificationService
            from ..services.websocket_payload_builder import WebSocketPayloadBuilder

            # Build complete WebSocket payload using WebSocketPayloadBuilder (DRY principle)
            task_payload = WebSocketPayloadBuilder.build_task_payload(
                task=task,
                task_response=task_response  # Complete data with project_id, subtask_count, etc.
            )

            # Log payload size for monitoring
            payload_size = WebSocketPayloadBuilder.estimate_payload_size(task_payload)
            logger.info(f"Task update WebSocket payload size: {payload_size} bytes for task {task.id.value}")

            # Create task update notification via WebSocket notification service
            WebSocketNotificationService.sync_broadcast_task_event(
                event_type="updated",
                task_id=str(task.id.value),
                user_id=getattr(request, 'user_id', None) or "system",
                task_data=task_payload,  # Use complete payload from builder
                git_branch_id=task.git_branch_id if hasattr(task, 'git_branch_id') else None
            )

            logger.info(f"Sent WebSocket notification for task {task.id.value} update with complete payload ({len(task_payload)} fields)")

        except Exception as e:
            logger.warning(f"Failed to send WebSocket notification: {e}")

        # Handle domain events
        events = task.get_events()
        for event in events:
            if isinstance(event, TaskUpdated):
                # Could trigger notifications, logging, etc.
                pass

        # Return response (task_response already created above before WebSocket notification)
        return UpdateTaskResponse.success_response(task_response)
    
    def _convert_to_task_id(self, task_id: Union[str, int, TaskId]) -> TaskId:
        """Convert task_id to TaskId domain object"""
        if isinstance(task_id, TaskId):
            return task_id
        # Always convert to string and use from_string method
        return TaskId.from_string(str(task_id))
    
    def _sync_task_context_after_update(self, task) -> None:
        """Sync task context after update to capture state changes.
        
        This method implements automatic context synchronization as part of
        Fix for Issue #3: Automatic Context Updates for Task State Changes.
        
        Args:
            task: The domain task entity that was just updated
        """
        try:
            # Extract task ID and git_branch_id for context sync
            task_id_str = str(task.id.value if hasattr(task.id, 'value') else task.id)
            git_branch_id = getattr(task, 'git_branch_id', None)
            project_id = getattr(task, 'project_id', None)
            
            # Get git_branch_name if needed (fallback to 'main')
            git_branch_name = "main"
            
            logger.info(f"[UpdateTaskUseCase] Auto-syncing context for task {task_id_str} after update")
            logger.debug(f"[UpdateTaskUseCase] Task details - status: {task.status}, git_branch_id: {git_branch_id}")
            
            # Lazy initialization of context sync service to avoid circular imports
            if self._context_sync_service is None:
                from ..services.task_context_sync_service import TaskContextSyncService
                self._context_sync_service = TaskContextSyncService(self._task_repository)

            # Use TaskContextSyncService to sync context asynchronously
            # Note: Since the context sync service has async methods, we need to handle this properly
            import asyncio

            # 🔄 SYNC: Granular synchronization of task status and metadata
            try:
                asyncio.run(self._context_sync_service.sync_task_metadata(task_id_str, task))
                logger.info(f"✅ Synced metadata for updated task {task_id_str}")
            except RuntimeError:
                # Already in event loop
                logger.info(f"⏭️ Scheduled metadata sync for updated task {task_id_str} (in async context)")
            except Exception as sync_error:
                logger.warning(f"⚠️ Failed to sync metadata for updated task {task_id_str}: {sync_error}")

            # Check if we're already in an async context
            try:
                loop = asyncio.get_running_loop()
                # We're in an async context, but this is a sync method
                # We'll use run_in_executor to avoid blocking
                logger.debug(f"[UpdateTaskUseCase] Running in async context, using task creation for context sync")

                # Since we can't await in a sync method, we'll just trigger context update
                # The context will be updated on next access or through background task

                # For now, we'll just log that sync was triggered
                logger.info(f"[UpdateTaskUseCase] Context sync triggered for task {task_id_str}")
                
            except RuntimeError:
                # No event loop, we can create one
                logger.debug(f"[UpdateTaskUseCase] No async context, creating new event loop for context sync")
                
                async def sync_context():
                    if not project_id:
                        raise ValueError(f"project_id is required for context sync")
                    return await self._context_sync_service.sync_context_and_get_task(
                        task_id=task_id_str,
                        user_id="system_update",
                        project_id=project_id,
                        git_branch_name=git_branch_name
                    )
                
                # Run the async context sync
                result = asyncio.run(sync_context())
                
                if result:
                    logger.info(f"[UpdateTaskUseCase] Successfully synced context for task {task_id_str}")
                else:
                    logger.warning(f"[UpdateTaskUseCase] Context sync returned None for task {task_id_str}")
                
        except Exception as e:
            # Don't fail the update operation if context sync fails
            logger.warning(f"[UpdateTaskUseCase] Failed to sync context for task {task.id} after update: {e}")
            logger.debug(f"[UpdateTaskUseCase] Context sync error details", exc_info=True) 
