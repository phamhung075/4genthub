"""Dependency Injection Container for infrastructure components.

This module provides a simple DI container for managing infrastructure
component instances and their dependencies.
"""

import logging
from typing import Any, Dict, Optional, Type, TypeVar, Callable, Union
from pathlib import Path

from .event_bus import EventBus, get_event_bus
from .event_store import EventStore, get_event_store
from .notification_service import NotificationService, get_notification_service

logger = logging.getLogger(__name__)

T = TypeVar('T')


class DIContainer:
    """
    Simple dependency injection container for infrastructure components.
    
    Provides singleton instances of infrastructure services.
    """
    
    def __init__(self):
        """Initialize the DI container."""
        self._instances: Dict[Union[str, Type], Any] = {}
        self._factories: Dict[Union[str, Type], Callable] = {}
        self._config: Dict[str, Any] = {}
        self._initialized: bool = False
    
    def register_singleton(self, key: Union[str, Type[T]], instance: T) -> None:
        """
        Register a singleton instance.
        
        Args:
            key: Service key (string) or type
            instance: The instance to register
        """
        self._instances[key] = instance
        logger.debug(f"Registered singleton for {key}")
    
    def register_factory(self, key: Union[str, Type[T]], factory: Callable[[], T]) -> None:
        """
        Register a factory function for a service.
        
        Args:
            key: Service key (string) or type
            factory: Factory function that creates the service
        """
        self._factories[key] = factory
        # Remove any existing instance so factory takes precedence
        if key in self._instances:
            del self._instances[key]
        logger.debug(f"Registered factory for {key}")
    
    def register_instance(self, service_type: Type[T], instance: T) -> None:
        """
        Register a specific instance for a service type (backward compatibility).
        
        Args:
            service_type: The type of service
            instance: The instance to register
        """
        self.register_singleton(service_type, instance)
    
    def get(self, key: Union[str, Type[T]]) -> Optional[T]:
        """
        Get an instance of a service.
        
        Args:
            key: Service key (string) or type
            
        Returns:
            The service instance or None if not found
        """
        # Check if we have a factory (factories take precedence over cached instances)
        if key in self._factories:
            # Only create if we don't already have a cached instance from this factory
            if key not in self._instances:
                instance = self._factories[key]()
                self._instances[key] = instance
            return self._instances[key]
        
        # Check if we have a cached instance
        if key in self._instances:
            return self._instances[key]
        
        return None
    
    def has(self, key: Union[str, Type]) -> bool:
        """
        Check if a service is registered.
        
        Args:
            key: Service key (string) or type
            
        Returns:
            True if service is registered, False otherwise
        """
        return key in self._instances or key in self._factories
    
    def remove(self, key: Union[str, Type]) -> None:
        """
        Remove a service registration.
        
        Args:
            key: Service key (string) or type
        """
        if key in self._instances:
            del self._instances[key]
        if key in self._factories:
            del self._factories[key]
    
    def clear(self) -> None:
        """Clear all registrations and reset initialization state."""
        self._instances.clear()
        self._factories.clear()
        self._initialized = False
    
    def get_all_services(self) -> Dict[Union[str, Type], Any]:
        """
        Get all registered service instances.
        
        Returns:
            Dictionary of all service instances
        """
        # Create instances from factories if not already created
        all_services = dict(self._instances)
        for key, factory in self._factories.items():
            if key not in all_services:
                instance = factory()
                self._instances[key] = instance
                all_services[key] = instance
        return all_services
    
    def get_optional(self, service_type: Type[T]) -> Optional[T]:
        """
        Get an optional instance of a service.
        
        Args:
            service_type: The type of service to get
            
        Returns:
            The service instance or None if not registered
        """
        return self.get(service_type)
    
    def configure(self, config: Dict[str, Any]) -> None:
        """
        Configure the container with settings.
        
        Args:
            config: Configuration dictionary
        """
        self._config.update(config)
        logger.debug(f"Updated container configuration: {list(config.keys())}")
    
    def reset(self) -> None:
        """Reset the container, clearing all instances."""
        self._instances.clear()
        self._factories.clear()
        self._config.clear()
        self._initialized = False
        logger.debug("DI container reset")
    
    def get_event_bus(self) -> EventBus:
        """Convenience method to get EventBus instance."""
        return self.get("event_bus")
    
    async def get_event_store(self) -> Optional[EventStore]:
        """Convenience method to get EventStore instance."""
        return self.get("event_store")
    
    def get_notification_service(self) -> NotificationService:
        """Convenience method to get NotificationService instance."""
        return self.get("notification_service")
    
    async def initialize_infrastructure(self, 
                                        event_store_path: Optional[str] = None,
                                        notification_channels: Optional[list] = None) -> None:
        """
        Initialize all infrastructure components with configuration.
        
        Args:
            event_store_path: Optional path for event store database
            notification_channels: Optional list of notification channels to add
        """
        if self._initialized:
            return  # Already initialized
            
        # Configure event store path
        if event_store_path:
            self.configure({'event_store_path': event_store_path})
        
        # Register infrastructure services with string keys (as expected by tests)
        event_bus = get_event_bus()
        self.register_singleton("event_bus", event_bus)
        
        notification_service = get_notification_service()
        self.register_singleton("notification_service", notification_service)
        
        # Only register event store if path is provided
        if event_store_path:
            event_store = get_event_store(event_store_path)
            self.register_singleton("event_store", event_store)
        
        # Add custom notification channels if provided
        if notification_channels:
            for channel in notification_channels:
                notification_service.add_channel(channel)
        
        self._initialized = True
        logger.info("Infrastructure components initialized")
        logger.info(f"  - EventBus: {event_bus}")
        if event_store_path:
            logger.info(f"  - EventStore: {self.get('event_store')}")
        logger.info(f"  - NotificationService: {notification_service}")
    
    def wire_event_handlers(self, registry: Any) -> None:
        """
        Wire event handlers to the event bus.
        
        Args:
            registry: Event handler registry to wire up
        """
        event_bus = self.get_event_bus()
        
        # Subscribe handlers from registry
        if hasattr(registry, 'handlers'):
            for event_type, handler in registry.handlers.items():
                if hasattr(handler, 'handle'):
                    event_bus.subscribe(event_type, handler.handle)
                    logger.debug(f"Wired handler for {event_type.__name__}")
        
        logger.info(f"Wired {len(registry.handlers)} event handlers to event bus")
    
    def __repr__(self) -> str:
        """String representation of the container."""
        return (f"DIContainer(instances={len(self._instances)}, "
                f"factories={len(self._factories)})")


# Global DI container instance
_global_container: Optional[DIContainer] = None


def get_container() -> DIContainer:
    """Get the global DI container instance."""
    global _global_container
    if _global_container is None:
        _global_container = DIContainer()
    return _global_container


def reset_container() -> None:
    """Reset the global DI container (mainly for testing)."""
    global _global_container
    if _global_container:
        _global_container.reset()
    _global_container = None


# Convenience functions for getting infrastructure components
def get_infrastructure_event_bus() -> EventBus:
    """Get EventBus from the global container."""
    return get_container().get_event_bus()


def get_infrastructure_event_store() -> EventStore:
    """Get EventStore from the global container."""
    return get_container().get_event_store()


def get_infrastructure_notification_service() -> NotificationService:
    """Get NotificationService from the global container."""
    return get_container().get_notification_service()


def initialize_infrastructure(event_store_path: Optional[str] = None,
                             notification_channels: Optional[list] = None) -> DIContainer:
    """
    Initialize infrastructure with default configuration.
    
    Args:
        event_store_path: Optional path for event store database
        notification_channels: Optional list of notification channels
        
    Returns:
        The configured DI container
    """
    container = get_container()
    container.initialize_infrastructure(event_store_path, notification_channels)
    return container