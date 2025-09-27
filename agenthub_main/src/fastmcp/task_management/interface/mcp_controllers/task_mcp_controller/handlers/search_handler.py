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
        """Handle next task retrieval with enhanced context inheritance from parents."""
        logger.info(f"DEBUG: SearchHandler get_next_task called with include_context={include_context}")
        try:
            # Step 1: Use list_tasks to find the next available task ID
            request = ListTasksRequest(
                git_branch_id=git_branch_id,
                status="todo",  # Only get todo tasks
                limit=1  # Just get the first one
            )
            
            result = facade.list_tasks(request)
            
            if result.get("success") and result.get("tasks") and len(result["tasks"]) > 0:
                next_task_minimal = result["tasks"][0]
                task_id = next_task_minimal["id"]
                
                logger.info(f"DEBUG: Found next task ID: {task_id}")
                
                # Step 2: Use the working CRUDHandler get_task to fetch full data with context
                from .crud_handler import CRUDHandler
                crud_handler = CRUDHandler(self._response_formatter)
                full_task_result = crud_handler.get_task(facade, task_id, include_context=include_context)
                
                logger.info(f"DEBUG: CRUDHandler get_task result - success={full_task_result.get('success')}, has_task={bool(full_task_result.get('task'))}")
                
                if full_task_result.get("success") and full_task_result.get("task"):
                    task_data = full_task_result["task"]
                    
                    # Step 3: Enhanced parent context resolution when include_context is True
                    if include_context:
                        try:
                            # Get the complete parent context hierarchy for this task
                            parent_context = self._resolve_parent_context_hierarchy(
                                task_data, git_branch_id
                            )
                            
                            if parent_context:
                                # Merge parent context with existing task context
                                if "inherited_context" not in task_data:
                                    task_data["inherited_context"] = {}
                                    
                                # Add explicit parent context section
                                task_data["parent_contexts"] = parent_context
                                task_data["parent_context_available"] = True
                                
                                logger.info(f"DEBUG: Added parent contexts to task {task_id}")
                            else:
                                task_data["parent_context_available"] = False
                                
                        except Exception as e:
                            logger.warning(f"Failed to resolve parent contexts for task {task_id}: {e}")
                            task_data["parent_context_available"] = False
                    
                    # Step 4: Format the successful get result as a "next" response
                    return {
                        "success": True,
                        "action": "next",
                        "task": task_data,  # Enhanced task data with parent contexts
                        "message": "Next task found with parent context",
                        "include_context": include_context
                    }
                else:
                    logger.error(f"Failed to get full task details for task {task_id}: {full_task_result}")
                    return self._response_formatter.create_error_response(
                        operation="next_task",
                        error=f"Failed to fetch full details for task {task_id}",
                        error_code=ErrorCodes.OPERATION_FAILED
                    )
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
    
    def _resolve_parent_context_hierarchy(self, task_data: Dict[str, Any], 
                                        git_branch_id: Optional[str]) -> Optional[Dict[str, Any]]:
        """Resolve the complete parent context hierarchy for a task."""
        try:
            # Get the facade service to access context operations
            from .....application.services.facade_service import FacadeService
            facade_service = FacadeService.get_instance()
            context_facade = facade_service.get_unified_context_facade()
            
            parent_contexts = {}
            
            # 1. Get Branch Context (immediate parent)
            if git_branch_id:
                try:
                    branch_context_result = context_facade.resolve_context(
                        level="branch", 
                        context_id=git_branch_id,
                        force_refresh=False
                    )
                    
                    if branch_context_result.get("success") and branch_context_result.get("resolved_context"):
                        parent_contexts["branch"] = branch_context_result["resolved_context"]
                        logger.info(f"DEBUG: Retrieved branch context for {git_branch_id}")
                        
                        # Extract project_id from branch context for project context lookup
                        project_id = None
                        branch_data = branch_context_result.get("resolved_context", {})
                        if isinstance(branch_data, dict):
                            project_id = branch_data.get("project_id")
                        
                        # 2. Get Project Context (grandparent)
                        if project_id:
                            try:
                                project_context_result = context_facade.resolve_context(
                                    level="project", 
                                    context_id=project_id,
                                    force_refresh=False
                                )
                                
                                if project_context_result.get("success") and project_context_result.get("resolved_context"):
                                    parent_contexts["project"] = project_context_result["resolved_context"]
                                    logger.info(f"DEBUG: Retrieved project context for {project_id}")
                                    
                                    # Extract user_id for global context lookup
                                    user_id = None
                                    project_data = project_context_result.get("resolved_context", {})
                                    if isinstance(project_data, dict):
                                        user_id = project_data.get("user_id")
                                    
                                    # 3. Get Global Context (great-grandparent)
                                    if user_id:
                                        try:
                                            global_context_result = context_facade.resolve_context(
                                                level="global", 
                                                context_id=user_id,
                                                force_refresh=False
                                            )
                                            
                                            if global_context_result.get("success") and global_context_result.get("resolved_context"):
                                                parent_contexts["global"] = global_context_result["resolved_context"]
                                                logger.info(f"DEBUG: Retrieved global context for user {user_id}")
                                        
                                        except Exception as e:
                                            logger.debug(f"Could not retrieve global context: {e}")
                                            
                            except Exception as e:
                                logger.debug(f"Could not retrieve project context: {e}")
                        
                except Exception as e:
                    logger.debug(f"Could not retrieve branch context: {e}")
            
            # Return parent contexts if any were found
            if parent_contexts:
                return {
                    "hierarchy_levels": list(parent_contexts.keys()),
                    "contexts": parent_contexts,
                    "inheritance_chain": self._build_inheritance_chain(parent_contexts)
                }
            
            return None
            
        except Exception as e:
            logger.warning(f"Failed to resolve parent context hierarchy: {e}")
            return None
    
    def _build_inheritance_chain(self, parent_contexts: Dict[str, Any]) -> Dict[str, Any]:
        """Build a flattened inheritance chain from parent contexts."""
        inheritance_chain = {}
        
        # Process in hierarchy order: global -> project -> branch
        hierarchy_order = ["global", "project", "branch"]
        
        for level in hierarchy_order:
            if level in parent_contexts:
                context_data = parent_contexts[level]
                if isinstance(context_data, dict):
                    # Flatten context data into inheritance chain
                    # Avoid overwriting with None values
                    for key, value in context_data.items():
                        if value is not None and key not in inheritance_chain:
                            inheritance_chain[key] = value
        
        return inheritance_chain
    
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