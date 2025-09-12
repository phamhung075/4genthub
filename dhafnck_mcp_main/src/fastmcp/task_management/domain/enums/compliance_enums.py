"""
Compliance and Validation Enums

Enums for compliance levels, validation results, and audit requirements.
"""

from enum import Enum


class ComplianceLevel(Enum):
    """Compliance levels for audit and validation"""
    NONE = "none"
    BASIC = "basic"
    STANDARD = "standard"
    STRICT = "strict"
    ENTERPRISE = "enterprise"


class ValidationResult(Enum):
    """Validation result types"""
    VALID = "valid"
    INVALID = "invalid"
    WARNING = "warning"
    ERROR = "error"
    SKIPPED = "skipped"


class AuditLevel(Enum):
    """Audit detail levels"""
    MINIMAL = "minimal"
    STANDARD = "standard"
    DETAILED = "detailed"
    COMPREHENSIVE = "comprehensive"


class ComplianceStatus(Enum):
    """Overall compliance status"""
    COMPLIANT = "compliant"
    NON_COMPLIANT = "non_compliant"
    PARTIAL_COMPLIANT = "partial_compliant"
    PENDING_REVIEW = "pending_review"
    EXEMPT = "exempt"


class ValidationSeverity(Enum):
    """Severity levels for validation issues"""
    INFO = "info"
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"