"""Task Workflow Operations Handler"""

import logging
from typing import Dict, Any, Optional
from datetime import datetime, timezone

logger = logging.getLogger(__name__)


class TaskWorkflowHandler:
    """Handler for task workflow operations"""
    
    def __init__(self, facade_service):
        """
        Initialize handler with facade service.
        
        Args:
            facade_service: Service for obtaining application facades
        """
        self.facade_service = facade_service
    
    def complete_task(self, task_id: str, completion_summary: str, 
                     testing_notes: Optional[str], user_id: str, session) -> Dict[str, Any]:
        """
        Complete a task.
        
        Args:
            task_id: Task identifier
            completion_summary: Summary of completion
            testing_notes: Optional testing notes
            user_id: Authenticated user ID
            session: Database session
            
        Returns:
            Completion result
        """
        try:
            # Get task facade with proper user context through service
            task_facade = self.facade_service.get_task_facade(
                project_id="default_project",
                git_branch_id=None,
                user_id=user_id
            )
            
            # Delegate to facade
            result = task_facade.complete_task(
                task_id=task_id,
                completion_summary=completion_summary,
                testing_notes=testing_notes,
                user_id=user_id
            )
            
            logger.info(f"Task {task_id} completed successfully by user {user_id}")
            
            return result
            
        except Exception as e:
            logger.error(f"Error completing task {task_id} for user {user_id}: {e}")
            return {
                "success": False,
                "error": str(e),
                "message": "Failed to complete task"
            }