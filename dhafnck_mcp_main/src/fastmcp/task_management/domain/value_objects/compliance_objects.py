"""
Compliance and Document Value Objects

Value objects for compliance, documentation, and validation requirements.
"""

from dataclasses import dataclass
from typing import Optional, Dict, Any
from datetime import datetime
from enum import Enum


class DocumentType(Enum):
    """Document types for compliance"""
    CONFIG = "config"
    TEMPLATE = "template"
    DOCUMENT = "document"
    AUDIT = "audit"
    REPORT = "report"


@dataclass(frozen=True)
class DocumentInfo:
    """Document information value object"""
    path: str
    type: DocumentType
    content: str
    metadata: Dict[str, Any]
    created_at: datetime
    updated_at: Optional[datetime] = None
    hash: Optional[str] = None
    
    def __post_init__(self):
        """Validate document info on creation"""
        if not self.path:
            raise ValueError("Document path cannot be empty")
        if not self.content:
            raise ValueError("Document content cannot be empty")


@dataclass(frozen=True)
class ComplianceStatus:
    """Compliance status value object"""
    is_compliant: bool
    validation_date: datetime
    validator: str
    issues: list[str]
    metadata: Dict[str, Any]


@dataclass(frozen=True)
class ValidationResult:
    """Validation result value object"""
    is_valid: bool
    errors: list[str]
    warnings: list[str]
    metadata: Dict[str, Any]


@dataclass(frozen=True)
class ValidationReport:
    """Comprehensive validation report value object"""
    validation_id: str
    entity_id: str
    entity_type: str
    validation_timestamp: datetime
    results: list[ValidationResult]
    overall_status: bool
    summary: str
    recommendations: list[str]
    metadata: Dict[str, Any]
    
    @property
    def total_errors(self) -> int:
        """Get total number of errors across all results"""
        return sum(len(result.errors) for result in self.results)
    
    @property
    def total_warnings(self) -> int:
        """Get total number of warnings across all results"""
        return sum(len(result.warnings) for result in self.results)
    
    @property
    def has_issues(self) -> bool:
        """Check if report has any errors or warnings"""
        return self.total_errors > 0 or self.total_warnings > 0