"""Subtask MCP Controller

This controller handles MCP tool registration for subtask management operations,
following DDD principles by delegating business logic to application services.
Includes automatic context updates and progress tracking for all actions.
"""

import logging
import asyncio
import uuid
import re
from typing import Dict, Any, Optional, List, Annotated, Union
from datetime import datetime, timezone
from pydantic import Field # type: ignore

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from fastmcp.server.server import FastMCP

from .desc import description_loader
from ...application.facades.subtask_application_facade import SubtaskApplicationFacade
from ...application.factories.subtask_facade_factory import SubtaskFacadeFactory
from .workflow_guidance.subtask import SubtaskWorkflowFactory
from ..utils.response_formatter import StandardResponseFormatter, ResponseStatus, ErrorCodes
from ..utils.parameter_validation_fix import coerce_parameter_types
from ..utils.schema_monkey_patch import apply_all_schema_patches
from .auth_helper import get_authenticated_user_id, log_authentication_details
from ...domain.constants import validate_user_id
from ...domain.exceptions.authentication_exceptions import (
    UserAuthenticationRequiredError,
    DefaultUserProhibitedError
)
from ....config.auth_config import AuthConfig

logger = logging.getLogger(__name__)

# Import user context utilities - REQUIRED for authentication
try:
    from fastmcp.auth.middleware.request_context_middleware import get_current_user_id
    from fastmcp.auth.mcp_integration.thread_context_manager import ContextPropagationMixin
except ImportError:
    # Use auth_helper which is already imported
    get_current_user_id = get_authenticated_user_id
    # Fallback mixin if thread context manager is not available
    class ContextPropagationMixin:
        def _run_async_with_context(self, async_func, *args, **kwargs):
            import asyncio
            import threading
            result = None
            exception = None
            def run_in_new_loop():
                nonlocal result, exception
                try:
                    new_loop = asyncio.new_event_loop()
                    asyncio.set_event_loop(new_loop)
                    try:
                        result = new_loop.run_until_complete(async_func(*args, **kwargs))
                    finally:
                        new_loop.close()
                        asyncio.set_event_loop(None)
                except Exception as e:
                    exception = e
            thread = threading.Thread(target=run_in_new_loop)
            thread.start()
            thread.join()
            if exception:
                raise exception
            return result


class SubtaskMCPController(ContextPropagationMixin):
    """
    MCP Controller for subtask management operations with integrated progress tracking.
    
    Handles only MCP protocol concerns and delegates business operations
    to the SubtaskApplicationFacade following proper DDD layer separation.
    All actions automatically update parent task context and progress.
    Enhanced with proper authentication context propagation across threads.
    """
    
    def __init__(self, subtask_facade_factory: SubtaskFacadeFactory, task_facade=None, context_facade=None, task_repository_factory=None):
        """
        Initialize controller with subtask application facade factory.
        
        Args:
            subtask_facade_factory: Factory for creating subtask application facades
            task_facade: Optional task facade for parent task operations
            context_facade: Optional context facade for parent context updates
            task_repository_factory: Optional task repository factory instance
        """
        self._subtask_facade_factory = subtask_facade_factory
        self._task_facade = task_facade
        self._context_facade = context_facade
        self._task_repository_factory = task_repository_factory
        self._workflow_guidance = SubtaskWorkflowFactory.create()
        logger.info("SubtaskMCPController initialized with integrated progress tracking")
    
    def _run_async(self, coro):
        """Helper method to run async operations in sync context with context preservation."""
        try:
            loop = asyncio.get_event_loop()
            if loop.is_running():
                # If loop is already running, use our context-aware threading
                async def _wrapper():
                    return await coro
                return self._run_async_with_context(_wrapper)
            else:
                # If no loop is running, use asyncio.run
                return asyncio.run(coro)
        except Exception as e:
            logger.error(f"Error running async operation: {e}")
            raise
    
    def register_tools(self, mcp: "FastMCP"):
        """Register subtask management tools with FastMCP."""
        
        # Apply schema monkey patches for flexible array parameters BEFORE registering tools
        apply_all_schema_patches()
        
        # Get tool descriptions
        manage_subtask_desc = self._get_subtask_management_descriptions().get("manage_subtask", {})
        
        @mcp.tool(name="manage_subtask", description=manage_subtask_desc["description"])
        def manage_subtask(
            action: Annotated[str, Field(description=manage_subtask_desc["parameters"].get("action", "Subtask management action"))],
            task_id: Annotated[str, Field(description=manage_subtask_desc["parameters"].get("task_id", "Parent task identifier (UUID)"))],
            subtask_id: Annotated[Optional[str], Field(description=manage_subtask_desc["parameters"].get("subtask_id", "Subtask ID"))] = None,
            title: Annotated[Optional[str], Field(description="Subtask title - be specific and actionable (e.g., 'Implement user login' not just 'Login'). Required for: create. Optional for: update")] = None,
            description: Annotated[Optional[str], Field(description="Detailed subtask description explaining what needs to be done. Include acceptance criteria if relevant. Optional for: create, update")] = None,
            status: Annotated[Optional[str], Field(description="Subtask status: 'todo', 'in_progress', 'done'. Optional - use progress_percentage instead for automatic status mapping.")] = None,
            priority: Annotated[Optional[str], Field(description="Subtask priority: 'low', 'medium', 'high', 'urgent', 'critical'. Optional for: create, update. Default: inherits from parent")] = None,
            assignees: Annotated[Optional[Union[List[str], str]], Field(description="List of assignee identifiers. Accepts array, JSON string array, or comma-separated string. Example: ['user1', 'user2'] or 'user1,user2'")] = None,
            progress_notes: Annotated[Optional[str], Field(description="Brief description of work done (for update action)")] = None,
            progress_percentage: Annotated[Optional[Union[int, str]], Field(description="Subtask completion percentage 0-100 (for update action). Accepts integer or string representation.")] = None,
            blockers: Annotated[Optional[str], Field(description="Any blockers encountered")] = None,
            insights_found: Annotated[Optional[Union[List[str], str]], Field(description="Insights discovered during subtask work. Accepts array, JSON string array, or comma-separated string.")] = None,
            completion_summary: Annotated[Optional[str], Field(description="Summary of what was accomplished (REQUIRED for complete action)")] = None,
            impact_on_parent: Annotated[Optional[str], Field(description="How this impacts the parent task")] = None,
            # Enhanced completion context parameters
            testing_notes: Annotated[Optional[str], Field(description="Detailed testing performed and results (for complete action)")] = None,
            deliverables: Annotated[Optional[Union[List[str], str]], Field(description="List of deliverables created - files, endpoints, components, etc. Accepts array, JSON string array, or comma-separated string. (for complete action)")] = None,
            skills_learned: Annotated[Optional[Union[List[str], str]], Field(description="New skills or knowledge gained during this subtask. Accepts array, JSON string array, or comma-separated string. (for complete action)")] = None,
            challenges_overcome: Annotated[Optional[Union[List[str], str]], Field(description="Challenges faced and how they were solved. Accepts array, JSON string array, or comma-separated string. (for complete action)")] = None,
            next_recommendations: Annotated[Optional[Union[List[str], str]], Field(description="Recommendations for future work or improvements. Accepts array, JSON string array, or comma-separated string. (for complete action)")] = None,
            completion_quality: Annotated[Optional[str], Field(description="Quality assessment: 'excellent', 'good', 'satisfactory', 'needs_improvement' (for complete action)")] = None,
            verification_status: Annotated[Optional[str], Field(description="Verification status: 'verified', 'pending_review', 'needs_testing', 'failed_verification' (for complete action)")] = None,
            user_id: Annotated[Optional[str], Field(description="User identifier for authentication and audit trails")] = None
        ) -> Dict[str, Any]:

            # Delegate to the public method
            return self.manage_subtask(
                action=action,
                task_id=task_id,
                subtask_id=subtask_id,
                title=title,
                description=description,
                status=status,
                priority=priority,
                assignees=assignees,
                progress_notes=progress_notes,
                progress_percentage=progress_percentage,
                blockers=blockers,
                insights_found=insights_found,
                completion_summary=completion_summary,
                impact_on_parent=impact_on_parent,
                testing_notes=testing_notes,
                deliverables=deliverables,
                skills_learned=skills_learned,
                challenges_overcome=challenges_overcome,
                next_recommendations=next_recommendations,
                completion_quality=completion_quality,
                verification_status=verification_status,
                user_id=user_id
            )
        
        logger.info("Subtask management tool registered")
    
    def manage_subtask(
        self,
        action: str,
        task_id: str,
        subtask_id: Optional[str] = None,
        title: Optional[str] = None,
        description: Optional[str] = None,
        status: Optional[str] = None,
        priority: Optional[str] = None,
        assignees: Optional[Union[List[str], str]] = None,
        progress_notes: Optional[str] = None,
        progress_percentage: Optional[Union[int, str]] = None,
        blockers: Optional[str] = None,
        insights_found: Optional[Union[List[str], str]] = None,
        completion_summary: Optional[str] = None,
        impact_on_parent: Optional[str] = None,
        testing_notes: Optional[str] = None,
        deliverables: Optional[Union[List[str], str]] = None,
        skills_learned: Optional[Union[List[str], str]] = None,
        challenges_overcome: Optional[Union[List[str], str]] = None,
        next_recommendations: Optional[Union[List[str], str]] = None,
        completion_quality: Optional[str] = None,
        verification_status: Optional[str] = None,
        user_id: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Public method for managing subtask operations.
        This method is called by both the MCP tool registration and tests.
        """
        # Parameter type coercion for all parameters
        try:
            params = {
                k: v for k, v in locals().items() 
                if k not in ['self', 'action', 'task_id'] and v is not None
            }
            coerced_params = coerce_parameter_types(params)
            
            # Apply coerced values back to local variables
            for param_name, coerced_value in coerced_params.items():
                if param_name in locals():
                    locals()[param_name] = coerced_value
            
            # Extract specific coerced values for type safety
            if 'progress_percentage' in coerced_params:
                progress_percentage = coerced_params['progress_percentage']
            if 'insights_found' in coerced_params:
                insights_found = coerced_params['insights_found']
            if 'assignees' in coerced_params:
                assignees = coerced_params['assignees']
            if 'deliverables' in coerced_params:
                deliverables = coerced_params['deliverables']
            if 'skills_learned' in coerced_params:
                skills_learned = coerced_params['skills_learned']
            if 'challenges_overcome' in coerced_params:
                challenges_overcome = coerced_params['challenges_overcome']
            if 'next_recommendations' in coerced_params:
                next_recommendations = coerced_params['next_recommendations']
                
        except Exception as e:
            logger.warning(f"Parameter coercion failed: {e}, continuing with original values")
        
        # Enhanced progress percentage validation
        if progress_percentage is not None:
            # Range validation: ensure value is between 0-100
            if not isinstance(progress_percentage, int) or not (0 <= progress_percentage <= 100):
                return {
                    "success": False,
                    "error": f"Invalid progress_percentage value: {progress_percentage}. Must be integer between 0-100.",
                    "error_code": "PARAMETER_RANGE_ERROR",
                    "parameter": "progress_percentage",
                    "provided_value": progress_percentage,
                    "valid_range": "0-100",
                    "hint": "Use percentage values: 0=not started, 50=half done, 100=complete"
                }
        
        # Validate common requirements
        if action in ["update", "delete", "get", "complete"] and not subtask_id:
            return {
                "success": False,
                "error": f"Missing required field: subtask_id for action '{action}'"
            }
        
        if action == "create" and not title:
            return {
                "success": False,
                "error": "Missing required field: title"
            }
        
        if action == "complete" and not completion_summary:
            return {
                "success": False,
                "error": "Missing required field: completion_summary for complete action"
            }
        
        # Validate UUID format for task_id
        if not self._is_valid_uuid(task_id):
            return {
                "success": False,
                "error": f"Invalid task_id format: '{task_id}'. Expected UUID format: xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx",
                "error_code": "INVALID_FORMAT",
                "field": "task_id",
                "expected_format": "UUID (e.g., 550e8400-e29b-41d4-a716-446655440000)",
                "hint": "Use a valid UUID for task_id. Get UUIDs from task creation or list operations."
            }
        
        # Validate UUID format for subtask_id if provided
        if subtask_id and not self._is_valid_uuid(subtask_id):
            return {
                "success": False,
                "error": f"Invalid subtask_id format: '{subtask_id}'. Expected UUID format: xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx",
                "error_code": "INVALID_FORMAT",
                "field": "subtask_id",
                "expected_format": "UUID (e.g., 550e8400-e29b-41d4-a716-446655440000)",
                "hint": "Use a valid UUID for subtask_id. Get UUIDs from subtask creation or list operations."
            }
        
        # Enhanced validation for completion parameters
        if action == "complete":
            validation_result = self._validate_completion_parameters(
                completion_quality=completion_quality,
                verification_status=verification_status,
                deliverables=deliverables,
                skills_learned=skills_learned,
                challenges_overcome=challenges_overcome,
                next_recommendations=next_recommendations
            )
            if not validation_result["valid"]:
                return validation_result
        
        # Validate parameter formats with helpful error messages
        validation_result = self._validate_subtask_parameters(
            progress_percentage=progress_percentage, assignees=assignees, insights_found=insights_found
        )
        if not validation_result["valid"]:
            return validation_result
        
        logger.info(f"Managing subtask with action: {action}, task_id: {task_id}")
        
        # Get the appropriate facade
        facade = self._get_facade_for_request(task_id=task_id, user_id=user_id)
        
        # Route to appropriate handler based on action
        if action == "create":
            result = self._handle_create_subtask(
                facade, task_id, title, description, priority, assignees, progress_notes
            )
        elif action == "update":
            result = self._handle_update_subtask(
                facade, task_id, subtask_id, title, description, status, 
                priority, assignees, progress_notes, progress_percentage, 
                blockers, insights_found
            )
        elif action == "delete":
            result = self._handle_delete_subtask(facade, task_id, subtask_id)
        elif action == "list":
            result = self._handle_list_subtasks(facade, task_id)
        elif action == "get":
            result = self._handle_get_subtask(facade, task_id, subtask_id)
        elif action == "complete":
            result = self._handle_complete_subtask(
                facade, task_id, subtask_id, completion_summary, 
                impact_on_parent, insights_found, testing_notes,
                deliverables, skills_learned, challenges_overcome,
                next_recommendations, completion_quality, verification_status
            )
        else:
            result = {
                "success": False,
                "error": f"Unknown action: {action}",
                "valid_actions": ["create", "update", "delete", "list", "get", "complete"]
            }
        
        # Enhance all responses with workflow hints
        if result.get("success"):
            subtasks = result.get("subtasks") if action == "list" else None
            result = self._enhance_with_workflow_hints(
                result, action, task_id, subtask_id, subtasks
            )
        
        return result
    
    def handle_crud_operations(
        self,
        action: str,
        task_id: str,
        subtask_data: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        Handle CRUD operations for subtasks.
        This method is for backward compatibility with tests.
        """
        # Extract parameters from subtask_data
        subtask_data = subtask_data or {}
        
        return self.manage_subtask(
            action=action,
            task_id=task_id,
            subtask_id=subtask_data.get("subtask_id"),
            title=subtask_data.get("title"),
            description=subtask_data.get("description"),
            status=subtask_data.get("status"),
            priority=subtask_data.get("priority"),
            assignees=subtask_data.get("assignees"),
            progress_notes=subtask_data.get("progress_notes"),
            progress_percentage=subtask_data.get("progress_percentage"),
            blockers=subtask_data.get("blockers"),
            insights_found=subtask_data.get("insights_found"),
            completion_summary=subtask_data.get("completion_summary"),
            impact_on_parent=subtask_data.get("impact_on_parent"),
            testing_notes=subtask_data.get("testing_notes"),
            deliverables=subtask_data.get("deliverables"),
            skills_learned=subtask_data.get("skills_learned"),
            challenges_overcome=subtask_data.get("challenges_overcome"),
            next_recommendations=subtask_data.get("next_recommendations"),
            completion_quality=subtask_data.get("completion_quality"),
            verification_status=subtask_data.get("verification_status")
        )
    
    def _handle_create_subtask(
        self, 
        facade: SubtaskApplicationFacade,
        task_id: str,
        title: str,
        description: Optional[str] = None,
        priority: Optional[str] = None,
        assignees: Optional[List[str]] = None,
        progress_notes: Optional[str] = None
    ) -> Dict[str, Any]:
        """Handle subtask creation with automatic parent context update."""
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
            
            if result.get("success") and self._context_facade:
                # Update parent task context with progress notes if provided
                try:
                    # Debug: Log result structure
                    logger.debug(f"Subtask creation result structure: {result}")
                    
                    # Safely extract subtask ID
                    subtask = result.get("subtask", {})
                    if isinstance(subtask, dict):
                        subtask_id = subtask.get("id") or subtask.get("subtask", {}).get("id")
                    else:
                        subtask_id = getattr(subtask, 'id', None)
                    
                    logger.debug(f"Extracted subtask_id: {subtask_id}")
                    
                    context_update = {
                        "action": "subtask_created",
                        "subtask_id": subtask_id,
                        "subtask_title": title,
                        "timestamp": datetime.now(timezone.utc).isoformat()
                    }
                    
                    if progress_notes:
                        context_update["progress_notes"] = progress_notes
                    
                    # Update parent context using add_progress method
                    progress_content = f"Created subtask: {title}" + (f" - {progress_notes}" if progress_notes else "")
                    progress_result = self._context_facade.add_progress(
                        task_id=task_id,
                        content=progress_content,
                        agent="subtask_controller"
                    )
                    
                    result["context_updated"] = True
                    result["parent_progress"] = self._get_parent_progress(facade, task_id)
                except Exception as e:
                    logger.error(f"Failed to update parent context: {e}")
                    # Context update failure should NOT block the operation - subtask creation succeeded
                    result["context_updated"] = False
                    result["context_update_error"] = str(e)
                    result["warning"] = "Subtask created successfully but parent context update failed"
            
            # Apply workflow guidance enhancement
            if result.get("success") and result.get("subtask"):
                result = self._enhance_response_with_workflow_guidance(
                    result, "create", task_id
                )
            
            # Convert to standardized response format
            return self._standardize_response(
                result,
                operation="create_subtask",
                metadata={
                    "task_id": task_id,
                    "title": title
                }
            )
            
        except Exception as e:
            logger.error(f"Error in _handle_create_subtask: {e}")
            return self._create_standardized_error(
                operation="create_subtask",
                field="general",
                expected="Successful subtask creation",
                hint=f"Failed to create subtask: {str(e)}"
            )
    
    def _handle_update_subtask(
        self,
        facade: SubtaskApplicationFacade,
        task_id: str,
        subtask_id: str,
        title: Optional[str] = None,
        description: Optional[str] = None,
        status: Optional[str] = None,
        priority: Optional[str] = None,
        assignees: Optional[List[str]] = None,
        progress_notes: Optional[str] = None,
        progress_percentage: Optional[Union[int, str]] = None,
        blockers: Optional[str] = None,
        insights_found: Optional[List[str]] = None
    ) -> Dict[str, Any]:
        """Handle subtask update with automatic parent context update."""
        try:
            # Auto-status mapping based on progress percentage
            if progress_percentage is not None:
                if progress_percentage == 0:
                    status = "todo"
                elif progress_percentage == 100:
                    status = "done"
                elif 1 <= progress_percentage <= 99:
                    status = "in_progress"
                else:
                    # This shouldn't happen due to earlier validation, but defensive programming
                    logger.warning(f"Unexpected progress_percentage value: {progress_percentage}")
                    status = "in_progress"
            
            # Update the subtask
            subtask_data = {
                "subtask_id": subtask_id,
                "title": title,
                "description": description,
                "status": status,
                "priority": priority,
                "assignees": assignees,
                "progress_percentage": progress_percentage
            }
            # Remove None values
            subtask_data = {k: v for k, v in subtask_data.items() if v is not None}
            
            result = facade.handle_manage_subtask(
                action="update",
                task_id=task_id,
                subtask_data=subtask_data
            )
            
            if result.get("success") and self._context_facade:
                # Update parent task context
                try:
                    updates = []
                    if progress_notes:
                        updates.append(f"Progress: {progress_notes}")
                    if progress_percentage is not None:
                        updates.append(f"Completion: {progress_percentage}%")
                    if blockers:
                        updates.append(f"Blocked: {blockers}")
                    if insights_found:
                        updates.append(f"Insights: {', '.join(insights_found)}")
                    
                    if updates:
                        # Safely get the subtask title, fallback to subtask_id if not available
                        subtask_title = result.get('subtask', {}).get('title', f'Subtask {subtask_id}')
                        progress_content = f"Subtask '{subtask_title}' - " + " | ".join(updates)
                        progress_result = self._context_facade.add_progress(
                            task_id=task_id,
                            content=progress_content,
                            agent="subtask_controller"
                        )
                    
                    # Add insights if found
                    if insights_found:
                        for insight in insights_found:
                            insight_data = {
                                "insights": [{
                                    "content": f"From subtask: {insight}",
                                    "agent": "subtask_controller",
                                    "category": "subtask_learning",
                                    "importance": "medium",
                                    "timestamp": datetime.now(timezone.utc).isoformat()
                                }]
                            }
                            insight_result = self._context_facade.merge_context("task", task_id, insight_data)
                    
                    result["context_updated"] = True
                    result["parent_progress"] = self._get_parent_progress(facade, task_id)
                except Exception as e:
                    logger.error(f"Failed to update parent context: {e}")
                    # Context update failure should block the operation
                    return {
                        "success": False,
                        "error": f"Operation succeeded but failed to update parent context: {str(e)}",
                        "subtask": result.get("subtask"),
                        "context_update_error": str(e)
                    }
            
            return result
            
        except Exception as e:
            logger.error(f"Error in _handle_update_subtask: {e}")
            return {
                "success": False,
                "error": f"Failed to update subtask: {str(e)}"
            }
    
    def _handle_delete_subtask(
        self,
        facade: SubtaskApplicationFacade,
        task_id: str,
        subtask_id: str
    ) -> Dict[str, Any]:
        """Handle subtask deletion with automatic parent context update."""
        try:
            # Get subtask info before deletion
            subtask_info = facade.handle_manage_subtask(
                action="get",
                task_id=task_id,
                subtask_data={"subtask_id": subtask_id}
            )
            subtask_title = subtask_info.get("subtask", {}).get("title", "Unknown")
            
            # Delete the subtask
            result = facade.handle_manage_subtask(
                action="delete",
                task_id=task_id,
                subtask_data={"subtask_id": subtask_id}
            )
            
            if result.get("success") and self._context_facade:
                # Update parent task context
                try:
                    progress_result = self._context_facade.add_progress(
                        task_id=task_id,
                        content=f"Deleted subtask: {subtask_title}",
                        agent="subtask_controller"
                    )
                    result["context_updated"] = True
                    result["parent_progress"] = self._get_parent_progress(facade, task_id)
                except Exception as e:
                    logger.error(f"Failed to update parent context: {e}")
                    # Context update failure should block the operation
                    return {
                        "success": False,
                        "error": f"Operation succeeded but failed to update parent context: {str(e)}",
                        "subtask": result.get("subtask"),
                        "context_update_error": str(e)
                    }
            
            return result
            
        except Exception as e:
            logger.error(f"Error in _handle_delete_subtask: {e}")
            return {
                "success": False,
                "error": f"Failed to delete subtask: {str(e)}"
            }
    
    def _handle_list_subtasks(
        self,
        facade: SubtaskApplicationFacade,
        task_id: str
    ) -> Dict[str, Any]:
        """Handle listing subtasks with progress summary."""
        try:
            result = facade.handle_manage_subtask(
                action="list",
                task_id=task_id
            )
            
            if result.get("success"):
                # Add progress summary
                subtasks = result.get("subtasks", [])
                total = len(subtasks)
                completed = sum(1 for s in subtasks if s.get("status") == "done")
                in_progress = sum(1 for s in subtasks if s.get("status") == "in_progress")
                
                result["progress_summary"] = {
                    "total_subtasks": total,
                    "completed": completed,
                    "in_progress": in_progress,
                    "pending": total - completed - in_progress,
                    "blocked": sum(1 for s in subtasks if s.get("status") == "blocked"),
                    "completion_percentage": (completed / total * 100) if total > 0 else 0.0,
                    "summary": f"{completed}/{total} subtasks complete ({(completed/total*100):.1f}%)" if total > 0 else "No subtasks"
                }
            
            return result
            
        except Exception as e:
            logger.error(f"Error in _handle_list_subtasks: {e}")
            return {
                "success": False,
                "error": f"Failed to list subtasks: {str(e)}"
            }
    
    def _handle_get_subtask(
        self,
        facade: SubtaskApplicationFacade,
        task_id: str,
        subtask_id: str
    ) -> Dict[str, Any]:
        """Handle getting a specific subtask."""
        try:
            return facade.handle_manage_subtask(
                action="get",
                task_id=task_id,
                subtask_data={"subtask_id": subtask_id}
            )
        except Exception as e:
            logger.error(f"Error in _handle_get_subtask: {e}")
            return {
                "success": False,
                "error": f"Failed to get subtask: {str(e)}"
            }
    
    def _handle_complete_subtask(
        self,
        facade: SubtaskApplicationFacade,
        task_id: str,
        subtask_id: str,
        completion_summary: Optional[str] = None,
        impact_on_parent: Optional[str] = None,
        insights_found: Optional[List[str]] = None,
        testing_notes: Optional[str] = None,
        deliverables: Optional[List[str]] = None,
        skills_learned: Optional[List[str]] = None,
        challenges_overcome: Optional[List[str]] = None,
        next_recommendations: Optional[List[str]] = None,
        completion_quality: Optional[str] = None,
        verification_status: Optional[str] = None
    ) -> Dict[str, Any]:
        """Handle subtask completion with enhanced context tracking."""
        try:
            # Get subtask info before completion
            subtask_info = facade.handle_manage_subtask(
                action="get",
                task_id=task_id,
                subtask_data={"subtask_id": subtask_id}
            )
            
            # Update subtask status to done
            result = facade.handle_manage_subtask(
                action="update",
                task_id=task_id,
                subtask_data={
                    "subtask_id": subtask_id,
                    "status": "done"
                }
            )
            
            if result.get("success"):
                # IMPORTANT: Preserve the original "complete" action in the response
                result["action"] = "complete"
                
            if result.get("success") and self._context_facade:
                # Build comprehensive completion context
                completion_context = self._build_completion_context(
                    subtask_info=subtask_info,
                    completion_summary=completion_summary,
                    impact_on_parent=impact_on_parent,
                    insights_found=insights_found,
                    testing_notes=testing_notes,
                    deliverables=deliverables,
                    skills_learned=skills_learned,
                    challenges_overcome=challenges_overcome,
                    next_recommendations=next_recommendations,
                    completion_quality=completion_quality,
                    verification_status=verification_status
                )
                
                # Update parent task context with enhanced completion info
                try:
                    # Add main completion progress
                    subtask_title = result.get('subtask', {}).get('title', f'Subtask {subtask_id}')
                    main_completion_msg = f"Completed subtask: {subtask_title}"
                    if completion_summary:
                        main_completion_msg += f" - {completion_summary}"
                    
                    self._context_facade.add_progress(
                        task_id=task_id,
                        content=main_completion_msg,
                        agent="subtask_controller"
                    )
                    
                    # Add impact information
                    if impact_on_parent:
                        self._context_facade.add_progress(
                            task_id=task_id,
                            content=f"Impact: {impact_on_parent}",
                            agent="subtask_controller"
                        )
                    
                    # Add testing information
                    if testing_notes:
                        self._context_facade.add_progress(
                            task_id=task_id,
                            content=f"Testing: {testing_notes}",
                            agent="subtask_controller"
                        )
                    
                    # Add deliverables
                    if deliverables:
                        deliverables_str = ", ".join(deliverables)
                        self._context_facade.add_progress(
                            task_id=task_id,
                            content=f"Deliverables: {deliverables_str}",
                            agent="subtask_controller"
                        )
                    
                    # Add quality and verification info
                    if completion_quality or verification_status:
                        quality_info = []
                        if completion_quality:
                            quality_info.append(f"Quality: {completion_quality}")
                        if verification_status:
                            quality_info.append(f"Verification: {verification_status}")
                        
                        self._context_facade.add_progress(
                            task_id=task_id,
                            content=f"Quality Assessment: {' | '.join(quality_info)}",
                            agent="subtask_controller"
                        )
                    
                    # Add insights and learnings
                    if insights_found:
                        for insight in insights_found:
                            insight_data = {
                                "insights": [{
                                    "content": f"Subtask insight: {insight}",
                                    "agent": "subtask_controller",
                                    "category": "subtask_completion",
                                    "importance": "high",
                                    "timestamp": datetime.now(timezone.utc).isoformat()
                                }]
                            }
                            self._context_facade.merge_context("task", task_id, insight_data)
                    
                    # Add skills learned
                    if skills_learned:
                        for skill in skills_learned:
                            skill_data = {
                                "insights": [{
                                    "content": f"Skill learned: {skill}",
                                    "agent": "subtask_controller",
                                    "category": "skill_development",
                                    "importance": "medium",
                                    "timestamp": datetime.now(timezone.utc).isoformat()
                                }]
                            }
                            self._context_facade.merge_context("task", task_id, skill_data)
                    
                    # Add challenges overcome
                    if challenges_overcome:
                        for challenge in challenges_overcome:
                            challenge_data = {
                                "insights": [{
                                    "content": f"Challenge overcome: {challenge}",
                                    "agent": "subtask_controller",
                                    "category": "problem_solving",
                                    "importance": "high",
                                    "timestamp": datetime.now(timezone.utc).isoformat()
                                }]
                            }
                            self._context_facade.merge_context("task", task_id, challenge_data)
                    
                    # Add next recommendations
                    if next_recommendations:
                        for recommendation in next_recommendations:
                            rec_data = {
                                "insights": [{
                                    "content": f"Recommendation: {recommendation}",
                                    "agent": "subtask_controller",
                                    "category": "future_work",
                                    "importance": "medium",
                                    "timestamp": datetime.now(timezone.utc).isoformat()
                                }]
                            }
                            self._context_facade.merge_context("task", task_id, rec_data)
                    
                    # Add comprehensive completion context
                    self._context_facade.merge_context(
                        "task", task_id, {"completion_context": completion_context}
                    )
                    
                    result["context_updated"] = True
                    result["completion_context"] = completion_context
                    result["parent_progress"] = self._get_parent_progress(facade, task_id)
                    
                    # Check if all subtasks are complete
                    list_result = facade.handle_manage_subtask(
                        action="list",
                        task_id=task_id
                    )
                    if list_result.get("success"):
                        subtasks = list_result.get("subtasks", [])
                        all_complete = all(s.get("status") == "done" for s in subtasks)
                        if all_complete and subtasks:
                            result["hint"] = "🎉 All subtasks complete! Parent task ready for completion with comprehensive context."
                            result["parent_completion_ready"] = True
                    
                except Exception as e:
                    logger.error(f"Failed to update enhanced parent context: {e}")
                    return {
                        "success": False,
                        "error": f"Operation succeeded but failed to update parent context: {str(e)}",
                        "subtask": result.get("subtask"),
                        "context_update_error": str(e)
                    }
            
            return result
            
        except Exception as e:
            logger.error(f"Error in _handle_complete_subtask: {e}")
            return {
                "success": False,
                "error": f"Failed to complete subtask: {str(e)}"
            }
    
    def _build_completion_context(
        self,
        subtask_info: Dict[str, Any],
        completion_summary: str,
        impact_on_parent: Optional[str] = None,
        insights_found: Optional[List[str]] = None,
        testing_notes: Optional[str] = None,
        deliverables: Optional[List[str]] = None,
        skills_learned: Optional[List[str]] = None,
        challenges_overcome: Optional[List[str]] = None,
        next_recommendations: Optional[List[str]] = None,
        completion_quality: Optional[str] = None,
        verification_status: Optional[str] = None
    ) -> Dict[str, Any]:
        """Build comprehensive completion context for subtask."""
        context = {
            "subtask_info": subtask_info,
            "completion_summary": completion_summary,
            "completion_timestamp": datetime.now(timezone.utc).isoformat(),
            "completion_metadata": {
                "completion_quality": completion_quality,
                "verification_status": verification_status,
                "impact_on_parent": impact_on_parent
            }
        }
        
        if testing_notes:
            context["testing"] = {
                "notes": testing_notes,
                "timestamp": datetime.now(timezone.utc).isoformat()
            }
        
        if deliverables:
            context["deliverables"] = {
                "items": deliverables,
                "count": len(deliverables),
                "timestamp": datetime.now(timezone.utc).isoformat()
            }
        
        if insights_found:
            context["insights"] = {
                "items": insights_found,
                "count": len(insights_found),
                "timestamp": datetime.now(timezone.utc).isoformat()
            }
        
        if skills_learned:
            context["skills_learned"] = {
                "items": skills_learned,
                "count": len(skills_learned),
                "timestamp": datetime.now(timezone.utc).isoformat()
            }
        
        if challenges_overcome:
            context["challenges_overcome"] = {
                "items": challenges_overcome,
                "count": len(challenges_overcome),
                "timestamp": datetime.now(timezone.utc).isoformat()
            }
        
        if next_recommendations:
            context["next_recommendations"] = {
                "items": next_recommendations,
                "count": len(next_recommendations),
                "timestamp": datetime.now(timezone.utc).isoformat()
            }
        
        return context
    
    def _get_parent_progress(self, facade: SubtaskApplicationFacade, task_id: str) -> Dict[str, Any]:
        """Calculate parent task progress based on subtasks."""
        try:
            list_result = facade.handle_manage_subtask(
                action="list",
                task_id=task_id
            )
            if list_result.get("success"):
                subtasks = list_result.get("subtasks", [])
                total = len(subtasks)
                completed = sum(1 for s in subtasks if s.get("status") == "done")
                in_progress = sum(1 for s in subtasks if s.get("status") == "in_progress")
                
                return {
                    "percentage": (completed / total * 100) if total > 0 else 0,
                    "completed": completed,
                    "in_progress": in_progress,
                    "total": total,
                    "method": "weighted_subtasks"
                }
        except Exception as e:
            logger.error(f"Error calculating parent progress: {e}")
        
        return {"percentage": 0, "completed": 0, "total": 0, "method": "unknown"}
    
    def _get_facade_for_request(self, task_id: Optional[str] = None, user_id: Optional[str] = None) -> SubtaskApplicationFacade:
        """Get the appropriate facade for the request with authenticated user context."""
        # Use provided user_id or fall back to authentication
        log_authentication_details()  # For debugging
        if user_id:
            validated_user_id = validate_user_id(user_id, "Subtask context resolution")
        else:
            validated_user_id = get_authenticated_user_id(None, "Subtask context resolution")
        
        # Derive project context from task_id if available
        project_id = "default"
        if task_id:
            logger.debug(f"Deriving context for subtask operations on task_id {task_id}")
            try:
                # Use TaskApplicationFacade with proper factory pattern
                from ...application.facades.task_application_facade import TaskApplicationFacade
                from ...infrastructure.repositories.repository_factory import RepositoryFactory
                
                task_facade = TaskApplicationFacade(
                    task_repository=RepositoryFactory.get_task_repository()
                )
                
                task_data = task_facade.get_task(task_id, include_context=False)
                if task_data and 'task' in task_data:
                    git_branch_id = task_data['task'].get('git_branch_id')
                    if git_branch_id:
                        logger.debug(f"Found git_branch_id {git_branch_id} for task_id {task_id}")
                        
                        # Look up project_id from git_branch_id using facade with factory
                        from ...application.facades.git_branch_application_facade import GitBranchApplicationFacade
                        from ...infrastructure.repositories.repository_factory import RepositoryFactory
                        
                        git_branch_facade = GitBranchApplicationFacade(
                            git_branch_repository=RepositoryFactory.get_git_branch_repository()
                        )
                        
                        try:
                            branch_data = git_branch_facade.get_git_branch_by_id(git_branch_id)
                            if branch_data and 'git_branch' in branch_data:
                                project_id = branch_data['git_branch'].get('project_id')
                                logger.debug(f"Found project_id {project_id} for git_branch_id {git_branch_id}")
                            else:
                                logger.warning(f"Project not found for git_branch_id {git_branch_id}, using default")
                        except Exception:
                            logger.warning(f"Project not found for git_branch_id {git_branch_id}, using default")
                else:
                    logger.warning(f"Task {task_id} not found, using default project")
            except Exception as e:
                logger.warning(f"Failed to derive project context for task_id {task_id}: {e}")
                logger.debug(f"Using default project for subtask operations")
        
        return self._subtask_facade_factory.create_subtask_facade(project_id, user_id=validated_user_id)
    
    # Workflow hint enhancement methods
    
    def _enhance_with_workflow_hints(self, response: Dict[str, Any], action: str, 
                                    task_id: str, subtask_id: Optional[str] = None,
                                    subtasks: Optional[List[Dict[str, Any]]] = None) -> Dict[str, Any]:
        """Enhance response with workflow hints and guidance using factory"""
        
        # Build context for the workflow guidance
        context = {
            "task_id": task_id,
            "subtask_id": subtask_id
        }
        
        # Use the factory to enhance the response
        return self._workflow_guidance.enhance_response(response, action, context)
    
    def _enhance_response_with_workflow_guidance(self, response: Dict[str, Any], action: str, 
                                               task_id: str, subtask_id: Optional[str] = None) -> Dict[str, Any]:
        """Enhance response with workflow hints and guidance - compatibility method"""
        return self._enhance_with_workflow_hints(response, action, task_id, subtask_id)
    
    def _get_subtask_management_descriptions(self) -> Dict[str, Any]:
        """Get tool descriptions for subtask management."""
        all_descriptions = description_loader.get_all_descriptions()
        # Navigate to subtask descriptions
        return all_descriptions.get("subtask", {})
    
    def _validate_subtask_parameters(self, progress_percentage: Optional[int] = None,
                                   assignees: Optional[List[str]] = None,
                                   insights_found: Optional[List[str]] = None) -> Dict[str, Any]:
        """
        Validate subtask parameter formats with helpful error messages.
        
        NOTE: progress_percentage validation has been moved to manage_subtask method
        for better type coercion handling. This method now focuses on other parameters.
        """
        # Progress percentage validation is now handled in manage_subtask method
        # before calling this method, so we can assume it's already properly validated
        # This method now focuses on other parameter validations
        
        # Check assignees format (same as task controller)
        if assignees is not None:
            if not isinstance(assignees, list):
                return {
                    "success": False,
                    "error": f"Invalid assignees format. Expected: array of strings like [\"user1\", \"user2\"]. Got: {type(assignees).__name__}",
                    "error_code": "PARAMETER_FORMAT_ERROR",
                    "parameter": "assignees", 
                    "provided_value": str(assignees),
                    "expected_format": "Array of strings: [\"user1\", \"user2\"]",
                    "examples": [
                        "assignees=[\"developer1\", \"tester2\"]",
                        "assignees=[\"senior_developer\"]"
                    ],
                    "hint": "Use array of user identifiers or role names"
                }
            
            for i, assignee in enumerate(assignees):
                if not isinstance(assignee, str):
                    return {
                        "success": False,
                        "error": f"Invalid assignee at position {i}. Expected: string, got: {type(assignee).__name__}",
                        "error_code": "PARAMETER_TYPE_ERROR",
                        "parameter": f"assignees[{i}]",
                        "provided_value": str(assignee),
                        "expected_type": "string",
                        "hint": "All assignees must be strings"
                    }
        
        # Check insights_found format
        if insights_found is not None:
            if not isinstance(insights_found, list):
                return {
                    "success": False,
                    "error": f"Invalid insights_found format. Expected: array of strings like [\"insight1\", \"insight2\"]. Got: {type(insights_found).__name__}",
                    "error_code": "PARAMETER_FORMAT_ERROR",
                    "parameter": "insights_found",
                    "provided_value": str(insights_found),
                    "expected_format": "Array of strings: [\"insight1\", \"insight2\"]", 
                    "examples": [
                        "insights_found=[\"Found existing utility function\", \"API has rate limiting\"]",
                        "insights_found=[\"Performance bottleneck identified\"]"
                    ],
                    "hint": "Use array of insight strings describing discoveries during work"
                }
            
            for i, insight in enumerate(insights_found):
                if not isinstance(insight, str):
                    return {
                        "success": False,
                        "error": f"Invalid insight at position {i}. Expected: string, got: {type(insight).__name__}",
                        "error_code": "PARAMETER_TYPE_ERROR",
                        "parameter": f"insights_found[{i}]",
                        "provided_value": str(insight),
                        "expected_type": "string",
                        "hint": "All insights must be strings describing what was discovered"
                    }
        
        # All validation passed
        return {"valid": True}
    
    def _validate_completion_parameters(
        self,
        completion_quality: Optional[str] = None,
        verification_status: Optional[str] = None,
        deliverables: Optional[List[str]] = None,
        skills_learned: Optional[List[str]] = None,
        challenges_overcome: Optional[List[str]] = None,
        next_recommendations: Optional[List[str]] = None
    ) -> Dict[str, Any]:
        """Validate enhanced completion parameters."""
        valid_quality_levels = ["excellent", "good", "satisfactory", "needs_improvement"]
        valid_verification_statuses = ["verified", "pending_review", "needs_testing", "failed_verification"]
        
        # Validate completion quality
        if completion_quality and completion_quality not in valid_quality_levels:
            return {
                "success": False,
                "error": f"Invalid completion_quality: {completion_quality}. Must be one of: {', '.join(valid_quality_levels)}",
                "error_code": "PARAMETER_VALUE_ERROR",
                "parameter": "completion_quality",
                "provided_value": completion_quality,
                "valid_values": valid_quality_levels,
                "hint": "Use quality levels to assess completion: excellent (exceeds expectations), good (meets expectations), satisfactory (basic requirements), needs_improvement (requires rework)"
            }
        
        # Validate verification status
        if verification_status and verification_status not in valid_verification_statuses:
            return {
                "success": False,
                "error": f"Invalid verification_status: {verification_status}. Must be one of: {', '.join(valid_verification_statuses)}",
                "error_code": "PARAMETER_VALUE_ERROR",
                "parameter": "verification_status",
                "provided_value": verification_status,
                "valid_values": valid_verification_statuses,
                "hint": "Use verification status to track testing: verified (fully tested), pending_review (awaiting review), needs_testing (requires testing), failed_verification (tests failed)"
            }
        
        # Validate list parameters
        for param_name, param_value in [
            ("deliverables", deliverables),
            ("skills_learned", skills_learned),
            ("challenges_overcome", challenges_overcome),
            ("next_recommendations", next_recommendations)
        ]:
            if param_value is not None:
                if not isinstance(param_value, list):
                    return {
                        "success": False,
                        "error": f"Invalid {param_name} format. Expected: array of strings like [\"item1\", \"item2\"]. Got: {type(param_value).__name__}",
                        "error_code": "PARAMETER_FORMAT_ERROR",
                        "parameter": param_name,
                        "provided_value": str(param_value),
                        "expected_format": "Array of strings: [\"item1\", \"item2\"]",
                        "hint": f"Use array of strings for {param_name}"
                    }
                
                for i, item in enumerate(param_value):
                    if not isinstance(item, str):
                        return {
                            "success": False,
                            "error": f"Invalid {param_name} item at position {i}. Expected: string, got: {type(item).__name__}",
                            "error_code": "PARAMETER_TYPE_ERROR",
                            "parameter": f"{param_name}[{i}]",
                            "provided_value": str(item),
                            "expected_type": "string",
                            "hint": f"All {param_name} items must be strings"
                        }
        
        return {"valid": True}
    
    def _standardize_response(
        self, 
        result: Dict[str, Any], 
        operation: str,
        workflow_guidance: Optional[Dict[str, Any]] = None,
        metadata: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        Convert legacy response format to standardized format.
        
        Args:
            result: The original response from facade
            operation: The operation performed (e.g., "create_subtask", "update_subtask")
            workflow_guidance: Workflow guidance to include
            metadata: Additional metadata
            
        Returns:
            Standardized response following the new format
        """
        # Check if this is already a standardized response
        if "operation_id" in result and "confirmation" in result:
            return result
            
        # Handle error responses
        if not result.get("success", False):
            error_code = result.get("error_code", ErrorCodes.OPERATION_FAILED)
            
            # Check for validation errors
            if "field" in result or "parameter" in result:
                return StandardResponseFormatter.create_validation_error_response(
                    operation=operation,
                    field=result.get("field") or result.get("parameter", "unknown"),
                    expected=result.get("expected", "valid value"),
                    hint=result.get("hint")
                )
            
            # Standard error response
            return StandardResponseFormatter.create_error_response(
                operation=operation,
                error=result.get("error", "Operation failed"),
                error_code=error_code,
                metadata=metadata
            )
        
        # Handle success responses
        data = self._extract_data_from_result(result)
        
        # Check for partial failures (e.g., context update failures)
        partial_failures = []
        if "context_update_error" in result:
            partial_failures.append({
                "operation": "context_update",
                "error": result["context_update_error"],
                "impact": "Parent task context may be out of sync"
            })
        
        # Create standardized response
        if partial_failures:
            return StandardResponseFormatter.create_partial_success_response(
                operation=operation,
                data=data,
                partial_failures=partial_failures,
                metadata=metadata,
                workflow_guidance=workflow_guidance or result.get("workflow_guidance")
            )
        else:
            return StandardResponseFormatter.create_success_response(
                operation=operation,
                data=data,
                metadata=metadata,
                workflow_guidance=workflow_guidance or result.get("workflow_guidance")
            )
    
    def _extract_data_from_result(self, result: Dict[str, Any]) -> Dict[str, Any]:
        """Extract data payload from result for subtask operations"""
        data = {}
        
        # Subtask-specific data extraction
        if "subtask" in result:
            data["subtask"] = result["subtask"]
        if "subtasks" in result:
            data["subtasks"] = result["subtasks"]
        if "parent_progress" in result:
            data["parent_progress"] = result["parent_progress"]
        if "context_updated" in result:
            data["context_updated"] = result["context_updated"]
        if "progress_summary" in result:
            data["progress_summary"] = result["progress_summary"]
        
        # If no standard keys found, include all non-metadata fields
        if not data:
            data = {k: v for k, v in result.items() 
                   if k not in ["success", "error", "workflow_guidance", "context_update_error"]}
        
        return data
    
    def _create_standardized_error(
        self,
        operation: str,
        field: str,
        expected: str,
        hint: Optional[str] = None
    ) -> Dict[str, Any]:
        """Create a standardized validation error response."""
        return StandardResponseFormatter.create_validation_error_response(
            operation=operation,
            field=field,
            expected=expected,
            hint=hint
        )
    
    def _is_valid_uuid(self, uuid_string: str) -> bool:
        """
        Validate if a string is a valid UUID format.
        
        Accepts both formats:
        - Standard UUID with hyphens: xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx
        - Hex format without hyphens: xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx (32 chars)
        
        Args:
            uuid_string: String to validate
            
        Returns:
            True if valid UUID format, False otherwise
        """
        if not uuid_string or not isinstance(uuid_string, str):
            return False
            
        uuid_string = uuid_string.strip()
        
        # Try to parse as UUID - this handles both formats
        try:
            uuid.UUID(uuid_string)
            return True
        except (ValueError, TypeError):
            # Check if it's a 32-character hex string (UUID without hyphens)
            if len(uuid_string) == 32 and re.match(r'^[0-9a-fA-F]{32}$', uuid_string):
                return True
            return False
    
    def _parse_array_parameter(self, value: Union[List[str], str, None]) -> Optional[List[str]]:
        """
        Parse array parameter that can be provided in multiple formats.
        
        Args:
            value: The parameter value to parse
            
        Returns:
            Optional[List[str]]: Parsed array or None
        """
        if value is None:
            return None
        
        if isinstance(value, list):
            return value
        
        if isinstance(value, str):
            value = value.strip()
            if not value:  # Empty string
                return None
            
            # Try to parse as JSON first
            try:
                import json
                parsed = json.loads(value)
                if isinstance(parsed, list):
                    return parsed
            except (json.JSONDecodeError, ValueError):
                pass
            
            # Parse as comma-separated values
            if ',' in value:
                return [item.strip() for item in value.split(',') if item.strip()]
            else:
                # Single string item
                return [value]
        
        # For other types, return None
        return None