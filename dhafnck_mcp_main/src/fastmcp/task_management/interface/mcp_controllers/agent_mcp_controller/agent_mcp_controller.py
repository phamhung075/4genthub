"""Agent MCP Controller - Modular Implementation

This is the modular implementation of the Agent MCP Controller, decomposed from
the original monolithic 402-line controller into specialized components.

The controller now uses:
- Factory Pattern for operation coordination
- Specialized Handlers for different operation types (CRUD, Assignment, Rebalancing)
- Standardized Response Formatting
- Authentication handling preservation
- Workflow guidance system integration
"""

import logging
from typing import Dict, Any, Optional, Annotated
from pydantic import Field  # type: ignore
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from fastmcp.server.server import FastMCP

# Import the description directly from the local file
from .manage_agent_description import get_manage_agent_description, get_manage_agent_parameters
from ....application.services.facade_service import FacadeService
from ....application.facades.agent_application_facade import AgentApplicationFacade
from ..workflow_guidance.agent.agent_workflow_factory import AgentWorkflowFactory
from ....domain.constants import validate_user_id
from ....domain.exceptions.authentication_exceptions import UserAuthenticationRequiredError
from .....config.auth_config import AuthConfig
from ...utils.response_formatter import StandardResponseFormatter

# Operation coordination factory
from .factories.operation_factory import AgentOperationFactory

logger = logging.getLogger(__name__)

# Import user context utilities - REQUIRED for authentication
try:
    from fastmcp.auth.middleware.request_context_middleware import get_current_user_id
except ImportError:
    # Try alternative import path for RequestContextMiddleware
    try:
        from ..auth_helper import get_authenticated_user_id as get_current_user_id
    except ImportError:
        # Authentication is required - no fallbacks allowed
        def get_current_user_id():
            raise UserAuthenticationRequiredError("User context middleware not available")


class AgentMCPController:
    """
    MCP controller for agent management operations - Modular Implementation.
    
    Handles only MCP protocol concerns and delegates business operations
    to specialized handlers through the AgentOperationFactory following 
    proper DDD layer separation.
    
    This modular implementation provides:
    - Factory-based operation coordination
    - Specialized handlers for different operation types
    - Standardized response formatting  
    - Authentication handling preservation
    - Workflow guidance system integration
    """
    
    def __init__(self, facade_service: Optional[FacadeService] = None):
        """
        Initialize controller with facade service and modular components.
        
        Args:
            facade_service: Service for obtaining application facades (optional)
        """
        self._facade_service = facade_service or FacadeService.get_instance()
        self._workflow_guidance = AgentWorkflowFactory.create()
        
        # Initialize modular components
        self._response_formatter = StandardResponseFormatter()
        self._operation_factory = AgentOperationFactory(self._response_formatter)
        
        logger.info("AgentMCPController initialized with modular architecture (factory pattern and workflow guidance)")

    def register_tools(self, mcp: "FastMCP"):
        """Register agent management MCP tools with the FastMCP server"""
        # Get centralized parameter definitions
        params = get_manage_agent_parameters()

        @mcp.tool(name="manage_agent", description=get_manage_agent_description())
        def manage_agent(
            action: Annotated[str, Field(description=params["action"]["description"])],
            project_id: Annotated[Optional[str], Field(description=params["project_id"]["description"])] = None,
            agent_id: Annotated[str, Field(description=params["agent_id"]["description"])] = None,
            name: Annotated[str, Field(description=params["name"]["description"])] = None,
            call_agent: Annotated[str, Field(description=params["call_agent"]["description"])] = None,
            git_branch_id: Annotated[str, Field(description=params["git_branch_id"]["description"])] = None,
            user_id: Annotated[str, Field(description=params["user_id"]["description"])] = None
        ) -> Dict[str, Any]:
            """Manage agent operations including register, assign, update, and unregister.
            
            Two-stage validation pattern:
            - Schema level: Only 'action' is required (MCP compatibility)
            - Business logic level: Action-specific validation in controller
            """
            return self.manage_agent(
                action=action,
                project_id=project_id,
                agent_id=agent_id,
                name=name,
                call_agent=call_agent,
                git_branch_id=git_branch_id,
                user_id=user_id
            )
    
    def _get_facade_for_request(self, project_id: str, user_id: Optional[str] = None) -> AgentApplicationFacade:
        """
        Get an AgentApplicationFacade with the appropriate context.
        
        Args:
            project_id: Project identifier
            user_id: Optional user identifier for authentication
            
        Returns:
            AgentApplicationFacade instance
        """
        # Use provided user_id or fall back to authentication
        if user_id:
            validated_user_id = validate_user_id(user_id, "Agent facade creation")
        else:
            # Get current user context from JWT token or handle authentication
            context_user_obj = get_current_user_id()
            logger.info(f"🎯 Agent Controller: get_current_user_id() returned: {context_user_obj} (type: {type(context_user_obj)})")
            
            # Extract user_id string from the context object (handles BackwardCompatUserContext objects)
            current_user_id = None
            if context_user_obj:
                if isinstance(context_user_obj, str):
                    # Already a string
                    current_user_id = context_user_obj
                elif hasattr(context_user_obj, 'user_id'):
                    # Extract user_id attribute from BackwardCompatUserContext
                    current_user_id = context_user_obj.user_id
                    logger.info(f"🔧 Agent Controller: Extracted user_id from context object: {current_user_id}")
                else:
                    # Fallback: convert to string
                    current_user_id = str(context_user_obj) if context_user_obj else None
                    logger.warning(f"⚠️ Agent Controller: Fallback string conversion: {current_user_id}")
            
            # Let validate_user_id handle MVP mode fallbacks
            validated_user_id = validate_user_id(current_user_id, "Agent facade creation")
        
        # Get facade from service for proper data isolation
        return self._facade_service.get_agent_facade(project_id=project_id, user_id=validated_user_id)
    
    def manage_agent(
        self,
        action: str,
        project_id: Optional[str] = None,
        agent_id: Optional[str] = None,
        name: Optional[str] = None,
        call_agent: Optional[str] = None,
        git_branch_id: Optional[str] = None,
        user_id: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Unified agent management method that handles all agent operations.
        Routes to appropriate handlers based on action through the operation factory.
        """
        logger.info(f"Managing agent with action: {action} for project: {project_id}")
        
        # Validate project_id is provided for all actions
        if not project_id:
            return {
                "success": False,
                "error": "project_id is required for all agent operations",
                "details": "Please provide a valid project identifier"
            }
        
        try:
            # Get facade for this request
            facade = self._get_facade_for_request(project_id, user_id)
            
            # Basic field validation before routing
            validation_result = self._validate_required_fields(action, agent_id, name, git_branch_id)
            if not validation_result["valid"]:
                return validation_result["response"]
            
            # Route operation through the factory
            response = self._operation_factory.handle_operation(
                operation=action,
                facade=facade,
                project_id=project_id,
                agent_id=agent_id,
                name=name,
                call_agent=call_agent,
                git_branch_id=git_branch_id,
                user_id=user_id
            )
            
            # Enhance response with workflow guidance if successful
            return self._enhance_response_with_workflow_guidance(response, action, project_id, agent_id)
            
        except Exception as e:
            logger.error(f"Error in agent management operation '{action}': {e}")
            return self._response_formatter.create_error_response(
                operation=action,
                error=f"Operation failed: {str(e)}",
                error_code="INTERNAL_ERROR",
                metadata={"action": action, "project_id": project_id}
            )

    def _validate_required_fields(self, action: str, agent_id: Optional[str], 
                                 name: Optional[str], git_branch_id: Optional[str]) -> Dict[str, Any]:
        """Validate required fields for different operations."""
        
        # Field requirements by action
        if action == "register" and not name:
            return {
                "valid": False,
                "response": self._create_missing_field_error("name", action)
            }
        
        if action in ["get", "update", "unregister", "assign", "unassign"] and not agent_id:
            return {
                "valid": False,
                "response": self._create_missing_field_error("agent_id", action)
            }
        
        if action in ["assign", "unassign"] and not git_branch_id:
            return {
                "valid": False,
                "response": self._create_missing_field_error("git_branch_id", action)
            }
        
        return {"valid": True}

    def _get_agent_management_descriptions(self) -> Dict[str, Any]:
        """
        Flatten agent descriptions for robust access, similar to other controllers.
        """
        all_desc = {}
        flat = {}
        # Look for 'manage_agent' in any subdict
        for sub in all_desc.values():
            if isinstance(sub, dict) and "manage_agent" in sub:
                flat["manage_agent"] = sub["manage_agent"]
        return flat
    
    def _create_missing_field_error(self, field: str, action: str) -> Dict[str, Any]:
        """Create standardized missing field error response."""
        return {
            "success": False,
            "error": f"Missing required field: {field}",
            "error_code": "MISSING_FIELD",
            "field": field,
            "action": action,
            "expected": f"A valid {field} value",
            "hint": f"Include '{field}' in your request for action '{action}'"
        }
    
    def _enhance_response_with_workflow_guidance(self, response: Dict[str, Any], action: str, 
                                               project_id: Optional[str] = None,
                                               agent_id: Optional[str] = None) -> Dict[str, Any]:
        """
        Enhance response with workflow guidance if operation was successful.
        
        Args:
            response: The original response
            action: The action performed
            project_id: Project ID if available
            agent_id: Agent ID if available
            
        Returns:
            Enhanced response with workflow guidance
        """
        if response.get("success", False):
            # Build context for workflow guidance
            guidance_context = {}
            if project_id:
                guidance_context["project_id"] = project_id
            if agent_id:
                guidance_context["agent_id"] = agent_id
            
            # Extract created agent ID from response if available
            if action == "register" and response.get("agent"):
                guidance_context["agent_id"] = response["agent"].get("id")
            
            # Generate and add workflow guidance
            workflow_guidance = self._workflow_guidance.generate_guidance(action, guidance_context)
            response["workflow_guidance"] = workflow_guidance
            
        return response