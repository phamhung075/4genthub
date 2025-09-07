"""Composition Handler for Rule Orchestration Controller"""

import logging
from typing import Dict, Any

from .....application.facades.rule_orchestration_facade import IRuleOrchestrationFacade

logger = logging.getLogger(__name__)


class CompositionHandler:
    """Handler for rule composition operations"""
    
    def __init__(self, rule_orchestration_facade: IRuleOrchestrationFacade):
        self.facade = rule_orchestration_facade
        logger.info("CompositionHandler initialized")
    
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