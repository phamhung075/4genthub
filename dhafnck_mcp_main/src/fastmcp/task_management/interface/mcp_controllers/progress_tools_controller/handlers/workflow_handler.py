"""
Workflow Handler

Handles workflow checkpoint and work state management operations.
"""

import logging
from typing import Dict, Any, Optional, List
from datetime import datetime, timezone
from ....application.services.facade_service import FacadeService
from ....utils.response_formatter import StandardResponseFormatter, ResponseStatus, ErrorCodes

logger = logging.getLogger(__name__)


class WorkflowHandler:
    """Handler for workflow checkpoint operations."""
    
    def __init__(self, response_formatter: StandardResponseFormatter,
                 context_facade_factory: UnifiedContextFacadeFactory):
        self._response_formatter = response_formatter
        self._context_facade_factory = context_facade_factory
    
    def checkpoint_work(self, task_id: str, current_state: str, next_steps: List[str],
                       notes: Optional[str] = None) -> Dict[str, Any]:
        """Create a checkpoint of current work state."""
        
        try:
            # Build checkpoint data
            checkpoint_data = {
                "checkpoint": {
                    "timestamp": datetime.now(timezone.utc).isoformat(),
                    "current_state": current_state,
                    "next_steps": next_steps
                }
            }
            
            if notes:
                checkpoint_data["checkpoint"]["notes"] = notes
            
            # Update context with checkpoint
            context_facade = self._context_facade_factory.create()
            result = context_facade.update_context(
                level="task",
                context_id=task_id,
                data=checkpoint_data,
                propagate_changes=True
            )
            
            if result.get("success"):
                return self._response_formatter.create_success_response(
                    operation="checkpoint_work",
                    data={
                        "checkpoint_time": checkpoint_data["checkpoint"]["timestamp"],
                        "next_steps_count": len(next_steps),
                        "has_notes": bool(notes)
                    },
                    message="Work checkpoint created",
                    metadata={
                        "task_id": task_id,
                        "hint": "Checkpoint saved. You can resume from this state later."
                    }
                )
            else:
                return self._response_formatter.create_error_response(
                    operation="checkpoint_work",
                    error=f"Failed to create checkpoint: {result.get('error')}",
                    error_code=ErrorCodes.OPERATION_FAILED,
                    metadata={"task_id": task_id}
                )
                
        except Exception as e:
            logger.error(f"Error creating checkpoint for task {task_id}: {e}")
            return self._response_formatter.create_error_response(
                operation="checkpoint_work",
                error=f"Checkpoint creation failed: {str(e)}",
                error_code=ErrorCodes.INTERNAL_ERROR,
                metadata={"task_id": task_id}
            )