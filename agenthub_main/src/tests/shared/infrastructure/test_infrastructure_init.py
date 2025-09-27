"""Test shared infrastructure module initialization"""

import pytest
from importlib import import_module


class TestSharedInfrastructureInit:
    """Test shared infrastructure module initialization and exports"""

    def test_module_imports(self):
        """Test that shared infrastructure module can be imported"""
        module = import_module('fastmcp.shared.infrastructure')
        assert module is not None

    def test_exported_items(self):
        """Test that all expected items are exported from infrastructure"""
        from fastmcp.shared.infrastructure import (
            EventBus,
            DomainEvent,
            EventMetadata,
            EventPriority,
            get_event_bus,
            set_event_bus
        )
        
        # Verify imports exist
        assert EventBus is not None
        assert DomainEvent is not None
        assert EventMetadata is not None
        assert EventPriority is not None
        assert callable(get_event_bus)
        assert callable(set_event_bus)

    def test_all_exports(self):
        """Test __all__ exports match actual exports"""
        module = import_module('fastmcp.shared.infrastructure')
        
        expected_exports = [
            "EventBus",
            "DomainEvent",
            "EventMetadata",
            "EventPriority",
            "get_event_bus",
            "set_event_bus"
        ]
        
        assert hasattr(module, '__all__')
        assert set(module.__all__) == set(expected_exports)
        
        # Verify each export is available
        for export in expected_exports:
            assert hasattr(module, export), f"Missing export: {export}"

    def test_messaging_imports(self):
        """Test that messaging imports are correctly re-exported"""
        from fastmcp.shared.infrastructure import EventBus, EventPriority
        from fastmcp.shared.infrastructure.messaging import EventBus as DirectEventBus
        from fastmcp.shared.infrastructure.messaging import EventPriority as DirectEventPriority
        
        # Verify same class/enum references
        assert EventBus is DirectEventBus
        assert EventPriority is DirectEventPriority

    def test_function_imports(self):
        """Test that utility functions are correctly imported"""
        from fastmcp.shared.infrastructure import get_event_bus, set_event_bus
        from fastmcp.shared.infrastructure.messaging import (
            get_event_bus as direct_get,
            set_event_bus as direct_set
        )
        
        # Verify same function references
        assert get_event_bus is direct_get
        assert set_event_bus is direct_set