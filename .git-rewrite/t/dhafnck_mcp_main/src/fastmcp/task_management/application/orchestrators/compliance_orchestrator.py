"""Compliance Orchestrator

Application layer orchestrator that coordinates compliance operations across multiple services.
"""

import logging
import uuid
from pathlib import Path
from typing import Dict, Any
from datetime import datetime

from ...domain.enums.compliance_enums import ComplianceLevel
from ..services.compliance_service import ComplianceService
from ..services.audit_service import AuditService
from ...infrastructure.monitoring.process_monitor import ProcessMonitor

logger = logging.getLogger(__name__)


class ComplianceOrchestrator:
    """Main orchestrator for compliance operations and monitoring"""
    
    def __init__(self, project_root: Path):
        """Initialize compliance orchestrator with dependencies"""
        self.project_root = project_root
        self._compliance_service = ComplianceService()
        self._audit_service = AuditService()
        self._process_monitor = ProcessMonitor()
        
        # Start process monitoring
        self._process_monitor.start_monitoring()
        
        logger.info("Compliance orchestrator initialized")
    
    def validate_operation(self, operation: str, **kwargs) -> Dict[str, Any]:
        """Validate operation against all compliance rules with audit logging"""
        try:
            # Perform compliance validation
            validation_result = self._compliance_service.validate_operation(operation, **kwargs)
            
            # Determine compliance level based on operation
            compliance_level = self._determine_compliance_level(operation, kwargs)
            
            # Log to audit trail
            self._audit_service.log_operation(operation, validation_result, compliance_level)
            
            return validation_result
            
        except Exception as e:
            logger.error(f"Operation validation failed: {e}")
            error_result = {
                "success": False,
                "error": str(e),
                "compliance_score": 0.0
            }
            
            # Log error to audit trail
            self._audit_service.log_operation(operation, error_result, ComplianceLevel.HIGH)
            
            return error_result
    
    def get_compliance_dashboard(self) -> Dict[str, Any]:
        """Get comprehensive compliance dashboard"""
        try:
            # Get compliance report
            compliance_report = self._audit_service.generate_compliance_report()
            
            # Get process monitoring status
            active_processes = self._process_monitor.get_active_processes()
            
            # Get compliance rules
            compliance_rules = self._compliance_service.get_compliance_rules()
            
            return {
                "success": True,
                "dashboard_id": str(uuid.uuid4()),
                "generated_at": datetime.now().isoformat(),
                "compliance_report": compliance_report,
                "active_processes": len(active_processes),
                "compliance_rules_count": len(compliance_rules),
                "system_health": {
                    "compliance_service": "active",
                    "audit_service": "active", 
                    "process_monitor": "active"
                },
                "project_root": str(self.project_root)
            }
            
        except Exception as e:
            logger.error(f"Dashboard generation failed: {e}")
            return {
                "success": False,
                "error": str(e),
                "dashboard_id": str(uuid.uuid4()),
                "generated_at": datetime.now().isoformat()
            }
    
    def execute_with_compliance(self, command: str, timeout: int = None, **kwargs) -> Dict[str, Any]:
        """Execute command with compliance validation and process monitoring"""
        try:
            # Validate operation first
            validation_result = self.validate_operation("execute_command", command=command, **kwargs)
            
            if not validation_result.get("success", False):
                return {
                    "success": False,
                    "error": "Compliance validation failed",
                    "validation_result": validation_result
                }
            
            # Execute with process monitoring
            execution_result = self._process_monitor.execute_with_timeout(command, timeout)
            
            # Combine results
            return {
                "success": execution_result.get("success", False),
                "validation_result": validation_result,
                "execution_result": execution_result,
                "compliance_enforced": True
            }
            
        except Exception as e:
            logger.error(f"Compliant execution failed: {e}")
            return {
                "success": False,
                "error": str(e),
                "compliance_enforced": False
            }
    
    def get_audit_trail(self, limit: int = 100) -> Dict[str, Any]:
        """Get audit trail with metadata"""
        try:
            audit_log = self._audit_service.get_audit_log(limit)
            metrics = self._audit_service.get_compliance_metrics()
            
            return {
                "success": True,
                "audit_entries": audit_log,
                "metrics": metrics,
                "total_entries": len(audit_log)
            }
            
        except Exception as e:
            logger.error(f"Failed to get audit trail: {e}")
            return {
                "success": False,
                "error": str(e)
            }
    
    def shutdown(self):
        """Shutdown orchestrator and cleanup resources"""
        try:
            self._process_monitor.stop_monitoring()
            logger.info("Compliance orchestrator shutdown complete")
        except Exception as e:
            logger.error(f"Error during shutdown: {e}")
    
    def _determine_compliance_level(self, operation: str, kwargs: Dict[str, Any]) -> ComplianceLevel:
        """Determine compliance level based on operation type"""
        # High-risk operations
        if operation in ["delete_file", "execute_command", "modify_system"]:
            return ComplianceLevel.CRITICAL
        
        # Medium-risk operations  
        elif operation in ["create_file", "edit_file", "update_config"]:
            return ComplianceLevel.HIGH
        
        # Low-risk operations
        elif operation in ["read_file", "list_files", "get_status"]:
            return ComplianceLevel.MEDIUM
        
        # Default
        else:
            return ComplianceLevel.LOW