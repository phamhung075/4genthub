"""Infrastructure Events Module

This module handles event infrastructure including:
- Event handler initialization and registration
- Event bus integration with repositories
"""

from .event_handler_initializer import (
    EventHandlerInitializer,
    initialize_event_handlers,
)

__all__ = [
    "EventHandlerInitializer",
    "initialize_event_handlers",
]
