"""Event infrastructure for async event processing."""

from .event_queue import EventQueue, QueueState, QueueMetrics
from .event_worker import (
    EventWorker,
    EventQueueItem,
    DeadLetterEvent,
    get_event_worker,
    shutdown_event_worker,
    RETRY_BACKOFF_SCHEDULE,
)


def initialize_event_handlers() -> bool:
    """
    Initialize event handlers for the application.

    This is called during server startup to set up event processing infrastructure.
    With the new async event queue system, event handlers are registered on-demand
    by the EventBus when publish_sync() is called with async mode enabled.

    Returns:
        bool: True if initialization successful, False otherwise
    """
    # Event handlers are now registered dynamically by EventBus
    # No upfront initialization needed with the queue-based system
    return True


__all__ = [
    "EventQueue",
    "QueueState",
    "QueueMetrics",
    "EventWorker",
    "EventQueueItem",
    "DeadLetterEvent",
    "get_event_worker",
    "shutdown_event_worker",
    "RETRY_BACKOFF_SCHEDULE",
    "initialize_event_handlers",
]
