"""Create Task Use Case"""

import logging

from ...application.dtos.task import CreateTaskRequest, CreateTaskResponse, TaskResponse
from ...domain.entities.task import Task
from ...domain.events import TaskCreated
from ...domain.repositories.task_repository import TaskRepository
from ...domain.value_objects import Priority, TaskStatus
from ...domain.value_objects.priority import PriorityLevel
from ...domain.value_objects.task_id import TaskId
from ...domain.value_objects.task_status import TaskStatusEnum

logger = logging.getLogger(__name__)


class CreateTaskUseCase:
    """Use case for creating a new task"""

    def __init__(self, task_repository: TaskRepository, git_branch_repository=None):
        self._task_repository = task_repository
        self._git_branch_repository = git_branch_repository
        self._logger = logging.getLogger(__name__)

    def execute(self, request: CreateTaskRequest) -> CreateTaskResponse:
        """Execute the create task use case following clean relationship chain"""
        try:
            # Generate new task ID
            task_id = self._task_repository.get_next_id()

            # Create domain value objects. Let ValueError propagate for invalid inputs.
            status = TaskStatus(request.status or TaskStatusEnum.TODO.value)
            priority = Priority(request.priority or PriorityLevel.MEDIUM.label)

            # Handle very long content gracefully by truncating
            title = request.title
            if title and len(title) > 200:
                title = title[:200]

            description = request.description
            if description and len(description) > 2000:
                description = description[:2000]

            # Validate git_branch_id existence before creating task
            # Note: We allow task creation even if git_branch doesn't exist as long as branch_context exists
            # This supports context auto-creation scenarios where context is created before git_branch
            if hasattr(
                self._task_repository, "git_branch_exists"
            ) and not self._task_repository.git_branch_exists(request.git_branch_id):
                logger.warning(
                    f"git_branch_id '{request.git_branch_id}' does not exist in project_git_branchs table. "
                    f"Task will be created with context auto-creation support. "
                    f"Ensure git branch is created later for full functionality."
                )

            # Create domain entity using git_branch_id from request (follows clean relationship chain)

            # Get user_id from request or repository
            user_id = (
                request.user_id
                if hasattr(request, "user_id") and request.user_id
                else None
            )
            if not user_id and hasattr(self._task_repository, "user_id"):
                user_id = self._task_repository.user_id

            task = Task.create(
                id=task_id,
                title=title,
                description=description,
                status=status,
                priority=priority,
                git_branch_id=request.git_branch_id,
                estimated_effort=request.estimated_effort,
                assignees=request.assignees,
                labels=request.labels,
                due_date=request.due_date,
                user_id=user_id,
            )

            # Add initial progress if details provided
            if request.details:
                task.append_progress(request.details)

            # Add dependencies if provided
            if hasattr(request, "dependencies") and request.dependencies:
                for dep_id in request.dependencies:
                    if dep_id and dep_id.strip():
                        try:
                            task.add_dependency(TaskId(dep_id))
                        except ValueError as e:
                            # Log but don't fail creation if dependency is invalid
                            import logging

                            logging.warning(
                                f"Skipping invalid dependency {dep_id}: {e}"
                            )

            # Create the task (with duplicate detection)
            save_result = self._task_repository.save(task)

            # Check if save was successful
            if not save_result:
                return CreateTaskResponse.error_response(
                    "Failed to save task to database. This may be due to an invalid git_branch_id or database constraint violation."
                )

            # Dispatch domain event for task creation
            # Branch statistics will be updated automatically by event handlers
            try:
                from ...domain.events.task_lifecycle_events import TaskCreatedEvent
                from ...domain.services.event_dispatcher import dispatch_domain_event

                event = TaskCreatedEvent.create(
                    task_id=str(task.id.value),
                    branch_id=request.git_branch_id,
                    title=task.title,
                    status=str(task.status.value),
                    priority=str(task.priority.value),
                    assignees=task.assignees,
                    user_id=getattr(request, "user_id", None),
                )

                dispatch_domain_event("task_created", event)
                self._logger.info(
                    f"Dispatched task_created event for task {task.id.value}"
                )

            except Exception as e:
                self._logger.warning(f"Failed to dispatch task creation event: {e}")

            # WebSocket notification moved after task_response creation for complete data

            # Handle domain events
            events = task.get_events()
            for event in events:
                if isinstance(event, TaskCreated):
                    # Could trigger notifications, logging, etc.
                    pass

            # Auto-create task context for hierarchical context inheritance
            try:
                # Use unified context facade for task context creation
                from ...application.factories.unified_context_facade_factory import (
                    UnifiedContextFacadeFactory,
                )
                from ...domain.constants import validate_user_id
                from ...domain.exceptions.authentication_exceptions import (
                    UserAuthenticationRequiredError,
                )

                # Get user_id from request or handle authentication
                user_id = getattr(request, "user_id", None)
                if user_id is None:
                    # NO FALLBACKS ALLOWED - user authentication is required
                    raise UserAuthenticationRequiredError("Task context creation")

                user_id = validate_user_id(user_id, "Task context creation")

                # Get project_id from the branch (ORM is source of truth)
                project_id = None
                try:
                    # Use injected git_branch_repository to get project_id
                    if self._git_branch_repository:
                        branch = self._git_branch_repository.get(request.git_branch_id)
                        if branch:
                            project_id = branch.project_id
                            self._logger.info(
                                f"Found project_id '{project_id}' for branch '{request.git_branch_id}'"
                            )
                except Exception as e:
                    self._logger.warning(f"Could not get project_id from branch: {e}")

                # Create unified context facade
                factory = UnifiedContextFacadeFactory()
                context_facade = factory.create_facade(
                    user_id=user_id,
                    git_branch_id=request.git_branch_id,
                    project_id=project_id,  # Pass project_id to facade
                )

                # Handle both TaskId objects and string IDs
                task_id_str = (
                    str(task.id.value) if hasattr(task.id, "value") else str(task.id)
                )

                # Create default task context with project_id
                context_data = {
                    "branch_id": request.git_branch_id,
                    "project_id": project_id,  # Include project_id in context data
                    "task_data": {
                        "title": task.title,
                        "status": str(task.status),
                        "description": task.description or "",
                        "priority": str(task.priority),
                    },
                }

                context_response = context_facade.create_context(
                    level="task", context_id=task_id_str, data=context_data
                )

                if not context_response["success"]:
                    # Log warning but don't fail task creation
                    self._logger.warning(
                        f"Failed to create task context for {task_id_str}: {context_response.get('error')}"
                    )
                else:
                    # Set context_id on task entity after successful context creation
                    task.set_context_id(task_id_str)
                    # Save the updated task with context_id
                    self._task_repository.save(task)

                    # 🔄 SYNC: Initial metadata synchronization after task creation
                    try:
                        import asyncio

                        from ..services.task_context_sync_service import (
                            TaskContextSyncService,
                        )

                        sync_service = TaskContextSyncService(
                            self._task_repository, user_id=user_id
                        )

                        # Sync task metadata (timestamps, assignees, estimated_effort, etc.)
                        try:
                            asyncio.run(
                                sync_service.sync_task_metadata(task_id_str, task)
                            )
                            self._logger.info(
                                f"✅ Synced metadata for newly created task {task_id_str}"
                            )
                        except RuntimeError:
                            # Already in event loop, use asyncio.create_task
                            loop = asyncio.get_event_loop()
                            loop.create_task(
                                sync_service.sync_task_metadata(task_id_str, task)
                            )
                            self._logger.info(
                                f"✅ Scheduled metadata sync for newly created task {task_id_str}"
                            )
                    except Exception as sync_error:
                        self._logger.warning(
                            f"⚠️ Failed to sync metadata for newly created task {task_id_str}: {sync_error}"
                        )

            except Exception as context_error:
                # Log context creation error but don't fail task creation
                task_id_str = (
                    str(task.id.value) if hasattr(task.id, "value") else str(task.id)
                )
                self._logger.warning(
                    f"Error creating task context for {task_id_str}: {context_error}"
                )

            # Convert to response DTO with project_id via repository join
            task_response = TaskResponse.from_domain(
                task, git_branch_repository=self._git_branch_repository
            )

            # Send WebSocket notification for frontend real-time updates (AFTER task_response creation for complete data)
            try:
                from ..services.websocket_notification_service import (
                    WebSocketNotificationService,
                )
                from ..services.websocket_payload_builder import WebSocketPayloadBuilder

                # Build complete WebSocket payload using WebSocketPayloadBuilder (DRY principle)
                # Now we have task_response with project_id and subtask counts for complete payload
                task_payload = WebSocketPayloadBuilder.build_task_payload(
                    task=task,
                    task_response=task_response,  # Complete data with project_id, subtask_count, etc.
                )

                # Log payload size for monitoring
                payload_size = WebSocketPayloadBuilder.estimate_payload_size(
                    task_payload
                )
                self._logger.info(
                    f"Task creation WebSocket payload size: {payload_size} bytes for task {task.id.value}"
                )

                # Create task creation notification via WebSocket notification service
                WebSocketNotificationService.sync_broadcast_task_event(
                    event_type="created",
                    task_id=str(task.id.value),
                    user_id=user_id or "system",
                    task_data=task_payload,  # Use complete payload from builder
                    git_branch_id=request.git_branch_id,
                )

                self._logger.info(
                    f"Sent WebSocket notification for task {task.id.value} creation with complete payload ({len(task_payload)} fields)"
                )

            except Exception as e:
                self._logger.error(
                    f"Failed to send WebSocket notification for task {task.id.value}: {e}"
                )
                import traceback

                self._logger.error(f"Full traceback: {traceback.format_exc()}")

            return CreateTaskResponse.success_response(task_response)

        except ValueError as e:
            # Re-raise validation errors so they can be handled by the caller
            raise e
        except Exception as e:
            # Handle any other errors during task creation
            import logging
            import traceback

            logging.error(f"Failed to create task: {e}")
            logging.error(f"Traceback: {traceback.format_exc()}")
            return CreateTaskResponse.error_response(f"Failed to create task: {str(e)}")
