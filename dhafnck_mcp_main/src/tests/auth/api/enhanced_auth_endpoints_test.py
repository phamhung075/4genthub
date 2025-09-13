"""Test suite for Enhanced Authentication API Endpoints

This test suite focuses on testing the request/response models and utility functions
of the enhanced auth endpoints. The actual endpoint testing should be done via 
integration tests with TestClient.
"""

import pytest
from datetime import datetime, timezone, timedelta
from unittest.mock import Mock
from fastapi import Request

# Import only the models and utility functions that are actually exported
from fastmcp.auth.api.enhanced_auth_endpoints import (
    EnhancedSignUpRequest,
    PasswordResetRequest,
    VerifyEmailRequest,
    ResetPasswordRequest,
    ResendVerificationRequest,
    EnhancedAuthResponse,
    get_client_info
)


class TestRequestModels:
    """Test request model validation"""
    
    def test_enhanced_sign_up_request_valid(self):
        """Test valid sign up request"""
        request = EnhancedSignUpRequest(
            email="user@example.com",
            password="SecurePass123!",
            username="testuser",
            full_name="Test User",
            send_custom_email=True
        )
        
        assert request.email == "user@example.com"
        assert request.password == "SecurePass123!"
        assert request.username == "testuser"
        assert request.full_name == "Test User"
        assert request.send_custom_email is True
    
    def test_enhanced_sign_up_request_minimal(self):
        """Test minimal sign up request"""
        request = EnhancedSignUpRequest(
            email="user@example.com",
            password="Pass123"
        )
        
        assert request.email == "user@example.com"
        assert request.password == "Pass123"
        assert request.username is None
        assert request.full_name is None
        assert request.send_custom_email is True
    
    def test_password_reset_request(self):
        """Test password reset request"""
        request = PasswordResetRequest(
            email="user@example.com"
        )
        
        assert request.email == "user@example.com"
    
    def test_verify_email_request(self):
        """Test verify email request"""
        request = VerifyEmailRequest(
            token="verify-token-123",
            email="test@example.com"
        )
        
        assert request.token == "verify-token-123"
        assert request.email == "test@example.com"
    
    def test_reset_password_request(self):
        """Test reset password with token request"""
        request = ResetPasswordRequest(
            token="reset-token-123",
            email="test@example.com",
            new_password="NewSecurePass456!"
        )
        
        assert request.token == "reset-token-123"
        assert request.email == "test@example.com"
        assert request.new_password == "NewSecurePass456!"
    
    def test_resend_verification_request(self):
        """Test resend verification email request"""
        request = ResendVerificationRequest(
            email="user@example.com"
        )
        
        assert request.email == "user@example.com"


class TestResponseModels:
    """Test response model validation"""
    
    def test_enhanced_auth_response_success(self):
        """Test successful auth response"""
        user_data = {
            "user_id": "user-789",
            "email": "user@example.com",
            "expires_at": (datetime.now(timezone.utc) + timedelta(hours=1)).isoformat()
        }
        response = EnhancedAuthResponse(
            success=True,
            message="Authentication successful",
            user=user_data,
            access_token="access-token-123",
            refresh_token="refresh-token-456",
            requires_email_verification=False,
            email_sent=False
        )
        
        assert response.success is True
        assert response.message == "Authentication successful"
        assert response.access_token == "access-token-123"
        assert response.refresh_token == "refresh-token-456"
        assert response.user["user_id"] == "user-789"
        assert response.user["email"] == "user@example.com"
        assert response.requires_email_verification is False
        assert response.email_sent is False
    
    def test_enhanced_auth_response_with_email_verification(self):
        """Test auth response requiring email verification"""
        response = EnhancedAuthResponse(
            success=True,
            message="Registration successful, please verify email",
            requires_email_verification=True,
            email_sent=True
        )
        
        assert response.success is True
        assert response.requires_email_verification is True
        assert response.email_sent is True
        assert response.access_token is None
        assert response.refresh_token is None
    
    def test_enhanced_auth_response_failure(self):
        """Test failed auth response"""
        response = EnhancedAuthResponse(
            success=False,
            message="Invalid credentials",
            email_error="Authentication failed"
        )
        
        assert response.success is False
        assert response.message == "Invalid credentials"
        assert response.email_error == "Authentication failed"
        assert response.access_token is None


class TestUtilityFunctions:
    """Test utility functions"""
    
    def test_get_client_info_full(self):
        """Test getting full client info from request"""
        # Create mock request with all headers
        mock_request = Mock(spec=Request)
        mock_request.client = Mock(host="192.168.1.100")
        mock_request.headers = {
            "user-agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)",
            "x-forwarded-for": "203.0.113.10, 198.51.100.15",
            "x-real-ip": "203.0.113.10"
        }
        
        client_info = get_client_info(mock_request)
        
        # Current implementation uses request.client.host directly
        assert client_info["ip_address"] == "192.168.1.100"
        assert client_info["user_agent"] == "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"
    
    def test_get_client_info_no_forwarded(self):
        """Test getting client info without forwarded headers"""
        mock_request = Mock(spec=Request)
        mock_request.client = Mock(host="10.0.0.5")
        mock_request.headers = {
            "user-agent": "TestClient/1.0"
        }
        
        client_info = get_client_info(mock_request)
        
        assert client_info["ip_address"] == "10.0.0.5"
        assert client_info["user_agent"] == "TestClient/1.0"
    
    def test_get_client_info_no_client(self):
        """Test getting client info when client is None"""
        mock_request = Mock(spec=Request)
        mock_request.client = None
        mock_request.headers = {
            "user-agent": "Unknown"
        }
        
        client_info = get_client_info(mock_request)
        
        assert client_info["ip_address"] == "unknown"
        assert client_info["user_agent"] == "Unknown"
    
    def test_get_client_info_empty_headers(self):
        """Test getting client info with empty headers"""
        mock_request = Mock(spec=Request)
        mock_request.client = Mock(host="127.0.0.1")
        mock_request.headers = {}
        
        client_info = get_client_info(mock_request)
        
        assert client_info["ip_address"] == "127.0.0.1"
        assert client_info["user_agent"] == "unknown"


class TestModelValidation:
    """Test model validation and edge cases"""
    
    def test_email_validation(self):
        """Test email field validation"""
        # Valid email
        request = EnhancedSignUpRequest(
            email="valid@example.com",
            password="Pass123"
        )
        assert request.email == "valid@example.com"
        
        # Invalid email should raise validation error
        with pytest.raises(ValueError):
            EnhancedSignUpRequest(
                email="invalid-email",
                password="Pass123"
            )
    
    def test_password_min_length(self):
        """Test password minimum length validation"""
        # Valid password (6+ chars)
        request = EnhancedSignUpRequest(
            email="user@example.com",
            password="123456"
        )
        assert len(request.password) >= 6
        
        # Too short password should raise validation error
        with pytest.raises(ValueError):
            EnhancedSignUpRequest(
                email="user@example.com",
                password="12345"
            )
    
    def test_optional_fields_default(self):
        """Test optional fields have correct defaults"""
        request = EnhancedSignUpRequest(
            email="user@example.com",
            password="Pass123"
        )
        
        assert request.username is None
        assert request.full_name is None
        assert request.send_custom_email is True
    
    def test_response_datetime_serialization(self):
        """Test datetime serialization in response"""
        expires = datetime.now(timezone.utc) + timedelta(hours=2)
        token_data = {
            "expires_at": expires.isoformat(),
            "token_type": "access"
        }
        response = EnhancedAuthResponse(
            success=True,
            message="Success",
            token_data=token_data
        )
        
        assert response.token_data["expires_at"] == expires.isoformat()
        # Check it can be serialized to dict
        response_dict = response.model_dump()
        assert response_dict["token_data"]["expires_at"] is not None