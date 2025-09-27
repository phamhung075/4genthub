"""
Rule Management Domain Value Objects
Generated from enhanced_rule_orchestrator.py refactoring
Date: 2025-01-27

This file contains value objects and DTOs for rule management following DDD principles.
"""

from dataclasses import dataclass, field
from typing import Dict, Any, List, Optional
from ..enums.rule_enums import (
    ClientAuthMethod, SyncOperation, SyncStatus, 
    ConflictResolution, RuleType, RuleFormat
)
from ..entities.rule_entity import RuleContent, RuleInheritance


@dataclass
class ClientConfig:
    """Client configuration for synchronization - Value Object"""
    client_id: str
    client_name: str
    auth_method: ClientAuthMethod
    auth_credentials: Dict[str, Any]
    sync_permissions: List[str]
    rate_limit: int = 100  # requests per minute
    sync_frequency: int = 300  # seconds
    allowed_rule_types: List[RuleType] = field(default_factory=lambda: list(RuleType))
    auto_sync: bool = True
    conflict_resolution: ConflictResolution = ConflictResolution.MERGE
    last_sync: Optional[float] = None
    sync_history: List[str] = field(default_factory=list)

    def __post_init__(self):
        """Validate client configuration"""
        if not self.client_id:
            raise ValueError("Client ID cannot be empty")
        if not self.client_name:
            raise ValueError("Client name cannot be empty")
        if self.rate_limit <= 0:
            raise ValueError("Rate limit must be positive")
        if self.sync_frequency <= 0:
            raise ValueError("Sync frequency must be positive")

    def add_permission(self, permission: str) -> None:
        """Add a sync permission"""
        if permission not in self.sync_permissions:
            self.sync_permissions.append(permission)

    def remove_permission(self, permission: str) -> None:
        """Remove a sync permission"""
        if permission in self.sync_permissions:
            self.sync_permissions.remove(permission)

    def has_permission(self, permission: str) -> bool:
        """Check if client has a specific permission"""
        return permission in self.sync_permissions

    def can_sync_rule_type(self, rule_type: RuleType) -> bool:
        """Check if client can sync a specific rule type"""
        return rule_type in self.allowed_rule_types

    def add_to_history(self, entry: str) -> None:
        """Add entry to sync history"""
        self.sync_history.append(entry)
        # Keep only last 100 entries
        if len(self.sync_history) > 100:
            self.sync_history = self.sync_history[-100:]


@dataclass
class SyncRequest:
    """Synchronization request - Value Object"""
    request_id: str
    client_id: str
    operation: SyncOperation
    rules: Dict[str, Any]
    metadata: Dict[str, Any]
    timestamp: float
    priority: int = 1

    def __post_init__(self):
        """Validate sync request"""
        if not self.request_id:
            raise ValueError("Request ID cannot be empty")
        if not self.client_id:
            raise ValueError("Client ID cannot be empty")
        if self.priority < 1:
            raise ValueError("Priority must be at least 1")

    @property
    def is_high_priority(self) -> bool:
        """Check if this is a high priority request"""
        return self.priority >= 5


@dataclass
class SyncResult:
    """Result of synchronization operation - Value Object"""
    request_id: str
    client_id: str
    status: SyncStatus
    operation: SyncOperation
    processed_rules: List[str]
    conflicts: List[Dict[str, Any]]
    errors: List[str]
    warnings: List[str]
    sync_duration: float
    timestamp: float
    changes_applied: int = 0

    def __post_init__(self):
        """Validate sync result"""
        if not self.request_id:
            raise ValueError("Request ID cannot be empty")
        if not self.client_id:
            raise ValueError("Client ID cannot be empty")
        if self.sync_duration < 0:
            raise ValueError("Sync duration cannot be negative")

    @property
    def is_successful(self) -> bool:
        """Check if sync was successful"""
        return self.status == SyncStatus.COMPLETED and len(self.errors) == 0

    @property
    def has_conflicts(self) -> bool:
        """Check if sync has conflicts"""
        return len(self.conflicts) > 0

    @property
    def has_warnings(self) -> bool:
        """Check if sync has warnings"""
        return len(self.warnings) > 0

    def add_error(self, error: str) -> None:
        """Add an error to the result"""
        if error not in self.errors:
            self.errors.append(error)

    def add_warning(self, warning: str) -> None:
        """Add a warning to the result"""
        if warning not in self.warnings:
            self.warnings.append(warning)

    def add_conflict(self, conflict: Dict[str, Any]) -> None:
        """Add a conflict to the result"""
        self.conflicts.append(conflict)


@dataclass
class RuleConflict:
    """Rule conflict information - Value Object"""
    rule_path: str
    client_version: str
    server_version: str
    conflict_type: str
    client_content: str
    server_content: str
    suggested_resolution: str
    auto_resolvable: bool = False

    def __post_init__(self):
        """Validate rule conflict"""
        if not self.rule_path:
            raise ValueError("Rule path cannot be empty")
        if not self.conflict_type:
            raise ValueError("Conflict type cannot be empty")

    @property
    def requires_manual_resolution(self) -> bool:
        """Check if conflict requires manual resolution"""
        return not self.auto_resolvable


@dataclass
class CompositionResult:
    """Result of rule composition operation - Value Object"""
    composed_content: str
    source_rules: List[str]
    inheritance_chain: List[RuleInheritance]
    conflicts_resolved: List[str]
    composition_metadata: Dict[str, Any]
    success: bool = True
    warnings: List[str] = field(default_factory=list)

    def __post_init__(self):
        """Validate composition result"""
        if not self.composed_content and self.success:
            raise ValueError("Successful composition must have content")

    @property
    def has_warnings(self) -> bool:
        """Check if composition has warnings"""
        return len(self.warnings) > 0

    @property
    def has_inheritance(self) -> bool:
        """Check if composition involved inheritance"""
        return len(self.inheritance_chain) > 0

    def add_warning(self, warning: str) -> None:
        """Add a warning to the result"""
        if warning not in self.warnings:
            self.warnings.append(warning)


@dataclass
class CacheEntry:
    """Cache entry for rule content - Value Object"""
    content: RuleContent
    timestamp: float
    access_count: int
    ttl: float

    def __post_init__(self):
        """Validate cache entry"""
        if self.ttl <= 0:
            raise ValueError("TTL must be positive")
        if self.access_count < 0:
            raise ValueError("Access count cannot be negative")

    @property
    def is_expired(self) -> bool:
        """Check if cache entry is expired"""
        import time
        return time.time() > (self.timestamp + self.ttl)

    def increment_access(self) -> None:
        """Increment access count"""
        self.access_count += 1

    def update_timestamp(self) -> None:
        """Update timestamp to current time"""
        import time
        self.timestamp = time.time()


@dataclass
class RuleHierarchyInfo:
    """Information about rule hierarchy - Value Object"""
    total_rules: int
    max_depth: int
    inheritance_relationships: int
    circular_dependencies: List[List[str]]
    rule_types_distribution: Dict[str, int]
    format_distribution: Dict[str, int]

    def __post_init__(self):
        """Validate hierarchy info"""
        if self.total_rules < 0:
            raise ValueError("Total rules cannot be negative")
        if self.max_depth < 0:
            raise ValueError("Max depth cannot be negative")

    @property
    def has_circular_dependencies(self) -> bool:
        """Check if hierarchy has circular dependencies"""
        return len(self.circular_dependencies) > 0

    @property
    def is_healthy(self) -> bool:
        """Check if hierarchy is healthy (no circular dependencies)"""
        return not self.has_circular_dependencies 