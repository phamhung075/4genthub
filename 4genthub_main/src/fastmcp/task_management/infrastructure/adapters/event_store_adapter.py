"""Event Store Adapter - Infrastructure Layer"""

from typing import Any, List, Optional, Dict
from datetime import datetime

from ...domain.interfaces.event_store import IEvent, IEventStore
from ..event_store import EventStore, Event


class EventAdapter(IEvent):
    """Adapter for infrastructure Event to domain IEvent"""
    
    def __init__(self, infrastructure_event: Event):
        self._event = infrastructure_event
    
    @property
    def event_type(self) -> str:
        """Get the event type"""
        return self._event.event_type
    
    @property
    def event_data(self) -> Dict[str, Any]:
        """Get the event data"""
        return self._event.event_data
    
    @property
    def timestamp(self) -> datetime:
        """Get the event timestamp"""
        return self._event.timestamp
    
    @property
    def aggregate_id(self) -> str:
        """Get the aggregate ID"""
        return self._event.aggregate_id


class EventStoreAdapter(IEventStore):
    """Adapter for infrastructure EventStore to domain IEventStore"""
    
    def __init__(self):
        self._event_store = EventStore()
    
    def append(self, aggregate_id: str, events: List[IEvent]) -> None:
        """Append events to the event store"""
        # Convert domain events to infrastructure events
        infra_events = []
        for event in events:
            infra_event = Event(
                event_type=event.event_type,
                event_data=event.event_data,
                aggregate_id=event.aggregate_id,
                timestamp=event.timestamp
            )
            infra_events.append(infra_event)
        
        self._event_store.append(aggregate_id, infra_events)
    
    def get_events(self, aggregate_id: str, from_version: int = 0) -> List[IEvent]:
        """Get events for an aggregate"""
        infra_events = self._event_store.get_events(aggregate_id, from_version)
        return [EventAdapter(event) for event in infra_events]
    
    def get_all_events(self, event_type: Optional[str] = None) -> List[IEvent]:
        """Get all events, optionally filtered by type"""
        infra_events = self._event_store.get_all_events(event_type)
        return [EventAdapter(event) for event in infra_events]
    
    def get_events_by_type(self, event_type: str) -> List[IEvent]:
        """Get events by type"""
        infra_events = self._event_store.get_events_by_type(event_type)
        return [EventAdapter(event) for event in infra_events]
    
    def store_event(self, event: IEvent) -> None:
        """Store a single event"""
        infra_event = Event(
            event_type=event.event_type,
            event_data=event.event_data,
            aggregate_id=event.aggregate_id,
            timestamp=event.timestamp
        )
        self._event_store.store_event(infra_event)