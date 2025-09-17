"""
Infrastructure Layer

Contains concrete implementations of domain interfaces, such as repositories,
external service integrations, and other infrastructure concerns.
"""

# Event infrastructure components
from .event_bus import EventBus, get_event_bus, reset_event_bus
from .event_store import EventStore, get_event_store, reset_event_store
from .notification_service import (
    NotificationService, 
    get_notification_service, 
    reset_notification_service,
    NotificationPriority,
    NotificationType,
    Notification,
    NotificationChannel,
    InMemoryNotificationChannel,
    LoggingNotificationChannel,
    FileNotificationChannel
)
from .di_container import (
    DIContainer,
    get_container,
    reset_container,
    get_infrastructure_event_bus,
    get_infrastructure_event_store,
    get_infrastructure_notification_service,
    initialize_infrastructure
)

# Note: AgentConverter and AgentDocGenerator have external dependencies
# and are not essential for core task management functionality
# They can be imported directly when needed

__all__ = [
    # Event Bus
    'EventBus',
    'get_event_bus',
    'reset_event_bus',
    
    # Event Store
    'EventStore',
    'get_event_store',
    'reset_event_store',
    
    # Notification Service
    'NotificationService',
    'get_notification_service',
    'reset_notification_service',
    'NotificationPriority',
    'NotificationType',
    'Notification',
    'NotificationChannel',
    'InMemoryNotificationChannel',
    'LoggingNotificationChannel',
    'FileNotificationChannel',
    
    # DI Container
    'DIContainer',
    'get_container',
    'reset_container',
    'get_infrastructure_event_bus',
    'get_infrastructure_event_store',
    'get_infrastructure_notification_service',
    'initialize_infrastructure'
] 