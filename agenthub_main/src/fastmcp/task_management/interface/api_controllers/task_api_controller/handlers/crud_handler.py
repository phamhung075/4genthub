"""Task CRUD Operations Handler"""

import logging
from typing import Dict, Any
from datetime import datetime, timezone

from .....application.dtos.task.create_task_request import CreateTaskRequest
from .....application.dtos.task.update_task_request import UpdateTaskRequest
from .....application.dtos.task.list_tasks_request import ListTasksRequest
# No direct factory imports - handlers receive facades from controller

logger = logging.getLogger(__name__)


class TaskCrudHandler:
    """Handler for task CRUD operations"""
    
    def __init__(self, facade_service):
        """
        Initialize handler with facade service.
        
        Args:
            facade_service: Service for obtaining application facades
        """
        self.facade_service = facade_service
    
    def create_task(self, request: CreateTaskRequest, user_id: str, session) -> Dict[str, Any]:
        """
        Create a new task.
        
        Args:
            request: Task creation request data
            user_id: Authenticated user ID
            session: Database session
            
        Returns:
            Task creation result
        """
        try:
            # Get task facade with proper user context through service
            # Project ID should come from git_branch_id context or be None
            task_facade = self.facade_service.get_task_facade(
                project_id=None,  # Derived from git_branch_id context
                git_branch_id=request.git_branch_id,
                user_id=user_id
            )
            
            # Delegate to facade
            result = task_facade.create_task(request)

            # Check if the creation was successful
            if result.get("success"):
                logger.info(f"Task created successfully for user {user_id}: {result.get('task', {}).get('id')}")
                return {
                    "success": True,
                    "task": result.get("task"),
                    "message": "Task created successfully"
                }
            else:
                # Handle validation or other errors from facade
                error_msg = result.get("error", "Failed to create task")
                logger.warning(f"Task creation failed for user {user_id}: {error_msg}")
                return {
                    "success": False,
                    "error": error_msg,
                    "message": error_msg
                }
            
        except Exception as e:
            logger.error(f"Error creating task for user {user_id}: {e}")
            return {
                "success": False,
                "error": str(e),
                "message": "Failed to create task"
            }
    
    def get_task(self, task_id: str, user_id: str, session) -> Dict[str, Any]:
        """
        Get a specific task.
        
        Args:
            task_id: Task identifier
            user_id: Authenticated user ID
            session: Database session
            
        Returns:
            Task details
        """
        try:
            # Get task facade with proper user context through service
            # Project ID derived from task context, not hardcoded
            task_facade = self.facade_service.get_task_facade(
                project_id=None,  # Derived from task context
                git_branch_id=None,  # Will be determined by task
                user_id=user_id
            )
            
            # Delegate to facade
            task = task_facade.get_task(task_id)
            
            if not task:
                return {
                    "success": False,
                    "error": "Task not found",
                    "message": "Task not found or access denied"
                }
            
            logger.info(f"Retrieved task {task_id} for user {user_id}")
            
            return {
                "success": True,
                "task": task
            }
            
        except Exception as e:
            logger.error(f"Error getting task {task_id} for user {user_id}: {e}")
            return {
                "success": False,
                "error": str(e),
                "message": "Failed to get task"
            }
    
    def update_task(self, task_id: str, request: UpdateTaskRequest, user_id: str, session) -> Dict[str, Any]:
        """
        Update a task.
        
        Args:
            task_id: Task identifier
            request: Task update request
            user_id: Authenticated user ID
            session: Database session
            
        Returns:
            Updated task details
        """
        try:
            # Get task facade with proper user context through service
            # Project ID derived from task context, not hardcoded
            task_facade = self.facade_service.get_task_facade(
                project_id=None,  # Derived from task context
                git_branch_id=None,
                user_id=user_id
            )
            
            # Set task_id in request
            request.task_id = task_id

            # Delegate to facade - pass both task_id and request
            result = task_facade.update_task(task_id, request)

            # Check if the update was successful
            if result.get("success"):
                logger.info(f"Task {task_id} updated successfully for user {user_id}")
                return {
                    "success": True,
                    "task": result.get("task"),
                    "message": "Task updated successfully"
                }
            else:
                # Handle validation or other errors from facade
                error_msg = result.get("error", "Failed to update task")
                logger.warning(f"Task {task_id} update failed for user {user_id}: {error_msg}")
                return {
                    "success": False,
                    "error": error_msg,
                    "message": error_msg
                }
            
        except Exception as e:
            logger.error(f"Error updating task {task_id} for user {user_id}: {e}")
            return {
                "success": False,
                "error": str(e),
                "message": "Failed to update task"
            }
    
    def delete_task(self, task_id: str, user_id: str, session) -> Dict[str, Any]:
        """
        Delete a task.
        
        Args:
            task_id: Task identifier
            user_id: Authenticated user ID
            session: Database session
            
        Returns:
            Deletion result
        """
        try:
            # Get task facade with proper user context through service
            # Project ID derived from task context, not hardcoded
            task_facade = self.facade_service.get_task_facade(
                project_id=None,  # Derived from task context
                git_branch_id=None,
                user_id=user_id
            )
            
            # Delegate to facade with user_id for proper WebSocket notification
            result = task_facade.delete_task(task_id, user_id)

            # Check if the deletion was successful
            if result.get("success"):
                logger.info(f"Task {task_id} deleted successfully for user {user_id}")
                return {
                    "success": True,
                    "message": "Task deleted successfully"
                }
            else:
                # Handle validation or other errors from facade
                error_msg = result.get("error", "Failed to delete task")
                logger.warning(f"Task {task_id} deletion failed for user {user_id}: {error_msg}")
                return {
                    "success": False,
                    "error": error_msg,
                    "message": error_msg
                }
            
        except Exception as e:
            logger.error(f"Error deleting task {task_id} for user {user_id}: {e}")
            return {
                "success": False,
                "error": str(e),
                "message": "Failed to delete task"
            }
    
    def list_tasks(self, request: ListTasksRequest, user_id: str, session) -> Dict[str, Any]:
        """
        List tasks for a user.
        
        Args:
            request: Task listing request
            user_id: Authenticated user ID
            session: Database session
            
        Returns:
            List of tasks
        """
        try:
            # Get task facade with proper user context through service
            task_facade = self.facade_service.get_task_facade(
                project_id="default_project",
                git_branch_id=request.git_branch_id,
                user_id=user_id
            )
            
            # Delegate to facade - include dependencies for proper display
            result = task_facade.list_tasks(request, include_dependencies=True, minimal=False)

            # Check if the listing was successful
            if result.get("success"):
                logger.info(f"Listed {len(result.get('tasks', []))} tasks for user {user_id}")
                return {
                    "success": True,
                    "tasks": result.get("tasks", []),
                    "count": len(result.get("tasks", [])),
                    "user_id": user_id
                }
            else:
                # Handle validation or other errors from facade
                error_msg = result.get("error", "Failed to list tasks")
                logger.warning(f"Task listing failed for user {user_id}: {error_msg}")
                return {
                    "success": False,
                    "error": error_msg,
                    "message": error_msg
                }
            
        except Exception as e:
            logger.error(f"Error listing tasks for user {user_id}: {e}")
            return {
                "success": False,
                "error": str(e),
                "message": "Failed to list tasks"
            }