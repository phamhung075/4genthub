"""
CRUD Handler for Subtask MCP Controller

Handles Create, Read, Update, Delete operations for subtasks with automatic progress tracking.
"""

import logging
from typing import Dict, Any, Optional, List
from datetime import datetime, timezone

from fastmcp.task_management.application.facades.subtask_application_facade import SubtaskApplicationFacade
from fastmcp.task_management.interface.utils.response_formatter import StandardResponseFormatter, ErrorCodes

logger = logging.getLogger(__name__)


class SubtaskCRUDHandler:
    """Handles CRUD operations for subtasks with integrated progress tracking."""
    
    def __init__(self, response_formatter: StandardResponseFormatter, 
                 context_facade=None, task_facade=None):
        self._response_formatter = response_formatter
        self._context_facade = context_facade
        self._task_facade = task_facade
    
    def create_subtask(self, facade: SubtaskApplicationFacade, task_id: str, 
                      title: str, description: Optional[str] = None, 
                      priority: Optional[str] = None, assignees: Optional[List[str]] = None,
                      progress_notes: Optional[str] = None, user_id: Optional[str] = None) -> Dict[str, Any]:
        """Handle subtask creation with automatic parent context update and agent inheritance.
        
        Enhanced to support agent inheritance from parent tasks when no assignees are provided.
        Validates all assignees using AgentRole enum before subtask creation.
        """
        
        if not task_id:
            return self._create_validation_error(
                "task_id", "A valid task_id string", 
                "Include 'task_id' in your request"
            )
        
        if not title:
            return self._create_validation_error(
                "title", "A non-empty title string",
                "Include 'title' in your request"
            )
        
        # Validate assignees if provided
        if assignees:
            try:
                # Validate assignees using AgentRole enum
                from ......domain.entities.task import Task
                dummy_task = Task(title="dummy", description="dummy")
                validated_assignees = dummy_task.validate_assignee_list(assignees)
                assignees = validated_assignees
                logger.info(f"Validated {len(assignees)} assignees for subtask creation: {assignees}")
            except ValueError as e:
                return self._response_formatter.create_error_response(
                    operation="create_subtask",
                    error=f"Invalid assignees: {str(e)}. Use valid agent roles like '@@coding_agent', '@test-orchestrator-agent'",
                    error_code=ErrorCodes.VALIDATION_ERROR,
                    metadata={"field": "assignees", "hint": "Provide valid agent roles from AgentRole enum"}
                )
        
        try:
            # Create the subtask
            subtask_data = {
                "title": title,
                "description": description,
                "priority": priority,
                "assignees": assignees
            }
            
            result = facade.handle_manage_subtask(
                action="create",
                task_id=task_id,
                subtask_data=subtask_data
            )
            
            # Add information about agent inheritance if it was applied
            if result.get("success") and result.get("agent_inheritance_applied"):
                logger.info(f"Agent inheritance applied for subtask creation: {result.get('inherited_assignees', [])}")
                result["inheritance_info"] = {
                    "applied": True,
                    "inherited_from": "parent_task",
                    "inherited_assignees": result.get("inherited_assignees", []),
                    "assignee_count": len(result.get("inherited_assignees", []))
                }
            
            # Update parent context if available
            if result.get("success") and self._context_facade:
                try:
                    subtask = result.get("subtask", {})
                    if isinstance(subtask, dict):
                        subtask_id = subtask.get("id") or subtask.get("subtask", {}).get("id")
                    else:
                        subtask_id = getattr(subtask, 'id', None)
                    
                    # Update parent context with inheritance information
                    progress_content = f"Created subtask: {title}"
                    if result.get("agent_inheritance_applied"):
                        inherited_count = len(result.get("inherited_assignees", []))
                        progress_content += f" (inherited {inherited_count} assignees from parent)"
                    if progress_notes:
                        progress_content += f" - {progress_notes}"
                    
                    progress_result = self._context_facade.add_progress(
                        task_id=task_id,
                        content=progress_content,
                        agent="subtask_controller"
                    )
                    
                    result["context_updated"] = True
                    result["parent_progress"] = self._get_parent_progress(facade, task_id)
                    
                except Exception as e:
                    logger.error(f"Failed to update parent context: {e}")
                    result["context_updated"] = False
                    result["context_update_error"] = str(e)
                    result["warning"] = "Subtask created successfully but parent context update failed"
            
            return result
            
        except Exception as e:
            logger.error(f"Error creating subtask: {str(e)}")
            return self._response_formatter.create_error_response(
                operation="create_subtask",
                error=f"Failed to create subtask: {str(e)}",
                error_code=ErrorCodes.OPERATION_FAILED,
                metadata={"task_id": task_id, "title": title}
            )
    
    def update_subtask(self, facade: SubtaskApplicationFacade, task_id: str, 
                      subtask_id: str, title: Optional[str] = None,
                      description: Optional[str] = None, status: Optional[str] = None,
                      priority: Optional[str] = None, assignees: Optional[List[str]] = None,
                      progress_percentage: Optional[int] = None,
                      progress_notes: Optional[str] = None) -> Dict[str, Any]:
        """Handle subtask update with automatic parent progress tracking."""
        
        if not task_id:
            return self._create_validation_error(
                "task_id", "A valid task_id string",
                "Include 'task_id' in your request"
            )
        
        if not subtask_id:
            return self._create_validation_error(
                "subtask_id", "A valid subtask_id string",
                "Include 'subtask_id' in your request"
            )
        
        try:
            # Prepare update data
            update_data = {}
            if title is not None:
                update_data['title'] = title
            if description is not None:
                update_data['description'] = description
            if status is not None:
                update_data['status'] = status
            if priority is not None:
                update_data['priority'] = priority
            if assignees is not None:
                update_data['assignees'] = assignees
            if progress_percentage is not None:
                update_data['progress_percentage'] = progress_percentage
            
            result = facade.handle_manage_subtask(
                action="update",
                task_id=task_id,
                subtask_id=subtask_id,
                subtask_data=update_data
            )
            
            # Update parent context if available
            if result.get("success") and self._context_facade:
                try:
                    progress_content = f"Updated subtask {subtask_id}"
                    if progress_notes:
                        progress_content += f" - {progress_notes}"
                    elif status:
                        progress_content += f" - Status: {status}"
                    
                    progress_result = self._context_facade.add_progress(
                        task_id=task_id,
                        content=progress_content,
                        agent="subtask_controller"
                    )
                    
                    result["context_updated"] = True
                    result["parent_progress"] = self._get_parent_progress(facade, task_id)
                    
                except Exception as e:
                    logger.error(f"Failed to update parent context: {e}")
                    result["context_updated"] = False
                    result["context_update_error"] = str(e)
            
            return result
            
        except Exception as e:
            logger.error(f"Error updating subtask: {str(e)}")
            return self._response_formatter.create_error_response(
                operation="update_subtask",
                error=f"Failed to update subtask: {str(e)}",
                error_code=ErrorCodes.OPERATION_FAILED,
                metadata={"task_id": task_id, "subtask_id": subtask_id}
            )
    
    def delete_subtask(self, facade: SubtaskApplicationFacade, task_id: str, 
                      subtask_id: str, progress_notes: Optional[str] = None) -> Dict[str, Any]:
        """Handle subtask deletion with automatic parent progress tracking."""
        
        if not task_id:
            return self._create_validation_error(
                "task_id", "A valid task_id string",
                "Include 'task_id' in your request"
            )
        
        if not subtask_id:
            return self._create_validation_error(
                "subtask_id", "A valid subtask_id string",
                "Include 'subtask_id' in your request"
            )
        
        try:
            result = facade.handle_manage_subtask(
                action="delete",
                task_id=task_id,
                subtask_id=subtask_id
            )
            
            # Update parent context if available
            if result.get("success") and self._context_facade:
                try:
                    progress_content = f"Deleted subtask {subtask_id}"
                    if progress_notes:
                        progress_content += f" - {progress_notes}"
                    
                    progress_result = self._context_facade.add_progress(
                        task_id=task_id,
                        content=progress_content,
                        agent="subtask_controller"
                    )
                    
                    result["context_updated"] = True
                    result["parent_progress"] = self._get_parent_progress(facade, task_id)
                    
                except Exception as e:
                    logger.error(f"Failed to update parent context: {e}")
                    result["context_updated"] = False
                    result["context_update_error"] = str(e)
            
            return result
            
        except Exception as e:
            logger.error(f"Error deleting subtask: {str(e)}")
            return self._response_formatter.create_error_response(
                operation="delete_subtask",
                error=f"Failed to delete subtask: {str(e)}",
                error_code=ErrorCodes.OPERATION_FAILED,
                metadata={"task_id": task_id, "subtask_id": subtask_id}
            )
    
    def get_subtask(self, facade: SubtaskApplicationFacade, task_id: str, 
                   subtask_id: str) -> Dict[str, Any]:
        """Handle subtask retrieval."""
        
        if not task_id:
            return self._create_validation_error(
                "task_id", "A valid task_id string",
                "Include 'task_id' in your request"
            )
        
        if not subtask_id:
            return self._create_validation_error(
                "subtask_id", "A valid subtask_id string",
                "Include 'subtask_id' in your request"
            )
        
        try:
            return facade.handle_manage_subtask(
                action="get",
                task_id=task_id,
                subtask_id=subtask_id
            )
            
        except Exception as e:
            logger.error(f"Error getting subtask: {str(e)}")
            return self._response_formatter.create_error_response(
                operation="get_subtask",
                error=f"Failed to get subtask: {str(e)}",
                error_code=ErrorCodes.OPERATION_FAILED,
                metadata={"task_id": task_id, "subtask_id": subtask_id}
            )
    
    def list_subtasks(self, facade: SubtaskApplicationFacade, task_id: str,
                     status: Optional[str] = None, priority: Optional[str] = None,
                     limit: Optional[int] = None, offset: Optional[int] = None) -> Dict[str, Any]:
        """Handle subtask listing with filters."""
        
        if not task_id:
            return self._create_validation_error(
                "task_id", "A valid task_id string",
                "Include 'task_id' in your request"
            )
        
        try:
            # Prepare filter data
            filter_data = {}
            if status:
                filter_data['status'] = status
            if priority:
                filter_data['priority'] = priority
            if limit:
                filter_data['limit'] = limit
            if offset:
                filter_data['offset'] = offset
            
            result = facade.handle_manage_subtask(
                action="list",
                task_id=task_id,
                subtask_data=filter_data
            )
            
            # Add parent progress information
            if result.get("success") and self._context_facade:
                result["parent_progress"] = self._get_parent_progress(facade, task_id)
            
            return result
            
        except Exception as e:
            logger.error(f"Error listing subtasks: {str(e)}")
            return self._response_formatter.create_error_response(
                operation="list_subtasks",
                error=f"Failed to list subtasks: {str(e)}",
                error_code=ErrorCodes.OPERATION_FAILED,
                metadata={"task_id": task_id}
            )
    
    def complete_subtask(self, facade: SubtaskApplicationFacade, task_id: str, 
                        subtask_id: str, completion_notes: Optional[str] = None, 
                        completion_summary: Optional[str] = None, **kwargs) -> Dict[str, Any]:
        """Handle subtask completion with automatic parent progress tracking."""
        
        if not task_id:
            return self._create_validation_error(
                "task_id", "A valid task_id string",
                "Include 'task_id' in your request"
            )
        
        if not subtask_id:
            return self._create_validation_error(
                "subtask_id", "A valid subtask_id string",
                "Include 'subtask_id' in your request"
            )
        
        try:
            # Complete the subtask
            completion_data = {
                "status": "done",
                "progress_percentage": 100,  # Automatically set progress to 100% when completed
                "completion_notes": completion_notes,
                "completed_at": datetime.now(timezone.utc).isoformat()
            }
            
            result = facade.handle_manage_subtask(
                action="update",
                task_id=task_id,
                subtask_id=subtask_id,
                subtask_data=completion_data
            )
            
            # Update parent context if available
            if result.get("success") and self._context_facade:
                try:
                    progress_content = f"Completed subtask {subtask_id}"
                    if completion_notes:
                        progress_content += f" - {completion_notes}"
                    
                    progress_result = self._context_facade.add_progress(
                        task_id=task_id,
                        content=progress_content,
                        agent="subtask_controller"
                    )
                    
                    result["context_updated"] = True
                    result["parent_progress"] = self._get_parent_progress(facade, task_id)
                    
                except Exception as e:
                    logger.error(f"Failed to update parent context: {e}")
                    result["context_updated"] = False
                    result["context_update_error"] = str(e)
            
            return result
            
        except Exception as e:
            logger.error(f"Error completing subtask: {str(e)}")
            return self._response_formatter.create_error_response(
                operation="complete_subtask",
                error=f"Failed to complete subtask: {str(e)}",
                error_code=ErrorCodes.OPERATION_FAILED,
                metadata={"task_id": task_id, "subtask_id": subtask_id}
            )
    
    def _get_parent_progress(self, facade: SubtaskApplicationFacade, task_id: str) -> Dict[str, Any]:
        """Get parent task progress information."""
        try:
            # Get all subtasks for the parent task
            subtasks_result = facade.handle_manage_subtask(
                action="list",
                task_id=task_id
            )
            
            if not subtasks_result.get("success"):
                return {"error": "Failed to get parent progress"}
            
            subtasks = subtasks_result.get("subtasks", [])
            total_subtasks = len(subtasks)
            
            if total_subtasks == 0:
                return {"total_subtasks": 0, "progress_percentage": 0}
            
            completed_subtasks = len([s for s in subtasks if s.get("status") == "done"])
            progress_percentage = int((completed_subtasks / total_subtasks) * 100)
            
            return {
                "total_subtasks": total_subtasks,
                "completed_subtasks": completed_subtasks,
                "progress_percentage": progress_percentage,
                "last_updated": datetime.now(timezone.utc).isoformat()
            }
            
        except Exception as e:
            logger.error(f"Error calculating parent progress: {e}")
            return {"error": f"Failed to calculate parent progress: {str(e)}"}
    
    def _create_validation_error(self, field: str, expected: str, hint: str) -> Dict[str, Any]:
        """Create standardized validation error."""
        return self._response_formatter.create_error_response(
            operation="subtask_validation",
            error=f"Missing required field: {field}. Expected: {expected}",
            error_code=ErrorCodes.VALIDATION_ERROR,
            metadata={"field": field, "hint": hint}
        )