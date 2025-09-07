"""
Operation Factory for Task MCP Controller

Coordinates and creates operation handlers for task management.
"""

import logging
from typing import Dict, Any, Optional

from ..handlers.crud_handler import CRUDHandler
from ..handlers.search_handler import SearchHandler
from ..handlers.workflow_handler import WorkflowHandler
from ....utils.response_formatter import StandardResponseFormatter

logger = logging.getLogger(__name__)


class OperationFactory:
    """Factory for creating and coordinating task operation handlers."""
    
    def __init__(self, response_formatter: StandardResponseFormatter,
                 context_facade_factory=None):
        self._response_formatter = response_formatter
        self._context_facade_factory = context_facade_factory
        
        # Initialize handlers
        self._crud_handler = CRUDHandler(response_formatter)
        self._search_handler = SearchHandler(response_formatter)
        self._workflow_handler = WorkflowHandler(response_formatter, context_facade_factory)
        
        logger.info("OperationFactory initialized with all handlers")
    
    def get_crud_handler(self) -> CRUDHandler:
        """Get CRUD operations handler."""
        return self._crud_handler
    
    def get_search_handler(self) -> SearchHandler:
        """Get search operations handler."""
        return self._search_handler
    
    def get_workflow_handler(self) -> WorkflowHandler:
        """Get workflow operations handler."""
        return self._workflow_handler
    
    async def handle_operation(self, operation: str, facade, **kwargs) -> Dict[str, Any]:
        """
        Route operation to appropriate handler.
        
        Args:
            operation: The operation to perform (create, update, delete, etc.)
            facade: The task application facade
            **kwargs: Operation parameters
            
        Returns:
            Operation result
        """
        try:
            # Route to appropriate handler based on operation
            if operation in ['create', 'update', 'delete', 'get', 'complete']:
                return self._handle_crud_operation(operation, facade, **kwargs)
            elif operation in ['list', 'search', 'next', 'count']:
                return await self._handle_search_operation(operation, facade, **kwargs)
            elif operation in ['enrich', 'context', 'workflow']:
                return self._handle_workflow_operation(operation, facade, **kwargs)
            elif operation in ['add_dependency', 'remove_dependency']:
                return self._handle_dependency_operation(operation, facade, **kwargs)
            else:
                logger.error(f"Unknown operation: {operation}")
                return self._response_formatter.create_error_response(
                    operation=operation,
                    error=f"Unknown operation: {operation}",
                    error_code="UNKNOWN_OPERATION"
                )
        
        except Exception as e:
            import traceback
            logger.error(f"Error handling operation {operation}: {str(e)}")
            logger.error(f"Traceback: {traceback.format_exc()}")
            return self._response_formatter.create_error_response(
                operation=operation,
                error=f"Operation failed: {str(e)}",
                error_code="OPERATION_FAILED"
            )
    
    def _handle_crud_operation(self, operation: str, facade, **kwargs) -> Dict[str, Any]:
        """Handle CRUD operations."""
        handler = self._crud_handler
        
        if operation == 'create':
            # Filter to only include parameters accepted by create_task method
            # Following DDD: only pass domain-relevant parameters for creation
            allowed_params = {
                'git_branch_id', 'title', 'description', 'status', 
                'priority', 'details', 'estimated_effort', 'assignees', 
                'labels', 'due_date', 'dependencies', 'user_id'
            }
            crud_kwargs = {k: v for k, v in kwargs.items() if k in allowed_params}
            logger.debug(f"Create operation - Original kwargs: {list(kwargs.keys())}")
            logger.debug(f"Create operation - Filtered kwargs: {list(crud_kwargs.keys())}")
            result = handler.create_task(facade, **crud_kwargs)
            
            # Auto-create context if task creation was successful
            if result.get("success") and result.get("task"):
                task_data = result["task"]
                task_id = task_data.get("id")
                git_branch_id = kwargs.get("git_branch_id")
                
                if task_id and git_branch_id:
                    context_result = self._workflow_handler.create_task_context(
                        task_id, task_data, git_branch_id
                    )
                    
                    if context_result.get("success"):
                        result["context_created"] = True
                        result["context_id"] = task_id
            
            return result
            
        elif operation == 'update':
            # Filter to only include parameters accepted by update_task method
            allowed_params = {
                'task_id', 'title', 'description', 'status', 'priority', 
                'details', 'estimated_effort', 'assignees', 'labels', 
                'due_date', 'context_id', 'completion_summary', 'testing_notes'
            }
            crud_kwargs = {k: v for k, v in kwargs.items() if k in allowed_params}
            return handler.update_task(facade, **crud_kwargs)
        elif operation == 'delete':
            # Filter to only include parameters accepted by delete_task method
            allowed_params = {'task_id'}
            crud_kwargs = {k: v for k, v in kwargs.items() if k in allowed_params}
            return handler.delete_task(facade, **crud_kwargs)
        elif operation == 'get':
            # Filter to only include parameters accepted by get_task method
            allowed_params = {'task_id', 'include_context'}
            crud_kwargs = {k: v for k, v in kwargs.items() if k in allowed_params}
            result = handler.get_task(facade, **crud_kwargs)
            
            # Enrich response with workflow information
            if result.get("success") and result.get("task"):
                result = self._workflow_handler.enrich_task_response(
                    result, operation, result["task"]
                )
            
            return result
            
        elif operation == 'complete':
            # Filter to only include parameters accepted by complete_task method
            allowed_params = {'task_id', 'completion_summary', 'testing_notes'}
            crud_kwargs = {k: v for k, v in kwargs.items() if k in allowed_params}
            return handler.complete_task(facade, **crud_kwargs)
        else:
            raise ValueError(f"Unknown CRUD operation: {operation}")
    
    async def _handle_search_operation(self, operation: str, facade, **kwargs) -> Dict[str, Any]:
        """Handle search and list operations."""
        handler = self._search_handler
        
        # Only include parameters expected by SearchHandler methods
        if operation == 'list':
            # list_tasks parameters: status, priority, assignee, tag, git_branch_id, limit, offset, sort_by, sort_order
            allowed_params = {'status', 'priority', 'assignee', 'tag', 'git_branch_id', 'limit', 'offset', 'sort_by', 'sort_order'}
            search_kwargs = {k: v for k, v in kwargs.items() if k in allowed_params}
        elif operation == 'search':
            # search_tasks parameters: query, status, priority, assignee, tag, git_branch_id, limit, offset
            allowed_params = {'query', 'status', 'priority', 'assignee', 'tag', 'git_branch_id', 'limit', 'offset'}
            search_kwargs = {k: v for k, v in kwargs.items() if k in allowed_params}
        elif operation == 'next':
            # get_next_task only expects git_branch_id and include_context
            allowed_params = {'git_branch_id', 'include_context'}
            search_kwargs = {k: v for k, v in kwargs.items() if k in allowed_params}
        else:
            # For other operations (count), filter out common problematic params
            excluded_params = {'user_id', 'task_id', 'title', 'description'}
            search_kwargs = {k: v for k, v in kwargs.items() if k not in excluded_params}
        
        if operation == 'list':
            return handler.list_tasks(facade, **search_kwargs)
        elif operation == 'search':
            return handler.search_tasks(facade, **search_kwargs)
        elif operation == 'next':
            result = await handler.get_next_task(facade, **search_kwargs)
            
            # Enrich response with workflow information
            if result.get("success") and result.get("task"):
                result = self._workflow_handler.enrich_task_response(
                    result, operation, result["task"]
                )
            
            return result
            
        elif operation == 'count':
            return handler.count_tasks(facade, **kwargs)
        else:
            raise ValueError(f"Unknown search operation: {operation}")
    
    def _handle_workflow_operation(self, operation: str, facade, **kwargs) -> Dict[str, Any]:
        """Handle workflow operations."""
        handler = self._workflow_handler
        
        if operation == 'enrich':
            response = kwargs.get('response', {})
            action = kwargs.get('action', 'unknown')
            task_data = kwargs.get('task_data')
            return handler.enrich_task_response(response, action, task_data)
        elif operation == 'context':
            task_id = kwargs.get('task_id')
            task_data = kwargs.get('task_data', {})
            git_branch_id = kwargs.get('git_branch_id')
            return handler.create_task_context(task_id, task_data, git_branch_id)
        else:
            raise ValueError(f"Unknown workflow operation: {operation}")
    
    def _handle_dependency_operation(self, operation: str, facade, **kwargs) -> Dict[str, Any]:
        """Handle dependency operations."""
        task_id = kwargs.get('task_id')
        dependency_id = kwargs.get('dependency_id')
        
        # Validate required parameters
        if not task_id:
            return self._response_formatter.create_error_response(
                operation=operation,
                error="task_id is required for dependency operations",
                error_code="VALIDATION_ERROR"
            )
        
        if not dependency_id:
            return self._response_formatter.create_error_response(
                operation=operation,
                error="dependency_id is required for dependency operations",
                error_code="VALIDATION_ERROR"
            )
        
        try:
            if operation == 'add_dependency':
                return facade.add_dependency(task_id, dependency_id)
            elif operation == 'remove_dependency':
                return facade.remove_dependency(task_id, dependency_id)
            else:
                raise ValueError(f"Unknown dependency operation: {operation}")
        
        except Exception as e:
            logger.error(f"Error in dependency operation {operation}: {str(e)}")
            return self._response_formatter.create_error_response(
                operation=operation,
                error=f"Dependency operation failed: {str(e)}",
                error_code="OPERATION_FAILED"
            )