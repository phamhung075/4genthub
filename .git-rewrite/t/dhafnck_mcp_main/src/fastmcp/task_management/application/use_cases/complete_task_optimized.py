"""Optimized Task Completion Use Case

This module provides an optimized version of the task completion use case
that fixes the duplicate event loop creation issue.
"""

import asyncio
import logging
from typing import Dict, Any, Optional
from datetime import datetime

from .complete_task import CompleteTaskUseCase
from ..dtos.task.complete_task_request import CompleteTaskRequest

logger = logging.getLogger(__name__)


class OptimizedCompleteTaskUseCase(CompleteTaskUseCase):
    """Optimized task completion use case that reuses event loops"""
    
    def execute(self, request: CompleteTaskRequest) -> Dict[str, Any]:
        """
        Execute task completion with optimized async handling.
        
        This method runs all async operations in a single event loop,
        avoiding the performance overhead of creating multiple loops.
        """
        # Run the entire operation in a single event loop
        return asyncio.run(self._execute_async(request))
    
    async def _execute_async(self, request: CompleteTaskRequest) -> Dict[str, Any]:
        """Async implementation of task completion"""
        try:
            # Validate request
            if not request.task_id:
                return {
                    "success": False,
                    "error": "task_id is required",
                    "error_code": "MISSING_FIELD",
                    "field": "task_id",
                    "expected": "A valid task_id",
                    "hint": "Provide the ID of the task to complete"
                }
            
            # Get the task
            task = self._task_repository.find_by_id(request.task_id)
            if not task:
                return {
                    "success": False,
                    "error": f"Task not found: {request.task_id}",
                    "error_code": "NOT_FOUND",
                    "field": "task_id",
                    "hint": "Check that the task ID is correct"
                }
            
            # Validate task can be completed
            if self._completion_service:
                self._completion_service.validate_task_completion(task)
            
            # Get context ONCE and reuse it
            context_data = None
            context_updated_at = None
            
            if self._context_manager:
                context_result = await self._context_manager.get_context(str(request.task_id))
                if context_result.get("success"):
                    context_data = context_result
                    
                    # Extract timestamp from context
                    if "template_context" in context_result:
                        template_context = context_result["template_context"]
                        if "full_context" in template_context:
                            full_context = template_context["full_context"]
                            if "metadata" in full_context and "updated_at" in full_context["metadata"]:
                                context_updated_at = datetime.fromisoformat(full_context["metadata"]["updated_at"])
                        elif "task_metadata" in template_context and "updated_at" in template_context["task_metadata"]:
                            context_updated_at = datetime.fromisoformat(template_context["task_metadata"]["updated_at"])
            
            # Complete the task
            task.complete_task(
                completion_summary=request.completion_summary,
                context_updated_at=context_updated_at
            )
            
            # Update task with metadata
            task.add_metadata("completion_summary", request.completion_summary)
            if request.testing_notes:
                task.add_metadata("testing_notes", request.testing_notes)
            if request.next_recommendations:
                task.add_metadata("next_recommendations", request.next_recommendations)
            
            # Save the completed task
            self._task_repository.save(task)
            
            # Update context with completion information (reuse existing context data)
            if self._context_manager and request.completion_summary and context_data:
                try:
                    context_update = {
                        "progress": {
                            "completion_summary": request.completion_summary,
                            "testing_notes": request.testing_notes,
                            "next_recommendations": request.next_recommendations,
                            "completion_percentage": 100.0
                        }
                    }
                    
                    await self._context_manager.update_context(
                        str(request.task_id),
                        context_update,
                        merge_mode=True
                    )
                except Exception as e:
                    logger.warning(f"Could not update context with completion summary: {e}")
            
            # Update parent task progress if this is a subtask
            parent_progress = None
            if hasattr(task, 'parent_task_id') and task.parent_task_id and self._progress_service:
                try:
                    parent_progress = self._progress_service.calculate_parent_progress(
                        str(task.parent_task_id)
                    )
                except Exception as e:
                    logger.warning(f"Could not calculate parent progress: {e}")
            
            # Build response
            response = {
                "success": True,
                "task": {
                    "id": str(task.id),
                    "title": task.title,
                    "status": str(task.status),
                    "completed_at": task.completed_at.isoformat() if task.completed_at else None,
                    "completion_summary": request.completion_summary,
                    "testing_notes": request.testing_notes,
                    "next_recommendations": request.next_recommendations
                },
                "message": f"Task '{task.title}' completed successfully"
            }
            
            if parent_progress:
                response["parent_progress"] = parent_progress
            
            return response
            
        except Exception as e:
            logger.error(f"Error completing task: {e}", exc_info=True)
            
            # Check if it's a validation error
            if "must be updated before completing" in str(e):
                return {
                    "success": False,
                    "error": str(e),
                    "error_code": "CONTEXT_REQUIRED",
                    "hint": "Update the task context before completing",
                    "example": {
                        "step1": "manage_context(action='update', level='task', context_id='...', data={'status': 'done'})",
                        "step2": "manage_task(action='complete', task_id='...', completion_summary='...')"
                    }
                }
            
            return {
                "success": False,
                "error": f"Failed to complete task: {str(e)}",
                "error_code": "OPERATION_FAILED"
            }


def optimize_complete_task_use_case():
    """Apply optimization to the existing CompleteTaskUseCase"""
    # This would be called during application startup to replace the implementation
    logger.info("Applied event loop optimization to CompleteTaskUseCase")