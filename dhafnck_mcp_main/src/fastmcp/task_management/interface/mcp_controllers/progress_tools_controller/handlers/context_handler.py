"""
Context Handler

Handles work context updates and structured information management.
"""

import logging
from typing import Dict, Any, Optional, List
from datetime import datetime, timezone
from ....application.services.facade_service import FacadeService
from ....utils.response_formatter import StandardResponseFormatter, ResponseStatus, ErrorCodes

logger = logging.getLogger(__name__)


class ContextHandler:
    """Handler for work context management operations."""
    
    def __init__(self, response_formatter: StandardResponseFormatter,
                 context_facade_factory: UnifiedContextFacadeFactory):
        self._response_formatter = response_formatter
        self._context_facade_factory = context_facade_factory
    
    def update_work_context(self, task_id: str, files_read: Optional[List[str]] = None,
                           files_modified: Optional[List[str]] = None,
                           key_decisions: Optional[List[str]] = None,
                           discoveries: Optional[List[str]] = None,
                           test_results: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """Update work context with structured information."""
        
        try:
            # Build structured context update
            context_data = {
                "work_context": {
                    "timestamp": datetime.now(timezone.utc).isoformat()
                }
            }
            
            if files_read:
                context_data["work_context"]["files_read"] = files_read
            if files_modified:
                context_data["work_context"]["files_modified"] = files_modified
            if key_decisions:
                context_data["work_context"]["key_decisions"] = key_decisions
            if discoveries:
                context_data["work_context"]["discoveries"] = discoveries
            if test_results:
                context_data["work_context"]["test_results"] = test_results
            
            # Calculate summary statistics
            total_files = len(files_read or []) + len(files_modified or [])
            decisions_count = len(key_decisions or [])
            discoveries_count = len(discoveries or [])
            
            # Update context through facade
            context_facade = self._context_facade_factory.create()
            result = context_facade.update_context(
                level="task",
                context_id=task_id,
                data=context_data,
                propagate_changes=True
            )
            
            if result.get("success"):
                # Build response message
                updates = []
                if files_read or files_modified:
                    updates.append(f"{total_files} files")
                if key_decisions:
                    updates.append(f"{decisions_count} decisions")
                if discoveries:
                    updates.append(f"{discoveries_count} discoveries")
                if test_results:
                    updates.append("test results")
                
                message = f"Work context updated with {', '.join(updates)}"
                
                return self._response_formatter.create_success_response(
                    operation="update_work_context",
                    data={
                        "files_count": total_files,
                        "decisions_count": decisions_count,
                        "discoveries_count": discoveries_count,
                        "has_test_results": bool(test_results),
                        "context_updated": True
                    },
                    message=message,
                    metadata={
                        "task_id": task_id,
                        "hint": "Work context updated. Information will be available for future sessions."
                    }
                )
            else:
                return self._response_formatter.create_error_response(
                    operation="update_work_context",
                    error=f"Failed to update work context: {result.get('error')}",
                    error_code=ErrorCodes.OPERATION_FAILED,
                    metadata={"task_id": task_id}
                )
                
        except Exception as e:
            logger.error(f"Error updating work context for task {task_id}: {e}")
            return self._response_formatter.create_error_response(
                operation="update_work_context",
                error=f"Work context update failed: {str(e)}",
                error_code=ErrorCodes.INTERNAL_ERROR,
                metadata={"task_id": task_id}
            )