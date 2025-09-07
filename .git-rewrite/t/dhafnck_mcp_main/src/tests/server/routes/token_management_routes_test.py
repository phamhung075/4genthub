"""
Tests for Token Management API Routes.
"""

import pytest
from unittest.mock import Mock, patch, AsyncMock
from datetime import datetime, timedelta
from fastapi import HTTPException, status
from fastapi.testclient import TestClient
import jwt
import os

from fastmcp.server.routes.token_management_routes import (
    router,
    generate_jwt_token,
    hash_token,
    stored_tokens,
    user_tokens,
    GenerateTokenRequest,
    UpdateTokenScopesRequest,
    TokenResponse
)
from fastmcp.auth.domain.entities.user import User


class TestTokenGeneration:
    """Test JWT token generation functions."""
    
    def test_generate_jwt_token_success(self):
        """Test successful JWT token generation."""
        with patch.dict(os.environ, {"JWT_SECRET_KEY": "test_secret"}):
            # Reload module to pick up env var
            import fastmcp.server.routes.token_management_routes
            fastmcp.server.routes.token_management_routes.JWT_SECRET_KEY = "test_secret"
            
            token = generate_jwt_token(
                user_id="user123",
                scopes=["read", "write"],
                expires_in_days=30,
                token_id="tok_test123"
            )
            
            # Decode token to verify contents
            payload = jwt.decode(token, "test_secret", algorithms=["HS256"])
            assert payload["user_id"] == "user123"
            assert payload["scopes"] == ["read", "write"]
            assert payload["token_id"] == "tok_test123"
            assert payload["type"] == "api_token"
            assert "exp" in payload
            assert "iat" in payload
    
    def test_generate_jwt_token_no_secret(self):
        """Test token generation fails without JWT secret."""
        with patch.dict(os.environ, {}, clear=True):
            import fastmcp.server.routes.token_management_routes
            fastmcp.server.routes.token_management_routes.JWT_SECRET_KEY = None
            
            with pytest.raises(ValueError) as exc:
                generate_jwt_token("user123", ["read"], 30, "tok_123")
            
            assert "JWT_SECRET_KEY not configured" in str(exc.value)
    
    def test_hash_token(self):
        """Test token hashing function."""
        token = "test_token_123"
        hashed = hash_token(token)
        
        assert isinstance(hashed, str)
        assert len(hashed) == 64  # SHA256 produces 64-char hex string
        assert hashed != token  # Should not be the same as input
        assert hash_token(token) == hashed  # Should be deterministic


class TestGenerateTokenEndpoint:
    """Test the POST /api/v2/tokens endpoint."""
    
    @pytest.fixture
    def mock_current_user(self):
        """Create a mock authenticated user."""
        return User(
            id="user123",
            email="user@example.com",
            username="testuser",
            password_hash="hashed"
        )
    
    @pytest.fixture
    def client(self):
        """Create test client."""
        from fastapi import FastAPI
        app = FastAPI()
        app.include_router(router)
        return TestClient(app)
    
    @pytest.fixture(autouse=True)
    def clear_storage(self):
        """Clear token storage before each test."""
        stored_tokens.clear()
        user_tokens.clear()
        yield
        stored_tokens.clear()
        user_tokens.clear()
    
    def test_generate_token_success(self, client, mock_current_user):
        """Test successful token generation."""
        with patch.dict(os.environ, {"JWT_SECRET_KEY": "test_secret"}):
            import fastmcp.server.routes.token_management_routes
            fastmcp.server.routes.token_management_routes.JWT_SECRET_KEY = "test_secret"
            
            with patch('fastmcp.server.routes.token_management_routes.get_current_user', return_value=mock_current_user):
                response = client.post(
                    "/api/v2/tokens",
                    json={
                        "name": "Test Token",
                        "scopes": ["read:tasks", "write:tasks"],
                        "expires_in_days": 30,
                        "rate_limit": 1000
                    },
                    headers={"Authorization": "Bearer test_token"}
                )
                
                assert response.status_code == 200
                data = response.json()
                assert data["name"] == "Test Token"
                assert data["scopes"] == ["read:tasks", "write:tasks"]
                assert data["rate_limit"] == 1000
                assert data["user_id"] == "user123"
                assert "token" in data  # Token should be included in creation response
                assert data["token"] is not None
                assert data["id"].startswith("tok_")
    
    def test_generate_token_no_jwt_secret(self, client, mock_current_user):
        """Test token generation fails without JWT secret."""
        with patch.dict(os.environ, {}, clear=True):
            import fastmcp.server.routes.token_management_routes
            fastmcp.server.routes.token_management_routes.JWT_SECRET_KEY = None
            
            with patch('fastmcp.server.routes.token_management_routes.get_current_user', return_value=mock_current_user):
                response = client.post(
                    "/api/v2/tokens",
                    json={
                        "name": "Test Token",
                        "scopes": ["read"],
                        "expires_in_days": 30
                    },
                    headers={"Authorization": "Bearer test_token"}
                )
                
                assert response.status_code == 500
                assert "JWT_SECRET_KEY not configured" in response.json()["detail"]
    
    def test_generate_token_unauthenticated(self, client):
        """Test token generation requires authentication."""
        response = client.post(
            "/api/v2/tokens",
            json={
                "name": "Test Token",
                "scopes": ["read"],
                "expires_in_days": 30
            }
        )
        
        assert response.status_code == 403  # No auth header provided


class TestListTokensEndpoint:
    """Test the GET /api/v2/tokens endpoint."""
    
    @pytest.fixture
    def setup_tokens(self):
        """Set up test tokens in storage."""
        stored_tokens["tok_1"] = {
            "id": "tok_1",
            "name": "Token 1",
            "token_hash": "hash1",
            "scopes": ["read"],
            "created_at": datetime.utcnow().isoformat(),
            "expires_at": (datetime.utcnow() + timedelta(days=30)).isoformat(),
            "user_id": "user123",
            "is_active": True,
            "usage_count": 5
        }
        stored_tokens["tok_2"] = {
            "id": "tok_2",
            "name": "Token 2",
            "token_hash": "hash2",
            "scopes": ["read", "write"],
            "created_at": datetime.utcnow().isoformat(),
            "expires_at": (datetime.utcnow() + timedelta(days=60)).isoformat(),
            "user_id": "user123",
            "is_active": True,
            "usage_count": 10
        }
        stored_tokens["tok_3"] = {
            "id": "tok_3",
            "name": "Other User Token",
            "token_hash": "hash3",
            "scopes": ["admin"],
            "created_at": datetime.utcnow().isoformat(),
            "expires_at": (datetime.utcnow() + timedelta(days=90)).isoformat(),
            "user_id": "other_user",
            "is_active": True
        }
        
        user_tokens["user123"] = ["tok_1", "tok_2"]
        user_tokens["other_user"] = ["tok_3"]
    
    def test_list_tokens_success(self, client, mock_current_user, setup_tokens):
        """Test listing tokens for authenticated user."""
        with patch('fastmcp.server.routes.token_management_routes.get_current_user', return_value=mock_current_user):
            response = client.get(
                "/api/v2/tokens",
                headers={"Authorization": "Bearer test_token"}
            )
            
            assert response.status_code == 200
            data = response.json()
            assert data["total"] == 2
            assert len(data["data"]) == 2
            
            # Should only see user's own tokens
            token_ids = [t["id"] for t in data["data"]]
            assert "tok_1" in token_ids
            assert "tok_2" in token_ids
            assert "tok_3" not in token_ids
            
            # Should not include token_hash
            for token in data["data"]:
                assert "token_hash" not in token
    
    def test_list_tokens_marks_expired_as_inactive(self, client, mock_current_user):
        """Test that expired tokens are marked as inactive."""
        # Add expired token
        stored_tokens["tok_expired"] = {
            "id": "tok_expired",
            "name": "Expired Token",
            "token_hash": "hash_expired",
            "scopes": ["read"],
            "created_at": (datetime.utcnow() - timedelta(days=60)).isoformat(),
            "expires_at": (datetime.utcnow() - timedelta(days=30)).isoformat(),  # Expired
            "user_id": "user123",
            "is_active": True
        }
        user_tokens["user123"] = ["tok_expired"]
        
        with patch('fastmcp.server.routes.token_management_routes.get_current_user', return_value=mock_current_user):
            response = client.get(
                "/api/v2/tokens",
                headers={"Authorization": "Bearer test_token"}
            )
            
            assert response.status_code == 200
            data = response.json()
            assert data["total"] == 1
            assert data["data"][0]["id"] == "tok_expired"
            assert data["data"][0]["is_active"] == False  # Marked as inactive


class TestRevokeTokenEndpoint:
    """Test the DELETE /api/v2/tokens/{token_id} endpoint."""
    
    def test_revoke_token_success(self, client, mock_current_user, setup_tokens):
        """Test successful token revocation."""
        with patch('fastmcp.server.routes.token_management_routes.get_current_user', return_value=mock_current_user):
            response = client.delete(
                "/api/v2/tokens/tok_1",
                headers={"Authorization": "Bearer test_token"}
            )
            
            assert response.status_code == 200
            assert response.json()["message"] == "Token revoked successfully"
            assert "tok_1" not in stored_tokens
            assert "tok_1" not in user_tokens["user123"]
    
    def test_revoke_token_not_found(self, client, mock_current_user):
        """Test revoking non-existent token."""
        with patch('fastmcp.server.routes.token_management_routes.get_current_user', return_value=mock_current_user):
            response = client.delete(
                "/api/v2/tokens/tok_nonexistent",
                headers={"Authorization": "Bearer test_token"}
            )
            
            assert response.status_code == 404
            assert response.json()["detail"] == "Token not found"
    
    def test_revoke_token_unauthorized(self, client, mock_current_user, setup_tokens):
        """Test cannot revoke another user's token."""
        with patch('fastmcp.server.routes.token_management_routes.get_current_user', return_value=mock_current_user):
            response = client.delete(
                "/api/v2/tokens/tok_3",  # Belongs to other_user
                headers={"Authorization": "Bearer test_token"}
            )
            
            assert response.status_code == 403
            assert response.json()["detail"] == "Not authorized to revoke this token"


class TestGetTokenDetailsEndpoint:
    """Test the GET /api/v2/tokens/{token_id} endpoint."""
    
    def test_get_token_details_success(self, client, mock_current_user, setup_tokens):
        """Test getting token details."""
        with patch('fastmcp.server.routes.token_management_routes.get_current_user', return_value=mock_current_user):
            response = client.get(
                "/api/v2/tokens/tok_1",
                headers={"Authorization": "Bearer test_token"}
            )
            
            assert response.status_code == 200
            data = response.json()
            assert data["id"] == "tok_1"
            assert data["name"] == "Token 1"
            assert data["scopes"] == ["read"]
            assert data["token"] is None  # Should not include actual token
            assert "token_hash" not in data


class TestUpdateTokenScopesEndpoint:
    """Test the PATCH /api/v2/tokens/{token_id}/scopes endpoint."""
    
    def test_update_token_scopes_success(self, client, mock_current_user, setup_tokens):
        """Test updating token scopes."""
        with patch('fastmcp.server.routes.token_management_routes.get_current_user', return_value=mock_current_user):
            response = client.patch(
                "/api/v2/tokens/tok_1/scopes",
                json={"scopes": ["read", "write", "admin"]},
                headers={"Authorization": "Bearer test_token"}
            )
            
            assert response.status_code == 200
            data = response.json()
            assert data["id"] == "tok_1"
            assert data["scopes"] == ["read", "write", "admin"]
            
            # Verify in storage
            assert stored_tokens["tok_1"]["scopes"] == ["read", "write", "admin"]


class TestRotateTokenEndpoint:
    """Test the POST /api/v2/tokens/{token_id}/rotate endpoint."""
    
    def test_rotate_token_success(self, client, mock_current_user, setup_tokens):
        """Test successful token rotation."""
        with patch.dict(os.environ, {"JWT_SECRET_KEY": "test_secret"}):
            import fastmcp.server.routes.token_management_routes
            fastmcp.server.routes.token_management_routes.JWT_SECRET_KEY = "test_secret"
            
            with patch('fastmcp.server.routes.token_management_routes.get_current_user', return_value=mock_current_user):
                response = client.post(
                    "/api/v2/tokens/tok_1/rotate",
                    headers={"Authorization": "Bearer test_token"}
                )
                
                assert response.status_code == 200
                data = response.json()
                assert data["id"] != "tok_1"  # New ID
                assert data["id"].startswith("tok_")
                assert data["name"] == "Token 1 (rotated)"
                assert data["scopes"] == ["read"]  # Same scopes
                assert data["token"] is not None  # New token included
                assert "tok_1" not in stored_tokens  # Old token removed
                assert data["id"] in stored_tokens  # New token stored


class TestValidateTokenEndpoint:
    """Test the POST /api/v2/tokens/validate endpoint."""
    
    def test_validate_token_success(self, client):
        """Test successful token validation."""
        with patch.dict(os.environ, {"JWT_SECRET_KEY": "test_secret"}):
            import fastmcp.server.routes.token_management_routes
            fastmcp.server.routes.token_management_routes.JWT_SECRET_KEY = "test_secret"
            
            # Create a valid token
            token = jwt.encode({
                "token_id": "tok_valid",
                "user_id": "user123",
                "scopes": ["read", "write"],
                "exp": (datetime.utcnow() + timedelta(hours=1)).timestamp()
            }, "test_secret", algorithm="HS256")
            
            # Store token data
            stored_tokens["tok_valid"] = {
                "id": "tok_valid",
                "usage_count": 0,
                "last_used_at": None
            }
            
            response = client.post(
                "/api/v2/tokens/validate",
                headers={"Authorization": f"Bearer {token}"}
            )
            
            assert response.status_code == 200
            data = response.json()
            assert data["valid"] == True
            assert data["user_id"] == "user123"
            assert data["scopes"] == ["read", "write"]
            assert data["token_id"] == "tok_valid"
            
            # Verify usage stats updated
            assert stored_tokens["tok_valid"]["usage_count"] == 1
            assert stored_tokens["tok_valid"]["last_used_at"] is not None
    
    def test_validate_token_expired(self, client):
        """Test validation of expired token."""
        with patch.dict(os.environ, {"JWT_SECRET_KEY": "test_secret"}):
            import fastmcp.server.routes.token_management_routes
            fastmcp.server.routes.token_management_routes.JWT_SECRET_KEY = "test_secret"
            
            # Create expired token
            token = jwt.encode({
                "token_id": "tok_expired",
                "user_id": "user123",
                "exp": (datetime.utcnow() - timedelta(hours=1)).timestamp()  # Expired
            }, "test_secret", algorithm="HS256")
            
            response = client.post(
                "/api/v2/tokens/validate",
                headers={"Authorization": f"Bearer {token}"}
            )
            
            assert response.status_code == 200
            data = response.json()
            assert data["valid"] == False
            assert data["error"] == "Token expired"
    
    def test_validate_token_invalid(self, client):
        """Test validation of invalid token."""
        response = client.post(
            "/api/v2/tokens/validate",
            headers={"Authorization": "Bearer invalid_token_123"}
        )
        
        assert response.status_code == 200
        data = response.json()
        assert data["valid"] == False
        assert "error" in data
    
    def test_validate_token_no_auth_header(self, client):
        """Test validation without auth header."""
        response = client.post("/api/v2/tokens/validate")
        
        assert response.status_code == 401
        assert response.json()["detail"] == "Invalid authorization header"


class TestGetTokenUsageStatsEndpoint:
    """Test the GET /api/v2/tokens/{token_id}/usage endpoint."""
    
    def test_get_usage_stats_success(self, client, mock_current_user, setup_tokens):
        """Test getting token usage statistics."""
        # Update token with usage data
        stored_tokens["tok_1"]["usage_count"] = 42
        stored_tokens["tok_1"]["last_used_at"] = datetime.utcnow().isoformat()
        
        with patch('fastmcp.server.routes.token_management_routes.get_current_user', return_value=mock_current_user):
            response = client.get(
                "/api/v2/tokens/tok_1/usage",
                headers={"Authorization": "Bearer test_token"}
            )
            
            assert response.status_code == 200
            data = response.json()
            assert data["token_id"] == "tok_1"
            assert data["usage_count"] == 42
            assert data["last_used_at"] is not None
            assert "days_active" in data
            assert "days_remaining" in data
            assert data["is_expired"] == False