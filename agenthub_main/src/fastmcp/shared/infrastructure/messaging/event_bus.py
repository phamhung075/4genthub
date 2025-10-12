"""Event Bus for Real-time Messaging and Event Distribution

This module provides a centralized event bus for publishing and subscribing
to domain events across the application with support for async handlers.
"""

import asyncio
import logging
from typing import Dict, List, Type, Callable, Any, Optional, Set, Tuple
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
import uuid
import inspect

logger = logging.getLogger(__name__)


class EventPriority(Enum):
    """Event priority levels"""
    LOW = 1
    NORMAL = 2
    HIGH = 3
    CRITICAL = 4


@dataclass
class EventMetadata:
    """Metadata for published events"""
    event_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    timestamp: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    source: Optional[str] = None
    user_id: Optional[str] = None
    correlation_id: Optional[str] = None
    priority: EventPriority = EventPriority.NORMAL
    retry_count: int = 0
    max_retries: int = 3


@dataclass
class DomainEvent:
    """Base class for domain events"""
    metadata: EventMetadata = field(default_factory=EventMetadata)
    
    def get_event_name(self) -> str:
        """Get the event name"""
        return self.__class__.__name__


class EventHandler:
    """Wrapper for event handlers with metadata"""
    
    def __init__(
        self,
        handler: Callable,
        event_type: Type[DomainEvent],
        filter_func: Optional[Callable] = None,
        priority: int = 0,
        is_async: bool = None
    ):
        self.handler = handler
        self.event_type = event_type
        self.filter_func = filter_func
        self.priority = priority
        
        # Auto-detect if handler is async
        if is_async is None:
            self.is_async = inspect.iscoroutinefunction(handler)
        else:
            self.is_async = is_async
        
        # Metrics
        self.call_count = 0
        self.error_count = 0
        self.total_duration_ms = 0
    
    async def handle(self, event: DomainEvent) -> Any:
        """Execute the handler"""
        # Apply filter if provided
        if self.filter_func and not self.filter_func(event):
            return None
        
        start_time = datetime.now(timezone.utc)
        self.call_count += 1
        
        try:
            if self.is_async:
                result = await self.handler(event)
            else:
                result = self.handler(event)
            
            # Track duration
            duration = (datetime.now(timezone.utc) - start_time).total_seconds() * 1000
            self.total_duration_ms += duration
            
            return result
            
        except Exception as e:
            self.error_count += 1
            raise
    
    @property
    def avg_duration_ms(self) -> float:
        """Get average handler duration"""
        if self.call_count == 0:
            return 0
        return self.total_duration_ms / self.call_count


class EventBus:
    """
    Centralized event bus for domain event publishing and handling.
    
    Features:
    - Async event handlers
    - Priority-based handler execution
    - Event filtering
    - Retry mechanism
    - Dead letter queue
    - Performance metrics
    """
    
    def __init__(
        self,
        max_queue_size: int = 10000,
        enable_dead_letter_queue: bool = True,
        worker_count: int = 4
    ):
        """Initialize the event bus"""
        self.max_queue_size = max_queue_size
        self.enable_dead_letter_queue = enable_dead_letter_queue
        self.worker_count = worker_count
        
        # Handler registry
        self._handlers: Dict[Type[DomainEvent], List[EventHandler]] = {}
        self._global_handlers: List[EventHandler] = []  # Handlers for all events
        
        # Event queue
        self._event_queue: asyncio.Queue = asyncio.Queue(maxsize=max_queue_size)
        
        # Dead letter queue for failed events
        self._dead_letter_queue: List[Tuple[DomainEvent, Exception]] = []
        
        # Worker tasks
        self._workers: List[asyncio.Task] = []
        self._is_running = False
        
        # Metrics
        self.metrics = {
            "events_published": 0,
            "events_processed": 0,
            "events_failed": 0,
            "events_retried": 0,
            "queue_size": 0,
            "dead_letter_size": 0,
            "handler_errors": {}
        }
    
    async def start(self) -> None:
        """Start the event bus workers"""
        if self._is_running:
            return
        
        self._is_running = True
        
        # Start worker tasks
        for i in range(self.worker_count):
            worker = asyncio.create_task(self._process_events(f"worker-{i}"))
            self._workers.append(worker)
        
        logger.info(f"Event bus started with {self.worker_count} workers")
    
    async def stop(self) -> None:
        """Stop the event bus"""
        self._is_running = False
        
        # Wait for queue to empty
        await self._event_queue.join()
        
        # Cancel workers
        for worker in self._workers:
            worker.cancel()
            try:
                await worker
            except asyncio.CancelledError:
                pass
        
        self._workers.clear()
        logger.info("Event bus stopped")
    
    def subscribe(
        self,
        event_type: Type[DomainEvent],
        handler: Callable,
        filter_func: Optional[Callable] = None,
        priority: int = 0
    ) -> str:
        """
        Subscribe to an event type.
        
        Args:
            event_type: The event class to subscribe to
            handler: Async or sync function to handle the event
            filter_func: Optional filter function (event) -> bool
            priority: Handler priority (higher = executed first)
            
        Returns:
            Subscription ID
        """
        handler_wrapper = EventHandler(
            handler=handler,
            event_type=event_type,
            filter_func=filter_func,
            priority=priority
        )
        
        if event_type not in self._handlers:
            self._handlers[event_type] = []
        
        self._handlers[event_type].append(handler_wrapper)
        
        # Sort by priority
        self._handlers[event_type].sort(key=lambda h: h.priority, reverse=True)
        
        subscription_id = f"{event_type.__name__}_{id(handler)}"
        logger.debug(f"Subscribed handler to {event_type.__name__}")
        
        return subscription_id
    
    def subscribe_all(
        self,
        handler: Callable,
        filter_func: Optional[Callable] = None,
        priority: int = 0
    ) -> str:
        """Subscribe to all events"""
        handler_wrapper = EventHandler(
            handler=handler,
            event_type=DomainEvent,
            filter_func=filter_func,
            priority=priority
        )
        
        self._global_handlers.append(handler_wrapper)
        self._global_handlers.sort(key=lambda h: h.priority, reverse=True)
        
        subscription_id = f"global_{id(handler)}"
        logger.debug("Subscribed global handler")
        
        return subscription_id
    
    def unsubscribe(self, event_type: Type[DomainEvent], handler: Callable) -> bool:
        """Unsubscribe from an event type"""
        if event_type not in self._handlers:
            return False
        
        original_count = len(self._handlers[event_type])
        self._handlers[event_type] = [
            h for h in self._handlers[event_type]
            if h.handler != handler
        ]
        
        removed = len(self._handlers[event_type]) < original_count
        
        # Clean up empty lists
        if not self._handlers[event_type]:
            del self._handlers[event_type]
        
        return removed
    
    async def publish(
        self,
        event: DomainEvent,
        priority: EventPriority = EventPriority.NORMAL,
        correlation_id: Optional[str] = None,
        user_id: Optional[str] = None
    ) -> None:
        """
        Publish an event to the bus.
        
        Args:
            event: The domain event to publish
            priority: Event priority
            correlation_id: Optional correlation ID for tracing
            user_id: Optional user ID for audit
        """
        # Update metadata
        event.metadata.priority = priority
        if correlation_id:
            event.metadata.correlation_id = correlation_id
        if user_id:
            event.metadata.user_id = user_id
        
        # Add to queue
        try:
            await self._event_queue.put(event)
            self.metrics["events_published"] += 1
            self.metrics["queue_size"] = self._event_queue.qsize()
            
            logger.debug(
                f"Published event {event.get_event_name()} "
                f"with priority {priority.name}"
            )
            
        except asyncio.QueueFull:
            logger.error(
                f"Event queue full, dropping event {event.get_event_name()}"
            )
            raise
    
    async def publish_batch(
        self,
        events: List[DomainEvent],
        priority: EventPriority = EventPriority.NORMAL
    ) -> None:
        """Publish multiple events"""
        for event in events:
            await self.publish(event, priority)
    
    async def _process_events(self, worker_name: str) -> None:
        """Worker task to process events from queue"""
        logger.info(f"Event worker {worker_name} started")
        
        while self._is_running:
            try:
                # Get event from queue
                event = await asyncio.wait_for(
                    self._event_queue.get(),
                    timeout=1.0
                )
                
                # Process event
                await self._handle_event(event)
                
                # Mark as done
                self._event_queue.task_done()
                self.metrics["queue_size"] = self._event_queue.qsize()
                
            except asyncio.TimeoutError:
                continue
            except Exception as e:
                logger.error(f"Error in event worker {worker_name}: {e}")
    
    async def _handle_event(self, event: DomainEvent) -> None:
        """Handle a single event"""
        event_type = type(event)
        event_name = event.get_event_name()
        
        # Get handlers
        handlers = []
        
        # Type-specific handlers
        if event_type in self._handlers:
            handlers.extend(self._handlers[event_type])
        
        # Global handlers
        handlers.extend(self._global_handlers)
        
        # Sort by priority
        handlers.sort(key=lambda h: h.priority, reverse=True)
        
        if not handlers:
            logger.debug(f"No handlers for event {event_name}")
            return
        
        # Execute handlers
        errors = []
        for handler_wrapper in handlers:
            try:
                await handler_wrapper.handle(event)
                
            except Exception as e:
                logger.error(
                    f"Error in handler for {event_name}: {e}",
                    exc_info=True
                )
                errors.append((handler_wrapper, e))
                
                # Track handler errors
                handler_name = handler_wrapper.handler.__name__
                if handler_name not in self.metrics["handler_errors"]:
                    self.metrics["handler_errors"][handler_name] = 0
                self.metrics["handler_errors"][handler_name] += 1
        
        # Handle processing result
        if errors:
            self.metrics["events_failed"] += 1
            
            # Retry if needed
            if event.metadata.retry_count < event.metadata.max_retries:
                event.metadata.retry_count += 1
                self.metrics["events_retried"] += 1
                
                # Re-queue with delay
                await asyncio.sleep(2 ** event.metadata.retry_count)  # Exponential backoff
                await self._event_queue.put(event)
                
            elif self.enable_dead_letter_queue:
                # Add to dead letter queue
                for handler, error in errors:
                    self._dead_letter_queue.append((event, error))
                self.metrics["dead_letter_size"] = len(self._dead_letter_queue)
                
                logger.error(
                    f"Event {event_name} moved to dead letter queue after "
                    f"{event.metadata.retry_count} retries"
                )
        else:
            self.metrics["events_processed"] += 1
    
    def get_handlers_for_event(
        self,
        event_type: Type[DomainEvent]
    ) -> List[EventHandler]:
        """Get all handlers for an event type"""
        handlers = []
        
        if event_type in self._handlers:
            handlers.extend(self._handlers[event_type])
        
        handlers.extend(self._global_handlers)
        
        return sorted(handlers, key=lambda h: h.priority, reverse=True)
    
    def get_dead_letter_queue(self) -> List[Tuple[DomainEvent, Exception]]:
        """Get events in dead letter queue"""
        return self._dead_letter_queue.copy()
    
    def clear_dead_letter_queue(self) -> int:
        """Clear dead letter queue and return count"""
        count = len(self._dead_letter_queue)
        self._dead_letter_queue.clear()
        self.metrics["dead_letter_size"] = 0
        return count
    
    async def replay_dead_letter_queue(self) -> int:
        """Replay events from dead letter queue"""
        events = self._dead_letter_queue.copy()
        self._dead_letter_queue.clear()
        
        replayed = 0
        for event, _ in events:
            event.metadata.retry_count = 0  # Reset retry count
            await self.publish(event)
            replayed += 1
        
        return replayed
    
    def get_metrics(self) -> Dict[str, Any]:
        """Get event bus metrics"""
        handler_metrics = {}
        
        # Collect handler metrics
        for event_type, handlers in self._handlers.items():
            for handler in handlers:
                name = f"{event_type.__name__}.{handler.handler.__name__}"
                handler_metrics[name] = {
                    "calls": handler.call_count,
                    "errors": handler.error_count,
                    "avg_duration_ms": handler.avg_duration_ms
                }
        
        return {
            **self.metrics,
            "handler_count": sum(len(h) for h in self._handlers.values()) + len(self._global_handlers),
            "event_types": len(self._handlers),
            "handler_metrics": handler_metrics
        }
    
    async def wait_for_empty_queue(self, timeout: Optional[float] = None) -> bool:
        """Wait for event queue to be empty"""
        try:
            await asyncio.wait_for(self._event_queue.join(), timeout)
            return True
        except asyncio.TimeoutError:
            return False


# Global event bus instance
_event_bus: Optional[EventBus] = None


def get_event_bus() -> EventBus:
    """Get the global event bus instance"""
    global _event_bus
    if _event_bus is None:
        _event_bus = EventBus()
    return _event_bus


def set_event_bus(event_bus: EventBus) -> None:
    """Set the global event bus instance"""
    global _event_bus
    _event_bus = event_bus