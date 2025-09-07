"""Compliance Service

Application layer service that orchestrates compliance validation using domain rules
and infrastructure components.
"""

import logging
import uuid
from typing import Dict, Any, List, Optional
from datetime import datetime

from ...domain.enums.compliance_enums import ComplianceLevel, ValidationResult, SecurityLevel
from ...domain.value_objects.compliance_objects import ComplianceRule, ValidationReport, SecurityContext
from ...infrastructure.validation.document_validator import DocumentValidator
from ...infrastructure.security.access_controller import AccessController

logger = logging.getLogger(__name__)


class ComplianceService:
    """Application service for compliance validation and enforcement"""
    
    def __init__(self, document_validator: DocumentValidator = None, access_controller: AccessController = None, user_id: Optional[str] = None):
        """Initialize compliance service with injected dependencies"""
        self._document_validator = document_validator or DocumentValidator()
        self._access_controller = access_controller or AccessController()
        self._user_id = user_id  # Store user context
        self._compliance_rules = self._initialize_compliance_rules()

    def with_user(self, user_id: str) -> 'ComplianceService':
        """Create a new service instance scoped to a specific user."""
        return ComplianceService(
            self._document_validator,
            self._access_controller,
            user_id
        )
        
    def validate_operation(self, operation: str, **kwargs) -> Dict[str, Any]:
        """Validate operation against all applicable compliance rules"""
        try:
            validation_results = []
            
            # Document validation for file operations
            if operation in ["edit_file", "create_file"]:
                doc_result = self._validate_document_operation(kwargs)
                if doc_result:
                    validation_results.append(doc_result)
            
            # Security validation for all operations
            security_result = self._validate_security_operation(operation, kwargs)
            if security_result:
                validation_results.append(security_result)
            
            # Calculate overall compliance
            overall_success, avg_score = self._calculate_overall_compliance(validation_results)
            
            return {
                "success": overall_success,
                "operation": operation,
                "compliance_score": avg_score,
                "validation_results": validation_results,
                "timestamp": datetime.now().isoformat()
            }
            
        except Exception as e:
            logger.error(f"Operation validation failed: {e}")
            return {
                "success": False,
                "error": str(e),
                "compliance_score": 0.0
            }
    
    def generate_compliance_report(self) -> ValidationReport:
        """Generate comprehensive compliance report"""
        try:
            # For now, generate a basic report
            # In a full implementation, this would aggregate historical data
            total_rules = len(self._compliance_rules)
            
            report = ValidationReport(
                report_id=str(uuid.uuid4()),
                timestamp=datetime.now().timestamp(),
                total_rules=total_rules,
                passed=total_rules,  # Placeholder
                failed=0,  # Placeholder
                warnings=0,  # Placeholder
                skipped=0,  # Placeholder
                overall_compliance=100.0,  # Placeholder
                details=(),
                recommendations=("Review compliance rules regularly", "Monitor validation results")
            )
            
            return report
            
        except Exception as e:
            logger.error(f"Failed to generate compliance report: {e}")
            # Return minimal report on error
            return ValidationReport(
                report_id=str(uuid.uuid4()),
                timestamp=datetime.now().timestamp(),
                total_rules=0,
                passed=0,
                failed=1,
                warnings=0,
                skipped=0,
                overall_compliance=0.0,
                details=({"error": str(e)},),
                recommendations=("Fix compliance service errors",)
            )
    
    def _validate_document_operation(self, kwargs: Dict[str, Any]) -> Dict[str, Any]:
        """Validate document-related operations"""
        file_path = kwargs.get("file_path", kwargs.get("target_file", ""))
        content = kwargs.get("content", "")
        
        if not file_path or not content:
            return None
            
        try:
            doc_result = self._document_validator.validate_document_creation(file_path, content)
            
            return {
                "rule_id": "DOC_VALIDATION",
                "rule_name": "Document Validation",
                "category": "document_compliance",
                "success": doc_result.get("success", False),
                "compliance_score": doc_result.get("compliance_score", 0.0),
                "details": doc_result,
                "result": ValidationResult.PASSED if doc_result.get("success") else ValidationResult.FAILED
            }
            
        except Exception as e:
            logger.error(f"Document validation failed: {e}")
            return {
                "rule_id": "DOC_VALIDATION",
                "rule_name": "Document Validation",
                "category": "document_compliance",
                "success": False,
                "compliance_score": 0.0,
                "details": {"error": str(e)},
                "result": ValidationResult.FAILED
            }
    
    def _validate_security_operation(self, operation: str, kwargs: Dict[str, Any]) -> Dict[str, Any]:
        """Validate security aspects of operations"""
        resource_path = kwargs.get("file_path", kwargs.get("target_file", kwargs.get("resource_path", "")))
        
        if not resource_path:
            return None
            
        try:
            # Convert security level string to enum
            security_level_str = kwargs.get("security_level", "public")
            try:
                security_level = SecurityLevel(security_level_str)
            except ValueError:
                logger.warning(f"Invalid security level '{security_level_str}', using PUBLIC as default")
                security_level = SecurityLevel.PUBLIC
            
            # Create security context
            context = SecurityContext(
                user_id=kwargs.get("user_id", "system"),
                operation=operation,
                resource_path=resource_path,
                security_level=security_level,
                permissions=tuple(kwargs.get("permissions", [])),
                audit_required=kwargs.get("audit_required", True)
            )
            
            # Validate access
            access_result = self._access_controller.validate_access(context)
            
            return {
                "rule_id": "SECURITY_VALIDATION",
                "rule_name": "Security Access Control",
                "category": "security_compliance",
                "success": access_result.get("success", False) and access_result.get("access_granted", False),
                "compliance_score": 100.0 if access_result.get("access_granted") else 0.0,
                "details": access_result,
                "result": ValidationResult.PASSED if access_result.get("access_granted") else ValidationResult.FAILED
            }
            
        except Exception as e:
            logger.error(f"Security validation failed: {e}")
            return {
                "rule_id": "SECURITY_VALIDATION",
                "rule_name": "Security Access Control",
                "category": "security_compliance",
                "success": False,
                "compliance_score": 0.0,
                "details": {"error": str(e)},
                "result": ValidationResult.FAILED
            }
    
    def _calculate_overall_compliance(self, validation_results: List[Dict[str, Any]]) -> tuple[bool, float]:
        """Calculate overall compliance from validation results"""
        if not validation_results:
            return True, 100.0
            
        total_score = sum(result.get("compliance_score", 0) for result in validation_results)
        avg_score = total_score / len(validation_results)
        overall_success = all(result.get("success", False) for result in validation_results)
        
        return overall_success, avg_score
    
    def _initialize_compliance_rules(self) -> List[ComplianceRule]:
        """Initialize default compliance rules"""
        return [
            ComplianceRule(
                rule_id="DOC_VALIDATION",
                name="Document Validation",
                description="Validate document structure and metadata",
                level=ComplianceLevel.HIGH,
                category="document_compliance"
            ),
            ComplianceRule(
                rule_id="SECURITY_VALIDATION", 
                name="Security Access Control",
                description="Validate security access permissions",
                level=ComplianceLevel.CRITICAL,
                category="security_compliance"
            )
        ]
    
    def get_compliance_rules(self) -> List[ComplianceRule]:
        """Get all compliance rules"""
        return self._compliance_rules.copy()
    
    def add_compliance_rule(self, rule: ComplianceRule):
        """Add a new compliance rule"""
        self._compliance_rules.append(rule)
        logger.info(f"Added compliance rule: {rule.rule_id}")
    
    def remove_compliance_rule(self, rule_id: str) -> bool:
        """Remove a compliance rule by ID"""
        original_count = len(self._compliance_rules)
        self._compliance_rules = [rule for rule in self._compliance_rules if rule.rule_id != rule_id]
        removed = len(self._compliance_rules) < original_count
        if removed:
            logger.info(f"Removed compliance rule: {rule_id}")
        return removed