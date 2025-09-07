"""
Tests for OAuth provider compatibility layer
"""

import pytest
from fastmcp.server.auth.auth import (
    ClientRegistrationOptions,
    RevocationOptions,
    OAuthProvider,
    AuthorizationCode,
    RefreshToken,
    AccessToken
)


class TestClientRegistrationOptions:
    """Test suite for ClientRegistrationOptions"""

    def test_default_values(self):
        """Test default values for ClientRegistrationOptions"""
        options = ClientRegistrationOptions()
        
        assert options.enabled is False
        assert options.client_name is None
        assert options.client_uri is None
        assert options.redirect_uris == []

    def test_custom_values(self):
        """Test custom values for ClientRegistrationOptions"""
        options = ClientRegistrationOptions(
            enabled=True,
            client_name="Test Client",
            client_uri="https://example.com",
            redirect_uris=["https://example.com/callback"]
        )
        
        assert options.enabled is True
        assert options.client_name == "Test Client"
        assert options.client_uri == "https://example.com"
        assert options.redirect_uris == ["https://example.com/callback"]

    def test_pydantic_validation(self):
        """Test Pydantic model validation"""
        # Should work with dict input
        options = ClientRegistrationOptions(**{
            "enabled": True,
            "client_name": "Test"
        })
        assert options.enabled is True
        assert options.client_name == "Test"


class TestRevocationOptions:
    """Test suite for RevocationOptions"""

    def test_default_values(self):
        """Test default values for RevocationOptions"""
        options = RevocationOptions()
        
        assert options.enabled is False
        assert options.revocation_endpoint is None

    def test_custom_values(self):
        """Test custom values for RevocationOptions"""
        options = RevocationOptions(
            enabled=True,
            revocation_endpoint="https://auth.example.com/revoke"
        )
        
        assert options.enabled is True
        assert options.revocation_endpoint == "https://auth.example.com/revoke"


class TestOAuthProvider:
    """Test suite for OAuthProvider"""

    def test_minimal_initialization(self):
        """Test OAuthProvider with minimal parameters"""
        provider = OAuthProvider(issuer_url="https://auth.example.com")
        
        assert provider.issuer_url == "https://auth.example.com"
        assert provider.service_documentation_url is None
        assert provider.client_registration_options is None
        assert provider.revocation_options is None
        assert provider.required_scopes == []

    def test_full_initialization(self):
        """Test OAuthProvider with all parameters"""
        client_reg = ClientRegistrationOptions(enabled=True)
        revocation = RevocationOptions(enabled=True)
        
        provider = OAuthProvider(
            issuer_url="https://auth.example.com",
            service_documentation_url="https://docs.example.com",
            client_registration_options=client_reg,
            revocation_options=revocation,
            required_scopes=["read", "write"]
        )
        
        assert provider.issuer_url == "https://auth.example.com"
        assert provider.service_documentation_url == "https://docs.example.com"
        assert provider.client_registration_options == client_reg
        assert provider.revocation_options == revocation
        assert provider.required_scopes == ["read", "write"]

    def test_none_required_scopes_defaults_to_empty_list(self):
        """Test that None required_scopes becomes empty list"""
        provider = OAuthProvider(
            issuer_url="https://auth.example.com",
            required_scopes=None
        )
        
        assert provider.required_scopes == []


class TestAuthorizationCode:
    """Test suite for AuthorizationCode dataclass"""

    def test_minimal_initialization(self):
        """Test AuthorizationCode with required parameters"""
        auth_code = AuthorizationCode(code="abc123")
        
        assert auth_code.code == "abc123"
        assert auth_code.state is None

    def test_full_initialization(self):
        """Test AuthorizationCode with all parameters"""
        auth_code = AuthorizationCode(
            code="abc123",
            state="xyz789"
        )
        
        assert auth_code.code == "abc123"
        assert auth_code.state == "xyz789"

    def test_dataclass_features(self):
        """Test dataclass features like equality"""
        auth_code1 = AuthorizationCode(code="abc123", state="xyz")
        auth_code2 = AuthorizationCode(code="abc123", state="xyz")
        auth_code3 = AuthorizationCode(code="def456", state="xyz")
        
        assert auth_code1 == auth_code2
        assert auth_code1 != auth_code3


class TestRefreshToken:
    """Test suite for RefreshToken dataclass"""

    def test_minimal_initialization(self):
        """Test RefreshToken with required parameters"""
        token = RefreshToken(token="refresh_abc123")
        
        assert token.token == "refresh_abc123"
        assert token.expires_at is None

    def test_full_initialization(self):
        """Test RefreshToken with all parameters"""
        expires = 1234567890
        token = RefreshToken(
            token="refresh_abc123",
            expires_at=expires
        )
        
        assert token.token == "refresh_abc123"
        assert token.expires_at == expires

    def test_dataclass_features(self):
        """Test dataclass features"""
        token1 = RefreshToken(token="refresh_abc", expires_at=123)
        token2 = RefreshToken(token="refresh_abc", expires_at=123)
        
        assert token1 == token2


class TestAccessToken:
    """Test suite for AccessToken dataclass"""

    def test_minimal_initialization(self):
        """Test AccessToken with required parameters"""
        token = AccessToken(token="access_abc123")
        
        assert token.token == "access_abc123"
        assert token.token_type == "Bearer"  # Default value
        assert token.expires_in is None
        assert token.scope is None

    def test_full_initialization(self):
        """Test AccessToken with all parameters"""
        token = AccessToken(
            token="access_abc123",
            token_type="Custom",
            expires_in=3600,
            scope="read write"
        )
        
        assert token.token == "access_abc123"
        assert token.token_type == "Custom"
        assert token.expires_in == 3600
        assert token.scope == "read write"

    def test_default_token_type(self):
        """Test that token_type defaults to Bearer"""
        token = AccessToken(token="test")
        assert token.token_type == "Bearer"

    def test_dataclass_equality(self):
        """Test dataclass equality comparison"""
        token1 = AccessToken(token="abc", expires_in=3600)
        token2 = AccessToken(token="abc", expires_in=3600)
        token3 = AccessToken(token="xyz", expires_in=3600)
        
        assert token1 == token2
        assert token1 != token3