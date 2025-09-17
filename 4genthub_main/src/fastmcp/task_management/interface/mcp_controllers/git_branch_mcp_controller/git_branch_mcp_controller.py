"""
Git Branch MCP Controller - Refactored Modular Implementation

This is the main entry point for the git branch MCP controller, now refactored into a modular 
architecture using factory pattern to maintain separation of concerns and workflow guidance.
"""

import logging
from typing import Dict, Any, Optional, Annotated
from pydantic import Field
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from fastmcp.server.server import FastMCP

# Import modular components
from .factories.operation_factory import GitBranchOperationFactory

# Import existing dependencies
# Import the description directly from the local file
from .manage_git_branch_description import get_manage_git_branch_description, get_manage_git_branch_parameters
from ...utils.response_formatter import StandardResponseFormatter, ResponseStatus, ErrorCodes
from ....application.facades.git_branch_application_facade import GitBranchApplicationFacade
from ....application.services.facade_service import FacadeService
from ..workflow_guidance.git_branch.git_branch_workflow_factory import GitBranchWorkflowFactory
from ..auth_helper import get_authenticated_user_id, log_authentication_details

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


class GitBranchMCPController(ContextPropagationMixin):
    """
    Refactored Git Branch MCP Controller with modular architecture.
    
    This controller now uses factory pattern to delegate operations to specialized handlers,
    maintaining the same interface while improving maintainability and separation of concerns.
    """

    def __init__(self, facade_service: Optional[FacadeService] = None):
        """Initialize the modular git branch MCP controller."""
        
        # Store facade factory
        self._facade_service = facade_service or FacadeService.get_instance()
        
        # Initialize response formatter
        self._response_formatter = StandardResponseFormatter()
        
        # Initialize modular operation factory
        self._operation_factory = GitBranchOperationFactory(
            response_formatter=self._response_formatter
        )
        
        # Initialize workflow guidance
        self._workflow_guidance = GitBranchWorkflowFactory.create()
        
        logger.info("GitBranchMCPController initialized with modular architecture")

    def register_tools(self, mcp: "FastMCP"):
        """Register MCP tools with the server."""
        
        # Get centralized parameter definitions
        params = get_manage_git_branch_parameters()
        
        @mcp.tool(description=get_manage_git_branch_description())
        def manage_git_branch(
            action: Annotated[str, Field(description=params["action"]["description"])],
            project_id: Annotated[str, Field(description=params["project_id"]["description"])] = None,
            git_branch_id: Annotated[str, Field(description=params["git_branch_id"]["description"])] = None,
            git_branch_name: Annotated[str, Field(description=params["git_branch_name"]["description"])] = None,
            git_branch_description: Annotated[str, Field(description=params["git_branch_description"]["description"])] = None,
            agent_id: Annotated[str, Field(description=params["agent_id"]["description"])] = None,
            user_id: Annotated[str, Field(description=params["user_id"]["description"])] = None
        ) -> Dict[str, Any]:
            """Main git branch management function with two-stage validation pattern:
            - Schema level: Only 'action' is required (MCP compatibility)
            - Business logic level: Action-specific validation in controller
            """
            return self.manage_git_branch(
                action=action, project_id=project_id, git_branch_id=git_branch_id,
                git_branch_name=git_branch_name, git_branch_description=git_branch_description,
                agent_id=agent_id, user_id=user_id
            )

    def manage_git_branch(self, action: str, user_id: Optional[str] = None, **kwargs) -> Dict[str, Any]:
        """Main entry point for git branch management operations."""
        
        try:
            # Authentication
            user_id = get_authenticated_user_id(
                provided_user_id=user_id,
                operation_name=f"manage_git_branch:{action}"
            )
            log_authentication_details(user_id, f"manage_git_branch:{action}")
            
            # Validate required project_id
            project_id = kwargs.get('project_id')
            if not project_id:
                return self._response_formatter.create_error_response(
                    operation=action,
                    error="Missing required field: project_id. Expected: A valid project_id string",
                    error_code=ErrorCodes.VALIDATION_ERROR,
                    metadata={"field": "project_id", "hint": "Include 'project_id' in your request"}
                )
            
            # Get facade for request
            facade = self._get_facade_for_request(project_id, user_id)
            
            # Execute operation using factory
            result = self._operation_factory.handle_operation(
                operation=action,
                facade=facade,
                **kwargs
            )
            
            # Apply workflow guidance enhancement
            if result.get("success"):
                result = self._enhance_response_with_workflow_guidance(
                    result, action, project_id
                )
            
            return result
            
        except Exception as e:
            logger.error(f"Error in manage_git_branch {action}: {str(e)}")
            return self._response_formatter.create_error_response(
                operation=action,
                error=f"Git branch operation failed: {str(e)}",
                error_code=ErrorCodes.OPERATION_FAILED,
                metadata={"project_id": kwargs.get('project_id')}
            )

    def _get_facade_for_request(self, project_id: str, user_id: str = None) -> GitBranchApplicationFacade:
        """Get appropriate facade for the request."""
        
        if not self._facade_service:
            raise ValueError("FacadeService is required but not provided")
        
        # Get facade from service with user context
        return self._facade_service.get_branch_facade(project_id=project_id, user_id=user_id)

    def _enhance_response_with_workflow_guidance(self, response: Dict[str, Any], 
                                               action: str, project_id: str) -> Dict[str, Any]:
        """Enhance response with workflow guidance using the workflow guidance system."""
        
        try:
            if self._workflow_guidance:
                # Generate workflow guidance
                guidance = self._workflow_guidance.generate_guidance(
                    action=action,
                    context={
                        "project_id": project_id,
                        "response": response
                    }
                )
                
                if guidance:
                    response["workflow_guidance"] = guidance
                    
        except Exception as e:
            logger.error(f"Error enhancing response with workflow guidance: {e}")
            # Don't fail the operation if guidance enhancement fails
        
        return response