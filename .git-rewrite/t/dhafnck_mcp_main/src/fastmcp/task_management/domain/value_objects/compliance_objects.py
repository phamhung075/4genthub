"""Domain Value Objects for Compliance System

Contains immutable value objects that represent compliance concepts.
"""

from dataclasses import dataclass
from typing import Dict, Any, Optional, List, Callable
from datetime import datetime

from ..enums.compliance_enums import ComplianceLevel, ValidationResult, SecurityLevel, ProcessStatus


@dataclass(frozen=True)
class ComplianceRule:
    """Immutable compliance rule definition"""
    rule_id: str
    name: str
    description: str
    level: ComplianceLevel
    category: str
    enabled: bool = True
    
    def __post_init__(self):
        if not self.rule_id:
            raise ValueError("Rule ID cannot be empty")
        if not self.name:
            raise ValueError("Rule name cannot be empty")


@dataclass(frozen=True)
class ValidationReport:
    """Immutable validation report"""
    report_id: str
    timestamp: float
    total_rules: int
    passed: int
    failed: int
    warnings: int
    skipped: int
    overall_compliance: float
    details: tuple = ()  # Use tuple for immutability
    recommendations: tuple = ()  # Use tuple for immutability
    
    def __post_init__(self):
        if self.total_rules < 0:
            raise ValueError("Total rules cannot be negative")
        if not (0 <= self.overall_compliance <= 100):
            raise ValueError("Overall compliance must be between 0 and 100")


@dataclass(frozen=True)
class SecurityContext:
    """Immutable security context for operations"""
    user_id: str
    operation: str
    resource_path: str
    security_level: SecurityLevel
    permissions: tuple  # Use tuple for immutability
    audit_required: bool = True
    
    def __post_init__(self):
        if not self.user_id:
            raise ValueError("User ID cannot be empty")
        if not self.operation:
            raise ValueError("Operation cannot be empty")


@dataclass(frozen=True)
class ProcessInfo:
    """Immutable process information"""
    process_id: str
    command: str
    start_time: float
    timeout_seconds: int
    status: ProcessStatus
    pid: Optional[int] = None
    
    def __post_init__(self):
        if not self.process_id:
            raise ValueError("Process ID cannot be empty")
        if self.timeout_seconds <= 0:
            raise ValueError("Timeout must be positive")


@dataclass(frozen=True)
class DocumentInfo:
    """Immutable document information"""
    file_path: str
    document_id: str
    title: str
    created_by: str
    size_bytes: int
    created_at: str
    checksum: str
    
    def __post_init__(self):
        if not self.file_path:
            raise ValueError("File path cannot be empty")
        if self.size_bytes < 0:
            raise ValueError("Size cannot be negative")