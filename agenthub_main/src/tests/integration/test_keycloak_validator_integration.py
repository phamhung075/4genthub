#!/usr/bin/env python3
"""
Comprehensive Integration Tests for Keycloak Token Validator

This test suite provides complete coverage for mcp_keycloak_validator.py (174 lines, currently 0% coverage).
Tests include happy path, error handling, and security scenarios for Keycloak token validation.

Priority: HIGHEST (ROI: 9.5/10)
Component: auth/mcp_keycloak_validator.py
Coverage Goal: 95%+ line coverage

Test Categories:
1. Happy Path: Valid token validation, JWKS caching, user info extraction
2. Error Scenarios: Invalid tokens, expired tokens, missing claims, network failures
3. Security Scenarios: Token introspection, permission validation, audience validation
4. Caching Scenarios: Token cache, JWKS cache, cache expiration
"""

import pytest
import asyncio
import os
import time
from datetime import datetime, timedelta
from typing import Dict, Any
from unittest.mock import AsyncMock, MagicMock, patch
import httpx
from jose import jwt

# Import the validator under test
from fastmcp.auth.mcp_keycloak_validator import (
    MCPKeycloakValidator,
    get_mcp_validator,
    validate_mcp_request
)


@pytest.fixture
def mock_keycloak_env():
    """Set up Keycloak environment variables for testing."""
    original_env = os.environ.copy()

    # Set test environment variables
    os.environ['KEYCLOAK_URL'] = 'http://localhost:8080'
    os.environ['KEYCLOAK_REALM'] = 'test-realm'
    os.environ['KEYCLOAK_CLIENT_ID'] = 'test-client'
    os.environ['KEYCLOAK_CLIENT_SECRET'] = 'test-secret'
    os.environ['KEYCLOAK_TOKEN_CACHE_TTL'] = '300'
    os.environ['KEYCLOAK_VERIFY_TOKEN_AUDIENCE'] = 'true'
    os.environ['KEYCLOAK_TOKEN_AUDIENCE'] = 'test-client'

    yield

    # Restore original environment
    os.environ.clear()
    os.environ.update(original_env)


@pytest.fixture
def validator(mock_keycloak_env):
    """Create a fresh validator instance for each test."""
    return MCPKeycloakValidator()


@pytest.fixture
def valid_jwt_claims():
    """Generate valid JWT claims for testing."""
    now = int(datetime.now().timestamp())
    exp = int((datetime.now() + timedelta(hours=1)).timestamp())

    return {
        'sub': 'test-user-id-123',
        'preferred_username': 'testuser',
        'email': 'test@example.com',
        'email_verified': True,
        'name': 'Test User',
        'given_name': 'Test',
        'family_name': 'User',
        'iat': now,
        'exp': exp,
        'aud': 'test-client',
        'iss': 'http://localhost:8080/realms/test-realm',
        'realm_access': {
            'roles': ['user', 'developer']
        },
        'resource_access': {
            'test-client': {
                'roles': ['mcp-access']
            }
        }
    }


@pytest.fixture
def mock_jwks():
    """Mock JWKS (JSON Web Key Set) for token validation."""
    return {
        'keys': [
            {
                'kid': 'test-key-id',
                'kty': 'RSA',
                'alg': 'RS256',
                'use': 'sig',
                'n': 'test-n-value',
                'e': 'AQAB'
            }
        ]
    }


@pytest.fixture
def create_test_token(valid_jwt_claims):
    """Factory to create test JWT tokens."""
    def _create_token(claims=None, kid='test-key-id'):
        """Create a JWT token with specified claims."""
        token_claims = claims or valid_jwt_claims.copy()
        # This creates a token without actual signing for testing
        # In real tests with jose library, you'd use a real signing key
        return jwt.encode(token_claims, 'test-secret', algorithm='HS256')

    return _create_token


# =============================================================================
# HAPPY PATH TESTS
# =============================================================================

class TestHappyPath:
    """Test successful token validation scenarios."""

    @pytest.mark.asyncio
    async def test_validate_mcp_token_success(self, validator, valid_jwt_claims, mock_jwks, create_test_token):
        """Test successful MCP token validation with valid token."""
        token = create_test_token()

        # Mock JWKS retrieval
        with patch.object(validator, '_get_jwks', return_value=mock_jwks):
            # Mock token decoding
            with patch.object(validator, '_decode_token', return_value=valid_jwt_claims):
                result = await validator.validate_mcp_token(token)

        assert result is not None
        assert result['sub'] == 'test-user-id-123'
        assert result['email'] == 'test@example.com'
        assert 'realm_access' in result

    @pytest.mark.asyncio
    async def test_extract_user_info_complete(self, validator, valid_jwt_claims):
        """Test extraction of complete user information from token claims."""
        user_info = validator.extract_user_info(valid_jwt_claims)

        assert user_info['user_id'] == 'test-user-id-123'
        assert user_info['username'] == 'testuser'
        assert user_info['email'] == 'test@example.com'
        assert user_info['name'] == 'Test User'
        assert user_info['given_name'] == 'Test'
        assert user_info['family_name'] == 'User'
        assert user_info['email_verified'] is True
        assert 'user' in user_info['roles']
        assert 'developer' in user_info['roles']
        assert len(user_info['mcp_permissions']) > 0

    @pytest.mark.asyncio
    async def test_role_extraction_from_realm_and_client(self, validator, valid_jwt_claims):
        """Test role extraction from both realm and client-specific access."""
        roles = validator._extract_roles(valid_jwt_claims)

        # Should include both realm roles and client roles
        assert 'user' in roles
        assert 'developer' in roles
        assert 'mcp-access' in roles
        assert len(roles) == 3

    @pytest.mark.asyncio
    async def test_mcp_permission_extraction_by_role(self, validator, valid_jwt_claims):
        """Test MCP permission extraction based on user roles."""
        permissions = validator._extract_mcp_permissions(valid_jwt_claims)

        # Developer role should have read, write, execute permissions
        assert 'mcp:read' in permissions
        assert 'mcp:write' in permissions
        assert 'mcp:execute' in permissions

    @pytest.mark.asyncio
    async def test_admin_permission_extraction(self, validator):
        """Test that admin role grants full MCP permissions."""
        admin_claims = {
            'sub': 'admin-user',
            'realm_access': {'roles': ['admin']},
            'resource_access': {}
        }

        permissions = validator._extract_mcp_permissions(admin_claims)

        assert 'mcp:*' in permissions

    @pytest.mark.asyncio
    async def test_jwks_caching_mechanism(self, validator, mock_jwks):
        """Test that JWKS is cached and reused within cache TTL."""
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = mock_jwks

        with patch('httpx.AsyncClient') as mock_client:
            mock_client.return_value.__aenter__.return_value.get = AsyncMock(return_value=mock_response)

            # First call should fetch from server
            result1 = await validator._get_jwks()

            # Second call should use cache (within 1 hour)
            result2 = await validator._get_jwks()

            # Should only call the API once due to caching
            assert mock_client.return_value.__aenter__.return_value.get.call_count == 1
            assert result1 == result2
            assert result1 == mock_jwks

    @pytest.mark.asyncio
    async def test_token_caching_mechanism(self, validator, valid_jwt_claims, mock_jwks, create_test_token):
        """Test that validated tokens are cached and reused."""
        token = create_test_token()

        with patch.object(validator, '_get_jwks', return_value=mock_jwks):
            with patch.object(validator, '_decode_token', return_value=valid_jwt_claims) as mock_decode:
                # First validation
                result1 = await validator.validate_mcp_token(token)

                # Second validation should use cache
                result2 = await validator.validate_mcp_token(token)

                # Decode should only be called once
                assert mock_decode.call_count == 1
                assert result1 == result2

    @pytest.mark.asyncio
    async def test_validate_mcp_request_success(self, create_test_token, valid_jwt_claims, mock_jwks):
        """Test successful MCP request validation with Bearer token."""
        token = create_test_token()
        authorization = f"Bearer {token}"

        with patch('fastmcp.auth.mcp_keycloak_validator.get_mcp_validator') as mock_get_validator:
            mock_validator = MagicMock()
            mock_validator.validate_mcp_token = AsyncMock(return_value=valid_jwt_claims)
            mock_validator.extract_user_info.return_value = {
                'user_id': 'test-user-id-123',
                'username': 'testuser',
                'email': 'test@example.com'
            }
            mock_get_validator.return_value = mock_validator

            result = await validate_mcp_request(authorization)

            assert result is not None
            assert result['user_id'] == 'test-user-id-123'
            assert result['username'] == 'testuser'


# =============================================================================
# ERROR SCENARIO TESTS
# =============================================================================

class TestErrorScenarios:
    """Test error handling for invalid tokens and edge cases."""

    @pytest.mark.asyncio
    async def test_validate_token_with_expired_claims(self, validator, valid_jwt_claims):
        """Test that expired tokens are rejected."""
        # Set expiration to past
        expired_claims = valid_jwt_claims.copy()
        expired_claims['exp'] = int((datetime.now() - timedelta(hours=1)).timestamp())

        is_valid = validator._validate_mcp_requirements(expired_claims)

        assert is_valid is False

    @pytest.mark.asyncio
    async def test_validate_token_missing_required_claims(self, validator, valid_jwt_claims):
        """Test that tokens missing required claims are rejected."""
        # Remove required 'sub' claim
        incomplete_claims = valid_jwt_claims.copy()
        del incomplete_claims['sub']

        is_valid = validator._validate_mcp_requirements(incomplete_claims)

        assert is_valid is False

    @pytest.mark.asyncio
    async def test_validate_token_missing_exp_claim(self, validator, valid_jwt_claims):
        """Test that tokens missing 'exp' claim are rejected."""
        incomplete_claims = valid_jwt_claims.copy()
        del incomplete_claims['exp']

        is_valid = validator._validate_mcp_requirements(incomplete_claims)

        assert is_valid is False

    @pytest.mark.asyncio
    async def test_validate_token_missing_iat_claim(self, validator, valid_jwt_claims):
        """Test that tokens missing 'iat' claim are rejected."""
        incomplete_claims = valid_jwt_claims.copy()
        del incomplete_claims['iat']

        is_valid = validator._validate_mcp_requirements(incomplete_claims)

        assert is_valid is False

    @pytest.mark.asyncio
    async def test_validate_token_invalid_audience(self, validator, valid_jwt_claims):
        """Test that tokens with invalid audience are rejected."""
        invalid_aud_claims = valid_jwt_claims.copy()
        invalid_aud_claims['aud'] = 'wrong-audience'

        is_valid = validator._validate_mcp_requirements(invalid_aud_claims)

        assert is_valid is False

    @pytest.mark.asyncio
    async def test_validate_token_audience_list_without_expected(self, validator, valid_jwt_claims):
        """Test that tokens with audience list not containing expected audience are rejected."""
        invalid_aud_claims = valid_jwt_claims.copy()
        invalid_aud_claims['aud'] = ['other-client', 'another-client']

        is_valid = validator._validate_mcp_requirements(invalid_aud_claims)

        assert is_valid is False

    @pytest.mark.asyncio
    async def test_validate_token_audience_list_with_expected(self, validator, valid_jwt_claims):
        """Test that tokens with audience list containing expected audience are accepted."""
        valid_aud_claims = valid_jwt_claims.copy()
        valid_aud_claims['aud'] = ['test-client', 'other-client']

        is_valid = validator._validate_mcp_requirements(valid_aud_claims)

        assert is_valid is True

    @pytest.mark.asyncio
    async def test_validate_token_no_mcp_permissions(self, validator, valid_jwt_claims):
        """Test that tokens without any MCP permissions are rejected."""
        no_perm_claims = valid_jwt_claims.copy()
        no_perm_claims['realm_access'] = {'roles': []}
        no_perm_claims['resource_access'] = {}

        is_valid = validator._validate_mcp_requirements(no_perm_claims)

        assert is_valid is False

    @pytest.mark.asyncio
    async def test_jwks_retrieval_failure(self, validator):
        """Test handling of JWKS retrieval failure."""
        with patch('httpx.AsyncClient') as mock_client:
            mock_client.return_value.__aenter__.return_value.get = AsyncMock(
                side_effect=httpx.RequestError("Network error")
            )

            result = await validator._get_jwks()

            assert result is None

    @pytest.mark.asyncio
    async def test_jwks_http_error_response(self, validator):
        """Test handling of HTTP error when fetching JWKS."""
        mock_response = MagicMock()
        mock_response.status_code = 500

        with patch('httpx.AsyncClient') as mock_client:
            mock_client.return_value.__aenter__.return_value.get = AsyncMock(return_value=mock_response)

            result = await validator._get_jwks()

            assert result is None

    @pytest.mark.asyncio
    async def test_decode_token_with_missing_kid(self, validator, mock_jwks, create_test_token):
        """Test token decoding failure when key ID not found in JWKS."""
        token = create_test_token()

        # Mock jwt.get_unverified_header to return different kid
        with patch('jose.jwt.get_unverified_header', return_value={'kid': 'non-existent-key'}):
            result = await validator._decode_token(token, mock_jwks)

            assert result is None

    @pytest.mark.asyncio
    async def test_decode_token_jwt_error(self, validator, mock_jwks, create_test_token):
        """Test handling of JWT decoding errors."""
        token = create_test_token()

        with patch('jose.jwt.get_unverified_header', return_value={'kid': 'test-key-id'}):
            with patch('jose.jwt.decode', side_effect=jwt.JWTError("Invalid signature")):
                result = await validator._decode_token(token, mock_jwks)

                assert result is None

    @pytest.mark.asyncio
    async def test_validate_mcp_request_invalid_authorization_format(self):
        """Test validation failure with invalid authorization header format."""
        # Missing Bearer prefix
        result = await validate_mcp_request("InvalidFormat token123")
        assert result is None

        # Only token without scheme
        result = await validate_mcp_request("token123")
        assert result is None

        # Empty authorization
        result = await validate_mcp_request("")
        assert result is None

        # None authorization
        result = await validate_mcp_request(None)
        assert result is None

    @pytest.mark.asyncio
    async def test_validate_mcp_token_general_exception(self, validator, create_test_token):
        """Test handling of unexpected exceptions during validation."""
        token = create_test_token()

        with patch.object(validator, '_get_jwks', side_effect=Exception("Unexpected error")):
            result = await validator.validate_mcp_token(token)

            assert result is None


# =============================================================================
# SECURITY SCENARIO TESTS
# =============================================================================

class TestSecurityScenarios:
    """Test security-related validation scenarios."""

    @pytest.mark.asyncio
    async def test_token_introspection_active_token(self, validator):
        """Test token introspection with active token."""
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            'active': True,
            'sub': 'user-123',
            'scope': 'openid profile email',
            'client_id': 'test-client'
        }

        with patch('httpx.AsyncClient') as mock_client:
            mock_client.return_value.__aenter__.return_value.post = AsyncMock(return_value=mock_response)

            result = await validator.introspect_token('test-token')

            assert result is not None
            assert result['active'] is True
            assert result['sub'] == 'user-123'

    @pytest.mark.asyncio
    async def test_token_introspection_inactive_token(self, validator):
        """Test token introspection with inactive/revoked token."""
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {'active': False}

        with patch('httpx.AsyncClient') as mock_client:
            mock_client.return_value.__aenter__.return_value.post = AsyncMock(return_value=mock_response)

            result = await validator.introspect_token('revoked-token')

            assert result is None

    @pytest.mark.asyncio
    async def test_token_introspection_network_error(self, validator):
        """Test handling of network errors during token introspection."""
        with patch('httpx.AsyncClient') as mock_client:
            mock_client.return_value.__aenter__.return_value.post = AsyncMock(
                side_effect=httpx.RequestError("Connection failed")
            )

            result = await validator.introspect_token('test-token')

            assert result is None

    @pytest.mark.asyncio
    async def test_token_introspection_http_error(self, validator):
        """Test handling of HTTP errors during token introspection."""
        mock_response = MagicMock()
        mock_response.status_code = 401

        with patch('httpx.AsyncClient') as mock_client:
            mock_client.return_value.__aenter__.return_value.post = AsyncMock(return_value=mock_response)

            result = await validator.introspect_token('test-token')

            assert result is None

    @pytest.mark.asyncio
    async def test_custom_mcp_permissions_in_token(self, validator):
        """Test extraction of custom MCP permissions from token claims."""
        claims = {
            'sub': 'user-123',
            'realm_access': {'roles': []},
            'mcp_permissions': ['mcp:custom:action1', 'mcp:custom:action2']
        }

        permissions = validator._extract_mcp_permissions(claims)

        assert 'mcp:custom:action1' in permissions
        assert 'mcp:custom:action2' in permissions

    @pytest.mark.asyncio
    async def test_viewer_role_limited_permissions(self, validator):
        """Test that viewer role has read-only permissions."""
        viewer_claims = {
            'sub': 'viewer-user',
            'realm_access': {'roles': ['viewer']},
            'resource_access': {}
        }

        permissions = validator._extract_mcp_permissions(viewer_claims)

        assert 'mcp:read' in permissions
        assert 'mcp:write' not in permissions
        assert 'mcp:execute' not in permissions

    @pytest.mark.asyncio
    async def test_user_role_execute_permissions(self, validator):
        """Test that user role has read and execute permissions."""
        user_claims = {
            'sub': 'regular-user',
            'realm_access': {'roles': ['user']},
            'resource_access': {}
        }

        permissions = validator._extract_mcp_permissions(user_claims)

        assert 'mcp:read' in permissions
        assert 'mcp:execute' in permissions
        assert 'mcp:write' not in permissions

    @pytest.mark.asyncio
    async def test_audience_validation_disabled(self, validator, valid_jwt_claims):
        """Test that audience validation can be disabled via environment variable."""
        # Disable audience verification
        os.environ['KEYCLOAK_VERIFY_TOKEN_AUDIENCE'] = 'false'

        # Create new validator with updated env
        test_validator = MCPKeycloakValidator()

        # Token with any audience should be valid when verification is disabled
        any_aud_claims = valid_jwt_claims.copy()
        any_aud_claims['aud'] = 'any-audience'

        is_valid = test_validator._validate_mcp_requirements(any_aud_claims)

        # Should pass even with wrong audience
        assert is_valid is True

        # Restore
        os.environ['KEYCLOAK_VERIFY_TOKEN_AUDIENCE'] = 'true'


# =============================================================================
# CACHING SCENARIO TESTS
# =============================================================================

class TestCachingScenarios:
    """Test caching mechanisms for performance optimization."""

    @pytest.mark.asyncio
    async def test_token_cache_expiration(self, validator, valid_jwt_claims, mock_jwks, create_test_token):
        """Test that cached token validations expire after TTL."""
        # Set short cache TTL for testing
        validator._cache_ttl = 1  # 1 second

        token = create_test_token()

        with patch.object(validator, '_get_jwks', return_value=mock_jwks):
            with patch.object(validator, '_decode_token', return_value=valid_jwt_claims) as mock_decode:
                # First validation
                result1 = await validator.validate_mcp_token(token)

                # Wait for cache to expire
                time.sleep(2)

                # Second validation should call decode again
                result2 = await validator.validate_mcp_token(token)

                # Decode should be called twice (cache expired)
                assert mock_decode.call_count == 2

    @pytest.mark.asyncio
    async def test_jwks_cache_expiration(self, validator, mock_jwks):
        """Test that JWKS cache expires after 1 hour."""
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = mock_jwks

        with patch('httpx.AsyncClient') as mock_client:
            mock_client.return_value.__aenter__.return_value.get = AsyncMock(return_value=mock_response)

            # First fetch
            await validator._get_jwks()

            # Set cache time to be old (more than 1 hour ago)
            validator._jwks_cache_time = datetime.now() - timedelta(hours=2)

            # Second fetch should refresh cache
            await validator._get_jwks()

            # Should call API twice (cache expired)
            assert mock_client.return_value.__aenter__.return_value.get.call_count == 2

    @pytest.mark.asyncio
    async def test_cache_cleanup_removes_expired_entries(self, validator, valid_jwt_claims):
        """Test that cache cleanup removes expired entries."""
        validator._cache_ttl = 1  # 1 second TTL

        # Add multiple unique tokens to cache manually
        for i in range(5):
            unique_token = f'test-token-{i}'
            validator._cache_validation(unique_token, valid_jwt_claims)

        # All tokens should be cached
        assert len(validator._token_cache) == 5

        # Wait for cache to expire
        time.sleep(2)

        # Trigger cleanup by caching new token
        validator._cache_validation('new-token', valid_jwt_claims)

        # Old entries should be cleaned up, only new token remains
        assert len(validator._token_cache) == 1
        assert 'new-token' in validator._token_cache

    @pytest.mark.asyncio
    async def test_get_cached_validation_hit(self, validator, valid_jwt_claims):
        """Test cache hit when getting cached validation."""
        token = 'test-token-123'
        validator._cache_validation(token, valid_jwt_claims)

        result = validator._get_cached_validation(token)

        assert result is not None
        assert result == valid_jwt_claims

    @pytest.mark.asyncio
    async def test_get_cached_validation_miss(self, validator):
        """Test cache miss when token not in cache."""
        result = validator._get_cached_validation('non-existent-token')

        assert result is None

    @pytest.mark.asyncio
    async def test_get_cached_validation_expired(self, validator, valid_jwt_claims):
        """Test that expired cache entries return None."""
        validator._cache_ttl = 1  # 1 second TTL

        token = 'test-token-456'
        validator._cache_validation(token, valid_jwt_claims)

        # Wait for expiration
        time.sleep(2)

        result = validator._get_cached_validation(token)

        # Should return None and remove expired entry
        assert result is None
        assert token not in validator._token_cache


# =============================================================================
# SINGLETON AND FACTORY TESTS
# =============================================================================

class TestSingletonAndFactory:
    """Test global validator instance and factory functions."""

    def test_get_mcp_validator_singleton(self, mock_keycloak_env):
        """Test that get_mcp_validator returns singleton instance."""
        # Clear global instance
        import fastmcp.auth.mcp_keycloak_validator as validator_module
        validator_module._validator = None

        # Get validator instances
        validator1 = get_mcp_validator()
        validator2 = get_mcp_validator()

        # Should be the same instance
        assert validator1 is validator2

    def test_validator_initialization(self, mock_keycloak_env):
        """Test that validator is properly initialized with environment variables."""
        validator = MCPKeycloakValidator()

        assert validator.keycloak_url == 'http://localhost:8080'
        assert validator.realm == 'test-realm'
        assert validator.client_id == 'test-client'
        assert validator.client_secret == 'test-secret'
        assert validator.realm_url == 'http://localhost:8080/realms/test-realm'
        assert validator.jwks_uri == 'http://localhost:8080/realms/test-realm/protocol/openid-connect/certs'
        assert validator.introspect_endpoint == 'http://localhost:8080/realms/test-realm/protocol/openid-connect/token/introspect'

    def test_validator_default_values(self):
        """Test validator initialization with default values."""
        # Save and clear environment to test defaults
        original_env = {}
        for key in ['KEYCLOAK_REALM', 'KEYCLOAK_CLIENT_ID', 'KEYCLOAK_TOKEN_CACHE_TTL']:
            original_env[key] = os.environ.get(key)
            if key in os.environ:
                del os.environ[key]

        # Set minimal required environment
        os.environ['KEYCLOAK_URL'] = 'http://localhost:8080'

        validator = MCPKeycloakValidator()

        # Should use default values
        assert validator.realm == 'agenthub'
        assert validator.client_id == 'mcp-backend'
        assert validator._cache_ttl == 300

        # Restore original environment
        for key, value in original_env.items():
            if value is not None:
                os.environ[key] = value


# =============================================================================
# EDGE CASES AND BOUNDARY TESTS
# =============================================================================

class TestEdgeCases:
    """Test edge cases and boundary conditions."""

    @pytest.mark.asyncio
    async def test_empty_roles_in_claims(self, validator):
        """Test handling of empty roles in token claims."""
        empty_roles_claims = {
            'sub': 'user-123',
            'realm_access': {},
            'resource_access': {}
        }

        roles = validator._extract_roles(empty_roles_claims)

        assert roles == []

    @pytest.mark.asyncio
    async def test_missing_realm_access(self, validator):
        """Test handling of missing realm_access in claims."""
        claims = {
            'sub': 'user-123',
            'resource_access': {}
        }

        roles = validator._extract_roles(claims)

        assert isinstance(roles, list)

    @pytest.mark.asyncio
    async def test_missing_resource_access(self, validator):
        """Test handling of missing resource_access in claims."""
        claims = {
            'sub': 'user-123',
            'realm_access': {'roles': ['user']}
        }

        roles = validator._extract_roles(claims)

        assert 'user' in roles

    @pytest.mark.asyncio
    async def test_invalid_mcp_permissions_format(self, validator):
        """Test handling of invalid mcp_permissions format in claims."""
        claims = {
            'sub': 'user-123',
            'realm_access': {'roles': ['user']},
            'mcp_permissions': 'not-a-list'  # Invalid format
        }

        # Should not raise exception, just skip custom permissions
        permissions = validator._extract_mcp_permissions(claims)

        # Should still have permissions from 'user' role
        assert 'mcp:read' in permissions

    @pytest.mark.asyncio
    async def test_empty_jwks_keys(self, validator, create_test_token):
        """Test handling of JWKS with empty keys array."""
        token = create_test_token()
        empty_jwks = {'keys': []}

        with patch('jose.jwt.get_unverified_header', return_value={'kid': 'test-key-id'}):
            result = await validator._decode_token(token, empty_jwks)

            # Should return None when key not found
            assert result is None

    @pytest.mark.asyncio
    async def test_extract_user_info_minimal_claims(self, validator):
        """Test user info extraction with minimal claims."""
        minimal_claims = {'sub': 'user-123'}

        user_info = validator.extract_user_info(minimal_claims)

        # Should handle missing fields gracefully
        assert user_info['user_id'] == 'user-123'
        assert user_info['username'] is None
        assert user_info['email'] is None
        assert user_info['email_verified'] is False
        assert user_info['roles'] == []


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
