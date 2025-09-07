"""Rule Orchestration Controller Factory"""

import logging
from typing import Dict, Any, Optional, TYPE_CHECKING

if TYPE_CHECKING:
    from fastmcp.server.server import FastMCP

from .....application.facades.rule_orchestration_facade import IRuleOrchestrationFacade
from ..handlers.rule_management_handler import RuleManagementHandler
from ..handlers.composition_handler import CompositionHandler
from ..handlers.client_sync_handler import ClientSyncHandler

logger = logging.getLogger(__name__)


class RuleOrchestrationControllerFactory:
    """Factory for creating and managing Rule Orchestration Controller components"""
    
    def __init__(self, rule_orchestration_facade: IRuleOrchestrationFacade):
        self.facade = rule_orchestration_facade
        self._rule_management_handler = None
        self._composition_handler = None
        self._client_sync_handler = None
        logger.info("RuleOrchestrationControllerFactory initialized")
    
    def get_rule_management_handler(self) -> RuleManagementHandler:
        """Get or create rule management handler"""
        if self._rule_management_handler is None:
            self._rule_management_handler = RuleManagementHandler(self.facade)
        return self._rule_management_handler
    
    def get_composition_handler(self) -> CompositionHandler:
        """Get or create composition handler"""
        if self._composition_handler is None:
            self._composition_handler = CompositionHandler(self.facade)
        return self._composition_handler
    
    def get_client_sync_handler(self) -> ClientSyncHandler:
        """Get or create client sync handler"""
        if self._client_sync_handler is None:
            self._client_sync_handler = ClientSyncHandler(self.facade)
        return self._client_sync_handler
    
    # Unified operation methods
    def handle_manage_rule_request(self, action: str, target: str = "", content: str = "", user_id: Optional[str] = None) -> Dict[str, Any]:
        """Handle manage_rule MCP tool requests"""
        return self.get_rule_management_handler().handle_manage_rule_request(action, target, content, user_id)
    
    def get_enhanced_rule_info(self) -> Dict[str, Any]:
        """Get enhanced information about the rule system"""
        return self.get_rule_management_handler().get_enhanced_rule_info()
    
    def compose_nested_rules(self, rule_path: str) -> Dict[str, Any]:
        """Compose nested rules with inheritance"""
        return self.get_composition_handler().compose_nested_rules(rule_path)
    
    def register_client(self, client_config: Dict[str, Any]) -> Dict[str, Any]:
        """Register a client for synchronization"""
        return self.get_client_sync_handler().register_client(client_config)
    
    def sync_with_client(self, client_id: str, operation: str, client_rules: Dict[str, Any] = None) -> Dict[str, Any]:
        """Synchronize rules with a client"""
        return self.get_client_sync_handler().sync_with_client(client_id, operation, client_rules)