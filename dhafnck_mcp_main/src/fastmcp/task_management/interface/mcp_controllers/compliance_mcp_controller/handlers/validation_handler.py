"""Validation Handler for Compliance MCP Controller"""

import logging
from typing import Dict, Any, Optional

from .....application.orchestrators.compliance_orchestrator import ComplianceOrchestrator

logger = logging.getLogger(__name__)


class ValidationHandler:
    """Handler for compliance validation operations"""
    
    def __init__(self, compliance_orchestrator: ComplianceOrchestrator):
        self._compliance_orchestrator = compliance_orchestrator
        logger.info("ValidationHandler initialized")
    
    def handle_validate_compliance(self, operation: Optional[str], file_path: Optional[str] = None,
                                   content: Optional[str] = None, user_id: Optional[str] = None,
                                   security_level: str = "public", audit_required: bool = True) -> Dict[str, Any]:
        """Handle validate_compliance action"""
        if not operation:
            return {"success": False, "error": "operation is required for validate_compliance action"}
        
        try:
            return self._compliance_orchestrator.validate_operation(
                operation=operation,
                file_path=file_path,
                content=content,
                user_id=user_id,
                security_level=security_level,
                audit_required=audit_required
            )
        except Exception as e:
            logger.error(f"Compliance validation failed: {e}")
            return {
                "success": False,
                "error": str(e),
                "compliance_score": 0.0
            }