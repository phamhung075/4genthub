"""
Subtask API Controller

This controller handles frontend subtask management operations following proper DDD architecture.
It serves as the interface layer, delegating business logic to application facades.
"""

import logging
from typing import Dict, Any, Optional

from ...application.facades.subtask_application_facade import SubtaskApplicationFacade
from ...application.services.facade_service import FacadeService
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
    
    def create_subtask(self, task_id: str, title: str, description: Optional[str], user_id: str, session) -> Dict[str, Any]:
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
                user_id=user_id
            )
            parent_task = temp_facade.get_task(task_id)
            if not parent_task or not parent_task.get('task'):
                raise ValueError(f"Parent task {task_id} not found")

            # Extract project context from parent task
            parent_git_branch_id = parent_task['task'].get('git_branch_id')
            if not parent_git_branch_id:
                raise ValueError(f"Parent task {task_id} missing git_branch_id required for context derivation")

            # Now get the proper SUBTASK facade with derived context
            subtask_facade = self.facade_service.get_subtask_facade(
                project_id=None,  # Will be derived from git_branch_id
                git_branch_id=parent_git_branch_id,
                user_id=user_id
            )

            # Create subtask request data
            subtask_data = {
                "task_id": task_id,
                "title": title,
                "description": description or "",
                "status": "todo",
                "priority": "medium"
            }

            # Delegate to SUBTASK facade using handle_manage_subtask
            result = subtask_facade.handle_manage_subtask(
                action="create",
                task_id=task_id,
                subtask_data=subtask_data
            )

            logger.info(f"Subtask created successfully for user {user_id}: {result.get('subtask', {}).get('id')}")

            return {
                "success": True,
                "subtask": result.get("subtask"),
                "message": "Subtask created successfully"
            }

        except Exception as e:
            logger.error(f"Error creating subtask for user {user_id}: {e}")
            return {
                "success": False,
                "error": str(e),
                "message": "Failed to create subtask"
            }
    
    def list_subtasks(self, task_id: str, user_id: str, session) -> Dict[str, Any]:
        """
        List subtasks for a parent task.

        Args:
            task_id: Parent task identifier
            user_id: Authenticated user ID
            session: Database session

        Returns:
            List of subtasks
        """
        try:
            # DDD Compliance: No hardcoded project IDs - derive from parent task
            temp_facade = self.facade_service.get_task_facade(
                project_id=None,
                git_branch_id=None,
                user_id=user_id
            )
            parent_task = temp_facade.get_task(task_id)
            if not parent_task or not parent_task.get('task'):
                raise ValueError(f"Parent task {task_id} not found")

            parent_git_branch_id = parent_task['task'].get('git_branch_id')
            if not parent_git_branch_id:
                raise ValueError(f"Parent task {task_id} missing git_branch_id")

            # Get SUBTASK facade for listing operations
            subtask_facade = self.facade_service.get_subtask_facade(
                project_id=None,
                git_branch_id=parent_git_branch_id,
                user_id=user_id
            )

            # Delegate to SUBTASK facade
            result = subtask_facade.handle_manage_subtask(
                action="list",
                task_id=task_id
            )

            logger.info(f"Listed {len(result.get('subtasks', []))} subtasks for task {task_id} by user {user_id}")

            return {
                "success": True,
                "subtasks": result.get("subtasks", []),
                "count": len(result.get("subtasks", [])),
                "parent_task_id": task_id,
                "user_id": user_id
            }

        except Exception as e:
            logger.error(f"Error listing subtasks for task {task_id} by user {user_id}: {e}")
            return {
                "success": False,
                "error": str(e),
                "message": "Failed to list subtasks"
            }
    
    def get_subtask(self, task_id: str, subtask_id: str, user_id: str, session) -> Dict[str, Any]:
        """
        Get a specific subtask.

        Args:
            task_id: Parent task identifier
            subtask_id: Subtask identifier
            user_id: Authenticated user ID
            session: Database session

        Returns:
            Subtask details
        """
        try:
            # DDD Compliance: No hardcoded project IDs - derive from parent task
            temp_facade = self.facade_service.get_task_facade(
                project_id=None,
                git_branch_id=None,
                user_id=user_id
            )
            parent_task = temp_facade.get_task(task_id)
            if not parent_task or not parent_task.get('task'):
                raise ValueError(f"Parent task {task_id} not found")

            parent_git_branch_id = parent_task['task'].get('git_branch_id')
            if not parent_git_branch_id:
                raise ValueError(f"Parent task {task_id} missing git_branch_id")

            # Get SUBTASK facade for get operations
            subtask_facade = self.facade_service.get_subtask_facade(
                project_id=None,
                git_branch_id=parent_git_branch_id,
                user_id=user_id
            )

            # Delegate to SUBTASK facade
            result = subtask_facade.handle_manage_subtask(
                action="get",
                task_id=task_id,
                subtask_id=subtask_id
            )

            if not result.get("success"):
                return {
                    "success": False,
                    "error": "Subtask not found",
                    "message": "Subtask not found or access denied"
                }

            logger.info(f"Retrieved subtask {subtask_id} for user {user_id}")

            return {
                "success": True,
                "subtask": result.get("subtask")
            }

        except Exception as e:
            logger.error(f"Error getting subtask {subtask_id} for user {user_id}: {e}")
            return {
                "success": False,
                "error": str(e),
                "message": "Failed to get subtask"
            }
    
    def update_subtask(self, task_id: str, subtask_id: str, update_data: Dict[str, Any], user_id: str, session) -> Dict[str, Any]:
        """
        Update a subtask.

        Args:
            task_id: Parent task identifier
            subtask_id: Subtask identifier
            update_data: Subtask update data
            user_id: Authenticated user ID
            session: Database session

        Returns:
            Updated subtask details
        """
        try:
            # DDD Compliance: No hardcoded project IDs - derive from parent task
            temp_facade = self.facade_service.get_task_facade(
                project_id=None,
                git_branch_id=None,
                user_id=user_id
            )
            parent_task = temp_facade.get_task(task_id)
            if not parent_task or not parent_task.get('task'):
                raise ValueError(f"Parent task {task_id} not found")

            parent_git_branch_id = parent_task['task'].get('git_branch_id')
            if not parent_git_branch_id:
                raise ValueError(f"Parent task {task_id} missing git_branch_id")

            # Get SUBTASK facade for update operations
            subtask_facade = self.facade_service.get_subtask_facade(
                project_id=None,
                git_branch_id=parent_git_branch_id,
                user_id=user_id
            )

            # Prepare update data with subtask_id
            update_data_with_id = {
                "subtask_id": subtask_id,
                **update_data
            }

            # Delegate to SUBTASK facade
            result = subtask_facade.handle_manage_subtask(
                action="update",
                task_id=task_id,
                subtask_data=update_data_with_id,
                subtask_id=subtask_id
            )

            if not result.get("success"):
                return {
                    "success": False,
                    "error": "Subtask not found",
                    "message": "Subtask not found or access denied"
                }

            logger.info(f"Updated subtask {subtask_id} for user {user_id}")

            return {
                "success": True,
                "subtask": result.get("subtask"),
                "message": "Subtask updated successfully"
            }

        except Exception as e:
            logger.error(f"Error updating subtask {subtask_id} for user {user_id}: {e}")
            return {
                "success": False,
                "error": str(e),
                "message": "Failed to update subtask"
            }
    
    def delete_subtask(self, task_id: str, subtask_id: str, user_id: str, session) -> Dict[str, Any]:
        """
        Delete a subtask.

        Args:
            task_id: Parent task identifier
            subtask_id: Subtask identifier
            user_id: Authenticated user ID
            session: Database session

        Returns:
            Deletion result
        """
        try:
            # DDD Compliance: No hardcoded project IDs - derive from parent task
            temp_facade = self.facade_service.get_task_facade(
                project_id=None,
                git_branch_id=None,
                user_id=user_id
            )
            parent_task = temp_facade.get_task(task_id)
            if not parent_task or not parent_task.get('task'):
                raise ValueError(f"Parent task {task_id} not found")

            parent_git_branch_id = parent_task['task'].get('git_branch_id')
            if not parent_git_branch_id:
                raise ValueError(f"Parent task {task_id} missing git_branch_id")

            # Get SUBTASK facade for delete operations
            subtask_facade = self.facade_service.get_subtask_facade(
                project_id=None,
                git_branch_id=parent_git_branch_id,
                user_id=user_id
            )

            # Delegate to SUBTASK facade
            result = subtask_facade.handle_manage_subtask(
                action="delete",
                task_id=task_id,
                subtask_id=subtask_id
            )

            if not result.get("success"):
                return {
                    "success": False,
                    "error": "Subtask not found",
                    "message": "Subtask not found or access denied"
                }

            logger.info(f"Deleted subtask {subtask_id} for user {user_id}")

            return {
                "success": True,
                "message": "Subtask deleted successfully"
            }

        except Exception as e:
            logger.error(f"Error deleting subtask {subtask_id} for user {user_id}: {e}")
            return {
                "success": False,
                "error": str(e),
                "message": "Failed to delete subtask"
            }
    
    def complete_subtask(self, task_id: str, subtask_id: str, completion_summary: str, user_id: str, session) -> Dict[str, Any]:
        """
        Complete a subtask.

        Args:
            task_id: Parent task identifier
            subtask_id: Subtask identifier
            completion_summary: Summary of work completed
            user_id: Authenticated user ID
            session: Database session

        Returns:
            Subtask completion result
        """
        try:
            # DDD Compliance: No hardcoded project IDs - derive from parent task
            temp_facade = self.facade_service.get_task_facade(
                project_id=None,
                git_branch_id=None,
                user_id=user_id
            )
            parent_task = temp_facade.get_task(task_id)
            if not parent_task or not parent_task.get('task'):
                raise ValueError(f"Parent task {task_id} not found")

            parent_git_branch_id = parent_task['task'].get('git_branch_id')
            if not parent_git_branch_id:
                raise ValueError(f"Parent task {task_id} missing git_branch_id")

            # Get SUBTASK facade for complete operations
            subtask_facade = self.facade_service.get_subtask_facade(
                project_id=None,
                git_branch_id=parent_git_branch_id,
                user_id=user_id
            )

            # Prepare completion data
            completion_data = {
                "subtask_id": subtask_id,
                "completion_summary": completion_summary
            }

            # Delegate to SUBTASK facade
            result = subtask_facade.handle_manage_subtask(
                action="complete",
                task_id=task_id,
                subtask_data=completion_data,
                subtask_id=subtask_id
            )

            if not result.get("success"):
                return {
                    "success": False,
                    "error": "Subtask not found",
                    "message": "Subtask not found or access denied"
                }

            logger.info(f"Completed subtask {subtask_id} for user {user_id}")

            return {
                "success": True,
                "subtask": result.get("subtask"),
                "message": "Subtask completed successfully"
            }

        except Exception as e:
            logger.error(f"Error completing subtask {subtask_id} for user {user_id}: {e}")
            return {
                "success": False,
                "error": str(e),
                "message": "Failed to complete subtask"
            }
    
    def list_subtasks_summary(self, parent_task_id: str, include_counts: bool, user_id: str, session) -> Dict[str, Any]:
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
            # Get parent task to extract project context
            task_repository = self.task_repository_factory.create(user_id, session)
            parent_task = task_repository.find_by_id(parent_task_id)
            
            if not parent_task:
                raise ValueError(f"Parent task {parent_task_id} not found")
            
            # Create task facade with proper user context from parent task
            task_facade_factory = TaskFacadeFactory(
                self.task_repository_factory,
                self.subtask_repository_factory
            )
            
            task_facade = task_facade_factory.create_task_facade(
                project_id=parent_task.project_id if parent_task.project_id else parent_task.git_branch_id,
                git_branch_id=parent_task.git_branch_id,
                user_id=user_id
            )
            
            # Get subtask summaries
            result = task_facade.list_subtasks_summary(
                parent_task_id=parent_task_id,
                include_counts=include_counts
            )
            
            return result
            
        except Exception as e:
            logger.error(f"Error listing subtask summaries for task {parent_task_id} by user {user_id}: {e}")
            return {
                "success": False,
                "error": str(e),
                "subtasks": []
            }