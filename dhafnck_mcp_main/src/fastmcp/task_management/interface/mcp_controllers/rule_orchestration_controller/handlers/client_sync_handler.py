"""Client Sync Handler for Rule Orchestration Controller"""

import logging
from typing import Dict, Any

from .....application.facades.rule_orchestration_facade import IRuleOrchestrationFacade

logger = logging.getLogger(__name__)


class ClientSyncHandler:
    """Handler for client synchronization operations"""
    
    def __init__(self, rule_orchestration_facade: IRuleOrchestrationFacade):
        self.facade = rule_orchestration_facade
        logger.info("ClientSyncHandler initialized")
    
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