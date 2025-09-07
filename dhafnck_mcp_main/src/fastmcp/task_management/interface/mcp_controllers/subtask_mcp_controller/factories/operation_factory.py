"""
Operation Factory for Subtask MCP Controller

Coordinates and creates operation handlers for subtask management.
"""

import logging
from typing import Dict, Any, Optional

from ..handlers.crud_handler import SubtaskCRUDHandler
from ..handlers.progress_handler import ProgressHandler
from ....utils.response_formatter import StandardResponseFormatter

logger = logging.getLogger(__name__)


class SubtaskOperationFactory:
    """Factory for creating and coordinating subtask operation handlers."""
    
    def __init__(self, response_formatter: StandardResponseFormatter,
                 context_facade=None, task_facade=None):
        self._response_formatter = response_formatter
        self._context_facade = context_facade
        self._task_facade = task_facade
        
        # Initialize handlers
        self._crud_handler = SubtaskCRUDHandler(
            response_formatter=response_formatter,
            context_facade=context_facade,
            task_facade=task_facade
        )
        
        self._progress_handler = ProgressHandler(
            context_facade=context_facade,
            task_facade=task_facade
        )
        
        logger.info("SubtaskOperationFactory initialized with all handlers")
    
    def get_crud_handler(self) -> SubtaskCRUDHandler:
        """Get CRUD operations handler."""
        return self._crud_handler
    
    def get_progress_handler(self) -> ProgressHandler:
        """Get progress tracking handler."""
        return self._progress_handler
    
    def handle_operation(self, operation: str, facade, **kwargs) -> Dict[str, Any]:
        """
        Route operation to appropriate handler.
        
        Args:
            operation: The operation to perform (create, update, delete, etc.)
            facade: The subtask application facade
            **kwargs: Operation parameters
            
        Returns:
            Operation result
        """
        try:
            # Route to appropriate handler based on operation
            if operation in ['create', 'update', 'delete', 'get', 'list', 'complete']:
                return self._handle_crud_operation(operation, facade, **kwargs)
            elif operation in ['progress', 'summary']:
                return self._handle_progress_operation(operation, facade, **kwargs)
            else:
                logger.error(f"Unknown operation: {operation}")
                return self._response_formatter.create_error_response(
                    operation=operation,
                    error=f"Unknown operation: {operation}",
                    error_code="UNKNOWN_OPERATION"
                )
        
        except Exception as e:
            logger.error(f"Error handling operation {operation}: {str(e)}")
            return self._response_formatter.create_error_response(
                operation=operation,
                error=f"Operation failed: {str(e)}",
                error_code="OPERATION_FAILED"
            )
    
    def _handle_crud_operation(self, operation: str, facade, **kwargs) -> Dict[str, Any]:
        """Handle CRUD operations with automatic progress tracking."""
        handler = self._crud_handler
        
        # Filter out authentication parameters that shouldn't be passed to CRUD handlers
        # Following DDD: authentication is handled at interface layer, not passed to domain
        # For each operation, only pass the parameters that the specific method accepts
        if operation == 'create':
            # create_subtask only accepts: task_id, title, description, priority, assignees, progress_notes, user_id
            allowed_params = {'task_id', 'title', 'description', 'priority', 'assignees', 'progress_notes', 'user_id'}
            filtered_kwargs = {k: v for k, v in kwargs.items() if k in allowed_params}
        elif operation == 'list':
            # list_subtasks only accepts: task_id, status, priority, limit, offset
            # Note: subtask_id is NOT needed for listing all subtasks
            allowed_params = {'task_id', 'status', 'priority', 'limit', 'offset'}
            filtered_kwargs = {k: v for k, v in kwargs.items() if k in allowed_params}
            # Debug logging to understand the issue
            if 'subtask_id' in kwargs:
                logger.debug(f"Warning: subtask_id found in kwargs for list operation and will be filtered out: {kwargs.get('subtask_id')}")
            logger.debug(f"List operation - Original kwargs: {list(kwargs.keys())}, Filtered kwargs: {list(filtered_kwargs.keys())}")
        elif operation == 'get':
            # get_subtask only accepts: task_id, subtask_id
            allowed_params = {'task_id', 'subtask_id'}
            filtered_kwargs = {k: v for k, v in kwargs.items() if k in allowed_params}
        elif operation == 'update':
            # update_subtask only accepts specific parameters
            allowed_params = {'task_id', 'subtask_id', 'title', 'description', 'status', 
                            'priority', 'assignees', 'progress_percentage', 'progress_notes'}
            filtered_kwargs = {k: v for k, v in kwargs.items() if k in allowed_params}
        elif operation in ['delete', 'complete']:
            # These operations require subtask_id, exclude only user_id
            excluded_params = {'user_id'}
            filtered_kwargs = {k: v for k, v in kwargs.items() if k not in excluded_params}
        else:
            # For other operations, just exclude user_id
            excluded_params = {'user_id'}
            filtered_kwargs = {k: v for k, v in kwargs.items() if k not in excluded_params}
        
        if operation == 'create':
            result = handler.create_subtask(facade, **filtered_kwargs)
        elif operation == 'update':
            result = handler.update_subtask(facade, **filtered_kwargs)
        elif operation == 'delete':
            result = handler.delete_subtask(facade, **filtered_kwargs)
        elif operation == 'get':
            result = handler.get_subtask(facade, **filtered_kwargs)
        elif operation == 'list':
            # Extra safety check to ensure subtask_id is not passed
            if 'subtask_id' in filtered_kwargs:
                logger.error(f"CRITICAL: subtask_id still in filtered_kwargs for list operation: {filtered_kwargs}")
                filtered_kwargs.pop('subtask_id', None)
            result = handler.list_subtasks(facade, **filtered_kwargs)
        elif operation == 'complete':
            result = handler.complete_subtask(facade, **filtered_kwargs)
        else:
            raise ValueError(f"Unknown CRUD operation: {operation}")
        
        # Enhance result with progress information if successful
        if result.get("success") and operation in ['create', 'update', 'delete', 'complete']:
            task_id = kwargs.get('task_id')
            if task_id and result.get('subtasks'):
                # Add progress summary to the result
                progress_summary = self._progress_handler.get_progress_summary(
                    task_id=task_id,
                    subtasks=result.get('subtasks', [])
                )
                result['progress_summary'] = progress_summary
        
        return result
    
    def _handle_progress_operation(self, operation: str, facade, **kwargs) -> Dict[str, Any]:
        """Handle progress tracking operations."""
        handler = self._progress_handler
        task_id = kwargs.get('task_id')
        
        if not task_id:
            return self._response_formatter.create_error_response(
                operation=operation,
                error="task_id is required for progress operations",
                error_code="VALIDATION_ERROR"
            )
        
        try:
            if operation == 'progress':
                # Get current subtasks and calculate progress
                subtasks_result = facade.handle_manage_subtask(
                    action="list",
                    task_id=task_id
                )
                
                if not subtasks_result.get("success"):
                    return subtasks_result
                
                subtasks = subtasks_result.get("subtasks", [])
                progress = handler.calculate_task_progress(task_id, subtasks)
                
                return self._response_formatter.create_success_response(
                    operation="get_progress",
                    data={"progress": progress}
                )
            
            elif operation == 'summary':
                # Get comprehensive progress summary
                subtasks_result = facade.handle_manage_subtask(
                    action="list",
                    task_id=task_id
                )
                
                if not subtasks_result.get("success"):
                    return subtasks_result
                
                subtasks = subtasks_result.get("subtasks", [])
                summary = handler.get_progress_summary(task_id, subtasks)
                
                return self._response_formatter.create_success_response(
                    operation="get_progress_summary",
                    data={"summary": summary}
                )
            
            else:
                raise ValueError(f"Unknown progress operation: {operation}")
            
        except Exception as e:
            logger.error(f"Error in progress operation {operation}: {str(e)}")
            return self._response_formatter.create_error_response(
                operation=operation,
                error=f"Progress operation failed: {str(e)}",
                error_code="OPERATION_FAILED"
            )