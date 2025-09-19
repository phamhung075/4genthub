"""
Unit tests for WebSocket security and user-scoped authorization.
Tests the critical security fix for broadcast message filtering.
"""

import pytest
from unittest.mock import Mock, patch, AsyncMock
from fastapi import WebSocket
from fastmcp.auth.domain.entities.user import User
from fastmcp.server.routes.websocket_routes import (
    is_user_authorized_for_message,
    connection_users
)


@pytest.mark.asyncio
class TestWebSocketSecurity:
    """Test WebSocket security and authorization."""

    def setup_method(self):
        """Set up test data."""
        # Clear connection users before each test
        connection_users.clear()

    @pytest.mark.asyncio
    async def test_user_authorized_for_own_message(self):
        """Test that users are authorized for their own messages."""
        # Mock WebSocket connection
        websocket = Mock(spec=WebSocket)

        # Create test user
        user = User(
            id="user123",
            email="test@example.com",
            username="testuser",
            password_hash="hashed"
        )

        # Store user in connection mapping
        connection_users[websocket] = user

        # Test authorization for user's own message
        is_authorized = await is_user_authorized_for_message(
            websocket=websocket,
            entity_type="task",
            entity_id="task123",
            triggering_user_id="user123",  # Same as connection user
            metadata={}
        )

        assert is_authorized is True

    @pytest.mark.asyncio
    async def test_user_not_authorized_for_other_user_message(self):
        """Test that users are NOT authorized for other users' messages."""
        # Mock WebSocket connection
        websocket = Mock(spec=WebSocket)

        # Create test user
        user = User(
            id="user123",
            email="test@example.com",
            username="testuser",
            password_hash="hashed"
        )

        # Store user in connection mapping
        connection_users[websocket] = user

        # Mock database session and query
        with patch('fastmcp.task_management.infrastructure.database.database_config.get_session') as mock_get_session:
            mock_session = Mock()
            mock_get_session.return_value.__enter__.return_value = mock_session

            # Mock that user does NOT own this task
            mock_session.query.return_value.filter.return_value.first.return_value = None

            # Test authorization for another user's message
            is_authorized = await is_user_authorized_for_message(
                websocket=websocket,
                entity_type="task",
                entity_id="task456",
                triggering_user_id="other_user",  # Different user
                metadata={}
            )

            assert is_authorized is False

    @pytest.mark.asyncio
    async def test_user_authorized_for_owned_task(self):
        """Test that users are authorized for tasks they own."""
        # Mock WebSocket connection
        websocket = Mock(spec=WebSocket)

        # Create test user
        user = User(
            id="user123",
            email="test@example.com",
            username="testuser",
            password_hash="hashed"
        )

        # Store user in connection mapping
        connection_users[websocket] = user

        # Mock database session and query
        with patch('fastmcp.task_management.infrastructure.database.database_config.get_session') as mock_get_session:
            mock_session = Mock()
            mock_get_session.return_value.__enter__.return_value = mock_session

            # Mock task that user owns
            mock_task = Mock()
            mock_task.id = "task456"
            mock_task.user_id = "user123"
            mock_session.query.return_value.filter.return_value.first.return_value = mock_task

            # Test authorization for user's owned task
            is_authorized = await is_user_authorized_for_message(
                websocket=websocket,
                entity_type="task",
                entity_id="task456",
                triggering_user_id="other_user",  # Different triggering user
                metadata={}
            )

            assert is_authorized is True

    @pytest.mark.asyncio
    async def test_connection_without_user_denied(self):
        """Test that connections without associated users are denied."""
        # Mock WebSocket connection NOT in connection_users
        websocket = Mock(spec=WebSocket)

        # Test authorization without user association
        is_authorized = await is_user_authorized_for_message(
            websocket=websocket,
            entity_type="task",
            entity_id="task123",
            triggering_user_id="user123",
            metadata={}
        )

        assert is_authorized is False

    @pytest.mark.asyncio
    async def test_subtask_authorization_via_parent_task(self):
        """Test that subtask authorization works through parent task ownership."""
        # Mock WebSocket connection
        websocket = Mock(spec=WebSocket)

        # Create test user
        user = User(
            id="user123",
            email="test@example.com",
            username="testuser",
            password_hash="hashed"
        )

        # Store user in connection mapping
        connection_users[websocket] = user

        # Mock database session and query
        with patch('fastmcp.task_management.infrastructure.database.database_config.get_session') as mock_get_session:
            mock_session = Mock()
            mock_get_session.return_value.__enter__.return_value = mock_session

            # Mock parent task that user owns
            mock_task = Mock()
            mock_task.id = "parent_task_123"
            mock_task.user_id = "user123"
            mock_session.query.return_value.filter.return_value.first.return_value = mock_task

            # Test authorization for subtask via parent task ownership
            is_authorized = await is_user_authorized_for_message(
                websocket=websocket,
                entity_type="subtask",
                entity_id="subtask456",
                triggering_user_id="other_user",
                metadata={"parent_task_id": "parent_task_123"}
            )

            assert is_authorized is True

    @pytest.mark.asyncio
    async def test_database_error_denies_access(self):
        """Test that database errors result in denied access (fail-closed security)."""
        # Mock WebSocket connection
        websocket = Mock(spec=WebSocket)

        # Create test user
        user = User(
            id="user123",
            email="test@example.com",
            username="testuser",
            password_hash="hashed"
        )

        # Store user in connection mapping
        connection_users[websocket] = user

        # Mock database session that raises an exception
        with patch('fastmcp.task_management.infrastructure.database.database_config.get_session') as mock_get_session:
            mock_get_session.side_effect = Exception("Database connection failed")

            # Test that database errors deny access
            is_authorized = await is_user_authorized_for_message(
                websocket=websocket,
                entity_type="task",
                entity_id="task123",
                triggering_user_id="other_user",
                metadata={}
            )

            assert is_authorized is False


if __name__ == "__main__":
    pytest.main([__file__, "-v"])