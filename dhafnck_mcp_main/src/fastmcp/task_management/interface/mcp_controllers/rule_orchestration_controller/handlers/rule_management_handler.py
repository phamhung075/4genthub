"""Rule Management Handler for Rule Orchestration Controller"""

import logging
from typing import Dict, Any, Optional, TYPE_CHECKING

if TYPE_CHECKING:
    from fastmcp.server.server import FastMCP

from .....application.facades.rule_orchestration_facade import IRuleOrchestrationFacade
from ...workflow_guidance.rule.rule_workflow_factory import RuleWorkflowFactory

logger = logging.getLogger(__name__)


class RuleManagementHandler:
    """Handler for rule management operations"""
    
    def __init__(self, rule_orchestration_facade: IRuleOrchestrationFacade):
        self.facade = rule_orchestration_facade
        self._workflow_guidance = RuleWorkflowFactory.create()
        logger.info("RuleManagementHandler initialized with workflow guidance")
    
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