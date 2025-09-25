"""Create Task Use Case"""

import logging
from typing import Optional

from ...application.dtos.task import (
    CreateTaskRequest,
    CreateTaskResponse,
    TaskResponse
)
from ...domain.entities.task import Task
from ...domain.repositories.task_repository import TaskRepository
from ...domain.value_objects import TaskStatus, Priority
from ...domain.value_objects.task_status import TaskStatusEnum
from ...domain.value_objects.priority import PriorityLevel
from ...domain.value_objects.task_id import TaskId
from ...domain.events import TaskCreated


class CreateTaskUseCase:
    """Use case for creating a new task"""
    
    def __init__(self, task_repository: TaskRepository):
        self._task_repository = task_repository
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
            if hasattr(self._task_repository, 'git_branch_exists') and not self._task_repository.git_branch_exists(request.git_branch_id):
                return CreateTaskResponse.error_response(
                    f"git_branch_id '{request.git_branch_id}' does not exist. Please ensure the git branch exists before creating tasks."
                )
            
            # Create domain entity using git_branch_id from request (follows clean relationship chain)
            
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
            )

            # Add initial progress if details provided
            if request.details:
                task.append_progress(request.details)
            
            # Add dependencies if provided
            if hasattr(request, 'dependencies') and request.dependencies:
                for dep_id in request.dependencies:
                    if dep_id and dep_id.strip():
                        try:
                            task.add_dependency(TaskId(dep_id))
                        except ValueError as e:
                            # Log but don't fail creation if dependency is invalid
                            import logging
                            logging.warning(f"Skipping invalid dependency {dep_id}: {e}")
            
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
                from ...domain.services.event_dispatcher import dispatch_domain_event
                from ...domain.events.task_lifecycle_events import TaskCreatedEvent

                event = TaskCreatedEvent.create(
                    task_id=str(task.id.value),
                    branch_id=request.git_branch_id,
                    title=task.title,
                    status=str(task.status.value),
                    priority=str(task.priority.value),
                    assignees=task.assignees,
                    user_id=getattr(request, 'user_id', None)
                )

                dispatch_domain_event("task_created", event)
                self._logger.info(f"Dispatched task_created event for task {task.id.value}")

            except Exception as e:
                self._logger.warning(f"Failed to dispatch task creation event: {e}")
            
            # Handle domain events
            events = task.get_events()
            for event in events:
                if isinstance(event, TaskCreated):
                    # Could trigger notifications, logging, etc.
                    pass
            
            # Auto-create task context for hierarchical context inheritance
            try:
                # Use unified context facade for task context creation
                from ...application.factories.unified_context_facade_factory import UnifiedContextFacadeFactory
                from ...domain.constants import validate_user_id
                from ...domain.exceptions.authentication_exceptions import UserAuthenticationRequiredError

                # Get user_id from request or handle authentication
                user_id = getattr(request, 'user_id', None)
                if user_id is None:
                    # NO FALLBACKS ALLOWED - user authentication is required
                    raise UserAuthenticationRequiredError("Task context creation")
                
                user_id = validate_user_id(user_id, "Task context creation")
                
                # Get project_id from the branch (ORM is source of truth)
                project_id = None
                try:
                    from ...application.services.repository_provider_service import RepositoryProviderService

                    # Get instance and use repository provider to get branch repository
                    provider = RepositoryProviderService.get_instance()
                    branch_repo = provider.get_git_branch_repository()
                    branch = branch_repo.get(request.git_branch_id)
                    
                    if branch:
                        project_id = branch.project_id
                        self._logger.info(f"Found project_id '{project_id}' for branch '{request.git_branch_id}'")
                except Exception as e:
                    self._logger.warning(f"Could not get project_id from branch: {e}")
                
                # Create unified context facade
                factory = UnifiedContextFacadeFactory()
                context_facade = factory.create_facade(
                    user_id=user_id,
                    git_branch_id=request.git_branch_id,
                    project_id=project_id  # Pass project_id to facade
                )
                
                # Handle both TaskId objects and string IDs
                task_id_str = str(task.id.value) if hasattr(task.id, 'value') else str(task.id)
                
                # Create default task context with project_id
                context_data = {
                    "branch_id": request.git_branch_id,
                    "project_id": project_id,  # Include project_id in context data
                    "task_data": {
                        "title": task.title,
                        "status": str(task.status),
                        "description": task.description or "",
                        "priority": str(task.priority)
                    }
                }
                
                context_response = context_facade.create_context(
                    level="task",
                    context_id=task_id_str,
                    data=context_data
                )
                
                if not context_response["success"]:
                    # Log warning but don't fail task creation
                    self._logger.warning(f"Failed to create task context for {task_id_str}: {context_response.get('error')}")
                else:
                    # Set context_id on task entity after successful context creation
                    task.set_context_id(task_id_str)
                    # Save the updated task with context_id
                    self._task_repository.save(task)
                    
            except Exception as context_error:
                # Log context creation error but don't fail task creation
                task_id_str = str(task.id.value) if hasattr(task.id, 'value') else str(task.id)
                self._logger.warning(f"Error creating task context for {task_id_str}: {context_error}")
            
            # Convert to response DTO
            task_response = TaskResponse.from_domain(task)
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