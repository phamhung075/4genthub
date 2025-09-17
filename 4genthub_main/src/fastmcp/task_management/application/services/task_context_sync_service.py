from typing import Optional, Any
import logging

from .unified_context_service import UnifiedContextService
from .facade_service import FacadeService
from ...domain.repositories.task_repository import TaskRepository
from ...domain.value_objects.task_id import TaskId
from fastmcp.task_management.application.use_cases.get_task import GetTaskUseCase
from ...domain.constants import validate_user_id
from ...domain.exceptions.authentication_exceptions import UserAuthenticationRequiredError
from fastmcp.config.auth_config import AuthConfig

logger = logging.getLogger(__name__)


class TaskContextSyncService:
    """Application-level service that ensures a freshly-created or updated Task
    has an up-to-date Context and returns the complete TaskResponse (including
    context data).
    
    This keeps infrastructure-heavy orchestration out of facades / use-cases and
    out of the Domain layer while remaining easily testable.
    """

    def __init__(self, task_repository: TaskRepository, context_service: Optional[Any] = None, user_id: Optional[str] = None):
        self._user_id = user_id  # Store user context
        self._task_repository = task_repository
        # Initialize hierarchical context service using FacadeService
        self._hierarchical_context_service = FacadeService.get_unified_context_facade(user_id=user_id)
        self._get_task_use_case = GetTaskUseCase(task_repository, context_service)

    def with_user(self, user_id: str) -> 'TaskContextSyncService':
        """Create a new service instance scoped to a specific user."""
        return TaskContextSyncService(self._task_repository, self._hierarchical_context_service, user_id)

    def _get_user_scoped_repository(self, repository):
        """Get user-scoped repository if user_id is available."""
        if self._user_id and hasattr(repository, 'with_user'):
            return repository.with_user(self._user_id)
        return repository

    # ------------------------------------------------------------------
    # Public helpers
    # ------------------------------------------------------------------

    async def sync_context_and_get_task(
        self,
        task_id: str,
        *,
        user_id: Optional[str] = None,
        project_id: str = "",
        git_branch_name: str = "main",
    ) -> Optional[Any]:
        """Ensure context exists for *task_id* and return TaskResponse with context.

        Returns None if the task cannot be found or any step fails. The caller
        can decide how to handle fallback behaviour.
        """
        try:
            # Validate user authentication
            if user_id is None:
                # NO FALLBACKS ALLOWED - user authentication is required
                raise UserAuthenticationRequiredError("Task context sync")
            
            user_id = validate_user_id(user_id, "Task context sync")
            
            # ------------------------------------------------------------------
            # 1. Reload domain task and create/update its context
            # ------------------------------------------------------------------
            task_id_obj = TaskId.from_string(task_id)
            repo = self._get_user_scoped_repository(self._task_repository)
            domain_task = repo.find_by_id(task_id_obj)
            if domain_task is None:
                logger.warning("[TaskContextSyncService] Task %s not found while syncing context", task_id)
                return None

            # Create or update task context in hierarchical system
            task_id_str = str(domain_task.id.value if hasattr(domain_task.id, 'value') else domain_task.id)
            
            # If project_id not provided, try to get it from the task's git_branch
            # Note: Current repository structure requires project_id to find git branch
            # This is a circular dependency that cannot be resolved without refactoring
            if not project_id and hasattr(domain_task, 'git_branch_id'):
                # Cannot retrieve project_id from branch without knowing project_id first
                logger.debug(f"Cannot retrieve project_id from branch {domain_task.git_branch_id} without knowing project_id")
                # Use domain_task.project_id if available, otherwise use default
                project_id = getattr(domain_task, 'project_id', None)
            
            # Ensure we have a project_id
            if not project_id:
                raise ValueError("project_id is required for context sync (no fallback allowed for DDD compliance)")
            
            # Try to get existing context first
            context_result = self._hierarchical_context_service.get_context(
                level="task",
                context_id=task_id_str
            )
            
            # Prepare task data
            task_data = {
                "task_data": {
                    "title": domain_task.title,
                    "description": domain_task.description,
                    "status": domain_task.status.value if hasattr(domain_task.status, 'value') else str(domain_task.status),
                    "priority": domain_task.priority.value if hasattr(domain_task.priority, 'value') else str(domain_task.priority),
                    "assignees": domain_task.assignees,
                    "labels": domain_task.labels,
                    "estimated_effort": domain_task.estimated_effort,
                    "due_date": domain_task.due_date if domain_task.due_date else None
                },
                # Add parent references for proper 4-tier hierarchy
                # Tasks belong to branches in the 4-tier system
                "parent_branch_id": domain_task.git_branch_id,
                "parent_branch_context_id": domain_task.git_branch_id
            }
            
            if not context_result:
                # Create new context
                logger.info("[TaskContextSyncService] Creating new context for task %s with project_id=%s", task_id_str, project_id)
                logger.debug("[TaskContextSyncService] Context data: %s", task_data)
                self._hierarchical_context_service.create_context(
                    level="task",
                    context_id=task_id_str,
                    data=task_data
                )
            else:
                # Update existing context
                self._hierarchical_context_service.update_context(
                    level="task",
                    context_id=task_id_str,
                    data=task_data
                )

            # ------------------------------------------------------------------
            # 2. Retrieve TaskResponse *with* context data
            # ------------------------------------------------------------------
            task_response = await self._get_task_use_case.execute(
                task_id,
                generate_rules=False,
                force_full_generation=False,
                include_context=True,
            )
            return task_response
        except UserAuthenticationRequiredError:
            # Re-raise authentication errors - they should not be swallowed
            raise
        except ValueError:
            # Re-raise validation errors - they should not be swallowed
            raise
        except Exception as exc:
            logger.error("[TaskContextSyncService] Failed to sync context for task %s: %s", task_id, exc, exc_info=True)
            return None 