"""Context Domain Events"""

from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any, Dict, Optional
from uuid import UUID, uuid4

from .base import DomainEvent


@dataclass(frozen=True)
class ContextCreated(DomainEvent):
    """Event raised when a context is created"""
    context_id: str
    level: str  # global, project, branch, task
    created_by: str
    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    event_id: UUID = field(default_factory=uuid4)
    
    @property
    def event_type(self) -> str:
        return "ContextCreated"
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "event_type": self.event_type,
            "event_id": str(self.event_id),
            "context_id": self.context_id,
            "level": self.level,
            "created_by": self.created_by,
            "created_at": self.created_at.isoformat(),
            "occurred_at": self.created_at.isoformat()
        }


@dataclass(frozen=True)
class ContextUpdated(DomainEvent):
    """Event raised when a context is updated"""
    context_id: str
    level: str
    updated_by: str
    changes: Dict[str, Any]
    updated_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    event_id: UUID = field(default_factory=uuid4)
    
    @property
    def event_type(self) -> str:
        return "ContextUpdated"
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "event_type": self.event_type,
            "event_id": str(self.event_id),
            "context_id": self.context_id,
            "level": self.level,
            "updated_by": self.updated_by,
            "changes": self.changes,
            "updated_at": self.updated_at.isoformat(),
            "occurred_at": self.updated_at.isoformat()
        }


@dataclass(frozen=True)
class ContextDelegated(DomainEvent):
    """Event raised when context data is delegated to a higher level"""
    source_context_id: str
    source_level: str
    target_level: str
    delegated_data: Dict[str, Any]
    delegation_reason: str
    delegated_by: str
    delegated_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    event_id: UUID = field(default_factory=uuid4)
    
    @property
    def event_type(self) -> str:
        return "ContextDelegated"
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "event_type": self.event_type,
            "event_id": str(self.event_id),
            "source_context_id": self.source_context_id,
            "source_level": self.source_level,
            "target_level": self.target_level,
            "delegated_data": self.delegated_data,
            "delegation_reason": self.delegation_reason,
            "delegated_by": self.delegated_by,
            "delegated_at": self.delegated_at.isoformat(),
            "occurred_at": self.delegated_at.isoformat()
        }


@dataclass(frozen=True)
class ContextInsightAdded(DomainEvent):
    """Event raised when an insight is added to a context"""
    context_id: str
    level: str
    insight_content: str
    insight_category: str
    importance: str
    added_by: str
    added_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    event_id: UUID = field(default_factory=uuid4)
    
    @property
    def event_type(self) -> str:
        return "ContextInsightAdded"
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "event_type": self.event_type,
            "event_id": str(self.event_id),
            "context_id": self.context_id,
            "level": self.level,
            "insight_content": self.insight_content,
            "insight_category": self.insight_category,
            "importance": self.importance,
            "added_by": self.added_by,
            "added_at": self.added_at.isoformat(),
            "occurred_at": self.added_at.isoformat()
        }


@dataclass(frozen=True)
class ContextProgressAdded(DomainEvent):
    """Event raised when progress update is added to a context"""
    context_id: str
    level: str
    progress_content: str
    added_by: str
    added_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    event_id: UUID = field(default_factory=uuid4)
    
    @property
    def event_type(self) -> str:
        return "ContextProgressAdded"
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "event_type": self.event_type,
            "event_id": str(self.event_id),
            "context_id": self.context_id,
            "level": self.level,
            "progress_content": self.progress_content,
            "added_by": self.added_by,
            "added_at": self.added_at.isoformat(),
            "occurred_at": self.added_at.isoformat()
        }


@dataclass(frozen=True)
class ContextInheritanceResolved(DomainEvent):
    """Event raised when context inheritance is resolved"""
    context_id: str
    level: str
    inheritance_chain: list[str]
    resolved_by: str
    resolved_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    event_id: UUID = field(default_factory=uuid4)
    
    @property
    def event_type(self) -> str:
        return "ContextInheritanceResolved"
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "event_type": self.event_type,
            "event_id": str(self.event_id),
            "context_id": self.context_id,
            "level": self.level,
            "inheritance_chain": self.inheritance_chain,
            "resolved_by": self.resolved_by,
            "resolved_at": self.resolved_at.isoformat(),
            "occurred_at": self.resolved_at.isoformat()
        }