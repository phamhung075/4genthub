"""Progress Tools Controller - Phase 2 Implementation

Simple tools for AI to report progress without understanding context structure.
Part of the Vision System Phase 2: Progress Reporting Tools.
"""

import logging
from typing import Dict, Any, Optional, List
from datetime import datetime, timezone

from ...application.facades.task_application_facade import TaskApplicationFacade
from ...application.factories.unified_context_facade_factory import UnifiedContextFacadeFactory
from ..utils.response_formatter import StandardResponseFormatter

logger = logging.getLogger(__name__)


class ProgressToolsController:
    """
    Controller providing simple progress reporting tools for AI agents.
    
    These tools allow AI to report progress without needing to understand
    the full context structure or hierarchy.
    """
    
    def __init__(self, 
                 task_facade: TaskApplicationFacade,
                 context_facade_factory: Optional[UnifiedContextFacadeFactory] = None):
        """
        Initialize progress tools controller.
        
        Args:
            task_facade: Task application facade for task operations
            context_facade_factory: Factory for creating context facades
        """
        self._task_facade = task_facade
        self._context_facade_factory = context_facade_factory or UnifiedContextFacadeFactory()
        
        # Progress type definitions for validation
        self.VALID_PROGRESS_TYPES = [
            "analysis",
            "implementation", 
            "testing",
            "debugging",
            "documentation",
            "review",
            "research",
            "planning",
            "integration",
            "deployment"
        ]
        
        logger.info("ProgressToolsController initialized for Vision System Phase 2")
    
    def report_progress(self,
                       task_id: str,
                       progress_type: str,
                       description: str,
                       percentage: Optional[int] = None,
                       files_affected: Optional[List[str]] = None,
                       next_steps: Optional[List[str]] = None) -> Dict[str, Any]:
        """
        Report progress on a task with simple parameters.
        
        Args:
            task_id: Task identifier
            progress_type: Type of progress (analysis, implementation, etc.)
            description: What was done
            percentage: Optional completion percentage (0-100)
            files_affected: Optional list of files modified
            next_steps: Optional list of next planned actions
            
        Returns:
            Response dictionary with success status
        """
        try:
            # Validate progress type
            if progress_type not in self.VALID_PROGRESS_TYPES:
                logger.warning(f"Unknown progress type '{progress_type}', using 'update' instead")
                progress_type = "update"
            
            # Validate percentage if provided
            if percentage is not None:
                if not 0 <= percentage <= 100:
                    return StandardResponseFormatter.create_validation_error_response(
                        operation="report_progress",
                        field="percentage",
                        expected="Integer between 0 and 100",
                        hint="Provide a percentage between 0 and 100"
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
                response = {
                    "success": True,
                    "message": f"Progress reported for task {task_id}",
                    "progress_type": progress_type,
                    "percentage": percentage,
                    "next_reminder": "Progress will be tracked automatically"
                }
                
                # Add helpful hints based on progress
                if percentage and percentage >= 90:
                    response["hint"] = "Task is nearly complete. Consider running tests and preparing completion summary."
                elif percentage and percentage >= 50:
                    response["hint"] = "Good progress! Remember to document key decisions."
                
                return response
            else:
                return {
                    "success": False,
                    "error": f"Failed to update progress: {result.get('error')}",
                    "task_id": task_id
                }
                
        except Exception as e:
            logger.error(f"Error reporting progress for task {task_id}: {e}")
            return {
                "success": False,
                "error": f"Failed to report progress: {str(e)}",
                "task_id": task_id
            }
    
    def quick_task_update(self,
                         task_id: str,
                         what_i_did: str,
                         progress_percentage: Optional[int] = None,
                         blockers: Optional[str] = None) -> Dict[str, Any]:
        """
        Quick and simple task update for AI agents.
        
        Args:
            task_id: Task identifier
            what_i_did: Simple description of work done
            progress_percentage: Optional completion percentage
            blockers: Optional description of blockers
            
        Returns:
            Response dictionary with success status
        """
        try:
            # Build simple context update
            context_data = {
                "quick_update": {
                    "what_i_did": what_i_did,
                    "timestamp": datetime.now(timezone.utc).isoformat()
                }
            }
            
            if progress_percentage is not None:
                context_data["quick_update"]["progress"] = progress_percentage
                
                # Update task status based on progress
                if progress_percentage == 0:
                    status = "todo"
                elif progress_percentage < 100:
                    status = "in_progress"
                else:
                    status = "done"
                
                # Update task status through facade
                self._task_facade.update_task({
                    "task_id": task_id,
                    "status": status
                })
            
            if blockers:
                context_data["quick_update"]["blockers"] = blockers
                # Also update task to blocked status if blockers exist
                self._task_facade.update_task({
                    "task_id": task_id,
                    "status": "blocked",
                    "details": f"Blocker: {blockers}"
                })
            
            # Update context
            context_facade = self._context_facade_factory.create()
            result = context_facade.update_context(
                level="task",
                context_id=task_id,
                data=context_data,
                propagate_changes=True
            )
            
            if result.get("success"):
                return {
                    "success": True,
                    "message": "Quick update recorded",
                    "task_id": task_id,
                    "progress": progress_percentage,
                    "hint": "Continue working or use 'complete' action when done"
                }
            else:
                return {
                    "success": False,
                    "error": f"Failed to record update: {result.get('error')}",
                    "task_id": task_id
                }
                
        except Exception as e:
            logger.error(f"Error in quick update for task {task_id}: {e}")
            return {
                "success": False,
                "error": f"Quick update failed: {str(e)}",
                "task_id": task_id
            }
    
    def checkpoint_work(self,
                       task_id: str,
                       current_state: str,
                       next_steps: List[str],
                       notes: Optional[str] = None) -> Dict[str, Any]:
        """
        Create a checkpoint of current work state.
        
        Args:
            task_id: Task identifier
            current_state: Description of current state
            next_steps: List of next planned actions
            notes: Optional additional notes
            
        Returns:
            Response dictionary with success status
        """
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
                return {
                    "success": True,
                    "message": "Work checkpoint created",
                    "task_id": task_id,
                    "checkpoint_time": checkpoint_data["checkpoint"]["timestamp"],
                    "next_steps_count": len(next_steps),
                    "hint": "Checkpoint saved. You can resume from this state later."
                }
            else:
                return {
                    "success": False,
                    "error": f"Failed to create checkpoint: {result.get('error')}",
                    "task_id": task_id
                }
                
        except Exception as e:
            logger.error(f"Error creating checkpoint for task {task_id}: {e}")
            return {
                "success": False,
                "error": f"Checkpoint creation failed: {str(e)}",
                "task_id": task_id
            }
    
    def update_work_context(self,
                           task_id: str,
                           files_read: Optional[List[str]] = None,
                           files_modified: Optional[List[str]] = None,
                           key_decisions: Optional[List[str]] = None,
                           discoveries: Optional[List[str]] = None,
                           test_results: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """
        Update work context with structured information.
        
        Args:
            task_id: Task identifier
            files_read: List of files read during work
            files_modified: List of files modified
            key_decisions: List of important decisions made
            discoveries: List of discoveries or insights
            test_results: Test execution results
            
        Returns:
            Response dictionary with success status
        """
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
            
            # Update context
            context_facade = self._context_facade_factory.create()
            result = context_facade.update_context(
                level="task",
                context_id=task_id,
                data=context_data,
                propagate_changes=True
            )
            
            if result.get("success"):
                response = {
                    "success": True,
                    "message": "Work context updated",
                    "task_id": task_id,
                    "items_tracked": {
                        "files_read": len(files_read) if files_read else 0,
                        "files_modified": len(files_modified) if files_modified else 0,
                        "decisions": len(key_decisions) if key_decisions else 0,
                        "discoveries": len(discoveries) if discoveries else 0
                    }
                }
                
                # Add contextual hints
                if files_modified and len(files_modified) > 5:
                    response["hint"] = "Many files modified. Consider creating tests for changes."
                elif discoveries and len(discoveries) > 0:
                    response["hint"] = "Great discoveries! Consider documenting these insights."
                
                return response
            else:
                return {
                    "success": False,
                    "error": f"Failed to update context: {result.get('error')}",
                    "task_id": task_id
                }
                
        except Exception as e:
            logger.error(f"Error updating work context for task {task_id}: {e}")
            return {
                "success": False,
                "error": f"Context update failed: {str(e)}",
                "task_id": task_id
            }