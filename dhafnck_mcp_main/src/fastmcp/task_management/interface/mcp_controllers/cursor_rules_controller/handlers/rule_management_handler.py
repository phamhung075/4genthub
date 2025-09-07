"""Rule Management Handler"""

import logging
from typing import Dict, Any

logger = logging.getLogger(__name__)


class RuleManagementHandler:
    """Handler for rule management operations"""
    
    def __init__(self, rule_facade):
        """
        Initialize handler with rule application facade.
        
        Args:
            rule_facade: Application facade for rule operations
        """
        self._rule_facade = rule_facade
        logger.info("RuleManagementHandler initialized")
    
    def handle_manage_rule(self, action: str, target: str = "", content: str = "") -> Dict[str, Any]:
        """
        Handle rule management operations.
        
        Args:
            action: Rule management action to perform
            target: Target for the action
            content: Content for the action
            
        Returns:
            Dict containing operation result
        """
        try:
            if not action:
                return {
                    "success": False,
                    "error": "Missing required field: action",
                    "error_code": "MISSING_FIELD",
                    "field": "action",
                    "expected": "A valid rule management action",
                    "hint": "Include 'action' in your request body"
                }
            
            return self._rule_facade.manage_rule(action, target, content)
            
        except Exception as e:
            logger.error(f"Cursor rules error: {e}")
            return {
                "success": False,
                "error": f"Cursor rules operation failed: {str(e)}",
                "error_code": "INTERNAL_ERROR",
                "details": str(e)
            }