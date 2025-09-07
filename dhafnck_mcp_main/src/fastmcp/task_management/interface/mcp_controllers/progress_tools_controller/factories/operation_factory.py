"""
Progress Operation Factory

Factory class that coordinates progress operations by routing them to appropriate handlers.
"""

import logging
from typing import Dict, Any, Optional, List
from .....application.facades.task_application_facade import TaskApplicationFacade
from ....application.services.facade_service import FacadeService
from ....utils.response_formatter import StandardResponseFormatter, ErrorCodes
from ..handlers.progress_reporting_handler import ProgressReportingHandler
from ..handlers.workflow_handler import WorkflowHandler
from ..handlers.context_handler import ContextHandler

logger = logging.getLogger(__name__)


class ProgressOperationFactory:
    """Factory for coordinating progress operations."""
    
    def __init__(self, response_formatter: StandardResponseFormatter, 
                 task_facade: TaskApplicationFacade,
                 context_facade_factory: UnifiedContextFacadeFactory):
        self._response_formatter = response_formatter
        self._task_facade = task_facade
        self._context_facade_factory = context_facade_factory
        
        # Initialize handlers
        self._progress_handler = ProgressReportingHandler(
            response_formatter, task_facade, context_facade_factory)
        self._workflow_handler = WorkflowHandler(
            response_formatter, context_facade_factory)
        self._context_handler = ContextHandler(
            response_formatter, context_facade_factory)
        
        logger.info("ProgressOperationFactory initialized with modular handlers")
    
    def handle_operation(self, operation: str, **kwargs) -> Dict[str, Any]:
        """Route operation to appropriate handler."""
        
        try:
            # Progress Reporting Operations
            if operation == "report_progress":
                return self._handle_progress_reporting(operation, **kwargs)
            
            # Quick Task Update Operations
            elif operation == "quick_task_update":
                return self._handle_quick_update(operation, **kwargs)
            
            # Workflow Operations
            elif operation == "checkpoint_work":
                return self._handle_workflow_operation(operation, **kwargs)
            
            # Context Operations
            elif operation == "update_work_context":
                return self._handle_context_operation(operation, **kwargs)
            
            else:
                return self._response_formatter.create_error_response(
                    operation=operation,
                    error=f"Unknown operation: {operation}",
                    error_code=ErrorCodes.INVALID_OPERATION,
                    metadata={"valid_operations": [
                        "report_progress", "quick_task_update", 
                        "checkpoint_work", "update_work_context"
                    ]}
                )
                
        except Exception as e:
            logger.error(f"Error in ProgressOperationFactory.handle_operation: {str(e)}")
            return self._response_formatter.create_error_response(
                operation=operation,
                error=f"Operation failed: {str(e)}",
                error_code=ErrorCodes.OPERATION_FAILED,
                metadata={"operation": operation}
            )
    
    def _handle_progress_reporting(self, operation: str, **kwargs) -> Dict[str, Any]:
        """Handle progress reporting operations."""
        
        task_id = kwargs.get('task_id')
        progress_type = kwargs.get('progress_type')
        description = kwargs.get('description')
        percentage = kwargs.get('percentage')
        files_affected = kwargs.get('files_affected')
        next_steps = kwargs.get('next_steps')
        
        return self._progress_handler.report_progress(
            task_id=task_id,
            progress_type=progress_type,
            description=description,
            percentage=percentage,
            files_affected=files_affected,
            next_steps=next_steps
        )
    
    def _handle_quick_update(self, operation: str, **kwargs) -> Dict[str, Any]:
        """Handle quick task update operations."""
        
        task_id = kwargs.get('task_id')
        status = kwargs.get('status')
        notes = kwargs.get('notes')
        completed_work = kwargs.get('completed_work')
        
        return self._progress_handler.quick_task_update(
            task_id=task_id,
            status=status,
            notes=notes,
            completed_work=completed_work
        )
    
    def _handle_workflow_operation(self, operation: str, **kwargs) -> Dict[str, Any]:
        """Handle workflow operations."""
        
        task_id = kwargs.get('task_id')
        current_state = kwargs.get('current_state')
        next_steps = kwargs.get('next_steps')
        notes = kwargs.get('notes')
        
        if operation == "checkpoint_work":
            return self._workflow_handler.checkpoint_work(
                task_id=task_id,
                current_state=current_state,
                next_steps=next_steps,
                notes=notes
            )
        
        else:
            return self._response_formatter.create_error_response(
                operation=operation,
                error=f"Unsupported workflow operation: {operation}",
                error_code=ErrorCodes.INVALID_OPERATION
            )
    
    def _handle_context_operation(self, operation: str, **kwargs) -> Dict[str, Any]:
        """Handle context operations."""
        
        task_id = kwargs.get('task_id')
        files_read = kwargs.get('files_read')
        files_modified = kwargs.get('files_modified')
        key_decisions = kwargs.get('key_decisions')
        discoveries = kwargs.get('discoveries')
        test_results = kwargs.get('test_results')
        
        if operation == "update_work_context":
            return self._context_handler.update_work_context(
                task_id=task_id,
                files_read=files_read,
                files_modified=files_modified,
                key_decisions=key_decisions,
                discoveries=discoveries,
                test_results=test_results
            )
        
        else:
            return self._response_formatter.create_error_response(
                operation=operation,
                error=f"Unsupported context operation: {operation}",
                error_code=ErrorCodes.INVALID_OPERATION
            )