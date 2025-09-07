"""Dashboard Handler for Compliance MCP Controller"""

import logging
from typing import Dict, Any

from .....application.orchestrators.compliance_orchestrator import ComplianceOrchestrator

logger = logging.getLogger(__name__)


class DashboardHandler:
    """Handler for compliance dashboard operations"""
    
    def __init__(self, compliance_orchestrator: ComplianceOrchestrator):
        self._compliance_orchestrator = compliance_orchestrator
        logger.info("DashboardHandler initialized")
    
    def handle_get_compliance_dashboard(self) -> Dict[str, Any]:
        """Handle get_compliance_dashboard action"""
        try:
            return self._compliance_orchestrator.get_compliance_dashboard()
        except Exception as e:
            logger.error(f"Dashboard generation failed: {e}")
            return {
                "success": False,
                "error": str(e)
            }