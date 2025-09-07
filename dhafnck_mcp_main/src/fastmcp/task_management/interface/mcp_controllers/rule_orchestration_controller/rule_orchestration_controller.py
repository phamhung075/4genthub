"""Rule Orchestration Controller - Modular Implementation

Generated from enhanced_rule_orchestrator.py refactoring
Date: 2025-01-27

This file contains the DDD-compliant controller for rule orchestration following established patterns.
"""

import logging
from typing import Dict, Any, Annotated, Optional, TYPE_CHECKING
from pydantic import Field  # type: ignore

if TYPE_CHECKING:
    from fastmcp.server.server import FastMCP

from .manage_rule_description import get_manage_rule_description, get_manage_rule_parameters
from ....application.facades.rule_orchestration_facade import IRuleOrchestrationFacade
from .factories.rule_orchestration_controller_factory import RuleOrchestrationControllerFactory

logger = logging.getLogger(__name__)


class RuleOrchestrationController:
    """
    DDD-compliant controller for rule orchestration operations.
    Delegates all business logic to the application facade.
    """
    
    def __init__(self, rule_orchestration_facade: IRuleOrchestrationFacade):
        """
        Initialize the controller with the application facade.
        
        Args:
            rule_orchestration_facade: The application facade for rule orchestration
        """
        self.facade = rule_orchestration_facade
        self._factory = RuleOrchestrationControllerFactory(rule_orchestration_facade)
        logger.info("RuleOrchestrationController initialized with modular architecture")
    
    def register_tools(self, mcp: "FastMCP"):
        """Register MCP tools with descriptions"""
        
        # Get centralized parameter definitions
        params = get_manage_rule_parameters()

        @mcp.tool(description=get_manage_rule_description())
        def manage_rule(
            action: Annotated[str, Field(description=params["action"]["description"])],
            target: Annotated[str, Field(description=params["target"]["description"])] = None,
            content: Annotated[str, Field(description=params["content"]["description"])] = None,
            user_id: Annotated[str, Field(description="[OPTIONAL] User identifier for authentication and audit trails")] = None
        ) -> Dict[str, Any]:
            """Main rule management function with two-stage validation pattern:
            - Schema level: Only 'action' is required (MCP compatibility)
            - Business logic level: Action-specific validation in controller
            """
            return self.handle_manage_rule_request(action=action, target=target, content=content, user_id=user_id)
    
    def handle_manage_rule_request(self, action: str, target: Optional[str] = None, content: Optional[str] = None, user_id: Optional[str] = None) -> Dict[str, Any]:
        """Handle manage_rule MCP tool requests with parameter coercion"""
        try:
            # Import parameter coercion utility
            from ...utils.parameter_validation_fix import coerce_parameter_types
            
            # Coerce string parameters to proper types
            coerced_params = coerce_parameter_types({
                "target": target,
                "content": content,
                "user_id": user_id
            })
            
            # Apply coerced values with defaults
            target = coerced_params.get("target", target) or ""
            content = coerced_params.get("content", content) or ""
            user_id = coerced_params.get("user_id", user_id)
            
            return self._factory.handle_manage_rule_request(action, target, content, user_id)
            
        except Exception as e:
            logger.error(f"Error in rule management action '{action}': {e}")
            return {
                "success": False,
                "error": f"Rule operation failed: {str(e)}",
                "error_code": "INTERNAL_ERROR",
                "details": str(e)
            }
    
    def get_enhanced_rule_info(self) -> Dict[str, Any]:
        """Get enhanced information about the rule system (legacy method)"""
        return self._factory.get_enhanced_rule_info()
    
    def compose_nested_rules(self, rule_path: str) -> Dict[str, Any]:
        """Compose nested rules with inheritance (legacy method)"""
        return self._factory.compose_nested_rules(rule_path)
    
    def register_client(self, client_config: Dict[str, Any]) -> Dict[str, Any]:
        """Register a client for synchronization (legacy method)"""
        return self._factory.register_client(client_config)
    
    def sync_with_client(self, client_id: str, operation: str, client_rules: Dict[str, Any] = None) -> Dict[str, Any]:
        """Synchronize rules with a client (legacy method)"""
        return self._factory.sync_with_client(client_id, operation, client_rules)
    
    def _get_available_actions(self) -> list:
        """Get list of available actions (legacy method)"""
        return self._factory.get_rule_management_handler()._get_available_actions()
    
    def _enhance_response_with_workflow_guidance(self, response: Dict[str, Any], action: str, target: str = "") -> Dict[str, Any]:
        """Enhance response with workflow guidance (legacy method)"""
        return self._factory.get_rule_management_handler()._enhance_response_with_workflow_guidance(response, action, target)


def create_rule_orchestration_controller(facade: IRuleOrchestrationFacade) -> RuleOrchestrationController:
    """
    Factory function to create a rule orchestration controller.
    
    Args:
        facade: The application facade for rule orchestration
        
    Returns:
        Configured RuleOrchestrationController instance
    """
    return RuleOrchestrationController(facade)