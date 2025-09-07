"""
Rule Orchestration Controller
Generated from enhanced_rule_orchestrator.py refactoring
Date: 2025-01-27

This file contains the DDD-compliant controller for rule orchestration following established patterns.
"""

import logging
from typing import Dict, Any, Annotated, Optional
from pydantic import Field  # type: ignore
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from fastmcp.server.server import FastMCP

from .desc import description_loader
from ...application.facades.rule_orchestration_facade import IRuleOrchestrationFacade
from .workflow_guidance.rule.rule_workflow_factory import RuleWorkflowFactory

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
        self._workflow_guidance = RuleWorkflowFactory.create()
        logger.info("RuleOrchestrationController initialized with workflow guidance")
    
    def register_tools(self, mcp: "FastMCP"):
        descriptions = description_loader.get_all_descriptions()
        manage_rule_desc = descriptions["rule"]["manage_rule"]

        @mcp.tool(description=manage_rule_desc["description"])
        def manage_rule(
            action: Annotated[str, Field(description=manage_rule_desc["parameters"].get("action", "Rule management action"))],
            target: Annotated[str, Field(description=manage_rule_desc["parameters"].get("target", "Target for the action"))] = "",
            content: Annotated[str, Field(description=manage_rule_desc["parameters"].get("content", "Content for the action"))] = "",
            user_id: Annotated[Optional[str], Field(description="User identifier for authentication and audit trails")] = None
        ) -> Dict[str, Any]:
            return self.handle_manage_rule_request(action=action, target=target, content=content, user_id=user_id)
    
    def handle_manage_rule_request(self, action: str, target: str = "", content: str = "", user_id: Optional[str] = None) -> Dict[str, Any]:
        """
        Handle manage_rule MCP tool requests.
        
        Args:
            action: The action to perform
            target: The target for the action (optional)
            content: The content for the action (optional)
            user_id: User identifier for authentication and audit trails (optional)
            
        Returns:
            Dictionary containing the result of the operation
        """
        try:
            if not action:
                return {
                    "success": False,
                    "error": "Missing required field: action",
                    "error_code": "MISSING_FIELD",
                    "field": "action",
                    "expected": "A valid rule management action",
                    "hint": "Include 'action' in your request body",
                    "available_actions": self._get_available_actions()
                }
            result = self.facade.execute_action(action, target, content, user_id)
            if not isinstance(result, dict):
                return {
                    "success": False,
                    "error": "Invalid response from facade",
                    "error_code": "INTERNAL_ERROR",
                    "field": "action",
                    "expected": "A dict response from facade",
                    "hint": "Check backend implementation"
                }
            result["action"] = action
            result["target"] = target
            # Enhance with workflow guidance
            return self._enhance_response_with_workflow_guidance(result, action, target)
        except Exception as e:
            logger.error(f"Controller error in manage_rule: {e}")
            return {
                "success": False,
                "error": f"Controller error: {str(e)}",
                "error_code": "INTERNAL_ERROR",
                "details": str(e),
                "action": action,
                "target": target
            }
    
    def get_enhanced_rule_info(self) -> Dict[str, Any]:
        """
        Get enhanced information about the rule system.
        
        Returns:
            Dictionary containing enhanced rule information
        """
        try:
            return self.facade.get_enhanced_rule_info()
        except Exception as e:
            return {
                "success": False,
                "error": f"Failed to get enhanced rule info: {str(e)}"
            }
    
    def compose_nested_rules(self, rule_path: str) -> Dict[str, Any]:
        """
        Compose nested rules with inheritance.
        
        Args:
            rule_path: Path to the rule to compose
            
        Returns:
            Dictionary containing composition result
        """
        try:
            if not rule_path:
                return {
                    "success": False,
                    "error": "Missing required field: rule_path",
                    "error_code": "MISSING_FIELD",
                    "field": "rule_path",
                    "expected": "A valid rule path string",
                    "hint": "Include 'rule_path' in your request body"
                }
            return self.facade.compose_nested_rules(rule_path)
        except Exception as e:
            return {
                "success": False,
                "error": f"Failed to compose nested rules: {str(e)}",
                "error_code": "INTERNAL_ERROR",
                "details": str(e),
                "rule_path": rule_path
            }
    
    def register_client(self, client_config: Dict[str, Any]) -> Dict[str, Any]:
        """
        Register a client for synchronization.
        
        Args:
            client_config: Client configuration dictionary
            
        Returns:
            Dictionary containing registration result
        """
        try:
            if not client_config:
                return {
                    "success": False,
                    "error": "Missing required field: client_config",
                    "error_code": "MISSING_FIELD",
                    "field": "client_config",
                    "expected": "A valid client configuration dictionary",
                    "hint": "Include 'client_config' in your request body"
                }
            return self.facade.register_client(client_config)
        except Exception as e:
            return {
                "success": False,
                "error": f"Failed to register client: {str(e)}",
                "error_code": "INTERNAL_ERROR",
                "details": str(e)
            }
    
    def sync_with_client(self, client_id: str, operation: str, client_rules: Dict[str, Any] = None) -> Dict[str, Any]:
        """
        Synchronize rules with a client.
        
        Args:
            client_id: ID of the client to sync with
            operation: Sync operation to perform
            client_rules: Client rules for synchronization (optional)
            
        Returns:
            Dictionary containing sync result
        """
        try:
            if not client_id:
                return {
                    "success": False,
                    "error": "Missing required field: client_id",
                    "error_code": "MISSING_FIELD",
                    "field": "client_id",
                    "expected": "A valid client ID string",
                    "hint": "Include 'client_id' in your request body"
                }
            if not operation:
                return {
                    "success": False,
                    "error": "Missing required field: operation",
                    "error_code": "MISSING_FIELD",
                    "field": "operation",
                    "expected": "A valid operation string",
                    "hint": "Include 'operation' in your request body"
                }
            return self.facade.sync_with_client(client_id, operation, client_rules)
        except Exception as e:
            return {
                "success": False,
                "error": f"Failed to sync with client: {str(e)}",
                "error_code": "INTERNAL_ERROR",
                "details": str(e),
                "client_id": client_id,
                "operation": operation
            }
    
    def _get_available_actions(self) -> list:
        """
        Get list of available actions.
        
        Returns:
            List of available action names
        """
        return [
            # Core actions
            "list", "backup", "restore", "clean", "info",
            # Enhanced actions
            "load_core", "parse_rule", "analyze_hierarchy", "get_dependencies", "enhanced_info",
            # Composition actions
            "compose_nested_rules", "resolve_rule_inheritance", "validate_rule_hierarchy", 
            "build_hierarchy", "load_nested",
            # Cache actions
            "cache_status",
            # Client integration actions
            "register_client", "authenticate_client", "sync_client", "client_diff", 
            "resolve_conflicts", "client_status", "client_analytics"
        ]
    
    def _enhance_response_with_workflow_guidance(self, response: Dict[str, Any], action: str, 
                                               target: str = "") -> Dict[str, Any]:
        """
        Enhance response with workflow guidance if operation was successful.
        
        Args:
            response: The original response
            action: The action performed
            target: The target of the action if any
            
        Returns:
            Enhanced response with workflow guidance
        """
        if response.get("success", False):
            # Build context for workflow guidance
            guidance_context = {}
            if target:
                guidance_context["target"] = target
            
            # Generate and add workflow guidance
            workflow_guidance = self._workflow_guidance.generate_guidance(action, guidance_context)
            response["workflow_guidance"] = workflow_guidance
            
        return response


def create_rule_orchestration_controller(facade: IRuleOrchestrationFacade) -> RuleOrchestrationController:
    """
    Factory function to create a rule orchestration controller.
    
    Args:
        facade: The application facade for rule orchestration
        
    Returns:
        Configured RuleOrchestrationController instance
    """
    return RuleOrchestrationController(facade) 