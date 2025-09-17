"""
Subtask MCP Controller - Refactored Modular Implementation

This is the main entry point for the subtask MCP controller, now refactored into a modular 
architecture using factory pattern to maintain separation of concerns and automatic progress tracking.
"""

import logging
import asyncio
import uuid
from typing import Dict, Any, Optional, List, Annotated, Union
from pydantic import Field
from datetime import datetime, timezone

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from fastmcp.server.server import FastMCP

# Import modular components
from .factories.operation_factory import SubtaskOperationFactory

# Import the description directly from the local file
from .manage_subtask_description import get_manage_subtask_description, get_manage_subtask_parameters
from ...utils.response_formatter import StandardResponseFormatter, ResponseStatus, ErrorCodes
from ...utils.parameter_validation_fix import coerce_parameter_types

from ....application.facades.subtask_application_facade import SubtaskApplicationFacade
from ....application.services.facade_service import FacadeService
# Import from the correct subtask.py file, not the subtask/ directory
from ..workflow_guidance import subtask as subtask_module
SubtaskWorkflowFactory = subtask_module.SubtaskWorkflowFactory
from ..auth_helper import get_authenticated_user_id, log_authentication_details
from ....domain.constants import validate_user_id
from ....domain.exceptions.authentication_exceptions import UserAuthenticationRequiredError
from .....config.auth_config import AuthConfig

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
    Refactored Subtask MCP Controller with modular architecture.
    
    This controller now uses factory pattern to delegate operations to specialized handlers,
    maintaining the same interface while improving maintainability and separation of concerns.
    Includes automatic progress tracking and parent task context updates.
    """

    def __init__(self, facade_service_or_factory=None, 
                 task_facade=None, context_facade=None, task_repository_factory=None):
        """Initialize the modular subtask MCP controller.
        
        Args:
            facade_service_or_factory: Either a FacadeService (new interface) or SubtaskFacadeFactory (legacy interface)
        """
        
        # Handle both FacadeService and legacy factory interfaces for backward compatibility
        if hasattr(facade_service_or_factory, 'create_subtask_facade'):
            # Legacy interface - store the factory and use FacadeService internally
            self._subtask_facade_factory = facade_service_or_factory
            self._facade_service = FacadeService.get_instance()
        else:
            # New interface - use FacadeService directly
            self._facade_service = facade_service_or_factory or FacadeService.get_instance()
            self._subtask_facade_factory = None  # Not using legacy factory
        
        self._task_application_facade = task_facade
        self._context_facade = context_facade
        
        # Initialize response formatter
        self._response_formatter = StandardResponseFormatter()
        
        # Initialize modular operation factory
        self._operation_factory = SubtaskOperationFactory(
            response_formatter=self._response_formatter,
            context_facade=context_facade,
            task_facade=task_facade
        )
        
        # Initialize workflow guidance
        self._workflow_guidance = SubtaskWorkflowFactory.create()
        
        logger.info("SubtaskMCPController initialized with modular architecture and progress tracking")

    def _run_async(self, coro):
        """Run coroutine in async context with proper event loop management."""
        try:
            loop = asyncio.get_event_loop()
            if loop.is_running():
                # If we're already in an event loop, run in a new thread with context
                async def _wrapper():
                    return await coro
                return self._run_async_with_context(_wrapper)
            else:
                return loop.run_until_complete(coro)
        except RuntimeError:
            # No event loop, create one
            return asyncio.run(coro)

    def register_tools(self, mcp: "FastMCP"):
        """Register MCP tools with the server."""
        
        # Get centralized parameter definitions
        params = get_manage_subtask_parameters()
        
        @mcp.tool(description=get_manage_subtask_description())
        def manage_subtask(
            action: Annotated[str, Field(description=params["action"]["description"])],
            task_id: Annotated[str, Field(description=params["task_id"]["description"])] = None,
            subtask_id: Annotated[str, Field(description=params["subtask_id"]["description"])] = None,
            title: Annotated[str, Field(description=params["title"]["description"])] = None,
            description: Annotated[str, Field(description=params["description"]["description"])] = None,
            status: Annotated[str, Field(description=params["status"]["description"])] = None,
            priority: Annotated[str, Field(description=params["priority"]["description"])] = None,
            assignees: Annotated[str, Field(description=params["assignees"]["description"])] = None,
            progress_percentage: Annotated[int, Field(description=params["progress_percentage"]["description"])] = None,
            progress_notes: Annotated[str, Field(description=params["progress_notes"]["description"])] = None,
            completion_summary: Annotated[str, Field(description=params["completion_summary"]["description"])] = None,
            testing_notes: Annotated[str, Field(description=params["testing_notes"]["description"])] = None,
            insights_found: Annotated[str, Field(description=params["insights_found"]["description"])] = None,
            challenges_overcome: Annotated[str, Field(description=params["challenges_overcome"]["description"])] = None,
            skills_learned: Annotated[str, Field(description=params["skills_learned"]["description"])] = None,
            next_recommendations: Annotated[str, Field(description=params["next_recommendations"]["description"])] = None,
            deliverables: Annotated[str, Field(description=params["deliverables"]["description"])] = None,
            completion_quality: Annotated[str, Field(description=params["completion_quality"]["description"])] = None,
            impact_on_parent: Annotated[str, Field(description=params["impact_on_parent"]["description"])] = None,
            blockers: Annotated[str, Field(description=params["blockers"]["description"])] = None,
            user_id: Annotated[str, Field(description=params["user_id"]["description"])] = None
        ) -> Dict[str, Any]:
            """Main subtask management function with two-stage validation pattern:
            - Schema level: Only 'action' is required (MCP compatibility)
            - Business logic level: Action-specific validation in controller
            """
            return self.manage_subtask(
                action=action, task_id=task_id, subtask_id=subtask_id,
                title=title, description=description, status=status, 
                priority=priority, assignees=assignees, 
                progress_percentage=progress_percentage, progress_notes=progress_notes,
                completion_summary=completion_summary, testing_notes=testing_notes,
                insights_found=insights_found, challenges_overcome=challenges_overcome,
                skills_learned=skills_learned, next_recommendations=next_recommendations,
                deliverables=deliverables, completion_quality=completion_quality,
                impact_on_parent=impact_on_parent, blockers=blockers, user_id=user_id
            )

    def manage_subtask(self, action: str, task_id: str, user_id: Optional[str] = None, **kwargs) -> Dict[str, Any]:
        """Main entry point for subtask management operations."""
        
        try:
            # Authentication
            user_id = get_authenticated_user_id(
                provided_user_id=user_id,
                operation_name=f"manage_subtask:{action}"
            )
            log_authentication_details(user_id, f"manage_subtask:{action}")
            
            # Check if using legacy facade factory interface (backward compatibility)
            if self._subtask_facade_factory:
                # Legacy path - call facade methods directly (for tests)
                facade = self._subtask_facade_factory.create_subtask_facade()
                
                # Call appropriate facade method based on action
                if action == "create":
                    result = facade.create_subtask(**kwargs)
                elif action == "update":
                    result = facade.update_subtask(**kwargs)
                elif action == "delete":
                    result = facade.delete_subtask(**kwargs)
                elif action == "get":
                    result = facade.get_subtask(**kwargs)
                elif action == "list":
                    result = facade.list_subtasks(**kwargs)
                elif action == "complete":
                    result = facade.complete_subtask(**kwargs)
                else:
                    return self._response_formatter.create_error_response(
                        operation=action,
                        error=f"Unknown action: {action}",
                        error_code=ErrorCodes.VALIDATION_ERROR
                    )
            else:
                # New path - use operation factory
                facade = self._get_facade_for_request(task_id, user_id)
                
                # Validate basic requirements
                if not task_id:
                    return self._response_formatter.create_error_response(
                        operation=action,
                        error="Missing required field: task_id. Expected: A valid task_id string",
                        error_code=ErrorCodes.VALIDATION_ERROR,
                        metadata={"field": "task_id", "hint": "Include 'task_id' in your request"}
                    )
                
                # Coerce parameter types before processing
                coerced_kwargs = coerce_parameter_types(kwargs)
                
                # Execute operation using factory
                result = self._operation_factory.handle_operation(
                    operation=action,
                    facade=facade,
                    task_id=task_id,
                    user_id=user_id,
                    **coerced_kwargs
                )
            
            # Apply workflow guidance enhancement
            if result.get("success"):
                result = self._enhance_response_with_workflow_guidance(
                    result, action, task_id
                )
            
            return result
            
        except Exception as e:
            logger.error(f"Error in manage_subtask {action}: {str(e)}")
            return self._response_formatter.create_error_response(
                operation=action,
                error=f"Subtask operation failed: {str(e)}",
                error_code=ErrorCodes.OPERATION_FAILED,
                metadata={"task_id": task_id}
            )

    def _get_facade_for_request(self, task_id: str, user_id: str) -> SubtaskApplicationFacade:
        """Get appropriate facade for the request."""
        
        # Check if using legacy factory interface (for backward compatibility)
        if self._subtask_facade_factory:
            # Legacy interface - use the factory directly (for tests)
            return self._subtask_facade_factory.create_subtask_facade()
        
        if not self._facade_service:
            raise ValueError("FacadeService is required but not provided")
        
        # Get facade from service with user context
        # Note: FacadeService.get_subtask_facade uses git_branch_id param, not task_id
        return self._facade_service.get_subtask_facade(user_id=user_id, git_branch_id=task_id)

    def _enhance_response_with_workflow_guidance(self, response: Dict[str, Any], 
                                               action: str, task_id: str) -> Dict[str, Any]:
        """Enhance response with workflow guidance using the workflow guidance system."""
        
        try:
            if self._workflow_guidance:
                # Enhance response with workflow guidance
                enhanced = self._workflow_guidance.enhance_response(
                    response=response,
                    action=action,
                    context={
                        "task_id": task_id
                    }
                )
                
                # Update response with enhanced content
                if enhanced and isinstance(enhanced, dict):
                    response.update(enhanced)
                    
        except Exception as e:
            logger.error(f"Error enhancing response with workflow guidance: {e}")
            # Don't fail the operation if guidance enhancement fails
        
        return response

    # ===============================================
    # BACKWARD COMPATIBILITY BRIDGE METHODS
    # Added for Round 7 test compatibility - same pattern as TaskMCPController
    # ===============================================

    def create_subtask(self, facade: Any, **kwargs) -> Dict[str, Any]:
        """Create subtask - backward compatibility method for tests."""
        return self._operation_factory.handle_operation(
            operation="create",
            facade=facade,
            **kwargs
        )

    def update_subtask(self, facade: Any, **kwargs) -> Dict[str, Any]:
        """Update subtask - backward compatibility method for tests."""
        return self._operation_factory.handle_operation(
            operation="update", 
            facade=facade,
            **kwargs
        )

    def delete_subtask(self, facade: Any, **kwargs) -> Dict[str, Any]:
        """Delete subtask - backward compatibility method for tests."""
        return self._operation_factory.handle_operation(
            operation="delete",
            facade=facade,
            **kwargs
        )

    def get_subtask(self, facade: Any, **kwargs) -> Dict[str, Any]:
        """Get subtask - backward compatibility method for tests."""
        return self._operation_factory.handle_operation(
            operation="get",
            facade=facade,
            **kwargs
        )

    def list_subtasks(self, facade: Any, **kwargs) -> Dict[str, Any]:
        """List subtasks - backward compatibility method for tests."""
        return self._operation_factory.handle_operation(
            operation="list",
            facade=facade,
            **kwargs
        )

    def complete_subtask(self, facade: Any, **kwargs) -> Dict[str, Any]:
        """Complete subtask - backward compatibility method for tests."""
        return self._operation_factory.handle_operation(
            operation="complete",
            facade=facade,
            **kwargs
        )