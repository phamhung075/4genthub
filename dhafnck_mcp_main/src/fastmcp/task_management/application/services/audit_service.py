"""Audit Service

Application layer service for managing audit trails and compliance monitoring.
"""

import logging
import uuid
from typing import Dict, Any, List, Union, Optional
from datetime import datetime, timezone

# Import compliance enums from proper location
from ...domain.enums.compliance_enums import ComplianceLevel

logger = logging.getLogger(__name__)


class AuditService:
    """Application service for audit trail and compliance monitoring"""
    
    def __init__(self, user_id: Optional[str] = None):
        self._user_id = user_id  # Store user context
        self._audit_log: List[Dict[str, Any]] = []
        self._compliance_metrics = {
            "total_operations": 0,
            "compliant_operations": 0,
            "violations": 0,
            "last_audit": None
        }

    def _get_user_scoped_repository(self, repository: Any) -> Any:
        """Get a user-scoped version of the repository if it supports user context."""
        if not repository:
            return repository
        if hasattr(repository, 'with_user') and self._user_id:
            return repository.with_user(self._user_id)
        elif hasattr(repository, 'user_id'):
            if self._user_id and repository.user_id != self._user_id:
                repo_class = type(repository)
                if hasattr(repository, 'session'):
                    return repo_class(repository.session, user_id=self._user_id)
        return repository

    def with_user(self, user_id: str) -> 'AuditService':
        """Create a new service instance scoped to a specific user."""
        return AuditService(user_id)
        
    def log_operation(self, operation: str, result: Dict[str, Any], compliance_level: Union[ComplianceLevel, str]):
        """Log operation for audit trail
        
        Args:
            operation: The operation being audited
            result: The result of the operation
            compliance_level: ComplianceLevel enum or string value for backwards compatibility
        """
        # Handle both ComplianceLevel enum and string values for backwards compatibility
        if isinstance(compliance_level, ComplianceLevel):
            compliance_level_value = compliance_level.value
        else:
            # If it's a string, use it directly but log a warning
            compliance_level_value = str(compliance_level)
            logger.warning(f"Received string compliance level instead of ComplianceLevel enum: {compliance_level}")
            
            # Validate that the string value is a valid compliance level
            valid_levels = [level.value for level in ComplianceLevel]
            if compliance_level_value not in valid_levels:
                logger.warning(f"Invalid compliance level '{compliance_level_value}', using 'low' as default")
                compliance_level_value = "low"
        
        audit_entry = {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "operation": operation,
            "compliance_level": compliance_level_value,
            "success": result.get("success", False),
            "compliance_score": result.get("compliance_score", 0.0),
            "details": result
        }
        
        self._audit_log.append(audit_entry)
        
        # Update metrics
        self._compliance_metrics["total_operations"] += 1
        if result.get("success", False) and result.get("compliance_score", 0) >= 85:
            self._compliance_metrics["compliant_operations"] += 1
        else:
            self._compliance_metrics["violations"] += 1
        
        self._compliance_metrics["last_audit"] = audit_entry["timestamp"]
        
        logger.info(f"Audit logged: {operation} - Success: {result.get('success')}")
    
    def generate_compliance_report(self) -> Dict[str, Any]:
        """Generate comprehensive compliance report"""
        try:
            total_ops = self._compliance_metrics["total_operations"]
            compliant_ops = self._compliance_metrics["compliant_operations"]
            
            compliance_rate = (compliant_ops / max(total_ops, 1)) * 100
            
            # Recent violations
            recent_violations = [
                entry for entry in self._audit_log[-100:]  # Last 100 entries
                if not entry["success"] or entry.get("compliance_score", 0) < 85
            ]
            
            return {
                "report_id": str(uuid.uuid4()),
                "generated_at": datetime.now().isoformat(),
                "overall_compliance_rate": compliance_rate,
                "total_operations": total_ops,
                "compliant_operations": compliant_ops,
                "violations": self._compliance_metrics["violations"],
                "recent_violations": recent_violations[:10],  # Top 10 recent violations
                "compliance_trend": self._calculate_compliance_trend(),
                "recommendations": self._generate_recommendations()
            }
            
        except Exception as e:
            logger.error(f"Failed to generate compliance report: {e}")
            return {
                "report_id": str(uuid.uuid4()),
                "generated_at": datetime.now().isoformat(),
                "error": str(e),
                "overall_compliance_rate": 0.0
            }
    
    def get_audit_log(self, limit: int = 100) -> List[Dict[str, Any]]:
        """Get recent audit log entries"""
        return self._audit_log[-limit:] if limit > 0 else self._audit_log
    
    def get_compliance_metrics(self) -> Dict[str, Any]:
        """Get current compliance metrics"""
        return self._compliance_metrics.copy()
    
    def clear_audit_log(self):
        """Clear audit log (for testing or maintenance)"""
        self._audit_log.clear()
        self._compliance_metrics = {
            "total_operations": 0,
            "compliant_operations": 0,
            "violations": 0,
            "last_audit": None
        }
        logger.info("Audit log cleared")
    
    def _calculate_compliance_trend(self) -> str:
        """Calculate compliance trend"""
        if len(self._audit_log) < 20:
            return "insufficient_data"
        
        # Compare last 10 vs previous 10 operations
        recent_10 = self._audit_log[-10:]
        previous_10 = self._audit_log[-20:-10]
        
        recent_compliance = sum(1 for entry in recent_10 if entry["success"]) / 10
        previous_compliance = sum(1 for entry in previous_10 if entry["success"]) / 10
        
        if recent_compliance > previous_compliance + 0.1:
            return "improving"
        elif recent_compliance < previous_compliance - 0.1:
            return "declining"
        else:
            return "stable"
    
    def _generate_recommendations(self) -> List[str]:
        """Generate compliance improvement recommendations"""
        recommendations = []
        
        total_ops = self._compliance_metrics["total_operations"]
        compliant_ops = self._compliance_metrics["compliant_operations"]
        compliance_rate = (compliant_ops / max(total_ops, 1)) * 100
        
        if compliance_rate < 85:
            recommendations.append("Overall compliance below target (85%). Review failed operations.")
        
        if self._compliance_metrics["violations"] > 10:
            recommendations.append("High number of violations detected. Implement additional validation.")
        
        # Analyze common failure patterns
        recent_failures = [entry for entry in self._audit_log[-50:] if not entry["success"]]
        if len(recent_failures) > 5:
            recommendations.append("Frequent failures detected. Review system stability.")
        
        if not recommendations:
            recommendations.append("Compliance is on track. Continue monitoring.")
        
        return recommendations