"""Test messaging module initialization"""

import pytest
from importlib import import_module


class TestMessagingInit:
    """Test messaging module initialization and exports"""

    def test_module_imports(self):
        """Test that messaging module can be imported"""
        module = import_module('fastmcp.shared.infrastructure.messaging')
        assert module is not None

    def test_exported_items(self):
        """Test that all expected items are exported"""
        from fastmcp.shared.infrastructure.messaging import (
            EventBus,
            DomainEvent,
            EventMetadata,
            EventPriority,
            EventHandler,
            get_event_bus,
            set_event_bus
        )
        
        # Verify imports exist
        assert EventBus is not None
        assert DomainEvent is not None
        assert EventMetadata is not None
        assert EventPriority is not None
        assert EventHandler is not None
        assert callable(get_event_bus)
        assert callable(set_event_bus)

    def test_all_exports(self):
        """Test __all__ exports match actual exports"""
        module = import_module('fastmcp.shared.infrastructure.messaging')
        
        expected_exports = [
            "EventBus",
            "DomainEvent",
            "EventMetadata",
            "EventPriority",
            "EventHandler",
            "get_event_bus",
            "set_event_bus"
        ]
        
        assert hasattr(module, '__all__')
        assert set(module.__all__) == set(expected_exports)
        
        # Verify each export is available
        for export in expected_exports:
            assert hasattr(module, export), f"Missing export: {export}"

    def test_event_bus_imports(self):
        """Test that event_bus imports are correctly exposed"""
        from fastmcp.shared.infrastructure.messaging import EventBus, EventHandler
        from fastmcp.shared.infrastructure.messaging.event_bus import (
            EventBus as DirectEventBus,
            EventHandler as DirectEventHandler
        )
        
        # Verify same class references
        assert EventBus is DirectEventBus
        assert EventHandler is DirectEventHandler

    def test_enums_and_types(self):
        """Test that enums and type definitions are properly imported"""
        from fastmcp.shared.infrastructure.messaging import EventPriority, DomainEvent
        
        # Test EventPriority is an enum
        assert hasattr(EventPriority, 'LOW')
        assert hasattr(EventPriority, 'NORMAL')
        assert hasattr(EventPriority, 'HIGH')
        assert hasattr(EventPriority, 'CRITICAL')
        
        # Test DomainEvent is a class
        assert hasattr(DomainEvent, '__init__')