"""
Comprehensive Unit Tests for Auth Endpoints Interface

This module provides comprehensive test coverage for the Keycloak/Supabase 
authentication endpoints, including all public functions, edge cases, and 
error conditions.
"""

import pytest
from unittest.mock import Mock, AsyncMock, patch, MagicMock
import httpx
import os
import json
from datetime import datetime, timedelta
from typing import Dict, Any, Optional

# Handle optional imports
try:
    from fastapi import FastAPI, HTTPException
    from fastapi.testclient import TestClient
    from sqlalchemy.orm import Session
except ImportError:
    FastAPI = None
    TestClient = None
    HTTPException = Exception
    Session = None

from fastmcp.auth.interface.auth_endpoints import (
    router,
    LoginRequest,
    LoginResponse,
    RegisterRequest,
    RegisterResponse,
    get_keycloak_admin_token,
    cleanup_incomplete_account_internal,
    setup_user_roles,
    AUTH_PROVIDER,
    EMAIL_VERIFIED_AUTO,
    KEYCLOAK_URL,
    KEYCLOAK_REALM,
    KEYCLOAK_CLIENT_ID,
    KEYCLOAK_CLIENT_SECRET,
)


class TestDataModels:
    """Test suite for Pydantic data models"""
    
    def test_login_request_model(self):
        """Test LoginRequest model validation"""
        # Arrange & Act
        request = LoginRequest(email="test@example.com", password="password123")
        
        # Assert
        assert pytest_request.email == "test@example.com"
        assert pytest_request.password == "password123"
    
    def test_register_request_model_valid(self):
        """Test RegisterRequest model with valid data"""
        # Arrange & Act
        request = RegisterRequest(
            email="test@example.com",
            password="Password123!",
            username="testuser"
        )
        
        # Assert
        assert pytest_request.email == "test@example.com"
        assert pytest_request.password == "Password123!"
        assert pytest_request.username == "testuser"
    
    def test_register_request_password_validation(self):
        """Test password validation in RegisterRequest"""
        # Test various invalid passwords
        invalid_passwords = [
            ("short", "at least 8 characters"),
            ("alllowercase123!", "at least 1 uppercase letter"),
            ("ALLUPPERCASE123!", "at least 1 lowercase letter"),
            ("NoNumbers!", "at least 1 number"),
            ("NoSpecialChar123", "at least 1 special character"),
        ]
        
        for password, expected_error in invalid_passwords:
            with pytest.raises(ValueError) as exc_info:
                RegisterRequest(email="test@example.com", password=password)
            assert expected_error in str(exc_info.value)
    
    def test_register_request_email_validation(self):
        """Test email validation in RegisterRequest"""
        # Test invalid email formats
        invalid_emails = [
            "notanemail",
            "missing@domain",
            "@missinglocal.com",
            "spaces in@email.com",
            "double@@at.com"
        ]
        
        for email in invalid_emails:
            with pytest.raises(ValueError) as exc_info:
                RegisterRequest(email=email, password="Password123!")
            assert "valid email address" in str(exc_info.value)
    
    def test_register_request_username_validation(self):
        """Test username validation in RegisterRequest"""
        # Test too short username
        with pytest.raises(ValueError) as exc_info:
            RegisterRequest(email="test@example.com", password="Password123!", username="ab")
        assert "at least 3 characters" in str(exc_info.value)
        
        # Test too long username
        with pytest.raises(ValueError) as exc_info:
            RegisterRequest(email="test@example.com", password="Password123!", username="a" * 21)
        assert "not exceed 20 characters" in str(exc_info.value)
        
        # Test invalid characters
        with pytest.raises(ValueError) as exc_info:
            RegisterRequest(email="test@example.com", password="Password123!", username="user@name")
        assert "letters, numbers, underscore" in str(exc_info.value)
    
    def test_register_response_model(self):
        """Test RegisterResponse model"""
        # Arrange & Act
        response = RegisterResponse(
            success=True,
            user_id="12345",
            email="test@example.com",
            username="testuser",
            message="Success",
            message_type="success",
            display_color="green",
            next_steps=["Step 1", "Step 2"]
        )
        
        # Assert
        assert response.success is True
        assert response.user_id == "12345"
        assert response.email == "test@example.com"
        assert response.username == "testuser"
        assert response.message == "Success"
        assert response.message_type == "success"
        assert response.display_color == "green"
        assert len(response.next_steps) == 2
    
    def test_login_response_model(self):
        """Test LoginResponse model"""
        # Arrange & Act
        response = LoginResponse(
            access_token="token123",
            refresh_token="refresh123",
            expires_in=3600,
            user_id="user123",
            email="test@example.com"
        )
        
        # Assert
        assert response.access_token == "token123"
        assert response.token_type == "bearer"
        assert response.refresh_token == "refresh123"
        assert response.expires_in == 3600
        assert response.user_id == "user123"
        assert response.email == "test@example.com"


class TestHelperFunctions:
    """Test suite for helper functions"""
    
    @pytest.mark.asyncio
    @patch('fastmcp.auth.interface.auth_endpoints.httpx.AsyncClient')
    async def test_get_keycloak_admin_token_client_credentials_success(self, mock_client_class):
        """Test getting admin token with client credentials"""
        # Arrange
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {"access_token": "admin-token-123"}
        
        mock_client = AsyncMock()
        mock_client.post.return_value = mock_response
        mock_client_class.return_value.__aenter__.return_value = mock_client
        
        # Act
        with patch.dict(os.environ, {
            "KEYCLOAK_URL": "http://localhost:8080",
            "KEYCLOAK_REALM": "test-realm",
            "KEYCLOAK_CLIENT_ID": "test-client",
            "KEYCLOAK_CLIENT_SECRET": "test-secret"
        }):
            token = await get_keycloak_admin_token()
        
        # Assert
        assert token == "admin-token-123"
        mock_client.post.assert_called_once()
    
    @pytest.mark.asyncio
    @patch('fastmcp.auth.interface.auth_endpoints.httpx.AsyncClient')
    async def test_get_keycloak_admin_token_fallback_to_admin(self, mock_client_class):
        """Test fallback to admin credentials when client credentials fail"""
        # Arrange
        # First response fails
        mock_response1 = Mock()
        mock_response1.status_code = 401
        
        # Second response succeeds (admin login)
        mock_response2 = Mock()
        mock_response2.status_code = 200
        mock_response2.json.return_value = {"access_token": "admin-token-456"}
        
        mock_client = AsyncMock()
        mock_client.post.side_effect = [mock_response1, mock_response2]
        mock_client_class.return_value.__aenter__.return_value = mock_client
        
        # Act
        with patch.dict(os.environ, {
            "KEYCLOAK_URL": "http://localhost:8080",
            "KEYCLOAK_REALM": "test-realm",
            "KEYCLOAK_CLIENT_ID": "test-client",
            "KEYCLOAK_CLIENT_SECRET": "test-secret",
            "KEYCLOAK_ADMIN_PASSWORD": "admin-password"
        }):
            token = await get_keycloak_admin_token()
        
        # Assert
        assert token == "admin-token-456"
        assert mock_client.post.call_count == 2
    
    @pytest.mark.asyncio
    @patch('fastmcp.auth.interface.auth_endpoints.httpx.AsyncClient')
    async def test_get_keycloak_admin_token_failure(self, mock_client_class):
        """Test admin token retrieval failure"""
        # Arrange
        mock_client = AsyncMock()
        mock_client.post.side_effect = httpx.RequestError("Connection failed")
        mock_client_class.return_value.__aenter__.return_value = mock_client
        
        # Act
        token = await get_keycloak_admin_token()
        
        # Assert
        assert token is None
    
    @pytest.mark.asyncio
    @patch('fastmcp.auth.interface.auth_endpoints.httpx.AsyncClient')
    @patch('fastmcp.auth.interface.auth_endpoints.get_keycloak_admin_token')
    async def test_cleanup_incomplete_account_success(self, mock_get_admin_token, mock_client_class):
        """Test successful cleanup of incomplete account"""
        # Arrange
        mock_get_admin_token.return_value = "admin-token"
        
        # Mock user search response
        mock_search_response = Mock()
        mock_search_response.status_code = 200
        mock_search_response.json.return_value = [{
            "id": "user-123",
            "emailVerified": False,
            "enabled": True,
            "requiredActions": ["VERIFY_EMAIL"],
            "credentials": []
        }]
        
        # Mock delete response
        mock_delete_response = Mock()
        mock_delete_response.status_code = 204
        
        mock_client = AsyncMock()
        mock_client.get.return_value = mock_search_response
        mock_client.delete.return_value = mock_delete_response
        mock_client_class.return_value.__aenter__.return_value = mock_client
        
        # Act
        with patch.dict(os.environ, {"AUTH_PROVIDER": "keycloak"}):
            result = await cleanup_incomplete_account_internal("test@example.com")
        
        # Assert
        assert result["success"] is True
        assert result["can_register"] is True
        assert "Incomplete account removed" in result["message"]
    
    @pytest.mark.asyncio
    @patch('fastmcp.auth.interface.auth_endpoints.httpx.AsyncClient')
    @patch('fastmcp.auth.interface.auth_endpoints.get_keycloak_admin_token')
    async def test_cleanup_incomplete_account_protected(self, mock_get_admin_token, mock_client_class):
        """Test protection of verified accounts from cleanup"""
        # Arrange
        mock_get_admin_token.return_value = "admin-token"
        
        # Mock user search response - verified account
        mock_search_response = Mock()
        mock_search_response.status_code = 200
        mock_search_response.json.return_value = [{
            "id": "user-123",
            "emailVerified": True,  # Verified account
            "enabled": True,
            "requiredActions": [],
            "credentials": [{"type": "password"}]
        }]
        
        mock_client = AsyncMock()
        mock_client.get.return_value = mock_search_response
        mock_client_class.return_value.__aenter__.return_value = mock_client
        
        # Act
        with patch.dict(os.environ, {"AUTH_PROVIDER": "keycloak"}):
            result = await cleanup_incomplete_account_internal("test@example.com")
        
        # Assert
        assert result["success"] is False
        assert result["can_register"] is False
        assert "verified and properly set up" in result["message"]
        # Ensure delete was never called
        mock_client.delete.assert_not_called()
    
    @pytest.mark.asyncio
    @patch('fastmcp.auth.interface.auth_endpoints.httpx.AsyncClient')
    async def test_setup_user_roles_success(self, mock_client_class):
        """Test successful user role setup"""
        # Arrange
        # Mock user get response
        mock_user_response = Mock()
        mock_user_response.status_code = 200
        mock_user_response.json.return_value = {
            "username": "testuser",
            "email": "test@example.com",
            "attributes": {}
        }
        
        # Mock user update response
        mock_update_response = Mock()
        mock_update_response.status_code = 204
        
        # Mock realm roles response
        mock_roles_response = Mock()
        mock_roles_response.status_code = 200
        mock_roles_response.json.return_value = [
            {"id": "role-1", "name": "user"},
            {"id": "role-2", "name": "offline_access"},
            {"id": "role-3", "name": "uma_authorization"}
        ]
        
        # Mock role assignment response
        mock_assign_response = Mock()
        mock_assign_response.status_code = 204
        
        # Mock client search response
        mock_clients_response = Mock()
        mock_clients_response.status_code = 200
        mock_clients_response.json.return_value = [{"id": "client-123"}]
        
        # Mock client roles response
        mock_client_roles_response = Mock()
        mock_client_roles_response.status_code = 200
        mock_client_roles_response.json.return_value = [
            {"id": "client-role-1", "name": "client-user"}
        ]
        
        mock_client = AsyncMock()
        mock_client.get.side_effect = [
            mock_user_response, 
            mock_clients_response, 
            mock_client_roles_response, 
            mock_roles_response
        ]
        mock_client.put.return_value = mock_update_response
        mock_client.post.side_effect = [mock_assign_response, mock_assign_response]
        
        mock_client_class.return_value = mock_client
        
        # Act
        with patch.dict(os.environ, {
            "KEYCLOAK_URL": "http://localhost:8080",
            "KEYCLOAK_REALM": "test-realm",
            "EMAIL_VERIFIED_AUTO": "true"
        }):
            await setup_user_roles(mock_client, "admin-token", "user-123", "test@example.com")
        
        # Assert
        # Verify user was updated
        assert mock_client.put.call_count == 1
        put_data = mock_client.put.call_args[1]["json"]
        assert put_data["emailVerified"] is True
        assert put_data["requiredActions"] == []
        
        # Verify roles were assigned
        assert mock_client.post.call_count >= 1


class TestLoginEndpoint:
    """Test suite for login endpoint"""
    
    @pytest.fixture
    def client(self):
        """Test client for FastAPI router"""
        if FastAPI is None:
            pytest.skip("FastAPI not available")
        app = FastAPI()
        app.include_router(router)
        return TestClient(app)
    
    @patch('fastmcp.auth.interface.auth_endpoints.httpx.AsyncClient')
    @patch.dict(os.environ, {
        "AUTH_PROVIDER": "keycloak",
        "KEYCLOAK_URL": "http://localhost:8080",
        "KEYCLOAK_REALM": "test-realm",
        "KEYCLOAK_CLIENT_ID": "test-client",
        "KEYCLOAK_CLIENT_SECRET": "test-secret"
    })
    def test_login_success(self, mock_client_class, client):
        """Test successful login"""
        # Arrange
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "access_token": "test-token",
            "refresh_token": "refresh-token",
            "expires_in": 3600
        }
        
        mock_client = AsyncMock()
        mock_client.post.return_value = mock_response
        mock_client_class.return_value.__aenter__.return_value = mock_client
        
        # Mock JWT decode
        with patch('jwt.decode') as mock_decode:
            mock_decode.return_value = {
                "sub": "user-123",
                "email": "test@example.com"
            }
            
            # Act
            response = client.post("/api/auth/login", json={
                "email": "test@example.com",
                "password": "password123"
            })
        
        # Assert
        assert response.status_code == 200
        data = response.json()
        assert data["access_token"] == "test-token"
        assert data["token_type"] == "bearer"
        assert data["refresh_token"] == "refresh-token"
        assert data["expires_in"] == 3600
        assert data["user_id"] == "user-123"
        assert data["email"] == "test@example.com"
    
    @patch('fastmcp.auth.interface.auth_endpoints.httpx.AsyncClient')
    @patch.dict(os.environ, {"AUTH_PROVIDER": "keycloak"})
    def test_login_invalid_credentials(self, mock_client_class, client):
        """Test login with invalid credentials"""
        # Arrange
        mock_response = Mock()
        mock_response.status_code = 401
        mock_response.text = "Invalid credentials"
        
        mock_client = AsyncMock()
        mock_client.post.return_value = mock_response
        mock_client_class.return_value.__aenter__.return_value = mock_client
        
        # Act
        response = client.post("/api/auth/login", json={
            "email": "test@example.com",
            "password": "wrong-password"
        })
        
        # Assert
        assert response.status_code == 401
        assert "Invalid credentials" in response.json()["detail"]
    
    @patch('fastmcp.auth.interface.auth_endpoints.httpx.AsyncClient')
    @patch.dict(os.environ, {"AUTH_PROVIDER": "keycloak"})
    def test_login_account_not_fully_setup(self, mock_client_class, client):
        """Test login when account is not fully set up"""
        # Arrange
        mock_response = Mock()
        mock_response.status_code = 400
        mock_response.json.return_value = {
            "error": "invalid_grant",
            "error_description": "Account is not fully set up"
        }
        mock_response.text = json.dumps(mock_response.json.return_value)
        
        mock_client = AsyncMock()
        mock_client.post.return_value = mock_response
        mock_client_class.return_value.__aenter__.return_value = mock_client
        
        # Act
        response = client.post("/api/auth/login", json={
            "email": "test@example.com",
            "password": "password123"
        })
        
        # Assert
        assert response.status_code == 400
        assert "account is incomplete" in response.json()["detail"].lower()
    
    @patch('fastmcp.auth.interface.auth_endpoints.httpx.AsyncClient')
    @patch.dict(os.environ, {"AUTH_PROVIDER": "keycloak"})
    def test_login_invalid_scope_retry(self, mock_client_class, client):
        """Test login with invalid scope and successful retry"""
        # Arrange
        # First response fails with invalid scope
        mock_response1 = Mock()
        mock_response1.status_code = 400
        mock_response1.json.return_value = {
            "error": "invalid_scope",
            "error_description": "Invalid scope"
        }
        mock_response1.text = json.dumps(mock_response1.json.return_value)
        
        # Second response succeeds with minimal scope
        mock_response2 = Mock()
        mock_response2.status_code = 200
        mock_response2.json.return_value = {
            "access_token": "test-token",
            "refresh_token": "refresh-token",
            "expires_in": 3600
        }
        
        mock_client = AsyncMock()
        mock_client.post.side_effect = [mock_response1, mock_response2]
        mock_client_class.return_value.__aenter__.return_value = mock_client
        
        # Mock JWT decode
        with patch('jwt.decode') as mock_decode:
            mock_decode.return_value = {
                "sub": "user-123",
                "email": "test@example.com"
            }
            
            # Act
            response = client.post("/api/auth/login", json={
                "email": "test@example.com",
                "password": "password123"
            })
        
        # Assert
        assert response.status_code == 200
        assert mock_client.post.call_count == 2
    
    @patch('fastmcp.auth.interface.auth_endpoints.httpx.AsyncClient')
    @patch.dict(os.environ, {"AUTH_PROVIDER": "keycloak"})
    def test_login_connection_error(self, mock_client_class, client):
        """Test login when Keycloak is unavailable"""
        # Arrange
        mock_client = AsyncMock()
        mock_client.post.side_effect = httpx.RequestError("Connection failed")
        mock_client_class.return_value.__aenter__.return_value = mock_client
        
        # Act
        response = client.post("/api/auth/login", json={
            "email": "test@example.com",
            "password": "password123"
        })
        
        # Assert
        assert response.status_code == 503
        assert "Authentication service unavailable" in response.json()["detail"]
    
    @patch.dict(os.environ, {"AUTH_PROVIDER": "supabase"})
    def test_login_supabase_not_implemented(self, client):
        """Test login with Supabase provider (not implemented)"""
        # Act
        response = client.post("/api/auth/login", json={
            "email": "test@example.com",
            "password": "password123"
        })
        
        # Assert
        assert response.status_code == 501
        assert "Supabase authentication not implemented" in response.json()["detail"]
    
    @patch.dict(os.environ, {"AUTH_PROVIDER": "test"})
    def test_login_test_mode(self, client):
        """Test login in test mode"""
        # Act
        response = client.post("/api/auth/login", json={
            "email": "test@example.com",
            "password": "password123"
        })
        
        # Assert
        assert response.status_code == 200
        data = response.json()
        assert data["access_token"] == "test-token-12345"
        assert data["user_id"] == "test-user-001"
        assert data["email"] == "test@example.com"


class TestRegisterEndpoint:
    """Test suite for register endpoint"""
    
    @pytest.fixture
    def client(self):
        """Test client for FastAPI router"""
        if FastAPI is None:
            pytest.skip("FastAPI not available")
        app = FastAPI()
        app.include_router(router)
        return TestClient(app)
    
    @patch('fastmcp.auth.interface.auth_endpoints.httpx.AsyncClient')
    @patch.dict(os.environ, {
        "AUTH_PROVIDER": "keycloak",
        "KEYCLOAK_URL": "http://localhost:8080",
        "KEYCLOAK_REALM": "test-realm",
        "KEYCLOAK_CLIENT_ID": "test-client",
        "KEYCLOAK_CLIENT_SECRET": "test-secret",
        "EMAIL_VERIFIED_AUTO": "true"
    })
    def test_register_success(self, mock_client_class, client):
        """Test successful user registration"""
        # Arrange
        # Mock token response
        mock_token_response = Mock()
        mock_token_response.status_code = 200
        mock_token_response.json.return_value = {"access_token": "admin-token"}
        
        # Mock create user response
        mock_create_response = Mock()
        mock_create_response.status_code = 201
        mock_create_response.headers = {"Location": "http://keycloak/users/user-123"}
        
        # Mock auto-login response
        mock_login_response = Mock()
        mock_login_response.status_code = 200
        mock_login_response.json.return_value = {"access_token": "user-token"}
        
        mock_client = AsyncMock()
        mock_client.post.side_effect = [
            mock_token_response,  # Admin token
            mock_create_response,  # Create user
            mock_login_response    # Auto-login
        ]
        mock_client_class.return_value.__aenter__.return_value = mock_client
        
        # Mock setup_user_roles
        with patch('fastmcp.auth.interface.auth_endpoints.setup_user_roles'):
            # Act
            response = client.post("/api/auth/register", json={
                "email": "test@example.com",
                "password": "Password123!",
                "username": "testuser"
            })
        
        # Assert
        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        assert data["user_id"] == "user-123"
        assert data["email"] == "test@example.com"
        assert "SUCCESS" in data["message"]
        assert "auto_login_token" in data
    
    @patch('fastmcp.auth.interface.auth_endpoints.httpx.AsyncClient')
    @patch.dict(os.environ, {
        "AUTH_PROVIDER": "keycloak",
        "EMAIL_VERIFIED_AUTO": "false"
    })
    def test_register_email_verification_required(self, mock_client_class, client):
        """Test registration when email verification is required"""
        # Arrange
        # Mock token response
        mock_token_response = Mock()
        mock_token_response.status_code = 200
        mock_token_response.json.return_value = {"access_token": "admin-token"}
        
        # Mock create user response
        mock_create_response = Mock()
        mock_create_response.status_code = 201
        mock_create_response.headers = {"Location": "http://keycloak/users/user-123"}
        
        mock_client = AsyncMock()
        mock_client.post.side_effect = [mock_token_response, mock_create_response]
        mock_client_class.return_value.__aenter__.return_value = mock_client
        
        # Mock setup_user_roles
        with patch('fastmcp.auth.interface.auth_endpoints.setup_user_roles'):
            # Act
            response = client.post("/api/auth/register", json={
                "email": "test@example.com",
                "password": "Password123!",
                "username": "testuser"
            })
        
        # Assert
        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        assert "check your email" in data["message"].lower()
        assert data["message_type"] == "warning"
        assert data["display_color"] == "yellow"
    
    def test_register_invalid_password(self, client):
        """Test registration with invalid password"""
        # Act
        response = client.post("/api/auth/register", json={
            "email": "test@example.com",
            "password": "weak",
            "username": "testuser"
        })
        
        # Assert
        assert response.status_code == 422
        assert "Password does not meet requirements" in response.json()["detail"]
    
    def test_register_invalid_email(self, client):
        """Test registration with invalid email"""
        # Act
        response = client.post("/api/auth/register", json={
            "email": "not-an-email",
            "password": "Password123!",
            "username": "testuser"
        })
        
        # Assert
        assert response.status_code == 422
        assert "valid email address" in response.json()["detail"]
    
    @patch('fastmcp.auth.interface.auth_endpoints.httpx.AsyncClient')
    @patch.dict(os.environ, {"AUTH_PROVIDER": "keycloak"})
    def test_register_user_already_exists(self, mock_client_class, client):
        """Test registration when user already exists"""
        # Arrange
        # Mock token response
        mock_token_response = Mock()
        mock_token_response.status_code = 200
        mock_token_response.json.return_value = {"access_token": "admin-token"}
        
        # Mock create user response - conflict
        mock_create_response = Mock()
        mock_create_response.status_code = 409
        
        mock_client = AsyncMock()
        mock_client.post.side_effect = [mock_token_response, mock_create_response]
        mock_client_class.return_value.__aenter__.return_value = mock_client
        
        # Mock cleanup function
        with patch('fastmcp.auth.interface.auth_endpoints.cleanup_incomplete_account_internal') as mock_cleanup:
            mock_cleanup.return_value = {
                "success": False,
                "message": "Account is verified and complete",
                "can_register": False
            }
            
            # Act
            response = client.post("/api/auth/register", json={
                "email": "test@example.com",
                "password": "Password123!",
                "username": "testuser"
            })
        
        # Assert
        assert response.status_code == 409
        assert "already exists" in response.json()["detail"]
    
    @patch('fastmcp.auth.interface.auth_endpoints.httpx.AsyncClient')
    @patch.dict(os.environ, {"AUTH_PROVIDER": "keycloak"})
    def test_register_with_cleanup_and_retry(self, mock_client_class, client):
        """Test registration with successful cleanup and retry"""
        # Arrange
        # Mock token response
        mock_token_response = Mock()
        mock_token_response.status_code = 200
        mock_token_response.json.return_value = {"access_token": "admin-token"}
        
        # First create fails with conflict
        mock_create_fail = Mock()
        mock_create_fail.status_code = 409
        
        # Second create succeeds after cleanup
        mock_create_success = Mock()
        mock_create_success.status_code = 201
        mock_create_success.headers = {"Location": "http://keycloak/users/user-456"}
        
        mock_client = AsyncMock()
        mock_client.post.side_effect = [
            mock_token_response,
            mock_create_fail,
            mock_create_success
        ]
        mock_client_class.return_value.__aenter__.return_value = mock_client
        
        # Mock cleanup function
        with patch('fastmcp.auth.interface.auth_endpoints.cleanup_incomplete_account_internal') as mock_cleanup:
            mock_cleanup.return_value = {
                "success": True,
                "message": "Cleanup successful",
                "can_register": True
            }
            
            with patch('fastmcp.auth.interface.auth_endpoints.setup_user_roles'):
                # Act
                response = client.post("/api/auth/register", json={
                    "email": "test@example.com",
                    "password": "Password123!",
                    "username": "testuser"
                })
        
        # Assert
        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        assert data["user_id"] == "user-456"
        assert "issue resolved" in data["message"].lower()
    
    @patch.dict(os.environ, {"AUTH_PROVIDER": "supabase"})
    def test_register_supabase_not_implemented(self, client):
        """Test registration with Supabase provider (not implemented)"""
        # Act
        response = client.post("/api/auth/register", json={
            "email": "test@example.com",
            "password": "Password123!",
            "username": "testuser"
        })
        
        # Assert
        assert response.status_code == 501
        assert "Supabase registration is not yet implemented" in response.json()["detail"]
    
    @patch.dict(os.environ, {"AUTH_PROVIDER": "test"})
    def test_register_test_mode(self, client):
        """Test registration in test mode"""
        # Act
        response = client.post("/api/auth/register", json={
            "email": "test@example.com",
            "password": "Password123!",
            "username": "testuser"
        })
        
        # Assert
        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        assert "Test Mode" in data["message"]
        assert len(data["user_id"]) == 36  # UUID length


class TestRefreshTokenEndpoint:
    """Test suite for refresh token endpoint"""
    
    @pytest.fixture
    def client(self):
        """Test client for FastAPI router"""
        if FastAPI is None:
            pytest.skip("FastAPI not available")
        app = FastAPI()
        app.include_router(router)
        return TestClient(app)
    
    @patch('fastmcp.auth.interface.auth_endpoints.httpx.AsyncClient')
    @patch.dict(os.environ, {"AUTH_PROVIDER": "keycloak"})
    def test_refresh_token_success(self, mock_client_class, client):
        """Test successful token refresh"""
        # Arrange
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "access_token": "new-token",
            "refresh_token": "new-refresh-token",
            "expires_in": 3600
        }
        
        mock_client = AsyncMock()
        mock_client.post.return_value = mock_response
        mock_client_class.return_value.__aenter__.return_value = mock_client
        
        # Act
        response = client.post("/api/auth/refresh?refresh_token=old-refresh-token")
        
        # Assert
        assert response.status_code == 200
        data = response.json()
        assert data["access_token"] == "new-token"
        assert data["refresh_token"] == "new-refresh-token"
        assert data["expires_in"] == 3600
    
    @patch('fastmcp.auth.interface.auth_endpoints.httpx.AsyncClient')
    @patch.dict(os.environ, {"AUTH_PROVIDER": "keycloak"})
    def test_refresh_token_invalid(self, mock_client_class, client):
        """Test refresh with invalid token"""
        # Arrange
        mock_response = Mock()
        mock_response.status_code = 401
        
        mock_client = AsyncMock()
        mock_client.post.return_value = mock_response
        mock_client_class.return_value.__aenter__.return_value = mock_client
        
        # Act
        response = client.post("/api/auth/refresh?refresh_token=invalid-token")
        
        # Assert
        assert response.status_code == 401
        assert "Invalid refresh token" in response.json()["detail"]
    
    @patch('fastmcp.auth.interface.auth_endpoints.httpx.AsyncClient')
    @patch.dict(os.environ, {"AUTH_PROVIDER": "keycloak"})
    def test_refresh_token_connection_error(self, mock_client_class, client):
        """Test refresh when Keycloak is unavailable"""
        # Arrange
        mock_client = AsyncMock()
        mock_client.post.side_effect = httpx.RequestError("Connection failed")
        mock_client_class.return_value.__aenter__.return_value = mock_client
        
        # Act
        response = client.post("/api/auth/refresh?refresh_token=some-token")
        
        # Assert
        assert response.status_code == 503
        assert "Authentication service unavailable" in response.json()["detail"]
    
    @patch.dict(os.environ, {"AUTH_PROVIDER": "test"})
    def test_refresh_token_not_implemented(self, client):
        """Test refresh in test mode (not implemented)"""
        # Act
        response = client.post("/api/auth/refresh?refresh_token=test-token")
        
        # Assert
        assert response.status_code == 501
        assert "Token refresh not implemented" in response.json()["detail"]


class TestLogoutEndpoint:
    """Test suite for logout endpoint"""
    
    @pytest.fixture
    def client(self):
        """Test client for FastAPI router"""
        if FastAPI is None:
            pytest.skip("FastAPI not available")
        app = FastAPI()
        app.include_router(router)
        return TestClient(app)
    
    @patch('fastmcp.auth.interface.auth_endpoints.httpx.AsyncClient')
    @patch.dict(os.environ, {"AUTH_PROVIDER": "keycloak"})
    def test_logout_success(self, mock_client_class, client):
        """Test successful logout"""
        # Arrange
        mock_response = Mock()
        mock_response.status_code = 204
        
        mock_client = AsyncMock()
        mock_client.post.return_value = mock_response
        mock_client_class.return_value.__aenter__.return_value = mock_client
        
        # Act
        response = client.post("/api/auth/logout", json={
            "refresh_token": "valid-token"
        })
        
        # Assert
        assert response.status_code == 200
        assert response.json()["message"] == "Logged out successfully"
    
    @patch('fastmcp.auth.interface.auth_endpoints.httpx.AsyncClient')
    @patch.dict(os.environ, {"AUTH_PROVIDER": "keycloak"})
    def test_logout_connection_error(self, mock_client_class, client):
        """Test logout when Keycloak is unavailable"""
        # Arrange
        mock_client = AsyncMock()
        mock_client.post.side_effect = httpx.RequestError("Connection failed")
        mock_client_class.return_value.__aenter__.return_value = mock_client
        
        # Act
        response = client.post("/api/auth/logout", json={
            "refresh_token": "some-token"
        })
        
        # Assert
        assert response.status_code == 200
        assert "Logout completed (local)" in response.json()["message"]
    
    def test_logout_without_token(self, client):
        """Test logout without refresh token"""
        # Act
        response = client.post("/api/auth/logout", json={})
        
        # Assert
        assert response.status_code == 200
        assert response.json()["message"] == "Logged out successfully"


class TestUtilityEndpoints:
    """Test suite for utility endpoints"""
    
    @pytest.fixture
    def client(self):
        """Test client for FastAPI router"""
        if FastAPI is None:
            pytest.skip("FastAPI not available")
        app = FastAPI()
        app.include_router(router)
        return TestClient(app)
    
    @patch.dict(os.environ, {
        "AUTH_PROVIDER": "keycloak",
        "KEYCLOAK_URL": "http://localhost:8080",
        "KEYCLOAK_REALM": "test-realm",
        "KEYCLOAK_CLIENT_ID": "test-client"
    })
    def test_get_provider(self, client):
        """Test getting auth provider configuration"""
        # Act
        response = client.get("/api/auth/provider")
        
        # Assert
        assert response.status_code == 200
        data = response.json()
        assert data["provider"] == "keycloak"
        assert data["keycloak_url"] == "http://localhost:8080"
        assert data["keycloak_realm"] == "test-realm"
        assert data["keycloak_client_id"] == "test-client"
    
    def test_verify_auth(self, client):
        """Test auth verification endpoint"""
        # Act
        response = client.get("/api/auth/verify")
        
        # Assert
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "ok"
    
    def test_get_password_requirements(self, client):
        """Test getting password requirements"""
        # Act
        response = client.get("/api/auth/password-requirements")
        
        # Assert
        assert response.status_code == 200
        data = response.json()
        assert len(data["requirements"]) == 5
        assert len(data["example_passwords"]) > 0
        assert len(data["tips"]) > 0
    
    def test_validate_password_strong(self, client):
        """Test validating a strong password"""
        # Act
        response = client.post("/api/auth/validate-password?password=StrongPass123!")
        
        # Assert
        assert response.status_code == 200
        data = response.json()
        assert data["valid"] is True
        assert data["strength"] == "strong"
        assert data["score"] >= 4
    
    def test_validate_password_weak(self, client):
        """Test validating a weak password"""
        # Act
        response = client.post("/api/auth/validate-password?password=weak")
        
        # Assert
        assert response.status_code == 200
        data = response.json()
        assert data["valid"] is False
        assert data["strength"] == "weak"
        assert len(data["issues"]) > 0
        assert len(data["suggestions"]) > 0
    
    def test_registration_success_handler(self, client):
        """Test post-registration success handler"""
        # Act
        response = client.post("/api/auth/registration-success?user_id=123&email=test@example.com")
        
        # Assert
        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        assert data["user_id"] == "123"
        assert data["email"] == "test@example.com"
        assert len(data["onboarding_steps"]) > 0
        assert len(data["quick_links"]) > 0
        assert len(data["tips"]) > 0


class TestTokenManagementEndpoints:
    """Test suite for token management endpoints"""
    
    @pytest.fixture
    def client(self):
        """Test client for FastAPI router"""
        if FastAPI is None:
            pytest.skip("FastAPI not available")
        app = FastAPI()
        app.include_router(router)
        return TestClient(app)
    
    @pytest.fixture
    def mock_current_user(self):
        """Mock current user for authenticated endpoints"""
        user = Mock()
        user.id = "user-123"
        user.email = "test@example.com"
        return user
    
    @pytest.fixture
    def mock_db_session(self):
        """Mock database session"""
        return Mock(spec=Session)
    
    @patch('fastmcp.auth.interface.auth_endpoints.get_current_user')
    @patch('fastmcp.auth.interface.auth_endpoints.get_db')
    @patch('fastmcp.auth.interface.auth_endpoints.token_controller')
    def test_create_auth_token_success(self, mock_controller, mock_get_db, mock_get_user, client, mock_current_user, mock_db_session):
        """Test successful API token creation"""
        # Skip if token management imports failed
        if not hasattr(router, "post") or "/api/auth/tokens" not in [r.path for r in router.routes]:
            pytest.skip("Token management endpoints not available")
        
        # Arrange
        mock_get_user.return_value = mock_current_user
        mock_get_db.return_value = mock_db_session
        
        mock_controller.generate_api_token.return_value = {
            "success": True,
            "token_data": {
                "id": "token-123",
                "name": "Test Token",
                "scopes": ["read"],
                "created_at": datetime.now(timezone.utc),
                "expires_at": datetime.now(timezone.utc) + timedelta(days=30),
                "token": "generated-token-string"
            }
        }
        
        # Act
        response = client.post("/api/auth/tokens", json={
            "name": "Test Token",
            "scopes": ["read"],
            "expires_in_days": 30,
            "rate_limit": 1000
        })
        
        # Assert
        assert response.status_code == 200
        data = response.json()
        assert data["id"] == "token-123"
        assert data["name"] == "Test Token"
        assert data["token"] == "generated-token-string"
    
    @patch('fastmcp.auth.interface.auth_endpoints.get_current_user')
    @patch('fastmcp.auth.interface.auth_endpoints.get_db')
    @patch('fastmcp.auth.interface.auth_endpoints.token_controller')
    def test_list_auth_tokens_success(self, mock_controller, mock_get_db, mock_get_user, client, mock_current_user, mock_db_session):
        """Test listing user's API tokens"""
        # Skip if token management imports failed
        if not hasattr(router, "get") or "/api/auth/tokens" not in [r.path for r in router.routes]:
            pytest.skip("Token management endpoints not available")
        
        # Arrange
        mock_get_user.return_value = mock_current_user
        mock_get_db.return_value = mock_db_session
        
        mock_controller.list_user_tokens.return_value = {
            "success": True,
            "tokens": [
                {
                    "id": "token-1",
                    "name": "Token 1",
                    "scopes": ["read"],
                    "created_at": datetime.now(timezone.utc)
                },
                {
                    "id": "token-2",
                    "name": "Token 2",
                    "scopes": ["read", "write"],
                    "created_at": datetime.now(timezone.utc)
                }
            ],
            "total": 2
        }
        
        # Act
        response = client.get("/api/auth/tokens")
        
        # Assert
        assert response.status_code == 200
        data = response.json()
        assert data["total"] == 2
        assert len(data["data"]) == 2
        assert data["data"][0]["id"] == "token-1"
        assert data["data"][1]["id"] == "token-2"
    
    @patch('fastmcp.auth.interface.auth_endpoints.get_current_user')
    @patch('fastmcp.auth.interface.auth_endpoints.get_db')
    @patch('fastmcp.auth.interface.auth_endpoints.token_controller')
    def test_delete_auth_token_success(self, mock_controller, mock_get_db, mock_get_user, client, mock_current_user, mock_db_session):
        """Test deleting an API token"""
        # Skip if token management imports failed
        if not hasattr(router, "delete") or "/api/auth/tokens/{token_id}" not in [r.path for r in router.routes]:
            pytest.skip("Token management endpoints not available")
        
        # Arrange
        mock_get_user.return_value = mock_current_user
        mock_get_db.return_value = mock_db_session
        
        mock_controller.delete_token.return_value = {
            "success": True,
            "message": "Token deleted successfully"
        }
        
        # Act
        response = client.delete("/api/auth/tokens/token-123")
        
        # Assert
        assert response.status_code == 200
        assert response.json()["message"] == "Token deleted successfully"
    
    @patch('fastmcp.auth.interface.auth_endpoints.get_db')
    @patch('fastmcp.auth.interface.auth_endpoints.token_controller')
    def test_validate_auth_token_invalid(self, mock_controller, mock_get_db, client, mock_db_session):
        """Test validating an invalid token"""
        # Skip if token management imports failed
        if not hasattr(router, "get") or "/api/auth/tokens/validate/{token}" not in [r.path for r in router.routes]:
            pytest.skip("Token management endpoints not available")
        
        # Arrange
        mock_get_db.return_value = mock_db_session
        
        mock_controller.validate_token.return_value = {
            "success": False,
            "error": "Invalid token"
        }
        
        # Act
        response = client.get("/api/auth/tokens/validate/invalid-token")
        
        # Assert
        assert response.status_code == 401
        assert "Invalid token" in response.json()["detail"]


class TestEdgeCasesAndErrorHandling:
    """Test suite for edge cases and error scenarios"""
    
    @pytest.fixture
    def client(self):
        """Test client for FastAPI router"""
        if FastAPI is None:
            pytest.skip("FastAPI not available")
        app = FastAPI()
        app.include_router(router)
        return TestClient(app)
    
    def test_register_empty_username(self, client):
        """Test registration with empty username (should use email)"""
        with patch('fastmcp.auth.interface.auth_endpoints.httpx.AsyncClient'):
            with patch.dict(os.environ, {"AUTH_PROVIDER": "test"}):
                response = client.post("/api/auth/register", json={
                    "email": "test@example.com",
                    "password": "Password123!"
                })
        
        assert response.status_code == 200
        data = response.json()
        assert data["username"] == "test@example.com"
    
    @patch('fastmcp.auth.interface.auth_endpoints.httpx.AsyncClient')
    def test_register_keycloak_bad_request(self, mock_client_class, client):
        """Test registration when Keycloak returns bad request with error details"""
        # Arrange
        mock_token_response = Mock()
        mock_token_response.status_code = 200
        mock_token_response.json.return_value = {"access_token": "admin-token"}
        
        mock_create_response = Mock()
        mock_create_response.status_code = 400
        mock_create_response.json.return_value = {
            "error": "validation_failed",
            "error_description": "Password policy not met: special character required"
        }
        mock_create_response.text = json.dumps(mock_create_response.json.return_value)
        
        mock_client = AsyncMock()
        mock_client.post.side_effect = [mock_token_response, mock_create_response]
        mock_client_class.return_value.__aenter__.return_value = mock_client
        
        with patch.dict(os.environ, {"AUTH_PROVIDER": "keycloak"}):
            # Act
            response = client.post("/api/auth/register", json={
                "email": "test@example.com",
                "password": "WeakPassword123",
                "username": "testuser"
            })
        
        # Assert
        assert response.status_code == 400
        assert "special character" in response.json()["detail"]
    
    @patch('fastmcp.auth.interface.auth_endpoints.httpx.AsyncClient')
    def test_login_keycloak_generic_error(self, mock_client_class, client):
        """Test login when Keycloak returns unexpected error code"""
        # Arrange
        mock_response = Mock()
        mock_response.status_code = 403
        mock_response.text = "Forbidden"
        
        mock_client = AsyncMock()
        mock_client.post.return_value = mock_response
        mock_client_class.return_value.__aenter__.return_value = mock_client
        
        with patch.dict(os.environ, {"AUTH_PROVIDER": "keycloak"}):
            # Act
            response = client.post("/api/auth/login", json={
                "email": "test@example.com",
                "password": "password123"
            })
        
        # Assert
        assert response.status_code == 403
        assert "Authentication failed" in response.json()["detail"]
    
    def test_validate_password_with_all_requirements(self, client):
        """Test password validation with different combinations"""
        test_cases = [
            ("Aa1!", False, "at least 8 characters"),  # Too short
            ("aaaaaaaa", False, "uppercase"),  # No uppercase
            ("AAAAAAAA", False, "lowercase"),  # No lowercase
            ("Aaaaaaaa", False, "number"),  # No number
            ("Aaaaaaa1", False, "special character"),  # No special
            ("Aa1!Aa1!", True, None),  # Valid
        ]
        
        for password, should_be_valid, expected_issue in test_cases:
            response = client.post(f"/api/auth/validate-password?password={password}")
            assert response.status_code == 200
            data = response.json()
            assert data["valid"] == should_be_valid
            if not should_be_valid:
                assert any(expected_issue in issue for issue in data["issues"])