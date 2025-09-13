"""Test suite for Hook Authentication System

Comprehensive test coverage for hook authentication including:
- JWT token validation
- Hook request detection
- Token creation and expiration
- MCP.json token extraction
- Error handling and edge cases
"""

import pytest
import os
import json
import tempfile
from datetime import datetime, timezone, timedelta
from unittest.mock import Mock, patch, MagicMock
from pathlib import Path

from jose import jwt, JWTError
from fastapi import HTTPException
from fastapi.security import HTTPAuthorizationCredentials

from fastmcp.auth.hook_auth import (
    HookAuthValidator,
    hook_auth_validator,
    get_hook_authenticated_user,
    is_hook_request,
    get_token_from_mcp_json,
    create_hook_token,
    HOOK_JWT_ALGORITHM,
    HOOK_JWT_SECRET
)


class TestHookAuthValidator:
    """Test HookAuthValidator class"""
    
    @pytest.fixture
    def validator(self):
        """Create HookAuthValidator instance"""
        return HookAuthValidator()
    
    def test_validate_hook_token_valid(self, validator):
        """Test validation of valid hook token"""
        # Create a valid token
        payload = {
            "sub": "test-user",
            "type": "api_token",
            "iss": "dhafnck-mcp",
            "exp": (datetime.now(timezone.utc) + timedelta(hours=1)).timestamp()
        }
        token = jwt.encode(payload, HOOK_JWT_SECRET, algorithm=HOOK_JWT_ALGORITHM)
        
        # Validate
        result = validator.validate_hook_token(token)
        
        # Verify
        assert result["sub"] == "test-user"
        assert result["type"] == "api_token"
        assert result["iss"] == "dhafnck-mcp"
    
    def test_validate_hook_token_expired(self, validator):
        """Test validation of expired token"""
        # Create an expired token
        payload = {
            "sub": "test-user",
            "type": "api_token",
            "iss": "dhafnck-mcp",
            "exp": (datetime.now(timezone.utc) - timedelta(hours=1)).timestamp()
        }
        token = jwt.encode(payload, HOOK_JWT_SECRET, algorithm=HOOK_JWT_ALGORITHM)
        
        # Validate and expect exception
        with pytest.raises(HTTPException) as exc_info:
            validator.validate_hook_token(token)
        
        assert exc_info.value.status_code == 401
        assert exc_info.value.detail == "Token expired"
    
    def test_validate_hook_token_invalid_signature(self, validator):
        """Test validation with invalid signature"""
        # Create token with wrong secret
        payload = {
            "sub": "test-user",
            "type": "api_token",
            "iss": "dhafnck-mcp"
        }
        token = jwt.encode(payload, "wrong_secret", algorithm=HOOK_JWT_ALGORITHM)
        
        # Validate and expect exception
        with pytest.raises(HTTPException) as exc_info:
            validator.validate_hook_token(token)
        
        assert exc_info.value.status_code == 401
        assert exc_info.value.detail == "Invalid hook token signature"
    
    def test_validate_hook_token_auth_disabled(self, validator):
        """Test validation with auth disabled (development mode)"""
        # Create token with wrong secret
        payload = {
            "sub": "test-user",
            "type": "api_token",
            "iss": "dhafnck-mcp"
        }
        token = jwt.encode(payload, "wrong_secret", algorithm=HOOK_JWT_ALGORITHM)
        
        # Disable auth
        with patch.dict(os.environ, {"AUTH_ENABLED": "false"}):
            result = validator.validate_hook_token(token)
        
        # Should return unverified payload
        assert result["sub"] == "test-user"
        assert result["type"] == "api_token"
    
    def test_validate_hook_token_not_hook_token(self, validator):
        """Test validation with non-hook token"""
        # Create token without hook-specific fields
        payload = {
            "sub": "user123",
            "aud": "some-other-service"
        }
        token = jwt.encode(payload, HOOK_JWT_SECRET, algorithm=HOOK_JWT_ALGORITHM)
        
        # Validate and expect exception
        with pytest.raises(HTTPException) as exc_info:
            validator.validate_hook_token(token)
        
        assert exc_info.value.status_code == 401
        assert exc_info.value.detail == "Not a valid hook token"
    
    def test_validate_hook_token_invalid_format(self, validator):
        """Test validation with invalid token format"""
        # Validate and expect exception
        with pytest.raises(HTTPException) as exc_info:
            validator.validate_hook_token("not.a.valid.token")
        
        assert exc_info.value.status_code == 401
        assert exc_info.value.detail == "Invalid token format"
    
    def test_validate_hook_token_unexpected_error(self, validator):
        """Test handling of unexpected errors"""
        with patch('fastmcp.auth.hook_auth.jwt.get_unverified_claims') as mock_get_claims:
            mock_get_claims.side_effect = Exception("Unexpected error")
            
            with pytest.raises(HTTPException) as exc_info:
                validator.validate_hook_token("some.token.here")
            
            assert exc_info.value.status_code == 500
            assert exc_info.value.detail == "Authentication error"


class TestHookAuthDependencies:
    """Test FastAPI dependencies"""
    
    @pytest.mark.asyncio
    async def test_get_hook_authenticated_user_success(self):
        """Test successful user authentication"""
        # Create valid token
        payload = {
            "sub": "hook-user-123",
            "type": "api_token",
            "iss": "dhafnck-mcp",
            "exp": (datetime.now(timezone.utc) + timedelta(hours=1)).timestamp()
        }
        token = jwt.encode(payload, HOOK_JWT_SECRET, algorithm=HOOK_JWT_ALGORITHM)
        
        # Create credentials
        credentials = HTTPAuthorizationCredentials(
            scheme="Bearer",
            credentials=token
        )
        
        # Get authenticated user
        user_data = await get_hook_authenticated_user(credentials)
        
        # Verify
        assert user_data["sub"] == "hook-user-123"
        assert user_data["auth_type"] == "hook"
        assert user_data["auth_method"] == "jwt_token"
    
    @pytest.mark.asyncio
    async def test_get_hook_authenticated_user_no_credentials(self):
        """Test authentication without credentials"""
        with pytest.raises(HTTPException) as exc_info:
            await get_hook_authenticated_user(None)
        
        assert exc_info.value.status_code == 401
        assert exc_info.value.detail == "No authentication provided"
    
    @pytest.mark.asyncio
    async def test_get_hook_authenticated_user_invalid_token(self):
        """Test authentication with invalid token"""
        credentials = HTTPAuthorizationCredentials(
            scheme="Bearer",
            credentials="invalid.token.here"
        )
        
        with pytest.raises(HTTPException) as exc_info:
            await get_hook_authenticated_user(credentials)
        
        assert exc_info.value.status_code == 401


class TestHookDetection:
    """Test hook request detection"""
    
    def test_is_hook_request_python(self):
        """Test detection of Python requests"""
        headers = {"user-agent": "python-requests/2.28.0"}
        assert is_hook_request(headers) is True
    
    def test_is_hook_request_aiohttp(self):
        """Test detection of aiohttp requests"""
        headers = {"user-agent": "aiohttp/3.8.0"}
        assert is_hook_request(headers) is True
    
    def test_is_hook_request_httpx(self):
        """Test detection of httpx requests"""
        headers = {"user-agent": "python-httpx/0.24.0"}
        assert is_hook_request(headers) is True
    
    def test_is_hook_request_claude_hook(self):
        """Test detection of Claude hook requests"""
        headers = {"user-agent": "Claude-Hook/1.0"}
        assert is_hook_request(headers) is True
    
    def test_is_hook_request_mcp_client(self):
        """Test detection of MCP client requests"""
        headers = {"user-agent": "MCP-Client/2.0"}
        assert is_hook_request(headers) is True
    
    def test_is_hook_request_browser(self):
        """Test non-detection of browser requests"""
        headers = {"user-agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"}
        assert is_hook_request(headers) is False
    
    def test_is_hook_request_no_user_agent(self):
        """Test with missing user agent"""
        headers = {}
        assert is_hook_request(headers) is False
    
    def test_is_hook_request_case_insensitive(self):
        """Test case-insensitive detection"""
        headers = {"user-agent": "Python-REQUESTS/2.28.0"}
        assert is_hook_request(headers) is True


class TestMcpJsonToken:
    """Test .mcp.json token extraction"""
    
    def test_get_token_from_mcp_json_success(self):
        """Test successful token extraction from .mcp.json"""
        # Create temporary .mcp.json
        with tempfile.TemporaryDirectory() as tmpdir:
            mcp_json = {
                "mcpServers": {
                    "dhafnck_mcp_http": {
                        "headers": {
                            "Authorization": "Bearer test_token_123"
                        }
                    }
                }
            }
            
            mcp_json_path = Path(tmpdir) / ".mcp.json"
            with open(mcp_json_path, 'w') as f:
                json.dump(mcp_json, f)
            
            # Mock the path calculation
            with patch('fastmcp.auth.hook_auth.Path') as mock_path:
                mock_path.return_value.parent.parent.parent.parent.parent = Path(tmpdir)
                
                token = get_token_from_mcp_json()
                assert token == "test_token_123"
    
    def test_get_token_from_mcp_json_no_file(self):
        """Test when .mcp.json doesn't exist"""
        with patch('fastmcp.auth.hook_auth.Path') as mock_path:
            mock_path.return_value.parent.parent.parent.parent.parent = Path("/nonexistent")
            
            token = get_token_from_mcp_json()
            assert token is None
    
    def test_get_token_from_mcp_json_invalid_structure(self):
        """Test with invalid .mcp.json structure"""
        with tempfile.TemporaryDirectory() as tmpdir:
            mcp_json = {"invalid": "structure"}
            
            mcp_json_path = Path(tmpdir) / ".mcp.json"
            with open(mcp_json_path, 'w') as f:
                json.dump(mcp_json, f)
            
            with patch('fastmcp.auth.hook_auth.Path') as mock_path:
                mock_path.return_value.parent.parent.parent.parent.parent = Path(tmpdir)
                
                token = get_token_from_mcp_json()
                assert token is None
    
    def test_get_token_from_mcp_json_no_bearer_prefix(self):
        """Test token without Bearer prefix"""
        with tempfile.TemporaryDirectory() as tmpdir:
            mcp_json = {
                "mcpServers": {
                    "dhafnck_mcp_http": {
                        "headers": {
                            "Authorization": "just_a_token"
                        }
                    }
                }
            }
            
            mcp_json_path = Path(tmpdir) / ".mcp.json"
            with open(mcp_json_path, 'w') as f:
                json.dump(mcp_json, f)
            
            with patch('fastmcp.auth.hook_auth.Path') as mock_path:
                mock_path.return_value.parent.parent.parent.parent.parent = Path(tmpdir)
                
                token = get_token_from_mcp_json()
                assert token is None


class TestTokenCreation:
    """Test hook token creation"""
    
    def test_create_hook_token_default(self):
        """Test creating token with default parameters"""
        token = create_hook_token()
        
        # Decode and verify
        payload = jwt.decode(token, HOOK_JWT_SECRET, algorithms=[HOOK_JWT_ALGORITHM], audience="mcp-server")
        
        assert payload["sub"] == "hook-user"
        assert payload["type"] == "api_token"
        assert payload["iss"] == "dhafnck-mcp"
        assert payload["aud"] == "mcp-server"
        assert "exp" in payload
        assert "iat" in payload
        assert "jti" in payload
        assert "scopes" in payload
        
        # Check scopes
        expected_scopes = [
            "mcp-api",
            "tasks:read",
            "tasks:create",
            "tasks:update",
            "contexts:read",
            "projects:read",
            "branches:read"
        ]
        assert payload["scopes"] == expected_scopes
    
    def test_create_hook_token_custom_user(self):
        """Test creating token with custom user ID"""
        token = create_hook_token(user_id="custom-hook-123")
        
        payload = jwt.decode(token, HOOK_JWT_SECRET, algorithms=[HOOK_JWT_ALGORITHM], audience="mcp-server")
        assert payload["sub"] == "custom-hook-123"
    
    def test_create_hook_token_custom_expiry(self):
        """Test creating token with custom expiry"""
        token = create_hook_token(expires_in_days=7)
        
        payload = jwt.decode(token, HOOK_JWT_SECRET, algorithms=[HOOK_JWT_ALGORITHM], audience="mcp-server")
        
        # Check expiry is approximately 7 days from now
        exp_time = datetime.fromtimestamp(payload["exp"], tz=timezone.utc)
        expected_time = datetime.now(timezone.utc) + timedelta(days=7)
        
        # Allow 1 minute difference for test execution time
        time_diff = abs((exp_time - expected_time).total_seconds())
        assert time_diff < 60
    
    def test_create_hook_token_unique_jti(self):
        """Test that tokens have unique JTI values"""
        token1 = create_hook_token()
        token2 = create_hook_token()
        
        payload1 = jwt.decode(token1, HOOK_JWT_SECRET, algorithms=[HOOK_JWT_ALGORITHM], audience="mcp-server")
        payload2 = jwt.decode(token2, HOOK_JWT_SECRET, algorithms=[HOOK_JWT_ALGORITHM], audience="mcp-server")
        
        assert payload1["jti"] != payload2["jti"]
        assert payload1["jti"].startswith("hook_")
        assert payload2["jti"].startswith("hook_")


class TestIntegration:
    """Integration tests"""
    
    def test_round_trip_token_creation_and_validation(self):
        """Test creating and then validating a token"""
        # Create token
        user_id = "integration-test-user"
        token = create_hook_token(user_id=user_id, expires_in_days=1)
        
        # Validate token
        validator = HookAuthValidator()
        payload = validator.validate_hook_token(token)
        
        # Verify
        assert payload["sub"] == user_id
        assert payload["type"] == "api_token"
        assert payload["iss"] == "dhafnck-mcp"
        assert "scopes" in payload
    
    @pytest.mark.asyncio
    async def test_full_auth_flow(self):
        """Test complete authentication flow"""
        # Create token
        token = create_hook_token(user_id="flow-test-user")
        
        # Create credentials
        credentials = HTTPAuthorizationCredentials(
            scheme="Bearer",
            credentials=token
        )
        
        # Authenticate
        user_data = await get_hook_authenticated_user(credentials)
        
        # Verify
        assert user_data["sub"] == "flow-test-user"
        assert user_data["auth_type"] == "hook"
        assert user_data["auth_method"] == "jwt_token"
        assert "scopes" in user_data


class TestEnvironmentVariables:
    """Test environment variable handling"""
    
    def test_hook_jwt_algorithm_default(self):
        """Test default JWT algorithm"""
        assert HOOK_JWT_ALGORITHM == "HS256"
    
    def test_hook_jwt_secret_required(self):
        """Test that JWT secret is required"""
        # This test verifies the module loaded successfully
        # which means HOOK_JWT_SECRET was present
        assert HOOK_JWT_SECRET is not None
        assert len(HOOK_JWT_SECRET) > 0