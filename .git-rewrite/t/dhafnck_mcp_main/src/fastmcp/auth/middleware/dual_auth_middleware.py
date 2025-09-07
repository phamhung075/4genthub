"""
Unified Authentication Middleware

This middleware provides a single, unified authentication approach where
any valid token (Supabase JWT, local JWT, or MCP token) authenticates 
the user for ALL request types.

Key Features:
- Single token authentication for both frontend and MCP requests
- Automatic token extraction from multiple sources (headers, cookies, etc.)
- Fallback chain: Supabase JWT → Local JWT → MCP Token
- No need to pass multiple tokens or handle different auth flows

The middleware extracts tokens from:
1. Authorization header (Bearer or Token prefix)
2. Custom MCP headers (x-mcp-token, mcp-token)
3. Cookies (access_token for browser requests)
4. Query parameters (for testing only, insecure)
"""

import logging
import json
from typing import Optional, Dict, Any, Union
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import Response, JSONResponse
from starlette.types import ASGIApp

from ..infrastructure.supabase_auth import SupabaseAuthService
from ..token_validator import TokenValidator, TokenValidationError, RateLimitError
from ..supabase_client import TokenInfo

logger = logging.getLogger(__name__)


class DualAuthMiddleware(BaseHTTPMiddleware):
    """
    Unified authentication middleware that accepts a single token
    for all request types (frontend, MCP, API).
    
    Any valid token authenticates the user universally:
    - Supabase JWT tokens (from frontend login)
    - Local JWT tokens (for development/testing)
    - MCP generated tokens (for tool access)
    
    No need to pass different tokens for different endpoints.
    """
    
    def __init__(self, app: ASGIApp):
        super().__init__(app)
        self.supabase_auth = SupabaseAuthService()
        self.token_validator = TokenValidator()
        logger.info("Dual authentication middleware initialized")
    
    async def dispatch(self, request: Request, call_next) -> Response:
        """
        Process request and apply unified authentication.
        
        A single token authenticates for all request types.
        
        Args:
            request: Incoming HTTP request
            call_next: Next middleware in chain
            
        Returns:
            HTTP response
        """
        # Detect request type (for logging and error formatting only)
        request_type = self._detect_request_type(request)
        
        # Add debug logging
        logger.debug(f"🔍 UNIFIED AUTH: Processing {request.method} {request.url.path}")
        logger.debug(f"🔍 UNIFIED AUTH: Request type: {request_type} (for error formatting)")
        
        # Skip authentication for certain paths
        if self._should_skip_auth(request):
            logger.debug("🔍 UNIFIED AUTH: Skipping authentication for this path")
            return await call_next(request)
        
        try:
            # Apply unified authentication (single token for all requests)
            auth_result = await self._authenticate_request(request, request_type)
            
            if auth_result:
                # Add authentication info to request state
                request.state.user_id = auth_result.get('user_id')
                request.state.auth_type = auth_result.get('auth_method', 'unified')
                request.state.auth_info = auth_result
                
                logger.info(f"✅ UNIFIED AUTH: Authenticated user {auth_result.get('user_id')} with {auth_result.get('auth_method')} method")
            else:
                # No authentication found - may be allowed for some endpoints
                logger.debug("🔍 UNIFIED AUTH: No authentication token provided")
            
            # Continue to next middleware
            response = await call_next(request)
            return response
            
        except (TokenValidationError, RateLimitError) as e:
            logger.warning(f"❌ UNIFIED AUTH: Authentication failed: {e}")
            return self._create_auth_error_response(request_type, str(e))
        except Exception as e:
            logger.error(f"❌ UNIFIED AUTH: Unexpected error: {e}")
            return self._create_auth_error_response(request_type, "Authentication system error")
    
    def _detect_request_type(self, request: Request) -> str:
        """
        Detect whether this is a frontend or MCP request.
        
        Args:
            request: HTTP request
            
        Returns:
            Request type: 'frontend', 'mcp', or 'unknown'
        """
        path = request.url.path
        content_type = request.headers.get('content-type', '').lower()
        user_agent = request.headers.get('user-agent', '').lower()
        
        # MCP requests characteristics
        if path.startswith('/mcp'):
            return 'mcp'
        
        # Check for MCP protocol headers
        if 'mcp-protocol-version' in request.headers:
            return 'mcp'
        
        # Check for JSON-RPC content (MCP uses JSON-RPC)
        if 'application/json' in content_type and 'jsonrpc' in str(request.headers.get('accept', '')):
            return 'mcp'
        
        # Frontend API requests
        if path.startswith('/api/v2/'):
            return 'frontend'
        
        # Check user agent for browser-like requests
        browser_indicators = ['mozilla', 'chrome', 'safari', 'firefox', 'edge']
        if any(indicator in user_agent for indicator in browser_indicators):
            return 'frontend'
        
        # Default to frontend for HTTP API requests
        if path.startswith('/api/'):
            return 'frontend'
        
        return 'unknown'
    
    def _should_skip_auth(self, request: Request) -> bool:
        """
        Check if authentication should be skipped for this request.
        
        Args:
            request: HTTP request
            
        Returns:
            True if authentication should be skipped
        """
        skip_paths = [
            '/health',
            '/docs',
            '/redoc',
            '/openapi.json',
            '/favicon.ico',
            '/static/',
        ]
        
        path = request.url.path
        return any(path.startswith(skip_path) for skip_path in skip_paths)
    
    async def _authenticate_request(self, request: Request, request_type: str) -> Optional[Dict[str, Any]]:
        """
        Authenticate request with a single unified token approach.
        
        Any valid token (Supabase JWT or MCP token) authenticates the user
        for both frontend and MCP requests.
        
        Args:
            request: HTTP request
            request_type: Type of request ('frontend' or 'mcp')
            
        Returns:
            Authentication result or None
        """
        # Extract token from request (Bearer header, cookies, or custom headers)
        token = self._extract_token(request)
        
        if not token:
            logger.debug("🔍 UNIFIED AUTH: No token found in request")
            return None
        
        # Try to validate token with any available method
        # Priority: API Token (JWT_SECRET_KEY) > Supabase JWT > MCP Token
        
        # 1. Check if it's a JWT token and try API token validation first
        if token.startswith('eyJ'):  # JWT tokens start with this
            try:
                logger.debug("🔍 UNIFIED AUTH: Detected JWT token, trying API token validation first")
                
                # Decode without verification to check token structure
                import jwt as pyjwt
                try:
                    unverified_payload = pyjwt.decode(token, options={"verify_signature": False})
                    
                    # Check if it's an API token (has token_id claim)
                    if unverified_payload.get('token_id') or unverified_payload.get('type') == 'api_token':
                        logger.debug("🔍 UNIFIED AUTH: Token appears to be an API token, validating with JWT_SECRET_KEY")
                        auth_result = await self._validate_api_token(token)
                        if auth_result:
                            logger.info(f"✅ UNIFIED AUTH: API token validated for user {auth_result.get('user_id')}")
                            return auth_result
                except Exception as decode_error:
                    logger.debug(f"🔍 UNIFIED AUTH: Could not decode token for inspection: {decode_error}")
                
                # If not an API token or validation failed, try other JWT validation methods
                logger.debug("🔍 UNIFIED AUTH: Trying general local JWT validation")
                auth_result = await self._validate_local_jwt(token)
                if auth_result:
                    logger.info(f"✅ UNIFIED AUTH: Local JWT validated for user {auth_result.get('user_id')}")
                    return auth_result
            except Exception as e:
                logger.debug(f"🔍 UNIFIED AUTH: JWT validation failed: {e}")
        
        # 2. Try Supabase validation (for Supabase-issued tokens)
        try:
            logger.debug("🔍 UNIFIED AUTH: Trying Supabase validation")
            result = await self.supabase_auth.verify_token(token)
            if result.success and result.user:
                user_id = result.user.id if hasattr(result.user, 'id') else result.user.get('id')
                email = result.user.email if hasattr(result.user, 'email') else result.user.get('email')
                
                # CRITICAL: Check that we actually got a valid user_id
                if user_id:
                    logger.info(f"✅ UNIFIED AUTH: Supabase token validated for user {user_id}")
                    return {
                        'user_id': user_id,
                        'email': email,
                        'auth_method': 'supabase',
                        'user_data': result.user
                    }
                else:
                    logger.debug("🔍 UNIFIED AUTH: Supabase returned success but no user_id")
        except Exception as e:
            logger.debug(f"🔍 UNIFIED AUTH: Supabase validation failed: {e}")
        
        # 3. Try MCP token validation (for generated tokens)
        try:
            logger.debug("🔍 UNIFIED AUTH: Trying MCP token validation")
            client_info = {
                'user_agent': request.headers.get('user-agent', ''),
                'path': request.url.path,
                'method': request.method
            }
            
            token_info = await self.token_validator.validate_token(token, client_info)
            
            logger.info(f"✅ UNIFIED AUTH: MCP token validated for user {token_info.user_id}")
            return {
                'user_id': token_info.user_id,
                'auth_method': 'mcp_token',
                'token_info': token_info,
                'created_at': token_info.created_at.isoformat() if token_info.created_at else None,
                'expires_at': token_info.expires_at.isoformat() if token_info.expires_at else None
            }
        except Exception as e:
            logger.debug(f"🔍 UNIFIED AUTH: MCP token validation failed: {e}")
        
        # No valid authentication found
        logger.warning("❌ UNIFIED AUTH: All token validation methods failed")
        return None
    
    async def _authenticate_frontend_request(self, request: Request) -> Optional[Dict[str, Any]]:
        """
        Authenticate frontend request using Supabase cookies or Bearer token.
        
        Args:
            request: HTTP request
            
        Returns:
            Authentication result
        """
        # Try Bearer token first (for API calls)
        auth_header = request.headers.get('authorization', '')
        if auth_header.startswith('Bearer '):
            token = auth_header[7:].strip()
            logger.debug("🔍 FRONTEND AUTH: Using Bearer token")
            
            try:
                result = await self.supabase_auth.verify_token(token)
                if result.success and result.user:
                    user_id = result.user.id if hasattr(result.user, 'id') else result.user.get('id')
                    email = result.user.email if hasattr(result.user, 'email') else result.user.get('email')
                    
                    return {
                        'user_id': user_id,
                        'email': email,
                        'auth_method': 'supabase_bearer',
                        'user_data': result.user
                    }
            except Exception as e:
                logger.debug(f"🔍 FRONTEND AUTH: Bearer token failed: {e}")
        
        # Try cookies (for browser requests)
        cookies = request.cookies
        access_token = cookies.get('access_token')
        
        if access_token:
            logger.debug("🔍 FRONTEND AUTH: Using access_token cookie")
            
            try:
                result = await self.supabase_auth.verify_token(access_token)
                if result.success and result.user:
                    user_id = result.user.id if hasattr(result.user, 'id') else result.user.get('id')
                    email = result.user.email if hasattr(result.user, 'email') else result.user.get('email')
                    
                    return {
                        'user_id': user_id,
                        'email': email,
                        'auth_method': 'supabase_cookie',
                        'user_data': result.user
                    }
            except Exception as e:
                logger.debug(f"🔍 FRONTEND AUTH: Cookie authentication failed: {e}")
        
        # No valid authentication found
        logger.debug("🔍 FRONTEND AUTH: No valid authentication found")
        return None
    
    async def _authenticate_mcp_request(self, request: Request) -> Optional[Dict[str, Any]]:
        """
        Authenticate MCP request using generated tokens.
        
        Args:
            request: HTTP request
            
        Returns:
            Authentication result
        """
        # Extract token from various sources
        token = None
        
        # Check Authorization header
        auth_header = request.headers.get('authorization', '')
        if auth_header.startswith('Bearer '):
            token = auth_header[7:].strip()
        elif auth_header.startswith('Token '):
            token = auth_header[6:].strip()
        
        # Check custom headers
        if not token:
            token = request.headers.get('x-mcp-token') or request.headers.get('mcp-token')
        
        # Check query parameters (less secure, only for testing)
        if not token and 'token' in request.query_params:
            token = request.query_params['token']
            logger.warning("🔍 MCP AUTH: Using token from query parameter (insecure)")
        
        if not token:
            logger.debug("🔍 MCP AUTH: No token found in MCP request")
            return None
        
        logger.debug(f"🔍 MCP AUTH: Validating MCP token (first 20 chars): {token[:20]}...")
        
        # Special handling for JWT tokens (local development)
        if token.startswith('eyJ'):  # JWT tokens start with this
            logger.info("🔍 MCP AUTH: Detected JWT token, trying dual secret validation")
            
            # Try both JWT secrets to handle the mismatch between frontend and backend
            import os
            from ..domain.services.jwt_service import JWTService
            
            # Get both potential secrets
            jwt_secret = os.getenv("JWT_SECRET_KEY", "default-secret-key-change-in-production")
            supabase_jwt_secret = os.getenv("SUPABASE_JWT_SECRET")
            
            # List of secrets to try (prioritize SUPABASE_JWT_SECRET since frontend uses it)
            secrets_to_try = []
            if supabase_jwt_secret:
                secrets_to_try.append(("SUPABASE_JWT_SECRET", supabase_jwt_secret))
            if jwt_secret and jwt_secret != "default-secret-key-change-in-production":
                secrets_to_try.append(("JWT_SECRET_KEY", jwt_secret))
            
            # Try each secret until one works
            for secret_name, secret_value in secrets_to_try:
                try:
                    logger.debug(f"🔍 MCP AUTH: Trying JWT validation with {secret_name} (length: {len(secret_value)})")
                    jwt_service = JWTService(secret_key=secret_value)
                    
                    # Try multiple token types for compatibility
                    payload = None
                    for token_type in ["api_token", "access"]:
                        # For Supabase tokens, try with "authenticated" audience
                        if secret_name == "SUPABASE_JWT_SECRET":
                            try:
                                # Try decoding directly with PyJWT for Supabase tokens
                                import jwt as pyjwt
                                payload = pyjwt.decode(
                                    token,
                                    secret_value,
                                    algorithms=["HS256"],
                                    audience="authenticated",  # Supabase uses this audience
                                    options={"verify_iss": False}  # Skip issuer check for Supabase
                                )
                                if payload:
                                    logger.info(f"✅ MCP AUTH: Supabase JWT token validated with audience 'authenticated'")
                                    break
                            except Exception as supabase_error:
                                logger.debug(f"🔍 MCP AUTH: Supabase token validation failed: {supabase_error}")
                        
                        # Try standard validation for local tokens
                        try:
                            payload = jwt_service.verify_token(token, expected_type=token_type)
                            if payload:
                                logger.info(f"✅ MCP AUTH: JWT token validated with {secret_name} as {token_type} type")
                                break
                        except Exception as type_error:
                            logger.debug(f"🔍 MCP AUTH: Token type {token_type} failed with {secret_name}: {type_error}")
                            continue
                    
                    if payload:
                        # Extract user_id from either 'user_id' or 'sub' fields
                        user_id = payload.get('user_id') or payload.get('sub')
                        return {
                            'user_id': user_id,
                            'auth_method': 'local_jwt',
                            'jwt_secret_used': secret_name,
                            'token_id': payload.get('token_id') or payload.get('jti'),
                            'scopes': payload.get('scopes', []),
                            'type': payload.get('type', 'api_token'),
                            'email': payload.get('email'),
                            'roles': payload.get('roles', [])
                        }
                        
                except Exception as jwt_error:
                    logger.debug(f"🔍 MCP AUTH: JWT validation with {secret_name} failed: {jwt_error}")
                    continue
            
            logger.warning("🔍 MCP AUTH: All JWT secret validation attempts failed, will try other methods")
            # Fall through to try other validation methods
        
        try:
            # Validate token using TokenValidator (for Supabase tokens)
            client_info = {
                'user_agent': request.headers.get('user-agent', ''),
                'path': request.url.path,
                'method': request.method
            }
            
            token_info = await self.token_validator.validate_token(token, client_info)
            
            return {
                'user_id': token_info.user_id,
                'auth_method': 'mcp_token',
                'token_info': token_info,
                'created_at': token_info.created_at.isoformat() if token_info.created_at else None,
                'expires_at': token_info.expires_at.isoformat() if token_info.expires_at else None
            }
            
        except Exception as e:
            logger.debug(f"🔍 MCP AUTH: Token validation failed: {e}")
            raise
    
    def _extract_token(self, request: Request) -> Optional[str]:
        """
        Extract token from various sources in the request.
        
        Priority order:
        1. Authorization header (Bearer or Token)
        2. Custom MCP headers
        3. Cookies (for browser requests)
        4. Query parameters (only for testing, insecure)
        
        Args:
            request: HTTP request
            
        Returns:
            Token string or None
        """
        # 1. Check Authorization header
        auth_header = request.headers.get('authorization', '')
        if auth_header.startswith('Bearer '):
            return auth_header[7:].strip()
        elif auth_header.startswith('Token '):
            return auth_header[6:].strip()
        
        # 2. Check custom headers
        token = request.headers.get('x-mcp-token') or request.headers.get('mcp-token')
        if token:
            return token
        
        # 3. Check cookies (for browser requests)
        access_token = request.cookies.get('access_token')
        if access_token:
            return access_token
        
        # 4. Check query parameters (insecure, only for testing)
        if 'token' in request.query_params:
            logger.warning("⚠️ UNIFIED AUTH: Using token from query parameter (insecure)")
            return request.query_params['token']
        
        return None
    
    async def _validate_api_token(self, token: str) -> Optional[Dict[str, Any]]:
        """
        Validate an API token generated by our token management system.
        
        Args:
            token: JWT token string
            
        Returns:
            Authentication result or None
        """
        import os
        from ..domain.services.jwt_service import JWTService
        
        # API tokens are signed with JWT_SECRET_KEY
        jwt_secret = os.getenv("JWT_SECRET_KEY")
        if not jwt_secret:
            logger.error("JWT_SECRET_KEY not configured")
            return None
        
        try:
            jwt_service = JWTService(secret_key=jwt_secret)
            
            # API tokens have type 'api_token'
            payload = jwt_service.verify_token(token, expected_type="api_token")
            if payload:
                user_id = payload.get('user_id') or payload.get('sub')
                return {
                    'user_id': user_id,
                    'auth_method': 'api_token',
                    'jwt_secret_used': 'JWT_SECRET_KEY',
                    'token_id': payload.get('token_id') or payload.get('jti'),
                    'scopes': payload.get('scopes', []),
                    'type': 'api_token',
                    'email': payload.get('email'),
                    'roles': payload.get('roles', [])
                }
        except Exception as e:
            logger.debug(f"API token validation failed: {e}")
        
        return None
    
    async def _validate_local_jwt(self, token: str) -> Optional[Dict[str, Any]]:
        """
        Validate a local JWT token using available secrets.
        
        Args:
            token: JWT token string
            
        Returns:
            Authentication result or None
        """
        import os
        from ..domain.services.jwt_service import JWTService
        
        # Get both potential secrets
        jwt_secret = os.getenv("JWT_SECRET_KEY", "default-secret-key-change-in-production")
        supabase_jwt_secret = os.getenv("SUPABASE_JWT_SECRET")
        
        # List of secrets to try
        secrets_to_try = []
        if supabase_jwt_secret:
            secrets_to_try.append(("SUPABASE_JWT_SECRET", supabase_jwt_secret))
        if jwt_secret and jwt_secret != "default-secret-key-change-in-production":
            secrets_to_try.append(("JWT_SECRET_KEY", jwt_secret))
        
        # Try each secret until one works
        for secret_name, secret_value in secrets_to_try:
            try:
                jwt_service = JWTService(secret_key=secret_value)
                
                # Special handling for Supabase tokens
                if secret_name == "SUPABASE_JWT_SECRET":
                    try:
                        import jwt as pyjwt
                        payload = pyjwt.decode(
                            token,
                            secret_value,
                            algorithms=["HS256"],
                            audience="authenticated",
                            options={"verify_iss": False}
                        )
                        if payload:
                            user_id = payload.get('user_id') or payload.get('sub')
                            return {
                                'user_id': user_id,
                                'auth_method': 'local_jwt',
                                'jwt_secret_used': secret_name,
                                'email': payload.get('email'),
                                'roles': payload.get('roles', [])
                            }
                    except:
                        pass
                
                # Try standard validation
                for token_type in ["api_token", "access"]:
                    try:
                        payload = jwt_service.verify_token(token, expected_type=token_type)
                        if payload:
                            user_id = payload.get('user_id') or payload.get('sub')
                            return {
                                'user_id': user_id,
                                'auth_method': 'local_jwt',
                                'jwt_secret_used': secret_name,
                                'token_id': payload.get('token_id') or payload.get('jti'),
                                'scopes': payload.get('scopes', []),
                                'type': payload.get('type', 'api_token'),
                                'email': payload.get('email'),
                                'roles': payload.get('roles', [])
                            }
                    except:
                        continue
                        
            except Exception as e:
                logger.debug(f"JWT validation with {secret_name} failed: {e}")
                continue
        
        return None
    
    def _create_auth_error_response(self, request_type: str, error_message: str) -> Response:
        """
        Create appropriate error response based on request type.
        
        Args:
            request_type: Type of request
            error_message: Error message
            
        Returns:
            Error response
        """
        if request_type == 'mcp':
            # MCP JSON-RPC error response
            error_data = {
                "jsonrpc": "2.0",
                "error": {
                    "code": -32001,  # Custom auth error code
                    "message": "Authentication failed",
                    "data": {
                        "detail": error_message,
                        "auth_type": "mcp_token_required"
                    }
                },
                "id": None
            }
            return JSONResponse(
                content=error_data,
                status_code=401,
                headers={"Content-Type": "application/json"}
            )
        else:
            # Standard HTTP error response for frontend
            return JSONResponse(
                content={
                    "detail": error_message,
                    "auth_type": "bearer_or_cookie_required"
                },
                status_code=401,
                headers={"WWW-Authenticate": "Bearer"}
            )


def create_dual_auth_middleware():
    """
    Factory function to create dual authentication middleware.
    
    Returns:
        Configured middleware class
    """
    return DualAuthMiddleware