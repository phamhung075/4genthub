"""BaseTimestampEntity - Single Source of Truth for Timestamp Management.

This module implements the foundation of clean timestamp architecture following
DDD patterns. NO LEGACY COMPATIBILITY - clean implementation only.

Key principles:
- Single source of truth: all timestamp logic centralised here
- Domain events emitted for creation/updates
- Immutable creation timestamp enforced
- Automatic conversion to UTC
- Domain layer owns business rules
"""

from __future__ import annotations

import logging
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any, Dict, List

from ...events.base import DomainEvent, create_event_metadata

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class TimestampUpdatedEvent(DomainEvent):
    """Domain event fired when entity timestamp is updated."""

    entity_id: str
    old_timestamp: datetime | None
    new_timestamp: datetime
    metadata: Dict[str, Any] = field(default_factory=create_event_metadata)

    @property
    def event_type(self) -> str:
        return "timestamp_updated"

    def to_dict(self) -> Dict[str, Any]:
        return {
            "event_type": self.event_type,
            "entity_id": self.entity_id,
            "old_timestamp": self.old_timestamp.isoformat() if self.old_timestamp else None,
            "new_timestamp": self.new_timestamp.isoformat(),
            "metadata": self.metadata
        }


@dataclass(frozen=True)
class TimestampCreatedEvent(DomainEvent):
    """Domain event fired when entity is first created."""

    entity_id: str
    created_timestamp: datetime
    metadata: Dict[str, Any] = field(default_factory=create_event_metadata)

    @property
    def event_type(self) -> str:
        return "timestamp_created"

    def to_dict(self) -> Dict[str, Any]:
        return {
            "event_type": self.event_type,
            "entity_id": self.entity_id,
            "created_timestamp": self.created_timestamp.isoformat(),
            "metadata": self.metadata
        }


@dataclass
class BaseTimestampEntity(ABC):
    """Base entity with automatic timestamp management following DDD patterns.

    This class provides the SINGLE SOURCE OF TRUTH for all timestamp handling
    in the agenthub system. All domain entities MUST inherit from this class.

    Features:
    - Automatic created_at/updated_at management
    - Domain events for timestamp changes
    - UTC timezone enforcement
    - Immutable creation timestamp
    - Clean touch() method for updates

    NO LEGACY SUPPORT:
    - No manual timestamp setting methods
    - No backward compatibility with old patterns
    - No fallback mechanisms

    Usage:
        class Task(BaseTimestampEntity):
            title: str

            def _get_entity_id(self) -> str:
                return str(self.id) if self.id else "unknown"
    """

    # Timestamp fields - managed automatically
    created_at: datetime | None = None
    updated_at: datetime | None = None

    # Domain events collection
    _domain_events: List[DomainEvent] = field(default_factory=list, init=False, repr=False)

    def __post_init__(self) -> None:
        """Initialise timestamps and validate entity state."""
        self._ensure_clean_timestamps()
        self._validate_entity()

    @abstractmethod
    def _get_entity_id(self) -> str:
        """Get the unique identifier for this entity.

        Must be implemented by concrete entity classes.
        Used for domain events and logging.

        Returns:
            str: Unique identifier for this entity
        """
        pass

    @abstractmethod
    def _validate_entity(self) -> None:
        """Validate entity business rules.

        Implementation must enforce entity-specific invariants. Called during
        initialisation and after timestamp updates.
        """
        raise NotImplementedError

    def _ensure_clean_timestamps(self) -> None:
        """Ensure timestamps exist, are UTC, and consistent."""
        now = datetime.now(timezone.utc)

        is_new_entity = self.created_at is None and self.updated_at is None

        if self.created_at is None:
            logger.debug("Setting created_at for %s", self._get_entity_id())
            self.created_at = now
        else:
            self.created_at = self._coerce_to_utc(self.created_at)

        if self.updated_at is None:
            logger.debug("Setting updated_at for %s", self._get_entity_id())
            self.updated_at = now
        else:
            self.updated_at = self._coerce_to_utc(self.updated_at)

        if self.updated_at < self.created_at:
            raise ValueError(
                f"Entity {self._get_entity_id()} has updated_at earlier than created_at"
            )

        if is_new_entity:
            event = TimestampCreatedEvent(
                entity_id=self._get_entity_id(),
                created_timestamp=self.created_at
            )
            self._add_domain_event(event)


    @staticmethod
    def _coerce_to_utc(value: datetime) -> datetime:
        """Return a timezone-aware UTC datetime."""
        if value.tzinfo is None:
            return value.replace(tzinfo=timezone.utc)
        if value.tzinfo != timezone.utc:
            return value.astimezone(timezone.utc)
        return value

    def touch(self, reason: str = "entity_updated") -> None:
        """Update the entity's timestamp and fire domain event.

        This is the ONLY method that should be used to update timestamps.
        It enforces business rules and maintains audit trail through events.

        Args:
            reason: Business reason for the update (for logging and events)
        """
        old_timestamp = self.updated_at
        self.updated_at = datetime.now(timezone.utc)

        logger.debug(f"Entity {self._get_entity_id()} touched: {reason}")

        # Fire domain event for timestamp update
        event = TimestampUpdatedEvent(
            entity_id=self._get_entity_id(),
            old_timestamp=old_timestamp,
            new_timestamp=self.updated_at
        )
        self._add_domain_event(event)

        # Validate entity state after update
        self._validate_entity()

    def is_newer_than(self, other: 'BaseTimestampEntity') -> bool:
        """Check if this entity is newer than another entity.

        Compares updated_at timestamps with proper null handling.

        Args:
            other: Another BaseTimestampEntity to compare against

        Returns:
            bool: True if this entity is newer
        """
        if not self.updated_at:
            return False
        if not other.updated_at:
            return True
        return self.updated_at > other.updated_at

    def get_age_seconds(self) -> float | None:
        """Get the age of this entity in seconds since creation.

        Returns:
            float | None: Age in seconds, or None if created_at not set
        """
        if not self.created_at:
            return None
        return (datetime.now(timezone.utc) - self.created_at).total_seconds()

    def get_staleness_seconds(self) -> float | None:
        """Get staleness in seconds since last update.

        Returns:
            float | None: Seconds since last update, or None if updated_at not set
        """
        if not self.updated_at:
            return None
        return (datetime.now(timezone.utc) - self.updated_at).total_seconds()

    def _add_domain_event(self, event: DomainEvent) -> None:
        """Add a domain event to the entity's event collection.

        Args:
            event: Domain event to add
        """
        if not hasattr(self, '_domain_events'):
            self._domain_events = []
        self._domain_events.append(event)
        logger.debug(f"Added domain event: {event}")

    def get_domain_events(self) -> List[DomainEvent]:
        """Get all domain events for this entity.

        Returns:
            List[DomainEvent]: Copy of domain events list
        """
        if not hasattr(self, '_domain_events'):
            return []
        return self._domain_events.copy()

    def clear_domain_events(self) -> None:
        """Clear all domain events after they have been processed.

        Typically called by repository after persisting events.
        """
        if hasattr(self, '_domain_events'):
            self._domain_events.clear()
        logger.debug(f"Cleared domain events for entity {self._get_entity_id()}")

    def to_timestamp_dict(self) -> Dict[str, Any]:
        """Export timestamp information as dictionary.

        Useful for serialization, logging, and debugging.

        Returns:
            Dict[str, Any]: Dictionary containing timestamp information
        """
        return {
            "entity_id": self._get_entity_id(),
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
            "age_seconds": self.get_age_seconds(),
            "staleness_seconds": self.get_staleness_seconds(),
            "domain_events_count": len(self.get_domain_events())
        }

    def __repr__(self) -> str:
        """String representation including timestamp info."""
        return (
            f"{self.__class__.__name__}("
            f"id={self._get_entity_id()}, "
            f"created_at={self.created_at}, "
            f"updated_at={self.updated_at})"
        )
