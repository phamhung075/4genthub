"""
Task API Controller

This controller handles frontend task management operations following proper DDD architecture.
It serves as the interface layer, delegating business logic to application facades.
"""

import logging
from typing import Dict, Any, Optional, List
from datetime import datetime, timezone

from ....application.dtos.task.create_task_request import CreateTaskRequest
from ....application.dtos.task.update_task_request import UpdateTaskRequest
from ....application.dtos.task.list_tasks_request import ListTasksRequest
from ....application.services.facade_service import FacadeService
# Using FacadeService from application layer - proper DDD boundaries maintained

from .handlers import (
    TaskCrudHandler,
    TaskSearchHandler,
    TaskDependencyHandler,
    TaskWorkflowHandler
)

logger = logging.getLogger(__name__)


class TaskAPIController:
    """
    API Controller for task management operations.
    
    This controller provides a clean interface between frontend routes and
    application services, ensuring proper separation of concerns.
    
    Following DDD patterns:
    - Controllers delegate to application facades
    - No direct repository or service access
    - Proper layer separation maintained
    """
    
    def __init__(self):
        """Initialize the controller with facade service"""
        # Use FacadeService for DDD compliance - application layer service
        self.facade_service = FacadeService.get_instance()
        
        # Don't create default facade at initialization - will be created on demand with user context
        self.default_facade = None
        
        # Initialize handlers with facade service (not factory)
        self.crud_handler = TaskCrudHandler(
            self.facade_service
        )
        self.search_handler = TaskSearchHandler(
            self.facade_service
        )
        self.workflow_handler = TaskWorkflowHandler(
            self.facade_service
        )
        self.dependency_handler = TaskDependencyHandler(
            self.facade_service
        )
    
    # CRUD Operations
    def create_task(self, request: CreateTaskRequest, user_id: str, session) -> Dict[str, Any]:
        """Create a new task"""
        return self.crud_handler.create_task(request, user_id, session)
    
    def get_task(self, task_id: str, user_id: str, session) -> Dict[str, Any]:
        """Get a specific task"""
        return self.crud_handler.get_task(task_id, user_id, session)
    
    def update_task(self, task_id: str, request: UpdateTaskRequest, user_id: str, session) -> Dict[str, Any]:
        """Update a task"""
        return self.crud_handler.update_task(task_id, request, user_id, session)
    
    def delete_task(self, task_id: str, user_id: str, session) -> Dict[str, Any]:
        """Delete a task"""
        return self.crud_handler.delete_task(task_id, user_id, session)
    
    def list_tasks(self, request: ListTasksRequest, user_id: str, session) -> Dict[str, Any]:
        """List tasks for a user"""
        return self.crud_handler.list_tasks(request, user_id, session)
    
    # Workflow Operations
    def complete_task(self, task_id: str, completion_summary: str, 
                     testing_notes: Optional[str], user_id: str, session) -> Dict[str, Any]:
        """Complete a task"""
        return self.workflow_handler.complete_task(
            task_id, completion_summary, testing_notes, user_id, session
        )
    
    # Search and Statistics Operations
    def get_task_statistics(self, user_id: str, session) -> Dict[str, Any]:
        """Get task statistics for a user"""
        return self.search_handler.get_task_statistics(user_id, session)
    
    def count_tasks(self, filters: Dict[str, Any], user_id: str, session) -> Dict[str, Any]:
        """Count tasks matching filters"""
        return self.search_handler.count_tasks(filters, user_id, session)
    
    def list_tasks_summary(self, filters: Dict[str, Any], offset: int, limit: int, 
                          user_id: str, session) -> Dict[str, Any]:
        """List task summaries with pagination"""
        return self.search_handler.list_tasks_summary(filters, offset, limit, user_id, session)
    
    def get_full_task(self, task_id: str, user_id: str, session) -> Dict[str, Any]:
        """Get full task details including subtasks and dependencies"""
        return self.search_handler.get_full_task(task_id, user_id, session)