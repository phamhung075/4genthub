"""Test websocket infrastructure module initialization"""

import pytest
from importlib import import_module


class TestWebSocketInit:
    """Test websocket module initialization and exports"""

    def test_module_imports(self):
        """Test that websocket module can be imported"""
        module = import_module('fastmcp.task_management.infrastructure.websocket')
        assert module is not None

    def test_exported_items(self):
        """Test that all expected items are exported"""
        from fastmcp.task_management.infrastructure.websocket import (
            AgentCommunicationHub,
            WebSocketMessage,
            MessageType,
            AgentConnection
        )
        
        # Verify imports exist
        assert AgentCommunicationHub is not None
        assert WebSocketMessage is not None
        assert MessageType is not None
        assert AgentConnection is not None

    def test_all_exports(self):
        """Test __all__ exports match actual exports"""
        module = import_module('fastmcp.task_management.infrastructure.websocket')
        
        expected_exports = [
            "AgentCommunicationHub",
            "WebSocketMessage",
            "MessageType",
            "AgentConnection"
        ]
        
        assert hasattr(module, '__all__')
        assert set(module.__all__) == set(expected_exports)
        
        # Verify each export is available
        for export in expected_exports:
            assert hasattr(module, export), f"Missing export: {export}"

    def test_agent_communication_hub_import(self):
        """Test that imports are correctly exposed from agent_communication_hub"""
        from fastmcp.task_management.infrastructure.websocket import AgentCommunicationHub
        from fastmcp.task_management.infrastructure.websocket.agent_communication_hub import (
            AgentCommunicationHub as DirectHub
        )
        
        # Verify same class reference
        assert AgentCommunicationHub is DirectHub

    def test_websocket_message_import(self):
        """Test WebSocketMessage import"""
        from fastmcp.task_management.infrastructure.websocket import WebSocketMessage
        from fastmcp.task_management.infrastructure.websocket.agent_communication_hub import (
            WebSocketMessage as DirectMessage
        )
        
        # Verify same class reference
        assert WebSocketMessage is DirectMessage

    def test_message_type_import(self):
        """Test MessageType enum import"""
        from fastmcp.task_management.infrastructure.websocket import MessageType
        from fastmcp.task_management.infrastructure.websocket.agent_communication_hub import (
            MessageType as DirectMessageType
        )
        
        # Verify same enum reference
        assert MessageType is DirectMessageType
        
        # Verify enum has expected values
        assert hasattr(MessageType, 'HANDOFF_REQUEST')
        assert hasattr(MessageType, 'STATUS_UPDATE')
        assert hasattr(MessageType, 'RESOURCE_REQUEST')

    def test_agent_connection_import(self):
        """Test AgentConnection import"""
        from fastmcp.task_management.infrastructure.websocket import AgentConnection
        from fastmcp.task_management.infrastructure.websocket.agent_communication_hub import (
            AgentConnection as DirectConnection
        )
        
        # Verify same class reference
        assert AgentConnection is DirectConnection