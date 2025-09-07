"""Agent MCP Controller

This controller handles agent management operations following DDD principles.
It delegates business logic to the AgentApplicationFacade and handles MCP-specific concerns.
Documentation is loaded from external files for maintainability.
"""

import logging
from typing import Dict, Any, Optional, Annotated
from pydantic import Field  # type: ignore
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from fastmcp.server.server import FastMCP

from .desc import description_loader
from ...application.factories.agent_facade_factory import AgentFacadeFactory
from ...application.facades.agent_application_facade import AgentApplicationFacade
from .workflow_guidance.agent.agent_workflow_factory import AgentWorkflowFactory
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
except ImportError:
    # Try alternative import path for RequestContextMiddleware
    try:
        from .auth_helper import get_authenticated_user_id as get_current_user_id
    except ImportError:
        # Authentication is required - no fallbacks allowed
        def get_current_user_id():
            raise UserAuthenticationRequiredError("User context middleware not available")


class AgentMCPController:
    """
    MCP controller for agent management operations.
    Handles only MCP protocol concerns and delegates business operations
    to the AgentApplicationFacade following proper DDD layer separation.
    """
    
    def __init__(self, agent_facade_factory: AgentFacadeFactory):
        """
        Initialize controller with agent facade factory.
        
        Args:
            agent_facade_factory: Factory for creating agent application facades
        """
        self._agent_facade_factory = agent_facade_factory
        self._workflow_guidance = AgentWorkflowFactory.create()
        logger.info("AgentMCPController initialized with factory pattern and workflow guidance")

    def register_tools(self, mcp: "FastMCP"):
        """Register agent management MCP tools with the FastMCP server"""
        # Load descriptions from external files
        descriptions = self._get_agent_management_descriptions()
        manage_agent_desc = descriptions.get("manage_agent", {})

        @mcp.tool(name="manage_agent", description=manage_agent_desc["description"])
        def manage_agent(
            action: Annotated[str, Field(description=manage_agent_desc["parameters"].get("action", "Agent management action"))],
            project_id: Annotated[str, Field(description=manage_agent_desc["parameters"].get("project_id", "Project identifier"))] = "default_project",
            agent_id: Annotated[Optional[str], Field(description=manage_agent_desc["parameters"].get("agent_id", "Agent identifier"))] = None,
            name: Annotated[Optional[str], Field(description=manage_agent_desc["parameters"].get("name", "Agent name"))] = None,
            call_agent: Annotated[Optional[str], Field(description=manage_agent_desc["parameters"].get("call_agent", "Call agent string/config"))] = None,
            git_branch_id: Annotated[Optional[str], Field(description=manage_agent_desc["parameters"].get("git_branch_id", "Task tree identifier"))] = None,
            user_id: Annotated[Optional[str], Field(description="User identifier for authentication and audit trails")] = None
        ) -> Dict[str, Any]:
            """Manage agent operations including register, assign, update, and unregister."""
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
            
            if current_user_id:
                validated_user_id = validate_user_id(current_user_id, "Agent facade creation")
            else:
                # NO FALLBACKS ALLOWED - user authentication is required
                raise UserAuthenticationRequiredError("Agent facade creation")
        
        # Pass user_id to facade factory for proper data isolation
        return self._agent_facade_factory.create_agent_facade(project_id=project_id, user_id=validated_user_id)
    
    def manage_agent(
        self,
        action: str,
        project_id: str = "default_project",
        agent_id: Optional[str] = None,
        name: Optional[str] = None,
        call_agent: Optional[str] = None,
        git_branch_id: Optional[str] = None,
        user_id: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Unified agent management method that handles all agent operations.
        Routes to appropriate handlers based on action.
        """
        logger.info(f"Managing agent with action: {action} for project: {project_id}")
        
        # Route to appropriate handler based on action
        if action in ["register", "get", "list", "update", "unregister"]:
            return self.handle_crud_operations(
                action, project_id, agent_id, name, call_agent, user_id
            )
        elif action in ["assign", "unassign"]:
            return self.handle_assignment_operations(
                action, project_id, agent_id, git_branch_id, user_id
            )
        elif action == "rebalance":
            return self.handle_rebalance_operation(project_id, user_id)
        else:
            return {
                "success": False,
                "error": f"Unknown action: {action}",
                "error_code": "UNKNOWN_ACTION",
                "valid_actions": [
                    "register", "assign", "get", "list", "update",
                    "unassign", "unregister", "rebalance"
                ],
                "hint": "Check the action parameter for typos"
            }
    
    def handle_crud_operations(
        self,
        action: str,
        project_id: str,
        agent_id: Optional[str] = None,
        name: Optional[str] = None,
        call_agent: Optional[str] = None,
        user_id: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Handle core CRUD operations by converting MCP parameters 
        and delegating to the application facade.
        """
        try:
            # Get facade for this request
            facade = self._get_facade_for_request(project_id, user_id)
            
            if action == "register":
                if not name:
                    return self._create_missing_field_error("name", "register")
                
                # Auto-generate agent_id if not provided
                if not agent_id:
                    import uuid
                    agent_id = str(uuid.uuid4())
                
                return self._handle_register_agent(facade, project_id, agent_id, name, call_agent)
                
            elif action == "get":
                if not agent_id:
                    return self._create_missing_field_error("agent_id", "get")
                return self._handle_get_agent(facade, project_id, agent_id)
                
            elif action == "list":
                return self._handle_list_agents(facade, project_id)
                
            elif action == "update":
                if not agent_id:
                    return self._create_missing_field_error("agent_id", "update")
                return self._handle_update_agent(facade, project_id, agent_id, name, call_agent)
                
            elif action == "unregister":
                if not agent_id:
                    return self._create_missing_field_error("agent_id", "unregister")
                return self._handle_unregister_agent(facade, project_id, agent_id)
                
            else:
                return self._create_invalid_action_error(action)

        except Exception as e:
            logger.error(f"Error in CRUD operation '{action}': {e}")
            return {
                "success": False,
                "error": f"Operation failed: {str(e)}",
                "error_code": "INTERNAL_ERROR",
                "details": str(e)
            }
    
    def handle_assignment_operations(
        self,
        action: str,
        project_id: str,
        agent_id: Optional[str] = None,
        git_branch_id: Optional[str] = None,
        user_id: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Handle agent assignment operations by converting MCP parameters 
        and delegating to the application facade.
        """
        try:
            # Get facade for this request
            facade = self._get_facade_for_request(project_id, user_id)
            
            # Validate required fields
            if not agent_id:
                return self._create_missing_field_error("agent_id", action)
            
            if action in ["assign", "unassign"] and not git_branch_id:
                return self._create_missing_field_error("git_branch_id", action)
            
            if action == "assign":
                return self._handle_assign_agent(facade, project_id, agent_id, git_branch_id)
            elif action == "unassign":
                return self._handle_unassign_agent(facade, project_id, agent_id, git_branch_id)
            else:
                return self._create_invalid_action_error(action)

        except Exception as e:
            logger.error(f"Error in assignment operation '{action}': {e}")
            return {
                "success": False,
                "error": f"Operation failed: {str(e)}",
                "error_code": "INTERNAL_ERROR",
                "details": str(e)
            }
    
    def handle_rebalance_operation(self, project_id: str, user_id: Optional[str] = None) -> Dict[str, Any]:
        """
        Handle agent rebalancing operation by delegating to the application facade.
        """
        try:
            # Get facade for this request
            facade = self._get_facade_for_request(project_id, user_id)
            return self._handle_rebalance_agents(facade, project_id)

        except Exception as e:
            logger.error(f"Error in rebalance operation: {e}")
            return {
                "success": False,
                "error": f"Operation failed: {str(e)}",
                "error_code": "INTERNAL_ERROR",
                "details": str(e)
            }

    # Private helper methods for converting MCP parameters and delegating to facade
    
    def _handle_register_agent(self, facade: AgentApplicationFacade, project_id: str,
                              agent_id: str, name: str, call_agent: Optional[str]) -> Dict[str, Any]:
        """Convert MCP register parameters and delegate to facade."""
        response = facade.register_agent(project_id, agent_id, name, call_agent)
        return self._enhance_response_with_workflow_guidance(response, "register", project_id)
    
    def _handle_get_agent(self, facade: AgentApplicationFacade, project_id: str,
                         agent_id: str) -> Dict[str, Any]:
        """Handle get agent request."""
        response = facade.get_agent(project_id, agent_id)
        return self._enhance_response_with_workflow_guidance(response, "get", project_id, agent_id)
    
    def _handle_list_agents(self, facade: AgentApplicationFacade, 
                           project_id: str) -> Dict[str, Any]:
        """Handle list agents request."""
        response = facade.list_agents(project_id)
        return self._enhance_response_with_workflow_guidance(response, "list", project_id)
    
    def _handle_update_agent(self, facade: AgentApplicationFacade, project_id: str,
                            agent_id: str, name: Optional[str], call_agent: Optional[str]) -> Dict[str, Any]:
        """Handle update agent request."""
        response = facade.update_agent(project_id, agent_id, name, call_agent)
        return self._enhance_response_with_workflow_guidance(response, "update", project_id, agent_id)
    
    def _handle_unregister_agent(self, facade: AgentApplicationFacade, project_id: str,
                                agent_id: str) -> Dict[str, Any]:
        """Handle unregister agent request."""
        response = facade.unregister_agent(project_id, agent_id)
        return self._enhance_response_with_workflow_guidance(response, "unregister", project_id, agent_id)
    
    def _handle_assign_agent(self, facade: AgentApplicationFacade, project_id: str,
                            agent_id: str, git_branch_id: str) -> Dict[str, Any]:
        """Handle assign agent request."""
        response = facade.assign_agent(project_id, agent_id, git_branch_id)
        return self._enhance_response_with_workflow_guidance(response, "assign", project_id, agent_id)
    
    def _handle_unassign_agent(self, facade: AgentApplicationFacade, project_id: str,
                              agent_id: str, git_branch_id: str) -> Dict[str, Any]:
        """Handle unassign agent request."""
        response = facade.unassign_agent(project_id, agent_id, git_branch_id)
        return self._enhance_response_with_workflow_guidance(response, "unassign", project_id, agent_id)
    
    def _handle_rebalance_agents(self, facade: AgentApplicationFacade, 
                                project_id: str) -> Dict[str, Any]:
        """Handle rebalance agents request."""
        response = facade.rebalance_agents(project_id)
        return self._enhance_response_with_workflow_guidance(response, "rebalance", project_id)

    def _get_agent_management_descriptions(self) -> Dict[str, Any]:
        """
        Flatten agent descriptions for robust access, similar to other controllers.
        """
        all_desc = description_loader.get_all_descriptions()
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
    
    def _create_invalid_action_error(self, action: str) -> Dict[str, Any]:
        """Create standardized invalid action error response."""
        return {
            "success": False,
            "error": f"Invalid action: {action}",
            "error_code": "INVALID_ACTION",
            "field": "action",
            "valid_actions": [
                "register", "assign", "get", "list", "update",
                "unassign", "unregister", "rebalance"
            ],
            "hint": "Check the action parameter for valid values"
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