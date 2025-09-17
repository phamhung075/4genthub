"""Test shared module initialization"""

import pytest
from importlib import import_module


class TestSharedInit:
    """Test shared module initialization and exports"""

    def test_module_imports(self):
        """Test that shared module can be imported"""
        module = import_module('fastmcp.shared')
        assert module is not None

    def test_exported_items(self):
        """Test that all expected items are exported"""
        from fastmcp.shared import (
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
        module = import_module('fastmcp.shared')
        
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

    def test_infrastructure_imports(self):
        """Test that infrastructure imports are correctly re-exported"""
        from fastmcp.shared import EventBus, DomainEvent
        from fastmcp.shared.infrastructure.messaging.event_bus import EventBus as DirectEventBus
        from fastmcp.shared.infrastructure.messaging.event_bus import DomainEvent as DirectDomainEvent
        
        # Verify same class references
        assert EventBus is DirectEventBus
        assert DomainEvent is DirectDomainEvent