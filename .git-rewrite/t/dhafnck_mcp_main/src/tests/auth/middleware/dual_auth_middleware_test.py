"""
Test suite for Dual Authentication Middleware

Tests the unified authentication middleware that handles
multiple token types (Supabase JWT, local JWT, MCP token)
for both frontend and MCP requests.
"""

import os
import pytest
import jwt as pyjwt
from unittest.mock import MagicMock, AsyncMock, patch
from datetime import datetime, timedelta
from typing import Dict, Any, Optional

from starlette.requests import Request
from starlette.responses import Response, JSONResponse
from starlette.middleware.base import BaseHTTPMiddleware

from fastmcp.auth.middleware.dual_auth_middleware import (
    DualAuthMiddleware,
    create_dual_auth_middleware
)
from fastmcp.auth.supabase_client import TokenInfo
from fastmcp.auth.token_validator import TokenValidationError, RateLimitError


class TestDualAuthMiddleware:
    """Test suite for DualAuthMiddleware"""

    @pytest.fixture
    def mock_env(self, monkeypatch):
        """Mock environment variables"""
        monkeypatch.setenv("JWT_SECRET_KEY", "test-jwt-secret")
        monkeypatch.setenv("SUPABASE_JWT_SECRET", "test-supabase-secret")
        monkeypatch.setenv("SUPABASE_URL", "https://test.supabase.co")
        monkeypatch.setenv("SUPABASE_ANON_KEY", "test-anon-key")

    @pytest.fixture
    def mock_request(self):
        """Create a mock request object"""
        request = MagicMock(spec=Request)
        request.url = MagicMock()
        request.url.path = "/api/v2/test"
        request.headers = {}
        request.cookies = {}
        request.query_params = {}
        request.method = "GET"
        request.state = MagicMock()
        return request

    @pytest.fixture
    def mock_app(self):
        """Create a mock ASGI app"""
        app = MagicMock()
        return app

    @pytest.fixture
    @patch('fastmcp.auth.middleware.dual_auth_middleware.SupabaseAuthService')
    @patch('fastmcp.auth.middleware.dual_auth_middleware.TokenValidator')
    def middleware(self, mock_token_validator_class, mock_supabase_auth_class, mock_app, mock_env):
        """Create middleware instance with mocked dependencies"""
        # Create mock instances
        mock_supabase_auth = MagicMock()
        mock_token_validator = MagicMock()
        
        # Configure the class mocks to return the instances
        mock_supabase_auth_class.return_value = mock_supabase_auth
        mock_token_validator_class.return_value = mock_token_validator
        
        # Create middleware
        middleware = DualAuthMiddleware(mock_app)
        
        # Attach the mocks for testing
        middleware.supabase_auth = mock_supabase_auth
        middleware.token_validator = mock_token_validator
        
        return middleware

    def test_detect_request_type_mcp_path(self, middleware):
        """Test detection of MCP requests by path"""
        request = MagicMock()
        request.url.path = "/mcp/tools/list"
        request.headers = {}
        
        assert middleware._detect_request_type(request) == "mcp"

    def test_detect_request_type_mcp_header(self, middleware):
        """Test detection of MCP requests by header"""
        request = MagicMock()
        request.url.path = "/some/path"
        request.headers = {"mcp-protocol-version": "1.0"}
        
        assert middleware._detect_request_type(request) == "mcp"

    def test_detect_request_type_frontend_api(self, middleware):
        """Test detection of frontend API requests"""
        request = MagicMock()
        request.url.path = "/api/v2/users"
        request.headers = {"content-type": "application/json"}
        
        assert middleware._detect_request_type(request) == "frontend"

    def test_detect_request_type_browser(self, middleware):
        """Test detection of browser requests"""
        request = MagicMock()
        request.url.path = "/dashboard"
        request.headers = {
            "user-agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) Chrome/91.0",
            "content-type": "text/html"
        }
        
        assert middleware._detect_request_type(request) == "frontend"

    def test_should_skip_auth_health_check(self, middleware):
        """Test auth skipping for health check"""
        request = MagicMock()
        request.url.path = "/health"
        
        assert middleware._should_skip_auth(request) is True

    def test_should_skip_auth_docs(self, middleware):
        """Test auth skipping for documentation"""
        request = MagicMock()
        request.url.path = "/docs"
        
        assert middleware._should_skip_auth(request) is True

    def test_should_skip_auth_regular_path(self, middleware):
        """Test auth required for regular paths"""
        request = MagicMock()
        request.url.path = "/api/v2/users"
        
        assert middleware._should_skip_auth(request) is False

    def test_extract_token_bearer_header(self, middleware, mock_request):
        """Test token extraction from Bearer header"""
        mock_request.headers = {"authorization": "Bearer test-token-123"}
        
        token = middleware._extract_token(mock_request)
        assert token == "test-token-123"

    def test_extract_token_token_header(self, middleware, mock_request):
        """Test token extraction from Token header"""
        mock_request.headers = {"authorization": "Token test-token-456"}
        
        token = middleware._extract_token(mock_request)
        assert token == "test-token-456"

    def test_extract_token_mcp_header(self, middleware, mock_request):
        """Test token extraction from MCP header"""
        mock_request.headers = {"x-mcp-token": "mcp-token-789"}
        
        token = middleware._extract_token(mock_request)
        assert token == "mcp-token-789"

    def test_extract_token_cookie(self, middleware, mock_request):
        """Test token extraction from cookies"""
        mock_request.cookies = {"access_token": "cookie-token-000"}
        
        token = middleware._extract_token(mock_request)
        assert token == "cookie-token-000"

    def test_extract_token_query_param(self, middleware, mock_request):
        """Test token extraction from query params (with warning)"""
        mock_request.query_params = {"token": "query-token-111"}
        
        with patch('fastmcp.auth.middleware.dual_auth_middleware.logger') as mock_logger:
            token = middleware._extract_token(mock_request)
            assert token == "query-token-111"
            mock_logger.warning.assert_called_once()

    @pytest.mark.asyncio
    async def test_dispatch_skip_auth(self, middleware, mock_request):
        """Test dispatch skips authentication for allowed paths"""
        mock_request.url.path = "/health"
        
        # Create a mock response
        expected_response = Response("OK")
        
        # Mock call_next
        async def call_next(request):
            return expected_response
        
        response = await middleware.dispatch(mock_request, call_next)
        assert response == expected_response

    @pytest.mark.asyncio
    async def test_dispatch_no_token(self, middleware, mock_request):
        """Test dispatch with no authentication token"""
        # Create a mock response
        expected_response = Response("OK")
        
        # Mock call_next
        async def call_next(request):
            return expected_response
        
        response = await middleware.dispatch(mock_request, call_next)
        assert response == expected_response

    @pytest.mark.asyncio
    async def test_authenticate_request_api_token(self, middleware, mock_request):
        """Test authentication with API token"""
        # Create a valid JWT token
        payload = {
            "user_id": "test-user-123",
            "token_id": "tok_123",
            "type": "api_token",
            "exp": datetime.utcnow() + timedelta(hours=1)
        }
        token = pyjwt.encode(payload, "test-jwt-secret", algorithm="HS256")
        
        with patch.object(middleware, '_extract_token', return_value=token):
            with patch.object(middleware, '_validate_api_token') as mock_validate:
                mock_validate.return_value = {
                    'user_id': 'test-user-123',
                    'auth_method': 'api_token',
                    'token_id': 'tok_123'
                }
                
                result = await middleware._authenticate_request(mock_request, 'frontend')
                
                assert result is not None
                assert result['user_id'] == 'test-user-123'
                assert result['auth_method'] == 'api_token'
                mock_validate.assert_called_once_with(token)

    @pytest.mark.asyncio
    async def test_authenticate_request_supabase_token(self, middleware, mock_request):
        """Test authentication with Supabase token"""
        token = "supabase-jwt-token"
        
        # Mock user object
        mock_user = MagicMock()
        mock_user.id = "supabase-user-456"
        mock_user.email = "user@example.com"
        
        # Mock successful Supabase auth
        mock_result = MagicMock()
        mock_result.success = True
        mock_result.user = mock_user
        
        with patch.object(middleware, '_extract_token', return_value=token):
            middleware.supabase_auth.verify_token = AsyncMock(return_value=mock_result)
            
            result = await middleware._authenticate_request(mock_request, 'frontend')
            
            assert result is not None
            assert result['user_id'] == 'supabase-user-456'
            assert result['email'] == 'user@example.com'
            assert result['auth_method'] == 'supabase'

    @pytest.mark.asyncio
    async def test_authenticate_request_mcp_token(self, middleware, mock_request):
        """Test authentication with MCP token"""
        token = "mcp-token-789"
        
        # Mock token info
        mock_token_info = TokenInfo(
            token_id="tok_mcp_789",
            user_id="mcp-user-789",
            scopes=["read:tasks", "write:tasks"],
            created_at=datetime.utcnow(),
            expires_at=datetime.utcnow() + timedelta(hours=1)
        )
        
        with patch.object(middleware, '_extract_token', return_value=token):
            middleware.token_validator.validate_token = AsyncMock(return_value=mock_token_info)
            
            result = await middleware._authenticate_request(mock_request, 'mcp')
            
            assert result is not None
            assert result['user_id'] == 'mcp-user-789'
            assert result['auth_method'] == 'mcp_token'
            assert 'token_info' in result

    @pytest.mark.asyncio
    async def test_authenticate_request_all_methods_fail(self, middleware, mock_request):
        """Test authentication when all methods fail"""
        token = "invalid-token"
        
        with patch.object(middleware, '_extract_token', return_value=token):
            # Mock all validation methods to fail
            with patch.object(middleware, '_validate_api_token', return_value=None):
                with patch.object(middleware, '_validate_local_jwt', return_value=None):
                    # Mock Supabase auth to fail
                    mock_result = MagicMock()
                    mock_result.success = False
                    middleware.supabase_auth.verify_token = AsyncMock(return_value=mock_result)
                    
                    # Mock MCP token validation to fail
                    middleware.token_validator.validate_token = AsyncMock(
                        side_effect=TokenValidationError("Invalid token")
                    )
                    
                    result = await middleware._authenticate_request(mock_request, 'frontend')
                    assert result is None

    @pytest.mark.asyncio
    async def test_dispatch_token_validation_error(self, middleware, mock_request):
        """Test dispatch handles token validation errors"""
        mock_request.headers = {"authorization": "Bearer invalid-token"}
        
        with patch.object(middleware, '_authenticate_request') as mock_auth:
            mock_auth.side_effect = TokenValidationError("Token expired")
            
            response = await middleware.dispatch(mock_request, lambda r: Response())
            
            assert response.status_code == 401
            assert isinstance(response, JSONResponse)

    @pytest.mark.asyncio
    async def test_dispatch_rate_limit_error(self, middleware, mock_request):
        """Test dispatch handles rate limit errors"""
        mock_request.headers = {"authorization": "Bearer valid-token"}
        
        with patch.object(middleware, '_authenticate_request') as mock_auth:
            mock_auth.side_effect = RateLimitError("Rate limit exceeded")
            
            response = await middleware.dispatch(mock_request, lambda r: Response())
            
            assert response.status_code == 401
            assert isinstance(response, JSONResponse)

    @pytest.mark.asyncio
    async def test_validate_api_token_success(self, middleware):
        """Test successful API token validation"""
        payload = {
            "user_id": "test-user",
            "token_id": "tok_123",
            "type": "api_token",
            "scopes": ["read:tasks"],
            "exp": datetime.utcnow() + timedelta(hours=1)
        }
        token = pyjwt.encode(payload, "test-jwt-secret", algorithm="HS256")
        
        with patch('fastmcp.auth.middleware.dual_auth_middleware.JWTService') as mock_jwt_service:
            mock_service = MagicMock()
            mock_jwt_service.return_value = mock_service
            mock_service.verify_token.return_value = payload
            
            result = await middleware._validate_api_token(token)
            
            assert result is not None
            assert result['user_id'] == 'test-user'
            assert result['auth_method'] == 'api_token'
            assert result['token_id'] == 'tok_123'

    @pytest.mark.asyncio
    async def test_validate_local_jwt_supabase_token(self, middleware):
        """Test local JWT validation with Supabase token"""
        payload = {
            "sub": "supabase-user-123",
            "email": "user@example.com",
            "aud": "authenticated",
            "exp": datetime.utcnow() + timedelta(hours=1)
        }
        token = pyjwt.encode(payload, "test-supabase-secret", algorithm="HS256")
        
        result = await middleware._validate_local_jwt(token)
        
        assert result is not None
        assert result['user_id'] == 'supabase-user-123'
        assert result['email'] == 'user@example.com'
        assert result['auth_method'] == 'local_jwt'
        assert result['jwt_secret_used'] == 'SUPABASE_JWT_SECRET'

    def test_create_auth_error_response_mcp(self, middleware):
        """Test error response creation for MCP requests"""
        response = middleware._create_auth_error_response("mcp", "Invalid token")
        
        assert response.status_code == 401
        assert isinstance(response, JSONResponse)
        
        # Check the response content structure
        assert response.headers["content-type"] == "application/json"

    def test_create_auth_error_response_frontend(self, middleware):
        """Test error response creation for frontend requests"""
        response = middleware._create_auth_error_response("frontend", "Token expired")
        
        assert response.status_code == 401
        assert isinstance(response, JSONResponse)
        assert "WWW-Authenticate" in response.headers
        assert response.headers["WWW-Authenticate"] == "Bearer"

    @pytest.mark.asyncio
    async def test_dispatch_successful_auth(self, middleware, mock_request):
        """Test successful authentication flow"""
        mock_request.headers = {"authorization": "Bearer valid-token"}
        
        auth_result = {
            'user_id': 'authenticated-user',
            'auth_method': 'api_token',
            'email': 'user@example.com'
        }
        
        with patch.object(middleware, '_authenticate_request', return_value=auth_result):
            # Create a mock response
            expected_response = Response("OK")
            
            # Mock call_next
            async def call_next(request):
                # Verify that auth info was added to request state
                assert hasattr(request.state, 'user_id')
                assert request.state.user_id == 'authenticated-user'
                assert request.state.auth_type == 'unified'
                assert request.state.auth_info == auth_result
                return expected_response
            
            response = await middleware.dispatch(mock_request, call_next)
            assert response == expected_response

    def test_create_dual_auth_middleware(self):
        """Test middleware factory function"""
        middleware_class = create_dual_auth_middleware()
        assert middleware_class == DualAuthMiddleware