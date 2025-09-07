"""Task Search and Statistics Handler"""

import logging
from typing import Dict, Any, Optional
from datetime import datetime, timezone

logger = logging.getLogger(__name__)


class TaskSearchHandler:
    """Handler for task search and statistics operations"""
    
    def __init__(self, facade_service):
        """
        Initialize handler with facade service.
        
        Args:
            facade_service: Service for obtaining application facades
        """
        self.facade_service = facade_service
    
    def get_task_statistics(self, user_id: str, session) -> Dict[str, Any]:
        """
        Get task statistics for a user.
        
        Args:
            user_id: Authenticated user ID
            session: Database session
            
        Returns:
            Task statistics
        """
        try:
            # Get task facade with proper user context through service
            task_facade = self.facade_service.get_task_facade(
                project_id="default_project",
                git_branch_id=None,
                user_id=user_id
            )
            
            # Get statistics through facade
            stats = task_facade.get_task_statistics(user_id)
            
            logger.info(f"Retrieved task statistics for user {user_id}")
            
            return {
                "success": True,
                "statistics": stats
            }
            
        except Exception as e:
            logger.error(f"Error getting task statistics for user {user_id}: {e}")
            return {
                "success": False,
                "error": str(e),
                "message": "Failed to get task statistics"
            }
    
    def count_tasks(self, filters: Dict[str, Any], user_id: str, session) -> Dict[str, Any]:
        """
        Count tasks matching filters.
        
        Args:
            filters: Task filters
            user_id: Authenticated user ID
            session: Database session
            
        Returns:
            Task count
        """
        try:
            # Get task facade through service
            task_facade = self.facade_service.get_task_facade(
                project_id="default_project",
                git_branch_id=None,
                user_id=user_id
            )
            
            # Add user_id to filters for security
            filters["user_id"] = user_id
            
            # Get count through facade
            count = task_facade.count_tasks(filters)
            
            logger.info(f"Counted {count} tasks for user {user_id} with filters {filters}")
            
            return {
                "success": True,
                "count": count,
                "filters": filters
            }
            
        except Exception as e:
            logger.error(f"Error counting tasks for user {user_id}: {e}")
            return {
                "success": False,
                "error": str(e),
                "message": "Failed to count tasks"
            }
    
    def list_tasks_summary(self, filters: Dict[str, Any], offset: int, limit: int, 
                          user_id: str, session) -> Dict[str, Any]:
        """
        List task summaries with pagination.
        
        Args:
            filters: Task filters
            offset: Pagination offset
            limit: Pagination limit
            user_id: Authenticated user ID
            session: Database session
            
        Returns:
            Task summaries
        """
        try:
            # Get task facade through service
            task_facade = self.facade_service.get_task_facade(
                project_id="default_project",
                git_branch_id=None,
                user_id=user_id
            )
            
            # Add user_id to filters for security
            filters["user_id"] = user_id
            
            # Get tasks through facade
            result = task_facade.list_tasks_with_pagination(filters, offset, limit)
            
            logger.info(f"Listed {len(result['tasks'])} task summaries for user {user_id}")
            
            return {
                "success": True,
                "tasks": result['tasks'],
                "offset": offset,
                "limit": limit,
                "total": result['total']
            }
            
        except Exception as e:
            logger.error(f"Error listing task summaries for user {user_id}: {e}")
            return {
                "success": False,
                "error": str(e),
                "message": "Failed to list task summaries"
            }
    
    def get_full_task(self, task_id: str, user_id: str, session) -> Dict[str, Any]:
        """
        Get full task details including subtasks and dependencies.
        
        Args:
            task_id: Task identifier
            user_id: Authenticated user ID
            session: Database session
            
        Returns:
            Full task details
        """
        try:
            # Get task facade with proper user context through service
            task_facade = self.facade_service.get_task_facade(
                project_id="default_project",
                git_branch_id=None,
                user_id=user_id
            )
            
            # Get task with all relations through facade
            task = task_facade.get_task_with_relations(task_id)
            
            if not task:
                return {
                    "success": False,
                    "error": "Task not found",
                    "message": "Task not found or access denied"
                }
            
            logger.info(f"Retrieved full task details for task {task_id}")
            
            return {
                "success": True,
                "task": task
            }
            
        except Exception as e:
            logger.error(f"Error getting full task {task_id} for user {user_id}: {e}")
            return {
                "success": False,
                "error": str(e),
                "message": "Failed to get task details"
            }