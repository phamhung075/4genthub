"""Tests for DI Container implementation."""

import pytest
import tempfile
import os
from unittest.mock import Mock, patch, AsyncMock, MagicMock

from fastmcp.task_management.infrastructure.di_container import DIContainer
from fastmcp.task_management.infrastructure.event_bus import EventBus
from fastmcp.task_management.infrastructure.event_store import EventStore, reset_event_store
from fastmcp.task_management.infrastructure.notification_service import NotificationService


class TestDIContainer:
    """Test suite for DIContainer."""
    
    @pytest.fixture
    def container(self):
        """Create a DIContainer instance."""
        return DIContainer()
    
    def test_initialization(self, container):
        """Test DIContainer initialization."""
        assert container._instances == {}
        assert container._factories == {}
        assert container._initialized is False
    
    def test_register_singleton(self, container):
        """Test registering a singleton instance."""
        instance = Mock()
        container.register_singleton("test_service", instance)
        
        assert "test_service" in container._instances
        assert container._instances["test_service"] == instance
    
    def test_register_factory(self, container):
        """Test registering a factory function."""
        factory = Mock(return_value=Mock())
        container.register_factory("test_factory", factory)
        
        assert "test_factory" in container._factories
        assert container._factories["test_factory"] == factory
    
    def test_get_singleton(self, container):
        """Test getting a singleton instance."""
        instance = Mock()
        container.register_singleton("test_service", instance)
        
        retrieved = container.get("test_service")
        
        assert retrieved == instance
    
    def test_get_from_factory(self, container):
        """Test getting an instance from a factory."""
        created_instance = Mock()
        factory = Mock(return_value=created_instance)
        container.register_factory("test_factory", factory)
        
        retrieved = container.get("test_factory")
        
        assert retrieved == created_instance
        factory.assert_called_once()
        # Should be cached as singleton after first creation
        assert "test_factory" in container._instances
    
    def test_get_nonexistent_service(self, container):
        """Test getting a non-existent service."""
        result = container.get("nonexistent")
        assert result is None
    
    def test_has_service(self, container):
        """Test checking if a service exists."""
        container.register_singleton("existing", Mock())
        
        assert container.has("existing") is True
        assert container.has("nonexistent") is False
    
    def test_has_factory(self, container):
        """Test checking if a factory exists."""
        container.register_factory("factory", Mock())
        
        assert container.has("factory") is True
    
    def test_remove_service(self, container):
        """Test removing a service."""
        instance = Mock()
        container.register_singleton("test_service", instance)
        
        container.remove("test_service")
        
        assert "test_service" not in container._instances
        assert container.get("test_service") is None
    
    def test_remove_factory(self, container):
        """Test removing a factory."""
        container.register_factory("test_factory", Mock())
        
        container.remove("test_factory")
        
        assert "test_factory" not in container._factories
    
    def test_clear_all(self, container):
        """Test clearing all services and factories."""
        container.register_singleton("service1", Mock())
        container.register_singleton("service2", Mock())
        container.register_factory("factory1", Mock())
        
        container.clear()
        
        assert container._instances == {}
        assert container._factories == {}
        assert container._initialized is False
    
    @pytest.mark.asyncio
    async def test_initialize_infrastructure(self, container):
        """Test initializing infrastructure components."""
        with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as f:
            db_path = f.name
        
        try:
            # Initialize with event store path
            await container.initialize_infrastructure(event_store_path=db_path)
            
            assert container._initialized is True
            
            # Check that core services are registered
            assert container.has("event_bus")
            assert container.has("event_store")
            assert container.has("notification_service")
            
            # Check instances are of correct types
            event_bus = container.get("event_bus")
            event_store = container.get("event_store")
            notification_service = container.get("notification_service")
            
            assert isinstance(event_bus, EventBus)
            assert isinstance(event_store, EventStore)
            assert isinstance(notification_service, NotificationService)
        finally:
            # Cleanup
            if os.path.exists(db_path):
                os.unlink(db_path)
    
    @pytest.mark.asyncio
    async def test_initialize_infrastructure_without_event_store(self, container):
        """Test initializing infrastructure without event store."""
        await container.initialize_infrastructure()
        
        assert container._initialized is True
        assert container.has("event_bus")
        assert container.has("notification_service")
        assert not container.has("event_store")  # Should not be created without path
    
    @pytest.mark.asyncio
    async def test_initialize_infrastructure_idempotent(self, container):
        """Test that initialization is idempotent."""
        await container.initialize_infrastructure()
        
        # Get initial instances
        event_bus1 = container.get("event_bus")
        notification_service1 = container.get("notification_service")
        
        # Initialize again
        await container.initialize_infrastructure()
        
        # Should get same instances
        event_bus2 = container.get("event_bus")
        notification_service2 = container.get("notification_service")
        
        assert event_bus1 is event_bus2
        assert notification_service1 is notification_service2
    
    def test_get_event_bus(self, container):
        """Test getting event bus."""
        event_bus = Mock(spec=EventBus)
        container.register_singleton("event_bus", event_bus)
        
        retrieved = container.get_event_bus()
        
        assert retrieved == event_bus
    
    @pytest.mark.asyncio
    async def test_get_event_store(self, container):
        """Test getting event store."""
        event_store = Mock(spec=EventStore)
        container.register_singleton("event_store", event_store)
        
        retrieved = await container.get_event_store()
        
        assert retrieved == event_store
    
    def test_get_notification_service(self, container):
        """Test getting notification service."""
        notification_service = Mock(spec=NotificationService)
        container.register_singleton("notification_service", notification_service)
        
        retrieved = container.get_notification_service()
        
        assert retrieved == notification_service
    
    def test_register_duplicate_singleton(self, container):
        """Test registering duplicate singleton (should replace)."""
        instance1 = Mock()
        instance2 = Mock()
        
        container.register_singleton("test_service", instance1)
        container.register_singleton("test_service", instance2)
        
        retrieved = container.get("test_service")
        assert retrieved == instance2
    
    def test_register_duplicate_factory(self, container):
        """Test registering duplicate factory (should replace)."""
        factory1 = Mock()
        factory2 = Mock()
        
        container.register_factory("test_factory", factory1)
        container.register_factory("test_factory", factory2)
        
        assert container._factories["test_factory"] == factory2
    
    def test_factory_called_only_once(self, container):
        """Test that factory is only called once (singleton behavior)."""
        instance = Mock()
        factory = Mock(return_value=instance)
        
        container.register_factory("test_factory", factory)
        
        # Get multiple times
        retrieved1 = container.get("test_factory")
        retrieved2 = container.get("test_factory")
        retrieved3 = container.get("test_factory")
        
        # Factory should only be called once
        factory.assert_called_once()
        
        # All retrievals should return same instance
        assert retrieved1 == instance
        assert retrieved2 == instance
        assert retrieved3 == instance
    
    def test_get_all_services(self, container):
        """Test getting all registered services."""
        container.register_singleton("service1", Mock())
        container.register_singleton("service2", Mock())
        container.register_factory("factory1", Mock())
        
        # Get factory to create instance
        container.get("factory1")
        
        all_services = container.get_all_services()
        
        assert "service1" in all_services
        assert "service2" in all_services
        assert "factory1" in all_services
    
    def test_override_with_factory(self, container):
        """Test overriding singleton with factory."""
        instance = Mock()
        container.register_singleton("test", instance)
        
        factory = Mock(return_value=Mock())
        container.register_factory("test", factory)
        
        # Should use factory now
        retrieved = container.get("test")
        factory.assert_called_once()
        assert retrieved != instance


class TestDIContainerIntegration:
    """Integration tests for DI Container."""
    
    @pytest.mark.asyncio
    async def test_full_infrastructure_setup(self):
        """Test setting up full infrastructure."""
        # Reset global event store to ensure fresh instance with correct path
        reset_event_store()
        
        container = DIContainer()
        
        with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as f:
            db_path = f.name
        
        try:
            # Initialize infrastructure
            await container.initialize_infrastructure(event_store_path=db_path)
            
            # Get services
            event_bus = container.get_event_bus()
            event_store = await container.get_event_store()
            notification_service = container.get_notification_service()
            
            # Test interaction between services
            class SampleEvent:
                def __init__(self, data):
                    self.data = data
                    self.aggregate_id = "test_agg"
                    self.user_id = "test_user"
                    self.occurred_at = None
                
                def to_dict(self):
                    return {"data": self.data}
            
            # Subscribe handler to event bus
            handler_called = False
            def handler(event):
                nonlocal handler_called
                handler_called = True
            
            event_bus.subscribe(SampleEvent, handler)
            
            # Publish event
            event = SampleEvent("test_data")
            await event_bus.publish(event)
            
            # Check handler was called
            assert handler_called is True
            
            # Store event
            if event_store:
                event_id = await event_store.append(event)
                assert event_id is not None
                
                # Retrieve event
                stored_event = await event_store.get_event_by_id(event_id)
                assert stored_event is not None
                assert stored_event.event_data["data"] == "test_data"
            
            # Send notification
            notif_id = await notification_service.notify(
                type="test",
                data={"message": "Integration test"},
                priority="medium"
            )
            assert notif_id is not None
            
        finally:
            # Cleanup
            reset_event_store()  # Reset global state
            if os.path.exists(db_path):
                os.unlink(db_path)
    
    @pytest.mark.asyncio
    async def test_singleton_behavior_across_instances(self):
        """Test that getting the global container returns same instance."""
        from fastmcp.task_management.infrastructure.di_container import get_container
        
        container1 = get_container()
        container2 = get_container()
        
        assert container1 is container2
        
        # Register in one, should be available in other
        container1.register_singleton("test_service", Mock())
        assert container2.has("test_service")
    
    @pytest.mark.asyncio
    async def test_custom_service_registration(self):
        """Test registering custom services alongside infrastructure."""
        container = DIContainer()
        
        # Register custom service before initialization
        custom_service = Mock()
        container.register_singleton("custom_service", custom_service)
        
        # Initialize infrastructure
        await container.initialize_infrastructure()
        
        # Custom service should still be available
        assert container.has("custom_service")
        assert container.get("custom_service") == custom_service
        
        # Infrastructure services should also be available
        assert container.has("event_bus")
        assert container.has("notification_service")