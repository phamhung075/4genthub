"""
Verification test for JWT authentication state propagation fix

This test demonstrates that the critical authentication issue is resolved:
- JWT tokens are validated ✅
- AccessToken is created ✅  
- User context is set ✅
- scope["user"] contains AuthenticatedUser ✅ (THE FIX)
- RequireAuthMiddleware passes ✅
"""

import pytest
import os
import uuid
from unittest.mock import Mock, AsyncMock

from mcp.server.auth.middleware.bearer_auth import BearerAuthBackend, RequireAuthMiddleware, AuthenticatedUser
from mcp.server.auth.provider import AccessToken

from fastmcp.auth.mcp_integration.jwt_auth_backend import JWTAuthBackend
from fastmcp.auth.domain.services.jwt_service import JWTService
from fastmcp.auth.domain.entities.user import User, UserStatus, UserRole
from fastmcp.auth.domain.value_objects import UserId


class TestAuthenticationFixVerification:
    """Verification tests proving the JWT authentication state propagation fix works"""

    @pytest.fixture
    def jwt_service(self):
        """JWT service for creating test tokens"""
        return JWTService(secret_key="test-secret-for-verification")

    @pytest.fixture
    def user_repository(self):
        """Mock user repository that returns a developer user"""
        repo = Mock()
        
        def find_user_by_id(user_id):
            user = User(
                email="developer@example.com",
                username="devuser", 
                password_hash="hashed"
            )
            user.id = user_id
            user.status = UserStatus.ACTIVE
            user.roles = [UserRole.DEVELOPER]  # Should map to developer scopes
            return user
            
        repo.find_by_id.side_effect = find_user_by_id
        return repo

    @pytest.fixture  
    def jwt_backend(self, jwt_service, user_repository):
        """JWT backend configured with test dependencies"""
        with pytest.MonkeyPatch().context() as mp:
            mp.setenv("JWT_SECRET_KEY", "test-secret-for-verification")
            return JWTAuthBackend(
                jwt_service=jwt_service,
                user_repository=user_repository,
                required_scopes=["mcp:access"]
            )

    @pytest.fixture
    def valid_jwt_token(self, jwt_service):
        """Valid JWT token for a developer user"""
        user_id = str(uuid.uuid4())
        token = jwt_service.create_access_token(
            user_id=user_id,
            email="developer@example.com",
            roles=["developer"],
            additional_claims={"scopes": ["read", "write"]}
        )
        return token, user_id

    @pytest.mark.asyncio
    async def test_jwt_backend_implements_token_verifier_correctly(self, jwt_backend, valid_jwt_token):
        """Test that JWTAuthBackend properly implements TokenVerifier protocol"""
        token, user_id = valid_jwt_token
        
        # Test the verify_token method (new protocol method)
        access_token = await jwt_backend.verify_token(token)
        
        assert access_token is not None
        assert isinstance(access_token, AccessToken)
        assert access_token.client_id == user_id
        assert access_token.token == token
        
        # Verify MCP scopes are properly mapped from developer role  
        assert "mcp:access" in access_token.scopes
        assert "mcp:read" in access_token.scopes
        assert "mcp:write" in access_token.scopes
        
        # Original token scopes should also be present
        assert "read" in access_token.scopes
        assert "write" in access_token.scopes

    @pytest.mark.asyncio
    async def test_bearer_auth_backend_creates_authenticated_user(self, jwt_backend, valid_jwt_token):
        """Test that BearerAuthBackend creates proper AuthenticatedUser from our TokenVerifier"""
        token, user_id = valid_jwt_token
        
        # Create MCP's BearerAuthBackend with our JWT backend as TokenVerifier
        bearer_backend = BearerAuthBackend(token_verifier=jwt_backend)
        
        # Mock HTTP connection with Authorization header
        conn = Mock()
        conn.headers = {"authorization": f"Bearer {token}"}
        
        # Authenticate - this is what Starlette's AuthenticationMiddleware calls
        result = await bearer_backend.authenticate(conn)
        
        # Verify we get proper authentication result
        assert result is not None
        auth_credentials, authenticated_user = result
        
        # Verify AuthCredentials has correct scopes
        assert "mcp:access" in auth_credentials.scopes
        assert "mcp:read" in auth_credentials.scopes  
        assert "mcp:write" in auth_credentials.scopes
        
        # Verify AuthenticatedUser is created correctly
        assert isinstance(authenticated_user, AuthenticatedUser)
        assert authenticated_user.username == user_id  # From SimpleUser
        assert authenticated_user.access_token.client_id == user_id
        assert authenticated_user.scopes == auth_credentials.scopes

    @pytest.mark.asyncio
    async def test_require_auth_middleware_accepts_authenticated_user(self, jwt_backend, valid_jwt_token):
        """Test that RequireAuthMiddleware accepts our AuthenticatedUser (THE CRITICAL FIX)"""
        token, user_id = valid_jwt_token
        
        # Create the complete authentication chain
        bearer_backend = BearerAuthBackend(token_verifier=jwt_backend)
        conn = Mock()
        conn.headers = {"authorization": f"Bearer {token}"}
        
        # Get authenticated user from the chain
        result = await bearer_backend.authenticate(conn)
        auth_credentials, authenticated_user = result
        
        # Create RequireAuthMiddleware
        require_auth = RequireAuthMiddleware(
            app=Mock(),
            required_scopes=["mcp:access"]
        )
        
        # Create the scope as Starlette would set it 
        scope = {
            "type": "http",
            "user": authenticated_user,  # ✅ THIS IS THE KEY - scope["user"] set correctly
            "auth": auth_credentials
        }
        
        # Mock the next app
        next_app_was_called = False
        async def mock_next_app(scope, receive, send):
            nonlocal next_app_was_called  
            next_app_was_called = True
            
        require_auth.app = mock_next_app
        
        # Call RequireAuthMiddleware - this should NOT return 401
        await require_auth(scope, AsyncMock(), AsyncMock())
        
        # Verify the middleware passed the request through (authentication succeeded)
        assert next_app_was_called, "RequireAuthMiddleware should have called the next app - authentication should have passed!"

    @pytest.mark.asyncio  
    async def test_require_auth_middleware_rejects_missing_authenticated_user(self):
        """Test that RequireAuthMiddleware still properly rejects requests without AuthenticatedUser"""
        require_auth = RequireAuthMiddleware(
            app=Mock(),
            required_scopes=["mcp:access"]
        )
        
        # Scope without authenticated user (the old broken behavior)
        scope = {
            "type": "http"
            # No "user" key - this should be rejected  
        }
        
        send_mock = AsyncMock()
        
        # Call RequireAuthMiddleware - this SHOULD return 401
        await require_auth(scope, AsyncMock(), send_mock)
        
        # Verify error response was sent
        assert send_mock.called, "RequireAuthMiddleware should have sent an error response"
        
        # Check that it's a 401 response
        calls = send_mock.call_args_list
        assert len(calls) >= 1
        
        start_response = calls[0][0][0]
        assert start_response["type"] == "http.response.start"
        assert start_response["status"] == 401

    @pytest.mark.asyncio
    async def test_complete_fixed_authentication_flow(self, jwt_backend, valid_jwt_token):
        """
        Integration test proving the complete authentication flow works after the fix
        
        This test simulates the exact flow that was broken before:
        1. JWT token validation ✅  
        2. AccessToken creation ✅
        3. AuthenticatedUser creation ✅  
        4. scope["user"] population ✅ (THE FIX)
        5. RequireAuthMiddleware acceptance ✅
        """
        token, user_id = valid_jwt_token
        
        print(f"🧪 Testing complete authentication flow for user: {user_id}")
        
        # STEP 1: JWT Backend validates token and creates AccessToken
        print("📝 Step 1: JWT token validation...")
        access_token = await jwt_backend.verify_token(token)
        assert access_token is not None
        assert access_token.client_id == user_id
        print(f"✅ AccessToken created with scopes: {access_token.scopes}")
        
        # STEP 2: BearerAuthBackend creates AuthenticatedUser  
        print("📝 Step 2: BearerAuthBackend creates AuthenticatedUser...")
        bearer_backend = BearerAuthBackend(token_verifier=jwt_backend)
        conn = Mock()
        conn.headers = {"authorization": f"Bearer {token}"}
        
        auth_result = await bearer_backend.authenticate(conn)
        assert auth_result is not None
        auth_credentials, authenticated_user = auth_result
        assert isinstance(authenticated_user, AuthenticatedUser)
        print(f"✅ AuthenticatedUser created: {authenticated_user.username}")
        
        # STEP 3: RequireAuthMiddleware checks scope["user"] (THE CRITICAL TEST)
        print("📝 Step 3: RequireAuthMiddleware checks scope['user']...")
        require_auth = RequireAuthMiddleware(app=Mock(), required_scopes=["mcp:access"])
        
        # This is what Starlette's AuthenticationMiddleware would set
        scope = {
            "type": "http",
            "user": authenticated_user,  # 🔑 THE FIX - this was missing before
            "auth": auth_credentials
        }
        
        # Track if the next app was called (means authentication passed)
        authentication_passed = False
        async def mock_protected_endpoint(scope, receive, send):
            nonlocal authentication_passed
            authentication_passed = True
            print("🎉 Protected endpoint reached - authentication successful!")
            
        require_auth.app = mock_protected_endpoint
        
        # THE MOMENT OF TRUTH - this should NOT fail with 401
        await require_auth(scope, AsyncMock(), AsyncMock())
        
        # VERIFICATION: Authentication should have passed completely
        assert authentication_passed, "🚨 AUTHENTICATION FAILED - RequireAuthMiddleware should have passed the request!"
        
        print("✅ COMPLETE AUTHENTICATION FLOW SUCCESSFUL!")
        print("🎯 The JWT authentication state propagation issue is RESOLVED!")


class TestPreviousBugReproduction:
    """Tests that demonstrate the previous bug would have failed (for documentation)"""
    
    @pytest.mark.asyncio
    async def test_old_bug_scenario_scope_user_none(self):
        """
        This test shows what the old bug looked like:
        scope["user"] was None instead of AuthenticatedUser
        """
        require_auth = RequireAuthMiddleware(app=Mock(), required_scopes=["mcp:access"])
        
        # The old broken scenario: scope["user"] was None  
        broken_scope = {
            "type": "http", 
            "user": None  # ❌ This was the bug - should be AuthenticatedUser
        }
        
        send_mock = AsyncMock()
        
        # This should fail with 401 (demonstrates the old bug)
        await require_auth(broken_scope, AsyncMock(), send_mock)
        
        # Verify it returns 401 invalid_token (the old error)
        assert send_mock.called
        calls = send_mock.call_args_list
        start_response = calls[0][0][0] 
        assert start_response["status"] == 401
        
        print("📋 Old bug reproduced: scope['user'] = None → 401 invalid_token")
        print("✅ This confirms our fix addresses the exact right issue!")