"""
Simple WebSocket JWT Authentication Test

Tests the critical security fix for JWT validation in WebSocket connections.
"""

import pytest
import asyncio
import json
from unittest.mock import AsyncMock, MagicMock, patch
import jwt
from datetime import datetime, timedelta, timezone

# Import the modules to test
from fastmcp.server.routes.websocket_routes import validate_websocket_token, is_user_authorized_for_message
from fastmcp.auth.domain.entities.user import User


class TestWebSocketJWTAuth:
    """Test WebSocket JWT authentication implementation"""

    @pytest.mark.asyncio
    async def test_validate_websocket_token_with_valid_token(self):
        """Test that valid tokens are accepted"""

        # Create a valid user object to return from mock
        mock_user = User(
            id="test_user_123",
            email="test@example.com",
            username="testuser",
            password_hash="hashed"
        )

        # Mock the validation functions and jwt decode
        with patch('fastmcp.server.routes.websocket_routes.validate_keycloak_token') as mock_keycloak:
            with patch('fastmcp.server.routes.websocket_routes.validate_local_token') as mock_local:
                with patch('fastmcp.server.routes.websocket_routes.os.getenv') as mock_getenv:
                    with patch('jwt.decode') as mock_jwt_decode:

                        # Configure mocks for local JWT validation
                        mock_getenv.side_effect = lambda key, default=None: {
                            'AUTH_PROVIDER': 'local',
                            'KEYCLOAK_URL': None
                        }.get(key, default)

                        # Mock jwt.decode to return a local token payload (no issuer for local tokens)
                        mock_jwt_decode.return_value = {
                            "sub": "test_user_123",
                            "email": "test@example.com"
                        }

                        mock_local.return_value = mock_user

                        # Test with a valid token
                        valid_token = "valid.jwt.token"
                        result = await validate_websocket_token(valid_token)

                        assert result is not None
                        assert result.id == "test_user_123"
                        assert result.email == "test@example.com"

    @pytest.mark.asyncio
    async def test_validate_websocket_token_with_invalid_token(self):
        """Test that invalid tokens are rejected"""

        # Mock the validation functions to return HTTPException
        with patch('fastmcp.server.routes.websocket_routes.validate_keycloak_token') as mock_keycloak:
            with patch('fastmcp.server.routes.websocket_routes.validate_local_token') as mock_local:
                with patch('fastmcp.server.routes.websocket_routes.os.getenv') as mock_getenv:
                    with patch('jwt.decode') as mock_jwt_decode:
                        from fastapi import HTTPException

                        # Configure mocks for local JWT validation
                        mock_getenv.side_effect = lambda key, default=None: {
                            'AUTH_PROVIDER': 'local',
                            'KEYCLOAK_URL': None
                        }.get(key, default)

                        # Mock jwt.decode to return a local token payload (no issuer for local tokens)
                        mock_jwt_decode.return_value = {
                            "sub": "invalid_user",
                            "email": "invalid@example.com"
                        }

                        # Mock validation to raise HTTPException (invalid token)
                        mock_local.side_effect = HTTPException(status_code=401, detail="Invalid token")

                        # Test with invalid token
                        invalid_token = "invalid.jwt.token"
                        result = await validate_websocket_token(invalid_token)

                        assert result is None

    @pytest.mark.asyncio
    async def test_validate_websocket_token_with_no_token(self):
        """Test that missing tokens are rejected"""

        result = await validate_websocket_token(None)
        assert result is None

        result = await validate_websocket_token("")
        assert result is None

    @pytest.mark.asyncio
    async def test_user_authorization_for_own_data(self):
        """Test that users are authorized for their own data"""

        # Create mock WebSocket and user
        mock_websocket = AsyncMock()
        mock_user = User(
            id="test_user_123",
            email="test@example.com",
            username="testuser",
            password_hash="hashed"
        )

        # Mock the connection_users dict
        with patch('fastmcp.server.routes.websocket_routes.connection_users', {mock_websocket: mock_user}) as mock_conn_users:

            # Test authorization for user's own data
            is_authorized = await is_user_authorized_for_message(
                websocket=mock_websocket,
                entity_type="task",
                entity_id="task_123",
                triggering_user_id="test_user_123",  # Same as user ID
                metadata={}
            )

            assert is_authorized is True

    @pytest.mark.asyncio
    async def test_user_authorization_for_others_data(self):
        """Test that users are not authorized for others' data"""

        # Create mock WebSocket and user
        mock_websocket = AsyncMock()
        mock_user = User(
            id="test_user_123",
            email="test@example.com",
            username="testuser",
            password_hash="hashed"
        )

        # Mock the connection_users dict and database session
        with patch('fastmcp.server.routes.websocket_routes.connection_users', {mock_websocket: mock_user}) as mock_conn_users:
            with patch('fastmcp.task_management.infrastructure.database.database_config.get_session') as mock_get_session:

                # Mock database session to return None (no access to task)
                mock_session = MagicMock()
                mock_session.query.return_value.filter.return_value.first.return_value = None
                mock_get_session.return_value.__enter__.return_value = mock_session

                # Test authorization for another user's data
                is_authorized = await is_user_authorized_for_message(
                    websocket=mock_websocket,
                    entity_type="task",
                    entity_id="task_456",
                    triggering_user_id="other_user_456",  # Different user
                    metadata={}
                )

                assert is_authorized is False

    @pytest.mark.asyncio
    async def test_user_authorization_without_user(self):
        """Test that authorization fails when no user is found"""

        mock_websocket = AsyncMock()

        # Mock empty connection_users dict
        with patch('fastmcp.server.routes.websocket_routes.connection_users', {}) as mock_conn_users:

            is_authorized = await is_user_authorized_for_message(
                websocket=mock_websocket,
                entity_type="task",
                entity_id="task_123",
                triggering_user_id="test_user_123",
                metadata={}
            )

            assert is_authorized is False


if __name__ == "__main__":
    pytest.main([__file__, "-v"])