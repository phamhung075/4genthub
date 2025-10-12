"""
Base domain event classes following DDD principles.

This module provides the foundation for all domain events in the system.
Events are immutable, self-contained records of state changes in aggregates.
"""

from abc import ABC
from dataclasses import dataclass, field, asdict
from datetime import datetime, timezone
from typing import Dict, Any, Optional
from uuid import UUID, uuid4


@dataclass(frozen=True)
class BaseDomainEvent(ABC):
    """
    Base class for all domain events following DDD principles.

    Design Principles:
    - Immutable: Events are frozen dataclasses (cannot be modified after creation)
    - Self-Contained: Events contain all data needed by handlers
    - Timestamped: All events record when they occurred
    - Identifiable: Each event has a unique ID
    - Traceable: Events track the aggregate they relate to

    All domain events should inherit from this class and add their specific fields.
    """

    # Event metadata (common to all events)
    event_id: UUID = field(default_factory=uuid4)
    occurred_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    aggregate_id: Optional[str] = None
    aggregate_type: Optional[str] = None
    user_id: Optional[str] = None

    @property
    def event_type(self) -> str:
        """
        Return the type name of this event.

        By default, uses the class name. Override for custom event type names.
        """
        return self.__class__.__name__

    def to_dict(self) -> Dict[str, Any]:
        """
        Convert event to dictionary for serialization.

        Handles UUID and datetime serialization automatically.
        Override to customize serialization if needed.
        """
        data = asdict(self)
        # Convert UUID to string
        if isinstance(data.get('event_id'), UUID):
            data['event_id'] = str(data['event_id'])
        # Convert datetime to ISO format
        if isinstance(data.get('occurred_at'), datetime):
            data['occurred_at'] = data['occurred_at'].isoformat()
        # Add event type
        data['event_type'] = self.event_type
        return data

    def __repr__(self) -> str:
        """Human-readable representation of the event."""
        return f"{self.event_type}(event_id={self.event_id}, occurred_at={self.occurred_at})"


# Alias for backward compatibility
DomainEvent = BaseDomainEvent


# Helper function to create event metadata dictionary
def create_event_metadata() -> Dict[str, Any]:
    """
    Factory function to create event metadata dictionary.

    Returns:
        Empty dictionary for event metadata

    Used as default_factory for metadata fields in events.
    """
    return {}


# Helper function to create event with metadata
def create_domain_event(
    event_class: type,
    aggregate_id: Optional[str] = None,
    aggregate_type: Optional[str] = None,
    user_id: Optional[str] = None,
    **kwargs
) -> BaseDomainEvent:
    """
    Factory function to create domain events with automatic metadata.

    Args:
        event_class: The event class to instantiate
        aggregate_id: ID of the aggregate this event relates to
        aggregate_type: Type/name of the aggregate
        user_id: ID of the user who triggered this event
        **kwargs: Additional event-specific fields

    Returns:
        Instance of the event class with metadata populated

    Example:
        event = create_domain_event(
            TaskCreatedEvent,
            aggregate_id="task-123",
            aggregate_type="Task",
            user_id="user-456",
            title="Implement feature X",
            status="todo"
        )
    """
    return event_class(
        aggregate_id=aggregate_id,
        aggregate_type=aggregate_type,
        user_id=user_id,
        **kwargs
    )