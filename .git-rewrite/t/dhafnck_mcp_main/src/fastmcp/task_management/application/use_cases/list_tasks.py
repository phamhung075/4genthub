"""List Tasks Use Case"""

import logging
from typing import List

from ...application.dtos.task import (
    ListTasksRequest,
    TaskListResponse
)

from ...domain import TaskRepository, TaskStatus, Priority

logger = logging.getLogger(__name__)


class ListTasksUseCase:
    """Use case for listing tasks with optional filtering"""
    
    def __init__(self, task_repository: TaskRepository):
        self._task_repository = task_repository
    
    def execute(self, request: ListTasksRequest) -> TaskListResponse:
        """Execute the list tasks use case"""
        logger.debug(f"[USE_CASE] ListTasksUseCase.execute called")
        logger.debug(f"[USE_CASE] Request git_branch_id: {request.git_branch_id}")
        logger.debug(f"[USE_CASE] Request status: {request.status}")
        logger.debug(f"[USE_CASE] Request priority: {request.priority}")
        logger.debug(f"[USE_CASE] Request limit: {request.limit}")
        
        # Build filter criteria
        filters = {}
        
        if request.status:
            filters['status'] = TaskStatus(request.status)
        
        if request.priority:
            filters['priority'] = Priority(request.priority)
        
        # Handle both new assignees field and legacy assignee field
        if hasattr(request, 'assignees') and request.assignees:
            filters['assignees'] = request.assignees
        elif hasattr(request, 'assignee') and request.assignee:
            filters['assignee'] = request.assignee
        
        if request.labels:
            filters['labels'] = request.labels
        
        # CRITICAL FIX: Include git_branch_id in filters so repository can filter by branch
        if request.git_branch_id:
            filters['git_branch_id'] = request.git_branch_id
            logger.debug(f"[USE_CASE] Added git_branch_id to filters: {request.git_branch_id}")
        else:
            logger.debug(f"[USE_CASE] No git_branch_id in request, not filtering by branch")
        
        logger.debug(f"[USE_CASE] Final filters being passed to repository: {filters}")
        
        # Get tasks from repository
        tasks = self._task_repository.find_by_criteria(filters, limit=request.limit)
        logger.debug(f"[USE_CASE] Repository returned {len(tasks) if tasks else 0} tasks")
        
        # Prepare filters_applied for response
        filters_applied = {}
        if request.status:
            filters_applied['status'] = request.status
        if request.priority:
            filters_applied['priority'] = request.priority
        if hasattr(request, 'assignees') and request.assignees:
            filters_applied['assignees'] = request.assignees
        elif hasattr(request, 'assignee') and request.assignee:
            filters_applied['assignee'] = request.assignee
        if request.labels:
            filters_applied['labels'] = request.labels
        if request.git_branch_id:
            filters_applied['git_branch_id'] = request.git_branch_id
        if request.limit:
            filters_applied['limit'] = request.limit
        
        # Convert to response DTO
        return TaskListResponse.from_domain_list(tasks, filters_applied=filters_applied) 