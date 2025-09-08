"""
Search Handler for Task MCP Controller

Handles search, list, and next task operations.
"""

import logging
from typing import Dict, Any, Optional, List

from .....application.dtos.task.list_tasks_request import ListTasksRequest
from .....application.dtos.task.search_tasks_request import SearchTasksRequest
from .....application.facades.task_application_facade import TaskApplicationFacade
from ....utils.response_formatter import StandardResponseFormatter, ErrorCodes

logger = logging.getLogger(__name__)


class SearchHandler:
    """Handles search and list operations for tasks."""
    
    def __init__(self, response_formatter: StandardResponseFormatter):
        self._response_formatter = response_formatter
    
    def list_tasks(self, facade: TaskApplicationFacade, status: Optional[str], 
                  priority: Optional[str], assignee: Optional[str], 
                  tag: Optional[str], git_branch_id: Optional[str], 
                  limit: Optional[int], offset: Optional[int], 
                  sort_by: Optional[str] = None, 
                  sort_order: Optional[str] = None) -> Dict[str, Any]:
        """Handle task listing with filtering and pagination."""
        try:
            # Create list request with individual parameters
            request = ListTasksRequest(
                git_branch_id=git_branch_id,
                status=status,
                priority=priority,
                assignees=[assignee] if assignee else None,
                labels=[tag] if tag else None,
                limit=limit or 50  # Default limit
            )
            
            result = facade.list_tasks(request)
            
            # Add pagination metadata if successful
            if result.get("success") and "tasks" in result:
                tasks = result["tasks"]
                result["pagination"] = {
                    "total": len(tasks),
                    "limit": request.limit,
                    "offset": offset or 0,
                    "has_more": len(tasks) == request.limit
                }
            
            return result
            
        except Exception as e:
            logger.error(f"Error in list_tasks: {str(e)}")
            return self._response_formatter.create_error_response(
                operation="list_tasks",
                error=f"Failed to list tasks: {str(e)}",
                error_code=ErrorCodes.OPERATION_FAILED
            )
    
    def search_tasks(self, facade: TaskApplicationFacade, query: Optional[str], 
                    status: Optional[str], priority: Optional[str], 
                    assignee: Optional[str], tag: Optional[str], 
                    git_branch_id: Optional[str], limit: Optional[int], 
                    offset: Optional[int]) -> Dict[str, Any]:
        """Handle task search operations."""
        if not query:
            return self._response_formatter.create_error_response(
                operation="search_tasks",
                error="Missing required field: query. Expected: A search query string",
                error_code=ErrorCodes.VALIDATION_ERROR,
                metadata={"field": "query", "hint": "Include 'query' in your request"}
            )
        
        try:
            # Create search request (SearchTasksRequest only supports query, git_branch_id, and limit)
            request = SearchTasksRequest(
                query=query,
                git_branch_id=git_branch_id,
                limit=limit or 10  # Default limit for search
            )
            
            result = facade.search_tasks(request)
            
            # Add search metadata
            if result.get("success"):
                result["search_metadata"] = {
                    "query": query,
                    "git_branch_id": git_branch_id,
                    "total_results": len(result.get("tasks", []))
                }
            
            return result
            
        except Exception as e:
            logger.error(f"Error in search_tasks: {str(e)}")
            return self._response_formatter.create_error_response(
                operation="search_tasks",
                error=f"Search failed: {str(e)}",
                error_code=ErrorCodes.OPERATION_FAILED
            )
    
    async def get_next_task(self, facade: TaskApplicationFacade, git_branch_id: Optional[str], 
                     include_context: bool = True) -> Dict[str, Any]:
        """Handle next task retrieval with context (defaults to True)."""
        try:
            # WORKAROUND: Use list_tasks to get the next available task
            # The facade's get_next_task has async/string conversion issues
            request = ListTasksRequest(
                git_branch_id=git_branch_id,
                status="todo",  # Only get todo tasks
                limit=1  # Just get the first one
            )
            
            result = facade.list_tasks(request)
            
            if result.get("success") and result.get("tasks") and len(result["tasks"]) > 0:
                next_task = result["tasks"][0]
                
                # Format as "next" response
                return {
                    "success": True,
                    "action": "next",
                    "task": next_task,
                    "message": "Next task found",
                    "include_context": include_context
                }
            else:
                return {
                    "success": False,
                    "action": "next", 
                    "message": "No tasks found. Create a task to get started!",
                    "error": "No actionable tasks found."
                }
            
        except Exception as e:
            logger.error(f"Error in get_next_task: {str(e)}")
            return self._response_formatter.create_error_response(
                operation="next_task",
                error=f"Failed to get next task: {str(e)}",
                error_code=ErrorCodes.OPERATION_FAILED
            )
    
    def count_tasks(self, facade: TaskApplicationFacade, status: Optional[str], 
                   priority: Optional[str], git_branch_id: Optional[str]) -> Dict[str, Any]:
        """Handle task counting with filters."""
        try:
            # Create filters for counting
            filters = {}
            if status:
                filters['status'] = status
            if priority:
                filters['priority'] = priority
            if git_branch_id:
                filters['git_branch_id'] = git_branch_id
            
            # Use list_tasks with limit 0 to get count
            request = ListTasksRequest(
                filters=filters,
                limit=0,  # Just get count
                offset=0
            )
            
            result = facade.count_tasks(filters)
            
            # Format count response
            if result.get("success"):
                count = result.get("count", 0)
                return self._response_formatter.create_success_response(
                    operation="count_tasks",
                    data={
                        "count": count,
                        "filters": filters,
                        "timestamp": result.get("timestamp")
                    }
                )
            
            return result
            
        except Exception as e:
            logger.error(f"Error in count_tasks: {str(e)}")
            return self._response_formatter.create_error_response(
                operation="count_tasks",
                error=f"Failed to count tasks: {str(e)}",
                error_code=ErrorCodes.OPERATION_FAILED
            )