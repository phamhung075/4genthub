"""Event Store Interface - Domain Layer"""

from abc import ABC, abstractmethod
from typing import Any, List, Optional, Dict
from datetime import datetime


class IEvent(ABC):
    """Domain interface for events"""
    
    @property
    @abstractmethod
    def event_type(self) -> str:
        """Get the event type"""
        pass
    
    @property
    @abstractmethod
    def event_data(self) -> Dict[str, Any]:
        """Get the event data"""
        pass
    
    @property
    @abstractmethod
    def timestamp(self) -> datetime:
        """Get the event timestamp"""
        pass
    
    @property
    @abstractmethod
    def aggregate_id(self) -> str:
        """Get the aggregate ID"""
        pass


class IEventStore(ABC):
    """Domain interface for event storage operations"""
    
    @abstractmethod
    def append(self, aggregate_id: str, events: List[IEvent]) -> None:
        """Append events to the event store"""
        pass
    
    @abstractmethod
    def get_events(self, aggregate_id: str, from_version: int = 0) -> List[IEvent]:
        """Get events for an aggregate"""
        pass
    
    @abstractmethod
    def get_all_events(self, event_type: Optional[str] = None) -> List[IEvent]:
        """Get all events, optionally filtered by type"""
        pass
    
    @abstractmethod
    def get_events_by_type(self, event_type: str) -> List[IEvent]:
        """Get events by type"""
        pass
    
    @abstractmethod
    def store_event(self, event: IEvent) -> None:
        """Store a single event"""
        pass