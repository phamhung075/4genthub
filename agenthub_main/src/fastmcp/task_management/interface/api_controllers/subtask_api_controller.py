"""
Subtask API Controller

This controller handles frontend subtask management operations following proper DDD architecture.
It serves as the interface layer, delegating business logic to application facades.
"""

import logging
from datetime import datetime, timezone
from typing import Any

from fastmcp.types import (
    DeleteResponse,
    SubtaskResponse,
    SubtasksResponse,
    subtask_summary_to_dto,
    subtask_to_dto,
)

from ...application.services.facade_service import FacadeService
from ...infrastructure.repositories.subtask_repository_factory import (
    SubtaskRepositoryFactory,
)

# FacadeService handles all facade creation (DDD compliant)

logger = logging.getLogger(__name__)


class SubtaskAPIController:
    """
    API Controller for subtask management operations.

    This controller provides a clean interface between frontend routes and
    application services, ensuring proper separation of concerns.
    """

    def __init__(self):
        """Initialize the controller"""
        # Use FacadeService for DDD compliance - no direct factory access
        self.facade_service = FacadeService.get_instance()

    def _get_task_id_from_subtask(self, subtask_id: str, user_id: str) -> str | None:
        """
        Helper method to get task_id from subtask_id by looking up the subtask.

        Args:
            subtask_id: Subtask identifier
            user_id: User identifier for repository access

        Returns:
            Task ID if subtask is found, None otherwise
        """
        try:
            # Create subtask repository factory and repository
            subtask_repository_factory = SubtaskRepositoryFactory()
            # Use create_orm_subtask_repository which accepts user_id
            subtask_repository = (
                subtask_repository_factory.create_orm_subtask_repository(
                    user_id=user_id
                )
            )

            # Look up the subtask
            subtask = subtask_repository.find_by_id(subtask_id)

            if subtask:
                # Return the parent task ID from the subtask
                return str(subtask.parent_task_id)
            return None

        except Exception as e:
            logger.error(f"Error looking up task_id for subtask {subtask_id}: {e}")
            return None

    def create_subtask(
        self, task_id: str, title: str, description: str | None, user_id: str, session
    ) -> SubtaskResponse:
        """
        Create a new subtask.

        Args:
            task_id: Parent task identifier
            title: Subtask title
            description: Optional subtask description
            user_id: Authenticated user ID
            session: Database session

        Returns:
            Subtask creation result
        """
        try:
            # First get the parent task to derive project_id and git_branch_id
            # DDD Compliance: No hardcoded project IDs - derive from parent task
            temp_facade = self.facade_service.get_task_facade(
                project_id=None,  # Will be determined from task lookup
                git_branch_id=None,  # Will be determined from task lookup
                user_id=user_id,
            )
            parent_task = temp_facade.get_task(task_id)
            if not parent_task or not parent_task.get("task"):
                raise ValueError(f"Parent task {task_id} not found")

            # Extract project context from parent task
            parent_git_branch_id = parent_task["task"].get("git_branch_id")
            if not parent_git_branch_id:
                raise ValueError(
                    f"Parent task {task_id} missing git_branch_id required for context derivation"
                )

            # Now get the proper SUBTASK facade with derived context
            subtask_facade = self.facade_service.get_subtask_facade(
                project_id=None,  # Will be derived from git_branch_id
                git_branch_id=parent_git_branch_id,
                user_id=user_id,
            )

            # Create subtask request data
            subtask_data = {
                "task_id": task_id,
                "title": title,
                "description": description or "",
                "status": "todo",
                "priority": "medium",
            }

            # Delegate to SUBTASK facade using handle_manage_subtask
            result = subtask_facade.handle_manage_subtask(
                action="create", task_id=task_id, subtask_data=subtask_data
            )

            logger.info(
                f"Subtask created successfully for user {user_id}: {result.get('subtask', {}).get('id')}"
            )

            # Convert subtask dict to DTO
            subtask_dict = result.get("subtask")

            # Create a simple object to pass to converter
            class SubtaskObj:
                def __init__(self, data):
                    for key, value in data.items():
                        setattr(self, key, value)

            subtask_obj = SubtaskObj(subtask_dict)

            return SubtaskResponse(
                success=True,
                subtask=subtask_to_dto(subtask_obj),
                message="Subtask created successfully",
                timestamp=datetime.now(timezone.utc).isoformat(),
            )

        except Exception as e:
            logger.error(f"Error creating subtask for user {user_id}: {e}")
            return SubtaskResponse(
                success=False,
                subtask=None,
                error=str(e),
                message="Failed to create subtask",
                timestamp=datetime.now(timezone.utc).isoformat(),
            )

    def list_subtasks(self, task_id: str, user_id: str, session) -> SubtasksResponse:
        """
        List subtasks for a parent task.

        Args:
            task_id: Parent task identifier
            user_id: Authenticated user ID
            session: Database session

        Returns:
            List of subtasks
        """
        logger.info(f"🟢 [CONTROLLER] list_subtasks called: task_id={task_id}, user_id={user_id}")

        try:
            # DDD Compliance: No hardcoded project IDs - derive from parent task
            logger.info(f"🟢 [CONTROLLER] Getting task facade to lookup parent task")
            temp_facade = self.facade_service.get_task_facade(
                project_id=None, git_branch_id=None, user_id=user_id
            )

            logger.info(f"🟢 [CONTROLLER] Looking up parent task: {task_id}")
            parent_task = temp_facade.get_task(task_id)
            if not parent_task or not parent_task.get("task"):
                logger.error(f"🔴 [CONTROLLER] Parent task {task_id} not found")
                raise ValueError(f"Parent task {task_id} not found")

            parent_git_branch_id = parent_task["task"].get("git_branch_id")
            logger.info(f"🟢 [CONTROLLER] Parent task found, git_branch_id={parent_git_branch_id}")

            if not parent_git_branch_id:
                logger.error(f"🔴 [CONTROLLER] Parent task {task_id} missing git_branch_id")
                raise ValueError(f"Parent task {task_id} missing git_branch_id")

            # Get SUBTASK facade for listing operations
            logger.info(f"🟢 [CONTROLLER] Getting subtask facade for git_branch_id={parent_git_branch_id}")
            subtask_facade = self.facade_service.get_subtask_facade(
                project_id=None, git_branch_id=parent_git_branch_id, user_id=user_id
            )

            # Delegate to SUBTASK facade
            logger.info(f"🟢 [CONTROLLER] Calling subtask_facade.handle_manage_subtask(action='list')")
            result = subtask_facade.handle_manage_subtask(
                action="list", task_id=task_id
            )

            subtasks_count = len(result.get('subtasks', []))
            logger.info(f"🟢 [CONTROLLER] Facade returned {subtasks_count} subtasks")
            if subtasks_count > 0:
                subtasks_sample = result.get('subtasks', [])[:3]  # First 3 for logging
                logger.info(f"🟢 [CONTROLLER] Sample subtasks: {[{'id': st.get('id'), 'title': st.get('title')} for st in subtasks_sample]}")

            # Convert subtasks to DTOs
            subtasks_list = result.get("subtasks", [])

            # Create objects for converter
            class SubtaskObj:
                def __init__(self, data):
                    for key, value in data.items():
                        setattr(self, key, value)

            logger.info(f"🟢 [CONTROLLER] Converting {len(subtasks_list)} subtasks to DTOs")
            subtask_dtos = [
                subtask_summary_to_dto(SubtaskObj(st)) for st in subtasks_list
            ]

            logger.info(f"🐛 [CONTROLLER DEBUG] Created {len(subtask_dtos)} DTOs")
            logger.info(f"🐛 [CONTROLLER DEBUG] DTO IDs: {[dto.id for dto in subtask_dtos]}")
            logger.info(f"🟢 [CONTROLLER] Returning SubtasksResponse with {len(subtask_dtos)} DTOs")
            return SubtasksResponse(
                success=True,
                subtasks=subtask_dtos,
                total=len(subtask_dtos),
                message=f"Retrieved {len(subtask_dtos)} subtasks",
                timestamp=datetime.now(timezone.utc).isoformat(),
            )

        except Exception as e:
            logger.error(
                f"🔴 [CONTROLLER ERROR] Error listing subtasks for task {task_id} by user {user_id}: {e}"
            )
            logger.exception("Full traceback:")
            return SubtasksResponse(
                success=False,
                subtasks=[],
                error=str(e),
                message="Failed to list subtasks",
                timestamp=datetime.now(timezone.utc).isoformat(),
            )

    def get_subtask(self, subtask_id: str, user_id: str, session) -> SubtaskResponse:
        """
        Get a specific subtask.

        Args:
            subtask_id: Subtask identifier
            user_id: Authenticated user ID
            session: Database session

        Returns:
            Subtask details
        """
        try:
            # First, look up the subtask to get its task_id
            task_id = self._get_task_id_from_subtask(subtask_id, user_id)
            if not task_id:
                return SubtaskResponse(
                    success=False,
                    subtask=None,
                    error="Subtask not found",
                    message="Subtask not found or access denied",
                    timestamp=datetime.now(timezone.utc).isoformat(),
                )

            # DDD Compliance: No hardcoded project IDs - derive from parent task
            temp_facade = self.facade_service.get_task_facade(
                project_id=None, git_branch_id=None, user_id=user_id
            )
            parent_task = temp_facade.get_task(task_id)
            if not parent_task or not parent_task.get("task"):
                raise ValueError(f"Parent task {task_id} not found")

            parent_git_branch_id = parent_task["task"].get("git_branch_id")
            if not parent_git_branch_id:
                raise ValueError(f"Parent task {task_id} missing git_branch_id")

            # Get SUBTASK facade for get operations
            subtask_facade = self.facade_service.get_subtask_facade(
                project_id=None, git_branch_id=parent_git_branch_id, user_id=user_id
            )

            # Delegate to SUBTASK facade
            result = subtask_facade.handle_manage_subtask(
                action="get", task_id=task_id, subtask_id=subtask_id
            )

            if not result.get("success"):
                return SubtaskResponse(
                    success=False,
                    subtask=None,
                    error="Subtask not found",
                    message="Subtask not found or access denied",
                    timestamp=datetime.now(timezone.utc).isoformat(),
                )

            logger.info(f"Retrieved subtask {subtask_id} for user {user_id}")

            # Convert subtask to DTO
            subtask_dict = result.get("subtask")

            class SubtaskObj:
                def __init__(self, data):
                    for key, value in data.items():
                        setattr(self, key, value)

            return SubtaskResponse(
                success=True,
                subtask=subtask_to_dto(SubtaskObj(subtask_dict)),
                timestamp=datetime.now(timezone.utc).isoformat(),
            )

        except Exception as e:
            logger.error(f"Error getting subtask {subtask_id} for user {user_id}: {e}")
            return SubtaskResponse(
                success=False,
                subtask=None,
                error=str(e),
                message="Failed to get subtask",
                timestamp=datetime.now(timezone.utc).isoformat(),
            )

    def update_subtask(
        self, subtask_id: str, update_data: dict[str, Any], user_id: str, session
    ) -> SubtaskResponse:
        """
        Update a subtask.

        Args:
            subtask_id: Subtask identifier
            update_data: Subtask update data
            user_id: Authenticated user ID
            session: Database session

        Returns:
            Updated subtask details
        """
        try:
            # First, look up the subtask to get its task_id
            task_id = self._get_task_id_from_subtask(subtask_id, user_id)
            if not task_id:
                return SubtaskResponse(
                    success=False,
                    subtask=None,
                    error="Subtask not found",
                    message="Subtask not found or access denied",
                    timestamp=datetime.now(timezone.utc).isoformat(),
                )

            # DDD Compliance: No hardcoded project IDs - derive from parent task
            temp_facade = self.facade_service.get_task_facade(
                project_id=None, git_branch_id=None, user_id=user_id
            )
            parent_task = temp_facade.get_task(task_id)
            if not parent_task or not parent_task.get("task"):
                raise ValueError(f"Parent task {task_id} not found")

            parent_git_branch_id = parent_task["task"].get("git_branch_id")
            if not parent_git_branch_id:
                raise ValueError(f"Parent task {task_id} missing git_branch_id")

            # Get SUBTASK facade for update operations
            subtask_facade = self.facade_service.get_subtask_facade(
                project_id=None, git_branch_id=parent_git_branch_id, user_id=user_id
            )

            # Prepare update data with subtask_id
            update_data_with_id = {"subtask_id": subtask_id, **update_data}

            # Delegate to SUBTASK facade
            result = subtask_facade.handle_manage_subtask(
                action="update",
                task_id=task_id,
                subtask_data=update_data_with_id,
                subtask_id=subtask_id,
            )

            if not result.get("success"):
                return SubtaskResponse(
                    success=False,
                    subtask=None,
                    error="Subtask not found",
                    message="Subtask not found or access denied",
                    timestamp=datetime.now(timezone.utc).isoformat(),
                )

            logger.info(f"Updated subtask {subtask_id} for user {user_id}")

            # Convert subtask to DTO
            subtask_dict = result.get("subtask")

            class SubtaskObj:
                def __init__(self, data):
                    for key, value in data.items():
                        setattr(self, key, value)

            return SubtaskResponse(
                success=True,
                subtask=subtask_to_dto(SubtaskObj(subtask_dict)),
                message="Subtask updated successfully",
                timestamp=datetime.now(timezone.utc).isoformat(),
            )

        except Exception as e:
            logger.error(f"Error updating subtask {subtask_id} for user {user_id}: {e}")
            return SubtaskResponse(
                success=False,
                subtask=None,
                error=str(e),
                message="Failed to update subtask",
                timestamp=datetime.now(timezone.utc).isoformat(),
            )

    def delete_subtask(self, subtask_id: str, user_id: str, session) -> DeleteResponse:
        """
        Delete a subtask.

        Args:
            subtask_id: Subtask identifier
            user_id: Authenticated user ID
            session: Database session

        Returns:
            Deletion result
        """
        try:
            # First, look up the subtask to get its task_id
            task_id = self._get_task_id_from_subtask(subtask_id, user_id)
            if not task_id:
                return DeleteResponse(
                    success=False,
                    deleted=False,
                    error="Subtask not found",
                    message="Subtask not found or access denied",
                    timestamp=datetime.now(timezone.utc).isoformat(),
                )

            # DDD Compliance: No hardcoded project IDs - derive from parent task
            temp_facade = self.facade_service.get_task_facade(
                project_id=None, git_branch_id=None, user_id=user_id
            )
            parent_task = temp_facade.get_task(task_id)
            if not parent_task or not parent_task.get("task"):
                raise ValueError(f"Parent task {task_id} not found")

            parent_git_branch_id = parent_task["task"].get("git_branch_id")
            if not parent_git_branch_id:
                raise ValueError(f"Parent task {task_id} missing git_branch_id")

            # Get SUBTASK facade for delete operations
            subtask_facade = self.facade_service.get_subtask_facade(
                project_id=None, git_branch_id=parent_git_branch_id, user_id=user_id
            )

            # Delegate to SUBTASK facade
            result = subtask_facade.handle_manage_subtask(
                action="delete", task_id=task_id, subtask_id=subtask_id
            )

            if not result.get("success"):
                return DeleteResponse(
                    success=False,
                    deleted=False,
                    error="Subtask not found",
                    message="Subtask not found or access denied",
                    timestamp=datetime.now(timezone.utc).isoformat(),
                )

            logger.info(f"Deleted subtask {subtask_id} for user {user_id}")

            return DeleteResponse(
                success=True,
                deleted=True,
                id=subtask_id,
                message="Subtask deleted successfully",
                timestamp=datetime.now(timezone.utc).isoformat(),
            )

        except Exception as e:
            logger.error(f"Error deleting subtask {subtask_id} for user {user_id}: {e}")
            return DeleteResponse(
                success=False,
                deleted=False,
                error=str(e),
                message="Failed to delete subtask",
                timestamp=datetime.now(timezone.utc).isoformat(),
            )

    def complete_subtask(
        self, subtask_id: str, completion_summary: str, user_id: str, session
    ) -> SubtaskResponse:
        """
        Complete a subtask.

        Args:
            subtask_id: Subtask identifier
            completion_summary: Summary of work completed
            user_id: Authenticated user ID
            session: Database session

        Returns:
            Subtask completion result
        """
        try:
            # First, look up the subtask to get its task_id
            task_id = self._get_task_id_from_subtask(subtask_id, user_id)
            if not task_id:
                return SubtaskResponse(
                    success=False,
                    subtask=None,
                    error="Subtask not found",
                    message="Subtask not found or access denied",
                    timestamp=datetime.now(timezone.utc).isoformat(),
                )

            # DDD Compliance: No hardcoded project IDs - derive from parent task
            temp_facade = self.facade_service.get_task_facade(
                project_id=None, git_branch_id=None, user_id=user_id
            )
            parent_task = temp_facade.get_task(task_id)
            if not parent_task or not parent_task.get("task"):
                raise ValueError(f"Parent task {task_id} not found")

            parent_git_branch_id = parent_task["task"].get("git_branch_id")
            if not parent_git_branch_id:
                raise ValueError(f"Parent task {task_id} missing git_branch_id")

            # Get SUBTASK facade for complete operations
            subtask_facade = self.facade_service.get_subtask_facade(
                project_id=None, git_branch_id=parent_git_branch_id, user_id=user_id
            )

            # Prepare completion data
            completion_data = {
                "subtask_id": subtask_id,
                "completion_summary": completion_summary,
            }

            # Delegate to SUBTASK facade
            result = subtask_facade.handle_manage_subtask(
                action="complete",
                task_id=task_id,
                subtask_data=completion_data,
                subtask_id=subtask_id,
            )

            if not result.get("success"):
                return SubtaskResponse(
                    success=False,
                    subtask=None,
                    error="Subtask not found",
                    message="Subtask not found or access denied",
                    timestamp=datetime.now(timezone.utc).isoformat(),
                )

            logger.info(f"Completed subtask {subtask_id} for user {user_id}")

            # Convert subtask to DTO
            subtask_dict = result.get("subtask")

            class SubtaskObj:
                def __init__(self, data):
                    for key, value in data.items():
                        setattr(self, key, value)

            return SubtaskResponse(
                success=True,
                subtask=subtask_to_dto(SubtaskObj(subtask_dict)),
                message="Subtask completed successfully",
                timestamp=datetime.now(timezone.utc).isoformat(),
            )

        except Exception as e:
            logger.error(
                f"Error completing subtask {subtask_id} for user {user_id}: {e}"
            )
            return SubtaskResponse(
                success=False,
                subtask=None,
                error=str(e),
                message="Failed to complete subtask",
                timestamp=datetime.now(timezone.utc).isoformat(),
            )

    def list_subtasks_summary(
        self, parent_task_id: str, include_counts: bool, user_id: str, session
    ) -> SubtasksResponse:
        """
        List subtasks with summary data for performance optimization.

        Args:
            parent_task_id: Parent task identifier
            include_counts: Whether to include counts
            user_id: Authenticated user ID
            session: Database session

        Returns:
            Subtask summary list result
        """
        try:
            # DDD Compliance: No hardcoded project IDs - derive from parent task
            temp_facade = self.facade_service.get_task_facade(
                project_id=None, git_branch_id=None, user_id=user_id
            )
            parent_task = temp_facade.get_task(parent_task_id)
            if not parent_task or not parent_task.get("task"):
                raise ValueError(f"Parent task {parent_task_id} not found")

            parent_git_branch_id = parent_task["task"].get("git_branch_id")
            if not parent_git_branch_id:
                raise ValueError(f"Parent task {parent_task_id} missing git_branch_id")

            # Get SUBTASK facade for listing operations
            subtask_facade = self.facade_service.get_subtask_facade(
                project_id=None, git_branch_id=parent_git_branch_id, user_id=user_id
            )

            # Delegate to SUBTASK facade
            result = subtask_facade.handle_manage_subtask(
                action="list", task_id=parent_task_id
            )

            logger.info(
                f"Listed {len(result.get('subtasks', []))} subtask summaries for task {parent_task_id} by user {user_id}"
            )

            # Convert subtasks to summary DTOs
            subtasks_list = result.get("subtasks", [])

            # Create objects for converter
            class SubtaskObj:
                def __init__(self, data):
                    for key, value in data.items():
                        setattr(self, key, value)

            subtask_dtos = [
                subtask_summary_to_dto(SubtaskObj(st)) for st in subtasks_list
            ]

            return SubtasksResponse(
                success=True,
                subtasks=subtask_dtos,
                total=len(subtask_dtos),
                message=f"Retrieved {len(subtask_dtos)} subtask summaries",
                timestamp=datetime.now(timezone.utc).isoformat(),
            )

        except Exception as e:
            logger.error(
                f"Error listing subtask summaries for task {parent_task_id} by user {user_id}: {e}"
            )
            return SubtasksResponse(
                success=False,
                subtasks=[],
                error=str(e),
                message="Failed to list subtask summaries",
                timestamp=datetime.now(timezone.utc).isoformat(),
            )
