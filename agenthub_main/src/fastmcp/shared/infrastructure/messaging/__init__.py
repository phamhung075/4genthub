"""Messaging infrastructure for event-driven communication"""

from .event_bus import (
    EventBus,
    DomainEvent,
    EventMetadata,
    EventPriority,
    EventHandler,
    get_event_bus,
    set_event_bus
)

__all__ = [
    "EventBus",
    "DomainEvent",
    "EventMetadata", 
    "EventPriority",
    "EventHandler",
    "get_event_bus",
    "set_event_bus"
]