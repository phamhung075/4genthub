"""Event Bus Interface - Domain Layer"""

from abc import ABC, abstractmethod
from typing import Any, Callable, Dict, List, Optional, Type
from .event_store import IEvent


class IEventHandler(ABC):
    """Domain interface for event handlers"""
    
    @abstractmethod
    async def handle(self, event: IEvent) -> None:
        """Handle an event"""
        pass
    
    @property
    @abstractmethod
    def event_types(self) -> List[str]:
        """Get the event types this handler can process"""
        pass


class IEventBus(ABC):
    """Domain interface for event bus operations"""
    
    @abstractmethod
    async def publish(self, event: IEvent) -> None:
        """Publish an event to the bus"""
        pass
    
    @abstractmethod
    async def publish_many(self, events: List[IEvent]) -> None:
        """Publish multiple events to the bus"""
        pass
    
    @abstractmethod
    def subscribe(self, event_type: str, handler: IEventHandler) -> None:
        """Subscribe a handler to an event type"""
        pass
    
    @abstractmethod
    def unsubscribe(self, event_type: str, handler: IEventHandler) -> None:
        """Unsubscribe a handler from an event type"""
        pass
    
    @abstractmethod
    def subscribe_to_all(self, handler: IEventHandler) -> None:
        """Subscribe a handler to all event types"""
        pass
    
    @abstractmethod
    def get_handlers(self, event_type: str) -> List[IEventHandler]:
        """Get all handlers for an event type"""
        pass
    
    @abstractmethod
    async def start(self) -> None:
        """Start the event bus"""
        pass
    
    @abstractmethod
    async def stop(self) -> None:
        """Stop the event bus"""
        pass
    
    @abstractmethod
    def is_running(self) -> bool:
        """Check if the event bus is running"""
        pass


class IEventDispatcher(ABC):
    """Domain interface for event dispatching"""
    
    @abstractmethod
    async def dispatch(self, event: IEvent, handlers: List[IEventHandler]) -> None:
        """Dispatch an event to specific handlers"""
        pass
    
    @abstractmethod
    async def dispatch_in_order(self, event: IEvent, handlers: List[IEventHandler]) -> None:
        """Dispatch an event to handlers in sequential order"""
        pass
    
    @abstractmethod
    async def dispatch_parallel(self, event: IEvent, handlers: List[IEventHandler]) -> None:
        """Dispatch an event to handlers in parallel"""
        pass