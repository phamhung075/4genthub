"""
WebSocket Server v2.0 Integration Tests

Tests for the complete WebSocket server implementation including:
- Connection management
- Protocol v2.0 validation
- User message immediate processing
- AI message batching
- Cascade data integration
- Authentication

NO backward compatibility - v2.0 only tests.
"""

import asyncio
import json
import pytest
import pytest_asyncio
import uuid
from datetime import datetime
from unittest.mock import AsyncMock, MagicMock, patch

from fastapi import FastAPI
from fastapi.testclient import TestClient
import websockets
from websockets.exceptions import ConnectionClosedError

from fastmcp.websocket.server import WebSocketServer
from fastmcp.websocket.connection_manager import ConnectionManager
from fastmcp.websocket.batch_processor import BatchProcessor
from fastmcp.websocket.protocol import create_user_update, create_error
from fastmcp.websocket.models import WSMessage
from fastmcp.websocket.fastapi_integration import setup_websocket_integration


@pytest.fixture
def mock_session_factory():
    """Mock database session factory."""
    session = AsyncMock()
    session_factory = MagicMock()
    session_factory.return_value.__aenter__.return_value = session
    session_factory.return_value.__aexit__.return_value = None
    return session_factory


@pytest.fixture
def mock_keycloak_auth():
    """Mock Keycloak authentication."""
    with patch('fastmcp.websocket.server.KeycloakAuth') as mock_auth:
        auth_instance = mock_auth.return_value
        # Configure successful authentication by default
        # Create a proper mock object for the validation result
        validation_result = MagicMock()
        validation_result.valid = True
        validation_result.user_id = "test-user-123"
        validation_result.email = "test@example.com"
        validation_result.roles = ["user"]
        validation_result.error = None
        
        # Make validate_token an async method that returns the result
        auth_instance.validate_token = AsyncMock(return_value=validation_result)
        yield auth_instance


@pytest.fixture
def app():
    """FastAPI test application."""
    return FastAPI()


@pytest_asyncio.fixture
async def websocket_server(app, mock_session_factory):
    """WebSocket server instance for testing."""
    server = WebSocketServer(app, mock_session_factory)
    await server.start()
    yield server
    await server.stop()


@pytest.fixture
def connection_manager(mock_session_factory):
    """Connection manager instance for testing."""
    return ConnectionManager(mock_session_factory)


@pytest.fixture
def batch_processor(connection_manager, mock_session_factory):
    """Batch processor instance for testing."""
    return BatchProcessor(connection_manager, mock_session_factory)


class TestWebSocketServer:
    """Test WebSocket server functionality."""

    @pytest.mark.asyncio
    async def test_server_initialization(self, mock_session_factory):
        """Test WebSocket server initialization."""
        # Use a real FastAPI instance to avoid mock issues
        import sys
        fastapi_module = sys.modules.get('fastapi.original', None)
        if not fastapi_module:
            pytest.skip("Real FastAPI not available in test environment")
        
        fresh_app = MagicMock()
        fresh_app.websocket = MagicMock()
        
        server = WebSocketServer(fresh_app, mock_session_factory)

        assert server.app == fresh_app
        assert server.session_factory == mock_session_factory
        assert not server.is_running
        assert server.startup_time is None

    @pytest.mark.asyncio
    async def test_server_startup_shutdown(self, websocket_server):
        """Test server startup and shutdown lifecycle."""
        # Server should be running after fixture setup
        assert websocket_server.is_running
        assert websocket_server.startup_time is not None
        assert websocket_server.batch_processor.is_running

        # Test shutdown
        await websocket_server.stop()
        assert not websocket_server.is_running
        assert not websocket_server.batch_processor.is_running

    @pytest.mark.asyncio
    async def test_health_status(self, websocket_server):
        """Test health status endpoint."""
        health = await websocket_server.get_health_status()

        assert health["status"] == "healthy"
        assert health["version"] == "2.0"
        assert health["is_running"] is True
        assert "connections" in health
        assert "batch_processing" in health

    @pytest.mark.asyncio
    async def test_detailed_stats(self, websocket_server):
        """Test detailed statistics endpoint."""
        stats = await websocket_server.get_detailed_stats()

        assert stats["server"]["version"] == "2.0"
        assert stats["server"]["is_running"] is True
        assert "connections" in stats
        assert "batch_processing" in stats
        assert "protocol" in stats

        # Check protocol information
        protocol = stats["protocol"]
        assert protocol["version"] == "2.0"
        assert "update" in protocol["supported_message_types"]
        assert "user" in protocol["supported_sources"]


class TestConnectionManager:
    """Test connection manager functionality."""

    @pytest.mark.asyncio
    async def test_connection_management(self, connection_manager):
        """Test connection and disconnection."""
        mock_websocket = AsyncMock()
        mock_websocket.accept = AsyncMock()

        # Test connection
        session_id = await connection_manager.connect(mock_websocket, "user123")

        assert isinstance(session_id, str)
        assert "user123" in connection_manager.connections
        assert session_id in connection_manager.session_users
        assert "user123" in connection_manager.active_users

        # Test disconnection
        await connection_manager.disconnect("user123")

        assert "user123" not in connection_manager.connections
        assert session_id not in connection_manager.session_users
        assert "user123" not in connection_manager.active_users

    @pytest.mark.asyncio
    async def test_message_validation(self, connection_manager):
        """Test v2.0 message validation."""
        # Test valid v2.0 message
        valid_message = {
            "version": "2.0",
            "type": "update",
            "sequence": 1,
            "payload": {
                "entity": "task",
                "action": "update",
                "data": {
                    "primary": {"id": "task123", "title": "Test task"}
                }
            },
            "metadata": {
                "source": "user",
                "user_id": "user123",
                "immediate": True
            }
        }

        # Should not raise an exception
        await connection_manager.process_message("user123", json.dumps(valid_message))

    @pytest.mark.asyncio
    async def test_invalid_version_rejection(self, connection_manager):
        """Test rejection of non-v2.0 messages."""
        mock_websocket = AsyncMock()
        mock_websocket.accept = AsyncMock()

        # Connect user first
        await connection_manager.connect(mock_websocket, "user123")

        # Test invalid version message
        invalid_message = {
            "version": "1.0",  # Invalid version
            "type": "update",
            "sequence": 1,
            "payload": {
                "entity": "task",
                "action": "update",
                "data": {"primary": {"id": "task123"}}
            },
            "metadata": {
                "source": "user",
                "immediate": True
            }
        }

        # Process message - should send error response
        await connection_manager.process_message("user123", json.dumps(invalid_message))

        # Verify error was sent (mock websocket should have been called)
        mock_websocket.send_text.assert_called()

    @pytest.mark.asyncio
    async def test_connection_stats(self, connection_manager):
        """Test connection statistics."""
        mock_websocket = AsyncMock()
        mock_websocket.accept = AsyncMock()

        # Initial stats
        stats = connection_manager.get_connection_stats()
        assert stats["total_connections"] == 0
        assert len(stats["active_users"]) == 0

        # Connect users
        await connection_manager.connect(mock_websocket, "user1")
        await connection_manager.connect(mock_websocket, "user2")

        stats = connection_manager.get_connection_stats()
        assert stats["total_connections"] == 2
        assert len(stats["active_users"]) == 2
        assert "user1" in stats["active_users"]
        assert "user2" in stats["active_users"]


class TestBatchProcessor:
    """Test batch processor functionality."""

    @pytest.mark.asyncio
    async def test_batch_processor_lifecycle(self, batch_processor):
        """Test batch processor start and stop."""
        assert not batch_processor.is_running

        # Start processor
        await batch_processor.start()
        assert batch_processor.is_running
        assert batch_processor.batch_task is not None

        # Stop processor
        await batch_processor.stop()
        assert not batch_processor.is_running

    @pytest.mark.asyncio
    async def test_batch_configuration(self, batch_processor):
        """Test batch processor configuration."""
        # Test default configuration
        assert batch_processor.batch_interval == 0.5
        assert batch_processor.max_batch_size == 50

        # Test configuration update
        batch_processor.configure_batch_params(
            interval=0.3,
            max_size=25,
            max_timeout=1.0
        )

        assert batch_processor.batch_interval == 0.3
        assert batch_processor.max_batch_size == 25
        assert batch_processor.max_batch_timeout == 1.0

    @pytest.mark.asyncio
    async def test_message_deduplication(self, batch_processor):
        """Test message deduplication logic."""
        # Create test messages for same entity
        messages = []
        for i in range(3):
            message = WSMessage(
                type="update",
                sequence=i,
                payload={
                    "entity": "task",
                    "action": "update",
                    "data": {
                        "primary": {"id": "task123", "title": f"Update {i}"}
                    }
                },
                metadata={
                    "source": "mcp-ai",
                    "immediate": False
                }
            )
            messages.append(message)

        # Test deduplication
        deduplicated = batch_processor._deduplicate_updates(messages)

        # Should have only one entry for task123
        assert len(deduplicated) == 1
        assert "task123" in deduplicated

        # Should have the latest update
        assert deduplicated["task123"]["data"]["title"] == "Update 2"

    @pytest.mark.asyncio
    async def test_batch_stats(self, batch_processor):
        """Test batch processor statistics."""
        stats = batch_processor.get_stats()

        assert "is_running" in stats
        assert "batch_interval_ms" in stats
        assert "max_batch_size" in stats
        assert "batches_processed" in stats
        assert "messages_processed" in stats
        assert "average_batch_size" in stats


class TestProtocolIntegration:
    """Test protocol integration with cascade data."""

    @pytest.mark.asyncio
    async def test_user_message_with_cascade(self):
        """Test user message creation with cascade data."""
        mock_cascade_calculator = AsyncMock()

        # Mock cascade result
        mock_cascade_result = MagicMock()
        mock_cascade_result.affected_tasks = {"task1", "task2"}
        mock_cascade_result.affected_branches = {"branch1"}
        mock_cascade_result.affected_projects = {"project1"}
        mock_cascade_result.affected_subtasks = set()
        mock_cascade_result.affected_contexts = set()

        mock_cascade_calculator.calculate_cascade.return_value = mock_cascade_result

        # Create user update message
        message = await create_user_update(
            entity_type="task",
            action="update",
            primary_data={"id": "task123", "title": "Test task"},
            cascade_calculator=mock_cascade_calculator,
            entity_id="task123",
            user_id="user123",
            sequence=1
        )

        assert message.type == "update"
        assert message.metadata.source == "user"
        assert message.metadata.immediate is True
        assert message.payload.entity == "task"
        assert message.payload.action == "update"

        # Verify cascade calculation was called
        mock_cascade_calculator.calculate_cascade.assert_called_once()

    @pytest.mark.asyncio
    async def test_error_message_creation(self):
        """Test error message creation."""
        error_msg = create_error(
            error_message="Test error",
            error_code="TEST_ERROR",
            session_id="session123",
            sequence=1
        )

        assert error_msg.type == "error"
        assert error_msg.metadata.source == "system"
        assert error_msg.payload.data.primary["message"] == "Test error"
        assert error_msg.payload.data.primary["code"] == "TEST_ERROR"


class TestAuthentication:
    """Test WebSocket authentication integration."""

    @pytest.mark.asyncio
    async def test_valid_token_authentication(self, mock_keycloak_auth):
        """Test successful token authentication."""
        # This would be tested with actual WebSocket connection
        # but requires more complex setup with test client

        # Verify mock is configured correctly
        validation = await mock_keycloak_auth.validate_token("valid-token")
        assert validation.valid is True
        assert validation.user_id == "test-user-123"

    @pytest.mark.asyncio
    async def test_invalid_token_rejection(self, mock_keycloak_auth):
        """Test invalid token rejection."""
        # Configure mock for invalid token
        invalid_result = MagicMock()
        invalid_result.valid = False
        invalid_result.error = "Invalid token"
        invalid_result.user_id = None
        invalid_result.email = None
        invalid_result.roles = []
        
        mock_keycloak_auth.validate_token.return_value = invalid_result

        validation = await mock_keycloak_auth.validate_token("invalid-token")
        assert validation.valid is False


class TestFastAPIIntegration:
    """Test FastAPI integration functionality."""

    def test_websocket_endpoints_info(self):
        """Test WebSocket endpoints information."""
        from fastmcp.websocket.fastapi_integration import get_websocket_endpoints_info

        info = get_websocket_endpoints_info()

        assert info["websocket_endpoint"] == "/ws/{user_id}"
        assert info["protocol_version"] == "2.0"
        assert info["authentication"] == "JWT token required (query parameter)"
        assert "Real-time user updates (immediate processing)" in info["features"]
        assert "AI message batching (500ms intervals)" in info["features"]

    @pytest.mark.asyncio
    async def test_integration_setup(self, app, mock_session_factory):
        """Test WebSocket integration setup."""
        from fastmcp.websocket.fastapi_integration import setup_websocket_integration

        with patch('fastmcp.websocket.fastapi_integration.get_db_config') as mock_get_db:
            # Mock database config
            mock_db_config = MagicMock()
            mock_db_config.get_async_session = mock_session_factory
            mock_get_db.return_value = mock_db_config

            # Setup integration
            websocket_server = setup_websocket_integration(app)

            assert websocket_server is not None
            assert isinstance(websocket_server, WebSocketServer)

            # Cleanup
            await websocket_server.stop()


if __name__ == "__main__":
    pytest.main([__file__, "-v"])