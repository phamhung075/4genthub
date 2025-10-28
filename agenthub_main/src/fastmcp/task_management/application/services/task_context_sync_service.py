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

        # Get git_branch_repository for dependency injection
        git_branch_repo = self._get_git_branch_repository()
        self._get_task_use_case = GetTaskUseCase(task_repository, context_service, git_branch_repo)

    def _get_git_branch_repository(self):
        """Get git_branch_repository from RepositoryProviderService - single source of truth.

        FAIL FAST: Raises RepositoryProviderError if repository provider fails.
        This is critical infrastructure - project_id is REQUIRED by frontend contract.

        Raises:
            RepositoryProviderError: When repository provider fails or returns None
        """
        try:
            from ...application.services.repository_provider_service import RepositoryProviderService
            from ..exceptions import RepositoryProviderError

            provider = RepositoryProviderService.get_instance()
            git_branch_repo = provider.get_git_branch_repository()

            if git_branch_repo is None:
                raise RepositoryProviderError("git_branch_repository is None - cannot lookup project_id")

            return git_branch_repo

        except RepositoryProviderError:
            # Re-raise our custom exception
            raise
        except Exception as e:
            # Log as ERROR (not warning) with full stack trace
            logger.error(
                f"CRITICAL: Failed to get git_branch_repository - cannot fetch project_id: {e}",
                exc_info=True  # Include stack trace for debugging
            )
            # Fail fast - raise custom exception
            from ..exceptions import RepositoryProviderError
            raise RepositoryProviderError(
                f"Cannot fetch project_id without git_branch_repository: {e}"
            ) from e

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

    # ------------------------------------------------------------------
    # New synchronization methods for data integrity
    # ------------------------------------------------------------------

    async def sync_subtask_counts(self, task_id: str, subtask_repository) -> None:
        """Sync subtask counts and items to context_data.subtasks.

        This method updates the denormalized cache in context_data to reflect
        the actual subtask counts and data from the database.

        Args:
            task_id: The task ID (UUID as string)
            subtask_repository: Repository to fetch subtasks
        """
        try:
            from ...domain.value_objects.task_id import TaskId

            task_id_obj = TaskId.from_string(task_id)

            # Fetch all subtasks for this task
            repo = self._get_user_scoped_repository(subtask_repository)
            subtasks = repo.find_by_parent_task_id(task_id_obj)

            # Calculate counts and progress
            total_count = len(subtasks)
            completed_count = sum(1 for st in subtasks if str(st.status) in ['done', 'completed'])
            progress_percentage = (completed_count / total_count * 100.0) if total_count > 0 else 0.0

            # Build subtask items array
            subtask_items = []
            for st in subtasks:
                subtask_items.append({
                    "id": str(st.id.value if hasattr(st.id, 'value') else st.id),
                    "title": st.title,
                    "description": st.description or "",
                    "status": str(st.status),
                    "assignees": st.assignees if hasattr(st, 'assignees') else [],
                    "completed": str(st.status) in ['done', 'completed'],
                    "progress_notes": getattr(st, 'progress_notes', '')
                })

            # Get current context
            context_result = self._hierarchical_context_service.get_context(
                level="task",
                context_id=task_id
            )

            if context_result and context_result.get("success"):
                # Update subtasks section in context
                context_data = context_result.get("context_data", {})
                context_data["subtasks"] = {
                    "items": subtask_items,
                    "total_count": total_count,
                    "completed_count": completed_count,
                    "progress_percentage": progress_percentage
                }

                # Update context
                self._hierarchical_context_service.update_context(
                    level="task",
                    context_id=task_id,
                    data=context_data
                )

                logger.info(
                    "[TaskContextSyncService] Synced subtask counts for task %s: %d total, %d completed (%.1f%%)",
                    task_id, total_count, completed_count, progress_percentage
                )

        except Exception as exc:
            logger.error(
                "[TaskContextSyncService] Failed to sync subtask counts for task %s: %s",
                task_id, exc, exc_info=True
            )

    async def sync_task_status(self, task_id: str, new_status: str) -> None:
        """Sync task status to context_data.metadata.status.

        Args:
            task_id: The task ID (UUID as string)
            new_status: The new status value
        """
        try:
            # Get current context
            context_result = self._hierarchical_context_service.get_context(
                level="task",
                context_id=task_id
            )

            if context_result and context_result.get("success"):
                # Update status in context metadata
                context_data = context_result.get("context_data", {})
                if "metadata" not in context_data:
                    context_data["metadata"] = {}

                context_data["metadata"]["status"] = new_status

                # Update context
                self._hierarchical_context_service.update_context(
                    level="task",
                    context_id=task_id,
                    data=context_data
                )

                logger.info(
                    "[TaskContextSyncService] Synced status for task %s: %s",
                    task_id, new_status
                )

        except Exception as exc:
            logger.error(
                "[TaskContextSyncService] Failed to sync status for task %s: %s",
                task_id, exc, exc_info=True
            )

    async def sync_task_metadata(self, task_id: str, task) -> None:
        """Sync all task metadata fields to context_data.

        This includes:
        - Assignees (with @ prefix for context)
        - Timestamps (created_at, updated_at)
        - Estimated effort
        - Priority, labels, etc.

        Args:
            task: The Task domain entity
            task_id: The task ID (UUID as string)
        """
        try:
            # Get current context
            context_result = self._hierarchical_context_service.get_context(
                level="task",
                context_id=task_id
            )

            if context_result and context_result.get("success"):
                context_data = context_result.get("context_data", {})

                # Ensure metadata section exists
                if "metadata" not in context_data:
                    context_data["metadata"] = {}

                # Ensure objective section exists
                if "objective" not in context_data:
                    context_data["objective"] = {}

                # Sync metadata fields
                context_data["metadata"]["status"] = str(task.status)
                context_data["metadata"]["priority"] = str(task.priority)
                context_data["metadata"]["labels"] = task.labels if hasattr(task, 'labels') else []

                # Sync assignees with @ prefix
                assignees = task.assignees if hasattr(task, 'assignees') else []
                context_data["metadata"]["assignees"] = [
                    f"@{a}" if not a.startswith('@') else a
                    for a in assignees
                ]

                # Sync timestamps
                if hasattr(task, 'created_at') and task.created_at:
                    context_data["metadata"]["created_at"] = task.created_at.isoformat() if hasattr(task.created_at, 'isoformat') else str(task.created_at)

                if hasattr(task, 'updated_at') and task.updated_at:
                    context_data["metadata"]["updated_at"] = task.updated_at.isoformat() if hasattr(task.updated_at, 'isoformat') else str(task.updated_at)

                # Sync estimated effort bidirectionally
                if hasattr(task, 'estimated_effort') and task.estimated_effort:
                    context_data["objective"]["estimated_effort"] = task.estimated_effort

                # Update context
                self._hierarchical_context_service.update_context(
                    level="task",
                    context_id=task_id,
                    data=context_data
                )

                logger.info(
                    "[TaskContextSyncService] Synced metadata for task %s",
                    task_id
                )

        except Exception as exc:
            logger.error(
                "[TaskContextSyncService] Failed to sync metadata for task %s: %s",
                task_id, exc, exc_info=True
            ) 