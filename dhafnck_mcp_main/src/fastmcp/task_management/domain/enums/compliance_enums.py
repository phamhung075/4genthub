"""Domain Enums for Compliance System

Contains all enumeration types used across the compliance domain.
"""

from enum import Enum


class ComplianceLevel(Enum):
    """Compliance level classifications"""
    CRITICAL = "critical"      # Must be 100% compliant
    HIGH = "high"             # Target 95%+ compliance
    MEDIUM = "medium"         # Target 85%+ compliance
    LOW = "low"              # Target 70%+ compliance


class ValidationResult(Enum):
    """Validation result status"""
    PASSED = "passed"
    FAILED = "failed"
    WARNING = "warning"
    SKIPPED = "skipped"


class SecurityLevel(Enum):
    """Security access levels"""
    PUBLIC = "public"
    PROTECTED = "protected"
    RESTRICTED = "restricted"
    CONFIDENTIAL = "confidential"


class DocumentType(Enum):
    """Document type classifications"""
    AI_GENERATED = "ai_generated"
    SYSTEM_CONFIG = "system_config"
    USER_CREATED = "user_created"


class ProcessStatus(Enum):
    """Process execution status"""
    RUNNING = "running"
    COMPLETED = "completed"
    TIMEOUT = "timeout"
    ERROR = "error"
    TERMINATED = "terminated"