"""
Unit tests for DualAuthMiddleware.

This module tests the unified authentication middleware that handles
multiple authentication methods (Supabase JWT, local JWT, MCP tokens).
"""

import pytest
import os
import uuid
from unittest.mock import Mock, MagicMock, AsyncMock, patch
from datetime import datetime, timedelta
from starlette.requests import Request
from starlette.responses import Response, JSONResponse
from starlette.datastructures import Headers, QueryParams, URL
from fastmcp.auth.middleware.dual_auth_middleware import DualAuthMiddleware, create_dual_auth_middleware
from fastmcp.auth.token_validator import TokenValidationError, RateLimitError


class TestDualAuthMiddleware:
    """Test suite for DualAuthMiddleware."""
    
    @pytest.fixture
    def mock_app(self):
        """Create a mock ASGI app."""
        return MagicMock()
    
    @pytest.fixture
    def middleware(self, mock_app):
        """Create a DualAuthMiddleware instance."""
        return DualAuthMiddleware(mock_app)
    
    @pytest.fixture
    def mock_request(self):
        """Create a mock request with common attributes."""
        request = Mock(spec=Request)
        request.url = Mock()
        request.url.path = "/api/v2/test"
        request.method = "GET"
        request.headers = Headers({})
        request.cookies = {}
        request.query_params = QueryParams()
        request.state = Mock()
        return request
    
    @pytest.fixture
    def mock_call_next(self):
        """Create a mock call_next function."""
        async def call_next(request):
            return Response("OK", status_code=200)
        return AsyncMock(side_effect=call_next)
    
    # Request Type Detection Tests
    
    def test_detect_request_type_mcp_path(self, middleware, mock_request):
        """Test detecting MCP request by path."""
        mock_request.url.path = "/mcp/tools/list"
        result = middleware._detect_request_type(mock_request)
        assert result == 'mcp'
    
    def test_detect_request_type_mcp_header(self, middleware, mock_request):
        """Test detecting MCP request by protocol header."""
        mock_request.headers = Headers({'mcp-protocol-version': '1.0'})
        result = middleware._detect_request_type(mock_request)
        assert result == 'mcp'
    
    def test_detect_request_type_frontend_api_v2(self, middleware, mock_request):
        """Test detecting frontend request by API v2 path."""
        mock_request.url.path = "/api/v2/tasks"
        result = middleware._detect_request_type(mock_request)
        assert result == 'frontend'
    
    def test_detect_request_type_frontend_browser(self, middleware, mock_request):
        """Test detecting frontend request by browser user agent."""
        mock_request.headers = Headers({'user-agent': 'Mozilla/5.0 Chrome/91.0'})
        mock_request.url.path = "/dashboard"
        result = middleware._detect_request_type(mock_request)
        assert result == 'frontend'
    
    def test_detect_request_type_unknown(self, middleware, mock_request):
        """Test detecting unknown request type."""
        mock_request.url.path = "/random/path"
        result = middleware._detect_request_type(mock_request)
        assert result == 'unknown'
    
    # Authentication Skip Tests
    
    def test_should_skip_auth_health_endpoint(self, middleware, mock_request):
        """Test skipping auth for health endpoint."""
        mock_request.url.path = "/health"
        result = middleware._should_skip_auth(mock_request)
        assert result is True
    
    def test_should_skip_auth_docs_endpoint(self, middleware, mock_request):
        """Test skipping auth for ai_docs endpoint."""
        mock_request.url.path = "/ai_docs"
        result = middleware._should_skip_auth(mock_request)
        assert result is True
    
    def test_should_skip_auth_static_path(self, middleware, mock_request):
        """Test skipping auth for static file paths."""
        mock_request.url.path = "/static/styles.css"
        result = middleware._should_skip_auth(mock_request)
        assert result is True
    
    @patch.dict(os.environ, {"PRODUCTION": "false"})
    def test_should_not_skip_auth_regular_path(self, middleware, mock_request):
        """Test not skipping auth for regular paths."""
        mock_request.url.path = "/api/v2/tasks"
        result = middleware._should_skip_auth(mock_request)
        assert result is False
    
    # Token Extraction Tests
    
    def test_extract_token_from_bearer_header(self, middleware, mock_request):
        """Test extracting token from Bearer authorization header."""
        mock_request.headers = Headers({'authorization': 'Bearer test_token_123'})
        result = middleware._extract_token(mock_request)
        assert result == 'test_token_123'
    
    def test_extract_token_from_token_header(self, middleware, mock_request):
        """Test extracting token from Token authorization header."""
        mock_request.headers = Headers({'authorization': 'Token test_token_456'})
        result = middleware._extract_token(mock_request)
        assert result == 'test_token_456'
    
    def test_extract_token_from_custom_header(self, middleware, mock_request):
        """Test extracting token from custom MCP header."""
        mock_request.headers = Headers({'x-mcp-token': 'mcp_token_789'})
        result = middleware._extract_token(mock_request)
        assert result == 'mcp_token_789'
    
    def test_extract_token_from_cookie(self, middleware, mock_request):
        """Test extracting token from cookie."""
        mock_request.cookies = {'access_token': 'cookie_token_abc'}
        result = middleware._extract_token(mock_request)
        assert result == 'cookie_token_abc'
    
    def test_extract_token_from_query_param(self, middleware, mock_request):
        """Test extracting token from query parameter (with warning)."""
        mock_request.query_params = QueryParams({'token': 'query_token_xyz'})
        with patch('fastmcp.auth.middleware.dual_auth_middleware.logger') as mock_logger:
            result = middleware._extract_token(mock_request)
            assert result == 'query_token_xyz'
            mock_logger.warning.assert_called_once()
    
    def test_extract_token_none_when_missing(self, middleware, mock_request):
        """Test returning None when no token is found."""
        result = middleware._extract_token(mock_request)
        assert result is None
    
    # Authentication Tests
    
    @pytest.mark.asyncio
    @patch.dict(os.environ, {"JWT_SECRET_KEY": "test_secret"})
    async def test_validate_api_token_success(self, middleware):
        """Test successful API token validation."""
        with patch('fastmcp.auth.domain.services.jwt_service.JWTService') as MockJWTService:
            mock_jwt_service = MockJWTService.return_value
            mock_jwt_service.verify_token.return_value = {
                'user_id': 'user_123',
                'token_id': 'token_abc',
                'type': 'api_token',
                'email': 'test@example.com',
                'scopes': ['read', 'write']
            }
            
            result = await middleware._validate_api_token('eyJ_test_token')
            
            assert result is not None
            assert result['user_id'] == 'user_123'
            assert result['auth_method'] == 'api_token'
            assert result['token_id'] == 'token_abc'
    
    @pytest.mark.asyncio
    @patch.dict(os.environ, {})
    async def test_validate_api_token_no_secret(self, middleware):
        """Test API token validation fails when JWT_SECRET_KEY is not set."""
        result = await middleware._validate_api_token('eyJ_test_token')
        assert result is None
    
    @pytest.mark.asyncio
    async def test_validate_local_jwt_supabase_secret(self, middleware):
        """Test local JWT validation with Supabase secret."""
        with patch.dict(os.environ, {"SUPABASE_JWT_SECRET": "supabase_secret"}):
            with patch('jwt.decode') as mock_decode:
                mock_decode.return_value = {
                    'sub': 'user_456',
                    'email': 'user@example.com',
                    'roles': ['user']
                }
                
                result = await middleware._validate_local_jwt('eyJ_supabase_token')
                
                assert result is not None
                assert result['user_id'] == 'user_456'
                assert result['auth_method'] == 'local_jwt'
                assert result['jwt_secret_used'] == 'SUPABASE_JWT_SECRET'
    
    @pytest.mark.asyncio
    async def test_authenticate_request_no_token(self, middleware, mock_request):
        """Test authentication returns None when no token is present."""
        result = await middleware._authenticate_request(mock_request, 'frontend')
        assert result is None
    
    @pytest.mark.asyncio
    async def test_authenticate_request_supabase_success(self, middleware, mock_request):
        """Test successful authentication with Supabase token."""
        mock_request.headers = Headers({'authorization': 'Bearer test_token'})
        
        # Create a mock Supabase auth service and set it on middleware
        mock_supabase_auth = Mock()
        middleware.supabase_auth = mock_supabase_auth
        
        mock_result = Mock()
        mock_result.success = True
        mock_result.user = Mock(id='user_789', email='test@example.com')
        mock_supabase_auth.verify_token = AsyncMock(return_value=mock_result)
        
        result = await middleware._authenticate_request(mock_request, 'frontend')
        
        assert result is not None
        assert result['user_id'] == 'user_789'
        assert result['email'] == 'test@example.com'
        assert result['auth_method'] == 'supabase'
    
    @pytest.mark.asyncio
    async def test_authenticate_request_mcp_token_success(self, middleware, mock_request):
        """Test successful authentication with MCP token."""
        mock_request.headers = Headers({'x-mcp-token': 'mcp_token_xyz'})
        
        with patch.object(middleware.token_validator, 'validate_token') as mock_validate:
            mock_token_info = Mock()
            mock_token_info.user_id = 'user_mcp_123'
            mock_token_info.created_at = datetime.now()
            mock_token_info.expires_at = datetime.now() + timedelta(hours=1)
            mock_validate.return_value = mock_token_info
            
            result = await middleware._authenticate_request(mock_request, 'mcp')
            
            assert result is not None
            assert result['user_id'] == 'user_mcp_123'
            assert result['auth_method'] == 'mcp_token'
    
    # Dispatch Tests
    
    @pytest.mark.asyncio
    async def test_dispatch_skip_auth_path(self, middleware, mock_request, mock_call_next):
        """Test dispatch skips authentication for allowed paths."""
        mock_request.url.path = "/health"
        
        response = await middleware.dispatch(mock_request, mock_call_next)
        
        assert response.status_code == 200
        mock_call_next.assert_called_once_with(mock_request)
    
    @pytest.mark.asyncio
    @patch.dict(os.environ, {"PRODUCTION": "true"})
    async def test_dispatch_with_mock_token_user(self, middleware, mock_request, mock_call_next):
        """Test dispatch with mock JWT token containing user ID."""
        import jwt
        from datetime import datetime, timezone, timedelta
        
        # Create mock JWT token with user ID
        mock_user_id = "mock-test-user-" + str(uuid.uuid4())
        payload = {
            "sub": mock_user_id,  # User ID in 'sub' claim
            "exp": int((datetime.now(timezone.utc) + timedelta(hours=1)).timestamp())
        }
        mock_token = jwt.encode(payload, "test-secret", algorithm="HS256")
        
        mock_request.url.path = "/api/test"
        mock_request.headers = Headers({'authorization': f'Bearer {mock_token}'})
        
        # Mock the JWT validation to accept our test token
        with patch('jwt.decode') as mock_decode:
            mock_decode.return_value = payload
            response = await middleware.dispatch(mock_request, mock_call_next)
        
        assert response.status_code == 200
        assert mock_request.state.user_id == mock_user_id
        assert mock_request.state.auth_type == 'local_jwt'
    
    @pytest.mark.asyncio
    @patch.dict(os.environ, {"PRODUCTION": "false"})
    async def test_dispatch_authenticated_request(self, middleware, mock_request, mock_call_next):
        """Test dispatch with successful authentication."""
        mock_request.headers = Headers({'authorization': 'Bearer test_token'})
        
        with patch.object(middleware, '_authenticate_request') as mock_auth:
            mock_auth.return_value = {
                'user_id': 'auth_user_123',
                'auth_method': 'supabase',
                'email': 'user@example.com'
            }
            
            response = await middleware.dispatch(mock_request, mock_call_next)
            
            assert response.status_code == 200
            assert mock_request.state.user_id == 'auth_user_123'
            assert mock_request.state.auth_type == 'supabase'
    
    @pytest.mark.asyncio
    @patch.dict(os.environ, {"PRODUCTION": "false"})
    async def test_dispatch_token_validation_error(self, middleware, mock_request, mock_call_next):
        """Test dispatch handles token validation errors."""
        mock_request.headers = Headers({'authorization': 'Bearer invalid_token'})
        
        with patch.object(middleware, '_authenticate_request') as mock_auth:
            mock_auth.side_effect = TokenValidationError("Invalid token")
            
            response = await middleware.dispatch(mock_request, mock_call_next)
            
            assert response.status_code == 401
            assert isinstance(response, JSONResponse)
    
    @pytest.mark.asyncio
    @patch.dict(os.environ, {"PRODUCTION": "false"})
    async def test_dispatch_rate_limit_error(self, middleware, mock_request, mock_call_next):
        """Test dispatch handles rate limit errors."""
        mock_request.headers = Headers({'authorization': 'Bearer test_token'})
        
        with patch.object(middleware, '_authenticate_request') as mock_auth:
            mock_auth.side_effect = RateLimitError("Too many requests")
            
            response = await middleware.dispatch(mock_request, mock_call_next)
            
            assert response.status_code == 401
            assert isinstance(response, JSONResponse)
    
    # Error Response Tests
    
    def test_create_auth_error_response_mcp(self, middleware):
        """Test creating MCP-style error response."""
        response = middleware._create_auth_error_response('mcp', 'Auth failed')
        
        assert response.status_code == 401
        assert isinstance(response, JSONResponse)
        # Check the response would contain JSON-RPC error format
        assert response.headers['Content-Type'] == 'application/json'
    
    def test_create_auth_error_response_frontend(self, middleware):
        """Test creating frontend-style error response."""
        response = middleware._create_auth_error_response('frontend', 'Auth failed')
        
        assert response.status_code == 401
        assert isinstance(response, JSONResponse)
        assert response.headers['WWW-Authenticate'] == 'Bearer'
    
    # Factory Function Test
    
    def test_create_dual_auth_middleware_factory(self):
        """Test the factory function creates middleware instance."""
        middleware_class = create_dual_auth_middleware()
        assert middleware_class == DualAuthMiddleware