"""
Test JWTAuthBackend properties for token_router compatibility
"""
import os
import pytest
from unittest.mock import Mock, patch

# Set test JWT secret before imports
os.environ['JWT_SECRET_KEY'] = 'test-secret-key-for-testing'

from fastmcp.auth.mcp_integration.jwt_auth_backend import JWTAuthBackend
from fastmcp.auth.domain.services.jwt_service import JWTService


class TestJWTAuthBackendProperties:
    """Test that JWTAuthBackend exposes necessary properties for token_router"""
    
    def setup_method(self):
        """Set up test environment"""
        os.environ['JWT_SECRET_KEY'] = 'test-secret-key-for-testing'
    
    def test_secret_key_property_accessible(self):
        """Test that secret_key property is accessible"""
        backend = JWTAuthBackend()
        
        # Access the property
        secret_key = backend.secret_key
        
        # Verify it's a string and matches expected value
        assert isinstance(secret_key, str)
        assert secret_key == 'test-secret-key-for-testing'
    
    def test_algorithm_property_accessible(self):
        """Test that algorithm property is accessible"""
        backend = JWTAuthBackend()
        
        # Access the property
        algorithm = backend.algorithm
        
        # Verify it's the expected algorithm
        assert algorithm == "HS256"
        assert algorithm == JWTService.ALGORITHM
    
    def test_properties_with_custom_jwt_service(self):
        """Test properties work with custom JWT service"""
        custom_secret = 'custom-secret-key'
        jwt_service = JWTService(secret_key=custom_secret)
        
        backend = JWTAuthBackend(jwt_service=jwt_service)
        
        # Verify properties return values from custom service
        assert backend.secret_key == custom_secret
        assert backend.algorithm == jwt_service.ALGORITHM
    
    def test_token_router_compatibility(self):
        """Test that properties work as expected by token_router"""
        import jwt
        from datetime import datetime, timedelta, timezone
        
        backend = JWTAuthBackend()
        
        # Simulate token_router usage pattern
        payload = {
            "token_id": "tok_test123",
            "user_id": "user_123",
            "scopes": ["read", "write"],
            "exp": datetime.now(timezone.utc) + timedelta(days=30),
            "iat": datetime.now(timezone.utc),
            "type": "api_token"
        }
        
        # This is how token_router uses the backend
        token = jwt.encode(payload, backend.secret_key, algorithm=backend.algorithm)
        
        # Verify the token can be decoded
        decoded = jwt.decode(token, backend.secret_key, algorithms=[backend.algorithm])
        
        assert decoded["token_id"] == "tok_test123"
        assert decoded["user_id"] == "user_123"
        assert decoded["type"] == "api_token"
    
    def test_properties_immutable(self):
        """Test that properties are read-only"""
        backend = JWTAuthBackend()
        
        # Attempt to modify properties should raise AttributeError
        with pytest.raises(AttributeError):
            backend.secret_key = "new-secret"
        
        with pytest.raises(AttributeError):
            backend.algorithm = "RS256"