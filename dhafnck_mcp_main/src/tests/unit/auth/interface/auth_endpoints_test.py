"""
Unit Tests for Auth Endpoints Interface

This module tests the Keycloak/Supabase authentication endpoints.
"""

import pytest
from unittest.mock import Mock, AsyncMock, patch
try:
    from fastapi.testclient import TestClient
except ImportError:
    TestClient = None  # Will be handled by fixture skip
import os

from fastmcp.auth.interface.auth_endpoints import (
    router,
    LoginRequest,
    LoginResponse
)


class TestLoginEndpoint:
    """Test suite for login endpoint with Keycloak integration"""
    
    @pytest.fixture
    def client(self):
        """Test client for FastAPI router"""
        try:
            from fastapi import FastAPI
            app = FastAPI()
            app.include_router(router)
            return TestClient(app)
        except ImportError:
            pytest.skip("FastAPI not available")
    
    @patch('fastmcp.auth.interface.auth_endpoints.httpx.AsyncClient')
    @patch.dict(os.environ, {
        "AUTH_PROVIDER": "keycloak",
        "KEYCLOAK_URL": "http://localhost:8080",
        "KEYCLOAK_REALM": "dhafnck",
        "KEYCLOAK_CLIENT_ID": "dhafnck-client",
        "KEYCLOAK_CLIENT_SECRET": "secret"
    })
    def test_login_keycloak_success(self, mock_client_class, client):
        """Test successful login with Keycloak"""
        # Mock Keycloak response
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "access_token": "test-access-token",
            "refresh_token": "test-refresh-token",
            "expires_in": 300,
            "token_type": "Bearer"
        }
        
        mock_client = AsyncMock()
        mock_client.post.return_value = mock_response
        mock_client_class.return_value.__aenter__.return_value = mock_client
        
        response = client.post("/api/auth/login", json={
            "email": "test@example.com",
            "password": "password123"
        })
        
        assert response.status_code == 200
        data = response.json()
        assert data["access_token"] == "test-access-token"
        assert data["token_type"] == "bearer"
    
    @patch('fastmcp.auth.interface.auth_endpoints.httpx.AsyncClient')
    @patch.dict(os.environ, {"AUTH_PROVIDER": "keycloak"})
    def test_login_keycloak_invalid_credentials(self, mock_client_class, client):
        """Test login with invalid credentials"""
        mock_response = Mock()
        mock_response.status_code = 401
        mock_response.json.return_value = {"error": "invalid_grant"}
        
        mock_client = AsyncMock()
        mock_client.post.return_value = mock_response
        mock_client_class.return_value.__aenter__.return_value = mock_client
        
        response = client.post("/api/auth/login", json={
            "email": "test@example.com",
            "password": "wrong_password"
        })
        
        assert response.status_code == 401
        assert "Invalid credentials" in response.json()["detail"]
    
    @patch('fastmcp.auth.interface.auth_endpoints.httpx.AsyncClient')
    @patch.dict(os.environ, {"AUTH_PROVIDER": "keycloak"})
    def test_login_keycloak_server_error(self, mock_client_class, client):
        """Test login when Keycloak returns server error"""
        mock_response = Mock()
        mock_response.status_code = 500
        mock_response.json.return_value = {"error": "internal_error"}
        
        mock_client = AsyncMock()
        mock_client.post.return_value = mock_response
        mock_client_class.return_value.__aenter__.return_value = mock_client
        
        response = client.post("/api/auth/login", json={
            "email": "test@example.com",
            "password": "password123"
        })
        
        assert response.status_code == 500
        assert "Authentication service error" in response.json()["detail"]
    
    @patch('fastmcp.auth.interface.auth_endpoints.httpx.AsyncClient')
    @patch.dict(os.environ, {"AUTH_PROVIDER": "supabase"})
    def test_login_unsupported_provider(self, mock_client_class, client):
        """Test login with unsupported auth provider"""
        response = client.post("/api/auth/login", json={
            "email": "test@example.com",
            "password": "password123"
        })
        
        # Currently returns 500, but should handle gracefully
        assert response.status_code == 500
        assert "Auth provider supabase not yet implemented" in response.json()["detail"]


class TestRefreshTokenEndpoint:
    """Test suite for token refresh endpoint"""
    
    @pytest.fixture
    def client(self):
        """Test client for FastAPI router"""
        try:
            from fastapi import FastAPI
            app = FastAPI()
            app.include_router(router)
            return TestClient(app)
        except ImportError:
            pytest.skip("FastAPI not available")
    
    @patch('fastmcp.auth.interface.auth_endpoints.httpx.AsyncClient')
    @patch.dict(os.environ, {
        "AUTH_PROVIDER": "keycloak",
        "KEYCLOAK_URL": "http://localhost:8080",
        "KEYCLOAK_REALM": "dhafnck",
        "KEYCLOAK_CLIENT_ID": "dhafnck-client",
        "KEYCLOAK_CLIENT_SECRET": "secret"
    })
    def test_refresh_token_success(self, mock_client_class, client):
        """Test successful token refresh"""
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "access_token": "new-access-token",
            "refresh_token": "new-refresh-token",
            "expires_in": 300,
            "token_type": "Bearer"
        }
        
        mock_client = AsyncMock()
        mock_client.post.return_value = mock_response
        mock_client_class.return_value.__aenter__.return_value = mock_client
        
        response = client.post("/api/auth/refresh", json={
            "refresh_token": "old-refresh-token"
        })
        
        assert response.status_code == 200
        data = response.json()
        assert data["access_token"] == "new-access-token"
        assert data["refresh_token"] == "new-refresh-token"
    
    @patch('fastmcp.auth.interface.auth_endpoints.httpx.AsyncClient')
    @patch.dict(os.environ, {"AUTH_PROVIDER": "keycloak"})
    def test_refresh_token_expired(self, mock_client_class, client):
        """Test refresh with expired token"""
        mock_response = Mock()
        mock_response.status_code = 400
        mock_response.json.return_value = {"error": "invalid_grant"}
        
        mock_client = AsyncMock()
        mock_client.post.return_value = mock_response
        mock_client_class.return_value.__aenter__.return_value = mock_client
        
        response = client.post("/api/auth/refresh", json={
            "refresh_token": "expired-token"
        })
        
        assert response.status_code == 401
        assert "Invalid or expired refresh token" in response.json()["detail"]


class TestLogoutEndpoint:
    """Test suite for logout endpoint"""
    
    @pytest.fixture
    def client(self):
        """Test client for FastAPI router"""
        try:
            from fastapi import FastAPI
            app = FastAPI()
            app.include_router(router)
            return TestClient(app)
        except ImportError:
            pytest.skip("FastAPI not available")
    
    @patch('fastmcp.auth.interface.auth_endpoints.httpx.AsyncClient')
    @patch.dict(os.environ, {
        "AUTH_PROVIDER": "keycloak",
        "KEYCLOAK_URL": "http://localhost:8080",
        "KEYCLOAK_REALM": "dhafnck",
        "KEYCLOAK_CLIENT_ID": "dhafnck-client",
        "KEYCLOAK_CLIENT_SECRET": "secret"
    })
    def test_logout_success(self, mock_client_class, client):
        """Test successful logout"""
        mock_response = Mock()
        mock_response.status_code = 204
        
        mock_client = AsyncMock()
        mock_client.post.return_value = mock_response
        mock_client_class.return_value.__aenter__.return_value = mock_client
        
        response = client.post("/api/auth/logout", json={
            "refresh_token": "valid-refresh-token"
        })
        
        assert response.status_code == 200
        data = response.json()
        assert data["message"] == "Logged out successfully"
    
    def test_logout_without_token(self, client):
        """Test logout without refresh token"""
        response = client.post("/api/auth/logout", json={})
        
        # Should still return success even without token
        assert response.status_code == 200
        data = response.json()
        assert data["message"] == "Logged out successfully"


class TestAuthProviderEndpoint:
    """Test suite for auth provider info endpoint"""
    
    @pytest.fixture
    def client(self):
        """Test client for FastAPI router"""
        try:
            from fastapi import FastAPI
            app = FastAPI()
            app.include_router(router)
            return TestClient(app)
        except ImportError:
            pytest.skip("FastAPI not available")
    
    @patch.dict(os.environ, {"AUTH_PROVIDER": "keycloak"})
    def test_get_auth_provider_keycloak(self, client):
        """Test getting auth provider info for Keycloak"""
        response = client.get("/api/auth/provider")
        
        assert response.status_code == 200
        data = response.json()
        assert data["provider"] == "keycloak"
        assert data["configured"] is True
    
    @patch.dict(os.environ, {"AUTH_PROVIDER": "supabase"})
    def test_get_auth_provider_supabase(self, client):
        """Test getting auth provider info for Supabase"""
        response = client.get("/api/auth/provider")
        
        assert response.status_code == 200
        data = response.json()
        assert data["provider"] == "supabase"
        # Supabase is not yet configured
        assert data["configured"] is False


class TestVerifyAuthEndpoint:
    """Test suite for auth verification endpoint"""
    
    @pytest.fixture
    def client(self):
        """Test client for FastAPI router"""
        try:
            from fastapi import FastAPI
            app = FastAPI()
            app.include_router(router)
            return TestClient(app)
        except ImportError:
            pytest.skip("FastAPI not available")
    
    def test_verify_auth(self, client):
        """Test auth verification endpoint"""
        response = client.get("/api/auth/verify")
        
        assert response.status_code == 200
        data = response.json()
        assert data["authenticated"] is True
        assert data["message"] == "Authentication verified"


class TestDataModels:
    """Test suite for request/response models"""
    
    def test_login_request_model(self):
        """Test LoginRequest model validation"""
        # Valid request
        request = LoginRequest(email="test@example.com", password="password123")
        assert pytest_request.email == "test@example.com"
        assert pytest_request.password == "password123"
        
        # LoginRequest accepts any string for email (no validation)
        request2 = LoginRequest(email="invalid-email", password="password123")
        assert request2.email == "invalid-email"
        assert request2.password == "password123"
    
    def test_login_response_model(self):
        """Test LoginResponse model"""
        response = LoginResponse(
            access_token="token123",
            refresh_token="refresh123",
            expires_in=300
        )
        assert response.access_token == "token123"
        assert response.token_type == "bearer"
        assert response.refresh_token == "refresh123"
        assert response.expires_in == 300