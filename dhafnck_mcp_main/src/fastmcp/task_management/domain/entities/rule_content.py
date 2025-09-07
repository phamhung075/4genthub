"""Rule Content Domain Entities

These entities represent the core domain concepts for rule management
following DDD principles.
"""

from typing import Dict, Any, List, Optional
from dataclasses import dataclass, field
from enum import Enum
from datetime import datetime


class RuleFormat(Enum):
    """Rule file format types"""
    MDC = "mdc"
    MD = "md"
    JSON = "json"
    YAML = "yaml"
    TXT = "txt"


class RuleType(Enum):
    """Rule classification types"""
    TASK = "task"
    CONTEXT = "context"
    CONFIG = "config"
    AGENT = "agent"
    GENERAL = "general"


class ConflictResolution(Enum):
    """Conflict resolution strategies"""
    OVERRIDE = "override"
    MERGE = "merge"
    SKIP = "skip"
    PROMPT = "prompt"


class InheritanceType(Enum):
    """Rule inheritance types"""
    FULL = "full"
    PARTIAL = "partial"
    OVERRIDE = "override"
    EXTENSION = "extension"


@dataclass
class RuleMetadata:
    """Metadata for rule files"""
    path: str
    format: RuleFormat
    type: RuleType
    size: int
    modified: float
    checksum: str
    dependencies: List[str] = field(default_factory=list)
    
    @property
    def modified_datetime(self) -> datetime:
        """Get modification time as datetime"""
        return datetime.fromtimestamp(self.modified)


@dataclass
class RuleContent:
    """Complete rule content with metadata and parsed data"""
    metadata: RuleMetadata
    raw_content: str
    parsed_content: Dict[str, Any]
    sections: Dict[str, str]
    references: List[str]
    variables: Dict[str, Any]
    
    def __post_init__(self):
        """Post-initialization validation"""
        if not self.raw_content:
            raise ValueError("Rule content cannot be empty")
        if not self.metadata:
            raise ValueError("Rule metadata is required")


@dataclass
class RuleInheritance:
    """Rule inheritance relationship"""
    parent_path: str
    child_path: str
    inheritance_type: InheritanceType
    inherited_sections: List[str] = field(default_factory=list)
    conflicts: List[str] = field(default_factory=list)


@dataclass
class CompositionResult:
    """Result of rule composition operation"""
    success: bool
    composed_content: Dict[str, Any]
    applied_rules: List[str]
    conflicts: List[str] = field(default_factory=list)
    errors: List[str] = field(default_factory=list)


@dataclass
class RuleConflict:
    """Represents a conflict between rules"""
    rule1_path: str
    rule2_path: str
    conflict_section: str
    conflict_type: str
    resolution: Optional[ConflictResolution] = None
    resolved_value: Optional[Any] = None