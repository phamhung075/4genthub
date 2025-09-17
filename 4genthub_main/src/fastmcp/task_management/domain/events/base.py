"""Base domain event class for the Vision System."""

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Dict, Any, Optional
from uuid import UUID, uuid4


class DomainEvent(ABC):
    """
    Abstract base class for all domain events in the Vision System.
    
    This is not a dataclass itself to avoid inheritance issues with frozen dataclasses.
    Subclasses should be frozen dataclasses and include event metadata fields.
    """
    
    @property
    @abstractmethod
    def event_type(self) -> str:
        """Return the type/name of this event."""
        pass
    
    @abstractmethod
    def to_dict(self) -> Dict[str, Any]:
        """Convert event to dictionary for serialization."""
        pass


# Helper function to create event metadata
def create_event_metadata() -> Dict[str, Any]:
    """Create default event metadata for domain events."""
    return {
        "event_id": uuid4(),
        "occurred_at": datetime.now(timezone.utc),
        "aggregate_id": None,
        "aggregate_type": None
    }