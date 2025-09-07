"""Execution Handler for Compliance MCP Controller"""

import logging
from typing import Dict, Any, Optional
from datetime import datetime

from .....application.orchestrators.compliance_orchestrator import ComplianceOrchestrator

logger = logging.getLogger(__name__)


class ExecutionHandler:
    """Handler for compliance execution operations"""
    
    def __init__(self, compliance_orchestrator: ComplianceOrchestrator):
        self._compliance_orchestrator = compliance_orchestrator
        logger.info("ExecutionHandler initialized")
    
    def handle_execute_with_compliance(self, command: Optional[str], timeout: Optional[int] = None,
                                       user_id: Optional[str] = None, audit_required: bool = True) -> Dict[str, Any]:
        """Handle execute_with_compliance action"""
        if not command:
            return {"success": False, "error": "command is required for execute_with_compliance action", "metadata": {"timestamp": datetime.now().isoformat()}}
        
        try:
            # Ensure timeout is an integer or None
            timeout_value = int(timeout) if timeout is not None else None
            result = self._compliance_orchestrator.execute_with_compliance(
                command=command,
                timeout=timeout_value,
                user_id=user_id,
                audit_required=audit_required
            )
            
            if isinstance(result, dict) and "success" in result:
                command_preview = command[:50] + "..." if len(command) > 50 else command
                metadata = {
                    "action": "execute_with_compliance",
                    "command": command_preview,
                    "timeout": timeout_value,
                    "timestamp": datetime.now().isoformat()
                }
                
                if result.get("success"):
                    result.setdefault("metadata", {}).update(metadata)
                else:
                    result.setdefault("metadata", {}).update(metadata)
                    
            return result
            
        except ValueError as ve:
            logger.error(f"Invalid timeout value: {ve}")
            return {
                "success": False,
                "error": f"Invalid timeout value: {str(ve)}. Timeout must be an integer or omitted.",
                "metadata": {
                    "action": "execute_with_compliance",
                    "command": command[:50] + "..." if len(command) > 50 else command,
                    "timestamp": datetime.now().isoformat()
                }
            }
        except Exception as e:
            logger.error(f"Compliant execution failed: {e}")
            return {
                "success": False,
                "error": str(e),
                "metadata": {
                    "action": "execute_with_compliance",
                    "command": command[:50] + "..." if len(command) > 50 else command,
                    "timeout": timeout,
                    "timestamp": datetime.now().isoformat(),
                    "error_type": type(e).__name__
                }
            }