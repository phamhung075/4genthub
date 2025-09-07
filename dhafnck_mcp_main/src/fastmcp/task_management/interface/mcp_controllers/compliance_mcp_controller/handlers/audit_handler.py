"""Audit Handler for Compliance MCP Controller"""

import logging
from typing import Dict, Any

from .....application.orchestrators.compliance_orchestrator import ComplianceOrchestrator

logger = logging.getLogger(__name__)


class AuditHandler:
    """Handler for compliance audit operations"""
    
    def __init__(self, compliance_orchestrator: ComplianceOrchestrator):
        self._compliance_orchestrator = compliance_orchestrator
        logger.info("AuditHandler initialized")
    
    def handle_get_audit_trail(self, limit: int = 100) -> Dict[str, Any]:
        """Handle get_audit_trail action"""
        try:
            return self._compliance_orchestrator.get_audit_trail(limit)
        except Exception as e:
            logger.error(f"Audit trail retrieval failed: {e}")
            return {
                "success": False,
                "error": str(e)
            }