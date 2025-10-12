"""Domain Event Dispatcher - Central hub for domain events"""

import logging
from typing import Dict, List, Callable, Any
from dataclasses import dataclass

logger = logging.getLogger(__name__)


class EventDispatcher:
    """
    Central event dispatcher for domain events.
    Follows the Observer pattern to decouple event producers from consumers.
    """

    def __init__(self):
        """Initialize the event dispatcher with empty handlers."""
        self._handlers: Dict[str, List[Callable]] = {}
        self._async_handlers: Dict[str, List[Callable]] = {}

    def register_handler(self, event_type: str, handler: Callable) -> None:
        """
        Register a synchronous event handler.

        Args:
            event_type: Type of event to handle
            handler: Callable that processes the event
        """
        if event_type not in self._handlers:
            self._handlers[event_type] = []

        if handler not in self._handlers[event_type]:
            self._handlers[event_type].append(handler)
            logger.debug(f"Registered handler {handler.__name__} for event {event_type}")

    def unregister_handler(self, event_type: str, handler: Callable) -> None:
        """
        Unregister an event handler.

        Args:
            event_type: Type of event
            handler: Handler to remove
        """
        if event_type in self._handlers and handler in self._handlers[event_type]:
            self._handlers[event_type].remove(handler)
            logger.debug(f"Unregistered handler {handler.__name__} for event {event_type}")

    def dispatch(self, event_type: str, event_data: Any) -> None:
        """
        Dispatch an event to all registered handlers.

        Args:
            event_type: Type of event
            event_data: Event data object
        """
        if event_type not in self._handlers:
            logger.debug(f"No handlers registered for event {event_type}")
            return

        handlers = self._handlers[event_type]
        logger.info(f"Dispatching {event_type} to {len(handlers)} handlers")

        for handler in handlers:
            try:
                handler(event_data)
                logger.debug(f"Handler {handler.__name__} processed {event_type}")
            except Exception as e:
                logger.error(
                    f"Handler {handler.__name__} failed processing {event_type}: {e}",
                    exc_info=True
                )

    def clear_handlers(self, event_type: str = None) -> None:
        """
        Clear handlers for a specific event type or all handlers.

        Args:
            event_type: Optional event type to clear handlers for
        """
        if event_type:
            self._handlers.pop(event_type, None)
            logger.debug(f"Cleared handlers for event {event_type}")
        else:
            self._handlers.clear()
            logger.debug("Cleared all event handlers")

    def get_handler_count(self, event_type: str) -> int:
        """
        Get the number of handlers registered for an event type.

        Args:
            event_type: Event type to check

        Returns:
            Number of registered handlers
        """
        return len(self._handlers.get(event_type, []))


# Global event dispatcher instance (Singleton)
_event_dispatcher = None


def get_event_dispatcher() -> EventDispatcher:
    """
    Get the global event dispatcher instance (Singleton pattern).

    Returns:
        The global EventDispatcher instance
    """
    global _event_dispatcher
    if _event_dispatcher is None:
        _event_dispatcher = EventDispatcher()
        logger.info("Created global event dispatcher")
    return _event_dispatcher


def dispatch_domain_event(event_type: str, event_data: Any) -> None:
    """
    Convenience function to dispatch domain events.

    Args:
        event_type: Type of event
        event_data: Event data
    """
    dispatcher = get_event_dispatcher()
    dispatcher.dispatch(event_type, event_data)