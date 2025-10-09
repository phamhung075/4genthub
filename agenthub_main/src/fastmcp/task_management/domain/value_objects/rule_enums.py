"""
Rule Management Domain Enums
Generated from enhanced_rule_orchestrator.py refactoring
Date: 2025-01-27

This file contains all enums related to rule management following DDD principles.
"""

from enum import Enum
from typing import List


class RuleFormat(Enum):
    """Supported rule file formats"""
    MDC = "mdc"
    MD = "md"
    JSON = "json"
    YAML = "yaml"
    TXT = "txt"

    @classmethod
    def get_all_formats(cls) -> List[str]:
        """Get list of all supported formats"""
        return [format_type.value for format_type in cls]

    @classmethod
    def is_valid_format(cls, format_str: str) -> bool:
        """Check if a format string is valid"""
        return format_str.lower() in cls.get_all_formats()


class RuleType(Enum):
    """Rule classification types"""
    CORE = "core"              # Essential system rules
    WORKFLOW = "workflow"      # Development workflow rules
    AGENT = "agent"           # Agent-specific rules
    PROJECT = "project"       # Project-specific rules
    CONTEXT = "context"       # Context management rules
    CUSTOM = "custom"         # User-defined rules

    @classmethod
    def get_all_types(cls) -> List[str]:
        """Get list of all rule types"""
        return [rule_type.value for rule_type in cls]

    @classmethod
    def is_valid_type(cls, type_str: str) -> bool:
        """Check if a type string is valid"""
        return type_str.lower() in cls.get_all_types()


class ConflictResolution(Enum):
    """Conflict resolution strategies"""
    MERGE = "merge"           # Intelligent merging
    OVERRIDE = "override"     # Last rule wins
    APPEND = "append"         # Combine content
    MANUAL = "manual"         # Require manual resolution

    @classmethod
    def get_all_strategies(cls) -> List[str]:
        """Get list of all resolution strategies"""
        return [strategy.value for strategy in cls]

    @classmethod
    def is_valid_strategy(cls, strategy_str: str) -> bool:
        """Check if a strategy string is valid"""
        return strategy_str.lower() in cls.get_all_strategies()


class InheritanceType(Enum):
    """Types of rule inheritance"""
    FULL = "full"             # Inherit all content and metadata
    CONTENT = "content"       # Inherit only content sections
    METADATA = "metadata"     # Inherit only metadata
    VARIABLES = "variables"   # Inherit only variables
    SELECTIVE = "selective"   # Inherit specific sections

    @classmethod
    def get_all_inheritance_types(cls) -> List[str]:
        """Get list of all inheritance types"""
        return [inheritance_type.value for inheritance_type in cls]

    @classmethod
    def is_valid_inheritance_type(cls, type_str: str) -> bool:
        """Check if an inheritance type string is valid"""
        return type_str.lower() in cls.get_all_inheritance_types()


class SyncOperation(Enum):
    """Types of synchronization operations"""
    PUSH = "push"             # Client to server
    PULL = "pull"             # Server to client
    BIDIRECTIONAL = "bidirectional"  # Both directions
    MERGE = "merge"           # Intelligent merge

    @classmethod
    def get_all_operations(cls) -> List[str]:
        """Get list of all sync operations"""
        return [operation.value for operation in cls]

    @classmethod
    def is_valid_operation(cls, operation_str: str) -> bool:
        """Check if an operation string is valid"""
        return operation_str.lower() in cls.get_all_operations()


class ClientAuthMethod(Enum):
    """Client authentication methods"""
    API_KEY = "api_key"
    TOKEN = "token"
    OAUTH2 = "oauth2"
    CERTIFICATE = "certificate"

    @classmethod
    def get_all_auth_methods(cls) -> List[str]:
        """Get list of all authentication methods"""
        return [method.value for method in cls]

    @classmethod
    def is_valid_auth_method(cls, method_str: str) -> bool:
        """Check if an auth method string is valid"""
        return method_str.lower() in cls.get_all_auth_methods()


class SyncStatus(Enum):
    """Synchronization status"""
    PENDING = "pending"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    FAILED = "failed"
    CONFLICT = "conflict"

    @classmethod
    def get_all_statuses(cls) -> List[str]:
        """Get list of all sync statuses"""
        return [status.value for status in cls]

    @classmethod
    def is_valid_status(cls, status_str: str) -> bool:
        """Check if a status string is valid"""
        return status_str.lower() in cls.get_all_statuses()

    @property
    def is_terminal(self) -> bool:
        """Check if this status is terminal (no further processing)"""
        return self in [SyncStatus.COMPLETED, SyncStatus.FAILED]

    @property
    def is_active(self) -> bool:
        """Check if this status indicates active processing"""
        return self in [SyncStatus.PENDING, SyncStatus.IN_PROGRESS] 