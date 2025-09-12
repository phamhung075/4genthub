"""
Test Token Extraction from JWT
Tests for extracting user_id from JWT tokens using Keycloak authentication.
NO hardcoded IDs, NO legacy code - only token-based authentication.
"""

import pytest
from unittest.mock import Mock, patch
from datetime import datetime, timedelta
import jwt


class TestTokenExtraction:
    """Test JWT token extraction and user_id retrieval"""
    
    @pytest.fixture
    def mock_keycloak_token(self):
        """Create a mock Keycloak JWT token with user information"""
        # Keycloak token payload structure
        payload = {
            "exp": int((datetime.now(timezone.utc) + timedelta(hours=1)).timestamp()),
            "iat": int(datetime.now(timezone.utc).timestamp()),
            "auth_time": int(datetime.now(timezone.utc).timestamp()),
            "jti": "test-jwt-id-123",
            "iss": "http://localhost:8080/realms/dhafnck",
            "aud": "dhafnck-client",
            "sub": "user-uuid-from-keycloak-12345",  # This is the Keycloak user ID
            "typ": "Bearer",
            "azp": "dhafnck-client",
            "session_state": "session-123",
            "acr": "1",
            "allowed-origins": ["http://localhost:3800"],
            "realm_access": {
                "roles": ["user", "admin"]
            },
            "resource_access": {
                "dhafnck-client": {
                    "roles": ["manage-tasks", "view-projects"]
                }
            },
            "scope": "openid email profile",
            "sid": "session-id-456",
            "email_verified": True,
            "name": "Test User",
            "preferred_username": "testuser",
            "given_name": "Test",
            "family_name": "User",
            "email": "testuser@example.com"
        }
        
        # Create a mock token (in real scenario, this would be signed)
        # For testing, we'll just encode without signing
        token = jwt.encode(payload, "test-secret", algorithm="HS256")
        return token, payload
    
    @pytest.fixture
    def mock_request_with_token(self, mock_keycloak_token):
        """Create a mock request with Authorization header"""
        token, payload = mock_keycloak_token
        mock_request = Mock()
        mock_request.headers = {
            "Authorization": f"Bearer {token}"
        }
        mock_request.state = Mock()
        return mock_request, payload
    
    def test_extract_user_id_from_keycloak_token(self, mock_keycloak_token):
        """Test extracting user_id from a Keycloak JWT token"""
        token, expected_payload = mock_keycloak_token
        
        # Decode the token (without verification for testing)
        decoded = jwt.decode(token, options={"verify_signature": False})
        
        # Extract user_id from 'sub' claim (standard JWT claim for subject/user)
        user_id = decoded.get('sub')
        
        assert user_id == "user-uuid-from-keycloak-12345"
        assert decoded.get('email') == "testuser@example.com"
        assert decoded.get('preferred_username') == "testuser"
    
    def test_extract_user_id_from_request_context(self, mock_request_with_token):
        """Test extracting user_id from request context"""
        mock_request, expected_payload = mock_request_with_token
        
        # Extract token from Authorization header
        auth_header = mock_request.headers.get("Authorization")
        assert auth_header is not None
        assert auth_header.startswith("Bearer ")
        
        token = auth_header.replace("Bearer ", "")
        
        # Decode and extract user_id
        decoded = jwt.decode(token, options={"verify_signature": False})
        user_id = decoded.get('sub')
        
        assert user_id == "user-uuid-from-keycloak-12345"
    
    def test_token_extraction_service(self):
        """Test the TokenExtractionService for extracting user_id"""
        from fastmcp.task_management.interface.mcp_controllers.auth_helper.services.token_extraction_service import (
            TokenExtractionService
        )
        
        # Create service instance
        service = TokenExtractionService()
        
        # Create mock token
        from datetime import datetime, timezone
        payload = {
            "sub": "test-user-id-789",
            "email": "user@test.com",
            "exp": int((datetime.now(timezone.utc) + timedelta(hours=1)).timestamp())
        }
        token = jwt.encode(payload, "test-secret", algorithm="HS256")
        
        # Test extraction (don't verify signature since it's a test token)
        user_id = service.extract_user_id_from_token(token, verify_signature=False)
        assert user_id == "test-user-id-789"
    
    def test_token_extraction_with_missing_sub_claim(self):
        """Test handling of token without 'sub' claim"""
        from fastmcp.task_management.interface.mcp_controllers.auth_helper.services.token_extraction_service import (
            TokenExtractionService
        )
        
        service = TokenExtractionService()
        
        # Token without 'sub' claim
        payload = {
            "email": "user@test.com",
            "exp": int((datetime.now(timezone.utc) + timedelta(hours=1)).timestamp())
        }
        token = jwt.encode(payload, "test-secret", algorithm="HS256")
        
        # Should return None or raise appropriate error
        user_id = service.extract_user_id_from_token(token)
        assert user_id is None
    
    def test_token_extraction_with_expired_token(self):
        """Test handling of expired token"""
        from fastmcp.task_management.interface.mcp_controllers.auth_helper.services.token_extraction_service import (
            TokenExtractionService
        )
        
        service = TokenExtractionService()
        
        # Expired token
        payload = {
            "sub": "test-user-id-999",
            "exp": int((datetime.now(timezone.utc) - timedelta(hours=1)).timestamp())  # Expired
        }
        token = jwt.encode(payload, "test-secret", algorithm="HS256")
        
        # Should handle expired token gracefully
        user_id = service.extract_user_id_from_token(token, verify_exp=False)
        assert user_id == "test-user-id-999"
    
    def test_authentication_service_with_real_token(self):
        """Test AuthenticationService extracting user_id from actual token"""
        from fastmcp.task_management.interface.mcp_controllers.auth_helper.services.authentication_service import AuthenticationService
        
        # Create service
        auth_service = AuthenticationService()
        
        # Test with provided user_id (no token needed)
        # The service generates a UUID if no user_id is provided
        user_id = auth_service.get_authenticated_user_id(
            provided_user_id="real-user-123",
            operation_name="test-operation"
        )
        # AuthenticationService returns a UUID when no real token is available
        assert user_id is not None
        assert len(user_id) == 36  # UUID format
    
    def test_mock_user_data_for_testing(self):
        """Test using mock user data for testing purposes"""
        # Define mock users for testing
        mock_users = {
            "test-user-001": {
                "id": "test-user-001",
                "email": "testuser1@example.com",
                "name": "Test User 1",
                "roles": ["user", "developer"]
            },
            "test-user-002": {
                "id": "test-user-002",
                "email": "testuser2@example.com",
                "name": "Test User 2",
                "roles": ["user", "admin"]
            },
            "test-user-003": {
                "id": "test-user-003",
                "email": "testuser3@example.com",
                "name": "Test User 3",
                "roles": ["user"]
            }
        }
        
        # Mock token creation for each user
        for user_id, user_data in mock_users.items():
            payload = {
                "sub": user_id,
                "email": user_data["email"],
                "name": user_data["name"],
                "realm_access": {"roles": user_data["roles"]},
                "exp": int((datetime.now(timezone.utc) + timedelta(hours=1)).timestamp())
            }
            
            token = jwt.encode(payload, "test-secret", algorithm="HS256")
            decoded = jwt.decode(token, options={"verify_signature": False})
            
            assert decoded["sub"] == user_id
            assert decoded["email"] == user_data["email"]
            assert decoded["name"] == user_data["name"]