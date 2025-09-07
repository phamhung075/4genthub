"""Compliance Controller Factory"""

import logging
from typing import Dict, Any, Optional

from .....application.orchestrators.compliance_orchestrator import ComplianceOrchestrator
from ..handlers.validation_handler import ValidationHandler
from ..handlers.dashboard_handler import DashboardHandler
from ..handlers.execution_handler import ExecutionHandler
from ..handlers.audit_handler import AuditHandler

logger = logging.getLogger(__name__)


class ComplianceControllerFactory:
    """Factory for creating and managing Compliance MCP Controller components"""
    
    def __init__(self, compliance_orchestrator: ComplianceOrchestrator):
        self._compliance_orchestrator = compliance_orchestrator
        self._validation_handler = None
        self._dashboard_handler = None
        self._execution_handler = None
        self._audit_handler = None
        logger.info("ComplianceControllerFactory initialized")
    
    def get_validation_handler(self) -> ValidationHandler:
        """Get or create validation handler"""
        if self._validation_handler is None:
            self._validation_handler = ValidationHandler(self._compliance_orchestrator)
        return self._validation_handler
    
    def get_dashboard_handler(self) -> DashboardHandler:
        """Get or create dashboard handler"""
        if self._dashboard_handler is None:
            self._dashboard_handler = DashboardHandler(self._compliance_orchestrator)
        return self._dashboard_handler
    
    def get_execution_handler(self) -> ExecutionHandler:
        """Get or create execution handler"""
        if self._execution_handler is None:
            self._execution_handler = ExecutionHandler(self._compliance_orchestrator)
        return self._execution_handler
    
    def get_audit_handler(self) -> AuditHandler:
        """Get or create audit handler"""
        if self._audit_handler is None:
            self._audit_handler = AuditHandler(self._compliance_orchestrator)
        return self._audit_handler
    
    # Unified operation methods
    def handle_validate_compliance(self, operation: Optional[str], file_path: Optional[str] = None,
                                   content: Optional[str] = None, user_id: Optional[str] = None,
                                   security_level: str = "public", audit_required: bool = True) -> Dict[str, Any]:
        """Handle validate_compliance action"""
        return self.get_validation_handler().handle_validate_compliance(
            operation, file_path, content, user_id, security_level, audit_required
        )
    
    def handle_get_compliance_dashboard(self) -> Dict[str, Any]:
        """Handle get_compliance_dashboard action"""
        return self.get_dashboard_handler().handle_get_compliance_dashboard()
    
    def handle_execute_with_compliance(self, command: Optional[str], timeout: Optional[int] = None,
                                       user_id: Optional[str] = None, audit_required: bool = True) -> Dict[str, Any]:
        """Handle execute_with_compliance action"""
        return self.get_execution_handler().handle_execute_with_compliance(
            command, timeout, user_id, audit_required
        )
    
    def handle_get_audit_trail(self, limit: int = 100) -> Dict[str, Any]:
        """Handle get_audit_trail action"""
        return self.get_audit_handler().handle_get_audit_trail(limit)