"""
WebSocket JWT Token Validation Tests

Focused tests for JWT token validation in WebSocket connections.
Tests the validate_websocket_token function and authentication flow.

COVERAGE:
- Token format validation
- Keycloak vs Local JWT token routing
- Token expiry handling
- Malformed token rejection
- Missing token rejection
- Token signature validation
"""

import pytest
import asyncio
import jwt
from datetime import datetime, timedelta, timezone
from unittest.mock import patch, AsyncMock, MagicMock
import os

# Import the function under test
from fastmcp.server.routes.websocket_routes import validate_websocket_token
from fastmcp.auth.domain.entities.user import User


class TestWebSocketTokenValidation:
    """Test JWT token validation for WebSocket connections"""

    def setup_method(self):
        """Set up test environment"""
        self.test_secret = "test-secret-for-validation"
        self.test_user_id = "test_user_123"
        self.test_email = "test@example.com"

    def create_test_token(self, issuer="local", expires_in_minutes=30, **extra_claims):
        """Create a test JWT token"""
        payload = {
            "sub": self.test_user_id,
            "user_id": self.test_user_id,
            "email": self.test_email,
            "aud": "authenticated" if issuer == "keycloak" else None,
            "iss": f"http://localhost:8080/realms/agenthub" if issuer == "keycloak" else "local-issuer",
            "exp": datetime.now(timezone.utc) + timedelta(minutes=expires_in_minutes),
            "iat": datetime.now(timezone.utc),
            "role": "authenticated",
            **extra_claims
        }
        return jwt.encode(payload, self.test_secret, algorithm="HS256")

    @pytest.mark.asyncio
    async def test_valid_keycloak_token_validation(self):
        """Test validation of valid Keycloak token"""
        # Set up environment for Keycloak
        with patch.dict(os.environ, {
            'KEYCLOAK_URL': 'http://localhost:8080',
            'AUTH_PROVIDER': 'keycloak'
        }):
            # Create Keycloak-style token
            token = self.create_test_token(issuer="keycloak")

            # Mock the validate_keycloak_token function
            expected_user = User(
                id=self.test_user_id,
                email=self.test_email,
                username="testuser",
                password_hash="dummy_hash_for_test"
            )

            with patch('fastmcp.server.routes.websocket_routes.validate_keycloak_token') as mock_validate:
                mock_validate.return_value = expected_user

                # Test validation
                result = await validate_websocket_token(token)

                # Assertions
                assert result is not None
                assert result.id == self.test_user_id
                assert result.email == self.test_email
                mock_validate.assert_called_once_with(token)

    @pytest.mark.asyncio
    async def test_valid_local_token_validation(self):
        """Test validation of valid local JWT token"""
        # Set up environment for local auth
        with patch.dict(os.environ, {
            'AUTH_PROVIDER': 'local'
        }):
            # Create local token
            token = self.create_test_token(issuer="local")

            # Mock the validate_local_token function
            expected_user = User(
                id=self.test_user_id,
                email=self.test_email,
                username="testuser",
                password_hash="dummy_hash_for_test"
            )

            with patch('fastmcp.server.routes.websocket_routes.validate_local_token') as mock_validate:
                mock_validate.return_value = expected_user

                # Test validation
                result = await validate_websocket_token(token)

                # Assertions
                assert result is not None
                assert result.id == self.test_user_id
                assert result.email == self.test_email
                mock_validate.assert_called_once_with(token)

    @pytest.mark.asyncio
    async def test_empty_token_rejection(self):
        """Test rejection of empty or None token"""
        # Test None token
        result = await validate_websocket_token(None)
        assert result is None

        # Test empty string token
        result = await validate_websocket_token("")
        assert result is None

        # Test whitespace token
        result = await validate_websocket_token("   ")
        assert result is None

    @pytest.mark.asyncio
    async def test_malformed_token_rejection(self):
        """Test rejection of malformed JWT tokens"""
        malformed_tokens = [
            "not.a.jwt.token",
            "definitely.not.jwt",
            "eyJ0eXAiOiJKV1QiLCJhbGciOiJIUzI1NiJ9.invalid",
            "header.payload",  # Missing signature
            "too.many.parts.in.token.here",
            "invalid-base64-@#$%",
        ]

        for token in malformed_tokens:
            result = await validate_websocket_token(token)
            assert result is None, f"Malformed token should be rejected: {token}"

    @pytest.mark.asyncio
    async def test_expired_token_rejection(self):
        """Test rejection of expired JWT tokens"""
        # Create expired token
        expired_token = self.create_test_token(expires_in_minutes=-30)  # Expired 30 minutes ago

        with patch.dict(os.environ, {'AUTH_PROVIDER': 'local'}):
            with patch('fastmcp.server.routes.websocket_routes.validate_local_token') as mock_validate:
                from fastapi import HTTPException
                mock_validate.side_effect = HTTPException(status_code=401, detail="Token expired")

                result = await validate_websocket_token(expired_token)
                assert result is None

    @pytest.mark.asyncio
    async def test_invalid_signature_rejection(self):
        """Test rejection of tokens with invalid signatures"""
        # Create token with wrong secret
        payload = {
            "sub": self.test_user_id,
            "exp": datetime.now(timezone.utc) + timedelta(minutes=30)
        }
        invalid_token = jwt.encode(payload, "wrong-secret", algorithm="HS256")

        with patch.dict(os.environ, {'AUTH_PROVIDER': 'local'}):
            with patch('fastmcp.server.routes.websocket_routes.validate_local_token') as mock_validate:
                from fastapi import HTTPException
                mock_validate.side_effect = HTTPException(status_code=401, detail="Invalid signature")

                result = await validate_websocket_token(invalid_token)
                assert result is None

    @pytest.mark.asyncio
    async def test_keycloak_token_fallback_to_local(self):
        """Test fallback from Keycloak to local validation when Keycloak fails"""
        # Create local-style token but with Keycloak environment
        token = self.create_test_token(issuer="local")

        with patch.dict(os.environ, {
            'KEYCLOAK_URL': 'http://localhost:8080',
            'AUTH_PROVIDER': 'keycloak'
        }):
            expected_user = User(
                id=self.test_user_id,
                email=self.test_email,
                username="testuser",
                password_hash="dummy_hash_for_test"
            )

            with patch('fastmcp.server.routes.websocket_routes.validate_keycloak_token') as mock_keycloak:
                from fastapi import HTTPException
                mock_keycloak.side_effect = HTTPException(status_code=401, detail="Not a Keycloak token")

                with patch('fastmcp.server.routes.websocket_routes.validate_local_token') as mock_local:
                    mock_local.return_value = expected_user

                    result = await validate_websocket_token(token)

                    # Should succeed with local validation
                    assert result is not None
                    assert result.id == self.test_user_id
                    mock_local.assert_called_once_with(token)

    @pytest.mark.asyncio
    async def test_token_validation_error_handling(self):
        """Test error handling during token validation"""
        token = self.create_test_token()

        with patch.dict(os.environ, {'AUTH_PROVIDER': 'local'}):
            with patch('fastmcp.server.routes.websocket_routes.validate_local_token') as mock_validate:
                # Simulate unexpected error
                mock_validate.side_effect = Exception("Database connection failed")

                result = await validate_websocket_token(token)
                assert result is None

    @pytest.mark.asyncio
    async def test_token_decode_error_handling(self):
        """Test handling of JWT decode errors"""
        # Create a token that looks valid but has decode issues
        invalid_base64_token = "eyJ0eXAiOiJKV1QiLCJhbGciOiJIUzI1NiJ9.invalid-base64.signature"

        result = await validate_websocket_token(invalid_base64_token)
        assert result is None

    @pytest.mark.asyncio
    async def test_missing_user_claims_rejection(self):
        """Test rejection of tokens missing required user claims"""
        # Create token without 'sub' claim
        payload = {
            "aud": "authenticated",
            "exp": datetime.now(timezone.utc) + timedelta(minutes=30),
            "role": "authenticated"
            # Missing 'sub' and 'user_id'
        }
        token = jwt.encode(payload, self.test_secret, algorithm="HS256")

        with patch.dict(os.environ, {'AUTH_PROVIDER': 'local'}):
            with patch('fastmcp.server.routes.websocket_routes.validate_local_token') as mock_validate:
                from fastapi import HTTPException
                mock_validate.side_effect = HTTPException(status_code=401, detail="Missing user claims")

                result = await validate_websocket_token(token)
                assert result is None

    @pytest.mark.asyncio
    async def test_revoked_token_rejection(self):
        """Test rejection of revoked tokens"""
        token = self.create_test_token()

        with patch.dict(os.environ, {'AUTH_PROVIDER': 'local'}):
            with patch('fastmcp.server.routes.websocket_routes.validate_local_token') as mock_validate:
                from fastapi import HTTPException
                mock_validate.side_effect = HTTPException(status_code=401, detail="Token revoked")

                result = await validate_websocket_token(token)
                assert result is None

    @pytest.mark.asyncio
    async def test_token_audience_mismatch(self):
        """Test handling of tokens with incorrect audience"""
        # Create token with wrong audience
        token = self.create_test_token(aud="wrong-audience")

        with patch.dict(os.environ, {'AUTH_PROVIDER': 'local'}):
            with patch('fastmcp.server.routes.websocket_routes.validate_local_token') as mock_validate:
                from fastapi import HTTPException
                mock_validate.side_effect = HTTPException(status_code=401, detail="Invalid audience")

                result = await validate_websocket_token(token)
                assert result is None

    @pytest.mark.asyncio
    async def test_performance_under_load(self):
        """Test token validation performance under concurrent load"""
        token = self.create_test_token()
        expected_user = User(
            id=self.test_user_id,
            email=self.test_email,
            username="testuser",
            password_hash="dummy_hash_for_test"
        )

        with patch.dict(os.environ, {'AUTH_PROVIDER': 'local'}):
            with patch('fastmcp.server.routes.websocket_routes.validate_local_token') as mock_validate:
                mock_validate.return_value = expected_user

                # Test concurrent validations
                tasks = [validate_websocket_token(token) for _ in range(10)]
                results = await asyncio.gather(*tasks)

                # All should succeed
                assert all(result is not None for result in results)
                assert all(result.id == self.test_user_id for result in results)


if __name__ == "__main__":
    pytest.main([__file__, "-v"])