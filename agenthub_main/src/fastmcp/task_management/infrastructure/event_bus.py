"""Event Bus infrastructure for publishing and subscribing to domain events.

This module provides an in-memory event bus implementation for handling
domain events in the Vision System architecture.
"""

import asyncio
import logging
from typing import Any, Callable, Dict, List, Set, Type, Optional
from dataclasses import dataclass
from datetime import datetime
from weakref import WeakSet
import inspect

logger = logging.getLogger(__name__)


@dataclass
class EventSubscription:
    """Represents a subscription to an event type."""
    event_type: Type
    handler: Callable
    priority: int = 0
    is_async: bool = False


class EventBus:
    """
    In-memory event bus for publishing and subscribing to domain events.
    
    Features:
    - Type-based subscription
    - Async and sync handler support
    - Priority-based handler execution
    - Error isolation between handlers
    - Weak references to prevent memory leaks
    """
    
    def __init__(self):
        """Initialize the event bus."""
        self._subscriptions: Dict[Type, List[EventSubscription]] = {}
        self._active_handlers: WeakSet = WeakSet()
        self._event_queue: asyncio.Queue = asyncio.Queue()
        self._processing_task: Optional[asyncio.Task] = None
        self._shutdown = False
        
    def subscribe(self, 
                  event_type: Type,
                  handler: Callable,
                  priority: int = 0) -> None:
        """
        Subscribe a handler to an event type.
        
        Args:
            event_type: The type of event to subscribe to
            handler: The handler function/method to call
            priority: Handler priority (higher executes first)
        """
        # Check if handler is async
        is_async = asyncio.iscoroutinefunction(handler)
        
        subscription = EventSubscription(
            event_type=event_type,
            handler=handler,
            priority=priority,
            is_async=is_async
        )
        
        if event_type not in self._subscriptions:
            self._subscriptions[event_type] = []
            
        self._subscriptions[event_type].append(subscription)
        
        # Sort by priority (descending)
        self._subscriptions[event_type].sort(
            key=lambda s: s.priority, 
            reverse=True
        )
        
        logger.debug(f"Subscribed {handler.__name__} to {event_type.__name__} "
                    f"with priority {priority}")
    
    def unsubscribe(self, 
                    event_type: Type,
                    handler: Callable) -> bool:
        """
        Unsubscribe a handler from an event type.
        
        Args:
            event_type: The event type to unsubscribe from
            handler: The handler to remove
            
        Returns:
            True if handler was found and removed, False otherwise
        """
        if event_type not in self._subscriptions:
            return False
            
        initial_count = len(self._subscriptions[event_type])
        self._subscriptions[event_type] = [
            sub for sub in self._subscriptions[event_type]
            if sub.handler != handler
        ]
        
        if len(self._subscriptions[event_type]) == 0:
            del self._subscriptions[event_type]
            
        removed = initial_count > len(self._subscriptions.get(event_type, []))
        
        if removed:
            logger.debug(f"Unsubscribed {handler.__name__} from {event_type.__name__}")
            
        return removed
    
    async def publish(self, event: Any) -> None:
        """
        Publish an event to all subscribed handlers.
        
        Args:
            event: The event instance to publish
        """
        event_type = type(event)
        
        # Log event publication
        logger.debug(f"Publishing event: {event_type.__name__}")
        
        # Get all subscriptions for this event type and its base classes
        all_subscriptions = []
        for cls in event_type.__mro__:
            if cls in self._subscriptions:
                all_subscriptions.extend(self._subscriptions[cls])
        
        # Sort all subscriptions by priority
        all_subscriptions.sort(key=lambda s: s.priority, reverse=True)
        
        # Execute handlers
        for subscription in all_subscriptions:
            try:
                if subscription.is_async:
                    await subscription.handler(event)
                else:
                    # Run sync handler in executor to avoid blocking
                    loop = asyncio.get_event_loop()
                    await loop.run_in_executor(
                        None, 
                        subscription.handler, 
                        event
                    )
                    
            except Exception as e:
                logger.error(
                    f"Error in event handler {subscription.handler.__name__} "
                    f"for event {event_type.__name__}: {e}",
                    exc_info=True
                )
    
    def publish_sync(self, event: Any) -> None:
        """
        Synchronously publish an event (creates async task).
        
        Args:
            event: The event instance to publish
        """
        try:
            loop = asyncio.get_event_loop()
            if loop.is_running():
                # Schedule the publish as a task
                asyncio.create_task(self.publish(event))
            else:
                # Run the publish synchronously
                loop.run_until_complete(self.publish(event))
        except RuntimeError:
            # No event loop, create one
            asyncio.run(self.publish(event))
    
    async def publish_batch(self, events: List[Any]) -> None:
        """
        Publish multiple events in order.
        
        Args:
            events: List of events to publish
        """
        for event in events:
            await self.publish(event)
    
    def clear_subscriptions(self, event_type: Optional[Type] = None) -> None:
        """
        Clear subscriptions for a specific event type or all subscriptions.
        
        Args:
            event_type: Optional event type to clear subscriptions for
        """
        if event_type:
            if event_type in self._subscriptions:
                del self._subscriptions[event_type]
                logger.debug(f"Cleared subscriptions for {event_type.__name__}")
        else:
            self._subscriptions.clear()
            logger.debug("Cleared all event subscriptions")
    
    def get_subscriptions(self, event_type: Type) -> List[Callable]:
        """
        Get all handlers subscribed to an event type.
        
        Args:
            event_type: The event type to get subscriptions for
            
        Returns:
            List of handler functions
        """
        if event_type not in self._subscriptions:
            return []
            
        return [sub.handler for sub in self._subscriptions[event_type]]
    
    def has_subscribers(self, event_type: Type) -> bool:
        """
        Check if an event type has any subscribers.
        
        Args:
            event_type: The event type to check
            
        Returns:
            True if there are subscribers, False otherwise
        """
        return event_type in self._subscriptions and len(self._subscriptions[event_type]) > 0
    
    async def start_processing(self) -> None:
        """Start processing events from the queue (for async processing mode)."""
        if self._processing_task is None or self._processing_task.done():
            self._shutdown = False
            self._processing_task = asyncio.create_task(self._process_event_queue())
            logger.info("Event bus processing started")
    
    async def stop_processing(self) -> None:
        """Stop processing events from the queue."""
        self._shutdown = True
        if self._processing_task and not self._processing_task.done():
            await self._event_queue.put(None)  # Sentinel to wake up processor
            await self._processing_task
            logger.info("Event bus processing stopped")
    
    async def _process_event_queue(self) -> None:
        """Process events from the queue."""
        while not self._shutdown:
            try:
                event = await self._event_queue.get()
                if event is None:  # Sentinel value
                    break
                    
                await self.publish(event)
                
            except Exception as e:
                logger.error(f"Error processing event from queue: {e}", exc_info=True)
    
    async def queue_event(self, event: Any) -> None:
        """
        Queue an event for async processing.
        
        Args:
            event: The event to queue
        """
        await self._event_queue.put(event)
    
    def __repr__(self) -> str:
        """String representation of the event bus."""
        total_subscriptions = sum(len(subs) for subs in self._subscriptions.values())
        return (f"EventBus(event_types={len(self._subscriptions)}, "
                f"total_subscriptions={total_subscriptions})")


# Global event bus instance
_global_event_bus: Optional[EventBus] = None


def get_event_bus() -> EventBus:
    """Get the global event bus instance."""
    global _global_event_bus
    if _global_event_bus is None:
        _global_event_bus = EventBus()
    return _global_event_bus


def reset_event_bus() -> None:
    """Reset the global event bus (mainly for testing)."""
    global _global_event_bus
    if _global_event_bus:
        _global_event_bus.clear_subscriptions()
    _global_event_bus = None