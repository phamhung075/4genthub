"""
Progress Reporting Handler

Handles progress reporting and task update operations.
"""

import logging
from typing import Dict, Any, Optional, List
from datetime import datetime, timezone
from .....application.facades.task_application_facade import TaskApplicationFacade
from .....application.factories.unified_context_facade_factory import UnifiedContextFacadeFactory
from ....application.services.facade_service import FacadeService
from ....utils.response_formatter import StandardResponseFormatter, ResponseStatus, ErrorCodes

logger = logging.getLogger(__name__)


class ProgressReportingHandler:
    """Handler for progress reporting operations."""
    
    def __init__(self, response_formatter: StandardResponseFormatter, 
                 task_facade: TaskApplicationFacade,
                 context_facade_factory: UnifiedContextFacadeFactory):
        self._response_formatter = response_formatter
        self._task_facade = task_facade
        self._context_facade_factory = context_facade_factory
        
        # Progress type definitions for validation
        self.VALID_PROGRESS_TYPES = [
            "analysis", "implementation", "testing", "debugging", "documentation",
            "review", "research", "planning", "integration", "deployment"
        ]
    
    def report_progress(self, task_id: str, progress_type: str, description: str,
                       percentage: Optional[int] = None, files_affected: Optional[List[str]] = None,
                       next_steps: Optional[List[str]] = None) -> Dict[str, Any]:
        """Report progress on a task with simple parameters."""
        
        try:
            # Validate progress type
            if progress_type not in self.VALID_PROGRESS_TYPES:
                logger.warning(f"Unknown progress type '{progress_type}', using 'update' instead")
                progress_type = "update"
            
            # Validate percentage if provided
            if percentage is not None:
                if not 0 <= percentage <= 100:
                    return self._response_formatter.create_error_response(
                        operation="report_progress",
                        error="Invalid percentage value",
                        error_code=ErrorCodes.VALIDATION_ERROR,
                        metadata={
                            "field": "percentage",
                            "expected": "Integer between 0 and 100",
                            "hint": "Provide a percentage between 0 and 100"
                        }
                    )
            
            # Build context update
            context_data = {
                "progress": {
                    "type": progress_type,
                    "description": description,
                    "timestamp": datetime.now(timezone.utc).isoformat(),
                    "percentage": percentage
                }
            }
            
            if files_affected:
                context_data["files_affected"] = files_affected
            
            if next_steps:
                context_data["next_steps"] = next_steps
            
            # Update context through facade
            context_facade = self._context_facade_factory.create()
            result = context_facade.update_context(
                level="task",
                context_id=task_id,
                data=context_data,
                propagate_changes=True
            )
            
            if result.get("success"):
                response_data = {
                    "progress_type": progress_type,
                    "percentage": percentage,
                    "next_reminder": "Progress will be tracked automatically"
                }
                
                # Add helpful hints based on progress
                if percentage and percentage >= 90:
                    response_data["hint"] = "Task is nearly complete. Consider running tests and preparing completion summary."
                elif percentage and percentage >= 50:
                    response_data["hint"] = "Good progress! Remember to document key decisions."
                
                return self._response_formatter.create_success_response(
                    operation="report_progress",
                    data=response_data,
                    message=f"Progress reported for task {task_id}",
                    metadata={"task_id": task_id}
                )
            else:
                return self._response_formatter.create_error_response(
                    operation="report_progress",
                    error=f"Failed to update progress: {result.get('error')}",
                    error_code=ErrorCodes.OPERATION_FAILED,
                    metadata={"task_id": task_id}
                )
                
        except Exception as e:
            logger.error(f"Error reporting progress for task {task_id}: {e}")
            return self._response_formatter.create_error_response(
                operation="report_progress",
                error=f"Failed to report progress: {str(e)}",
                error_code=ErrorCodes.INTERNAL_ERROR,
                metadata={"task_id": task_id}
            )
    
    def quick_task_update(self, task_id: str, status: Optional[str] = None,
                         notes: Optional[str] = None, completed_work: Optional[str] = None) -> Dict[str, Any]:
        """Quick task status and notes update."""
        
        try:
            # Build update data
            update_data = {}
            context_data = {}
            
            if status:
                update_data["status"] = status
                context_data["status_change"] = {
                    "new_status": status,
                    "timestamp": datetime.now(timezone.utc).isoformat()
                }
            
            if notes:
                context_data["quick_notes"] = {
                    "notes": notes,
                    "timestamp": datetime.now(timezone.utc).isoformat()
                }
            
            if completed_work:
                context_data["completed_work"] = {
                    "description": completed_work,
                    "timestamp": datetime.now(timezone.utc).isoformat()
                }
            
            # Update task through facade if status changed
            if status:
                task_result = self._task_facade.update_task(task_id=task_id, **update_data)
                if not task_result.get("success"):
                    return self._response_formatter.create_error_response(
                        operation="quick_task_update",
                        error=f"Failed to update task: {task_result.get('error')}",
                        error_code=ErrorCodes.OPERATION_FAILED,
                        metadata={"task_id": task_id}
                    )
            
            # Update context if we have context data
            if context_data:
                context_facade = self._context_facade_factory.create()
                context_result = context_facade.update_context(
                    level="task",
                    context_id=task_id,
                    data=context_data,
                    propagate_changes=True
                )
                
                if not context_result.get("success"):
                    logger.warning(f"Context update failed for task {task_id}: {context_result.get('error')}")
            
            return self._response_formatter.create_success_response(
                operation="quick_task_update",
                data={
                    "updated_fields": list(update_data.keys()) + list(context_data.keys()),
                    "status_updated": bool(status),
                    "context_updated": bool(context_data)
                },
                message=f"Task {task_id} updated successfully",
                metadata={"task_id": task_id}
            )
            
        except Exception as e:
            logger.error(f"Error in quick task update for {task_id}: {e}")
            return self._response_formatter.create_error_response(
                operation="quick_task_update",
                error=f"Failed to update task: {str(e)}",
                error_code=ErrorCodes.INTERNAL_ERROR,
                metadata={"task_id": task_id}
            )