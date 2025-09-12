"""
Unit tests for JWT Authentication Middleware

Tests JWT token extraction, user context management, and middleware functionality.
"""

import pytest
from unittest.mock import Mock, patch
import jwt
from datetime import datetime, timedelta
import logging

from fastmcp.auth.middleware.jwt_auth_middleware import (
    JWTAuthMiddleware, UserContextManager, create_auth_middleware
)


class TestJWTAuthMiddleware:
    """Test cases for JWTAuthMiddleware class"""
    
    @pytest.fixture
    def secret_key(self):
        return "test_secret_key_12345"
    
    @pytest.fixture
    def algorithm(self):
        return "HS256"
    
    @pytest.fixture
    def middleware(self, secret_key, algorithm):
        return JWTAuthMiddleware(secret_key, algorithm)
    
    @pytest.fixture
    def valid_token(self, secret_key, algorithm):
        """Generate a valid JWT token"""
        payload = {
            "sub": "user123",
            "exp": datetime.now(timezone.utc) + timedelta(hours=1),
            "iat": datetime.now(timezone.utc)
        }
        return jwt.encode(payload, secret_key, algorithm=algorithm)
    
    @pytest.fixture
    def valid_token_with_user_id(self, secret_key, algorithm):
        """Generate a valid JWT token with user_id field"""
        payload = {
            "user_id": "user456",
            "exp": datetime.now(timezone.utc) + timedelta(hours=1),
            "iat": datetime.now(timezone.utc)
        }
        return jwt.encode(payload, secret_key, algorithm=algorithm)
    
    @pytest.fixture
    def expired_token(self, secret_key, algorithm):
        """Generate an expired JWT token"""
        payload = {
            "sub": "user789",
            "exp": datetime.now(timezone.utc) - timedelta(hours=1),
            "iat": datetime.now(timezone.utc) - timedelta(hours=2)
        }
        return jwt.encode(payload, secret_key, algorithm=algorithm)
    
    def test_init(self, secret_key, algorithm):
        """Test middleware initialization"""
        middleware = JWTAuthMiddleware(secret_key, algorithm)
        assert middleware.secret_key == secret_key
        assert middleware.algorithm == algorithm
    
    def test_extract_user_from_valid_token_with_sub(self, middleware, valid_token):
        """Test extracting user from valid token with 'sub' claim"""
        user_id = middleware.extract_user_from_token(valid_token)
        assert user_id == "user123"
    
    def test_extract_user_from_valid_token_with_user_id(self, middleware, valid_token_with_user_id):
        """Test extracting user from valid token with 'user_id' claim"""
        user_id = middleware.extract_user_from_token(valid_token_with_user_id)
        assert user_id == "user456"
    
    def test_extract_user_from_token_with_bearer_prefix(self, middleware, valid_token):
        """Test extracting user from token with Bearer prefix"""
        token_with_bearer = f"Bearer {valid_token}"
        user_id = middleware.extract_user_from_token(token_with_bearer)
        assert user_id == "user123"
    
    def test_extract_user_from_expired_token(self, middleware, expired_token):
        """Test extracting user from expired token returns None"""
        user_id = middleware.extract_user_from_token(expired_token)
        assert user_id is None
    
    def test_extract_user_from_invalid_token(self, middleware):
        """Test extracting user from invalid token returns None"""
        invalid_token = "invalid.token.here"
        user_id = middleware.extract_user_from_token(invalid_token)
        assert user_id is None
    
    def test_extract_user_from_token_without_user_claim(self, middleware, secret_key, algorithm):
        """Test extracting user from token without user_id or sub claim"""
        payload = {
            "exp": datetime.now(timezone.utc) + timedelta(hours=1),
            "iat": datetime.now(timezone.utc),
            "other": "data"
        }
        token = jwt.encode(payload, secret_key, algorithm=algorithm)
        user_id = middleware.extract_user_from_token(token)
        assert user_id is None
    
    def test_create_user_scoped_repository_with_user_id_in_init(self, middleware):
        """Test creating repository that accepts user_id in constructor"""
        # Mock repository class that accepts user_id
        class MockRepository:
            def __init__(self, session, user_id=None, **kwargs):
                self.session = session
                self.user_id = user_id
                self.kwargs = kwargs
        
        session = Mock()
        user_id = "test_user"
        extra_arg = "extra_value"
        
        repo = middleware.create_user_scoped_repository(
            MockRepository, session, user_id, extra_arg=extra_arg
        )
        
        assert isinstance(repo, MockRepository)
        assert repo.session == session
        assert repo.user_id == user_id
        assert repo.kwargs == {"extra_arg": extra_arg}
    
    def test_create_user_scoped_repository_with_with_user_method(self, middleware):
        """Test creating repository that has with_user method"""
        # Mock repository with with_user method
        class MockRepository:
            def __init__(self, session, **kwargs):
                self.session = session
                self.kwargs = kwargs
                self._user_id = None
            
            def with_user(self, user_id):
                self._user_id = user_id
                return self
        
        session = Mock()
        user_id = "test_user"
        
        repo = middleware.create_user_scoped_repository(
            MockRepository, session, user_id
        )
        
        assert isinstance(repo, MockRepository)
        assert repo._user_id == user_id
    
    def test_create_user_scoped_repository_with_user_id_property(self, middleware):
        """Test creating repository that has user_id property"""
        # Mock repository with user_id property
        class MockRepository:
            def __init__(self, session, **kwargs):
                self.session = session
                self.kwargs = kwargs
                self.user_id = None
        
        session = Mock()
        user_id = "test_user"
        
        repo = middleware.create_user_scoped_repository(
            MockRepository, session, user_id
        )
        
        assert isinstance(repo, MockRepository)
        assert repo.user_id == user_id
    
    def test_create_user_scoped_repository_without_user_support(self, middleware, caplog):
        """Test creating repository that doesn't support user scoping"""
        # Mock repository without user support
        class MockRepository:
            def __init__(self, session, **kwargs):
                self.session = session
                self.kwargs = kwargs
        
        session = Mock()
        user_id = "test_user"
        
        with caplog.at_level(logging.WARNING):
            repo = middleware.create_user_scoped_repository(
                MockRepository, session, user_id
            )
        
        assert isinstance(repo, MockRepository)
        assert "doesn't support user scoping" in caplog.text
    
    def test_create_user_scoped_service_with_user_id_in_init(self, middleware):
        """Test creating service that accepts user_id in constructor"""
        # Mock service class that accepts user_id
        class MockService:
            def __init__(self, user_id=None, **deps):
                self.user_id = user_id
                self.deps = deps
        
        user_id = "test_user"
        dep1 = "value1"
        
        service = middleware.create_user_scoped_service(
            MockService, user_id, dep1=dep1
        )
        
        assert isinstance(service, MockService)
        assert service.user_id == user_id
        assert service.deps == {"dep1": dep1}
    
    def test_create_user_scoped_service_with_with_user_method(self, middleware):
        """Test creating service that has with_user method"""
        # Mock service with with_user method
        class MockService:
            def __init__(self, **deps):
                self.deps = deps
                self._user_id = None
            
            def with_user(self, user_id):
                self._user_id = user_id
                return self
        
        user_id = "test_user"
        
        service = middleware.create_user_scoped_service(
            MockService, user_id
        )
        
        assert isinstance(service, MockService)
        assert service._user_id == user_id
    
    def test_create_user_scoped_service_with_user_id_property(self, middleware):
        """Test creating service that has _user_id property"""
        # Mock service with _user_id property
        class MockService:
            def __init__(self, **deps):
                self.deps = deps
                self._user_id = None
        
        user_id = "test_user"
        
        service = middleware.create_user_scoped_service(
            MockService, user_id
        )
        
        assert isinstance(service, MockService)
        assert service._user_id == user_id
    
    def test_create_user_scoped_service_without_user_support(self, middleware, caplog):
        """Test creating service that doesn't support user scoping"""
        # Mock service without user support
        class MockService:
            def __init__(self, **deps):
                self.deps = deps
        
        user_id = "test_user"
        
        with caplog.at_level(logging.WARNING):
            service = middleware.create_user_scoped_service(
                MockService, user_id
            )
        
        assert isinstance(service, MockService)
        assert "doesn't support user scoping" in caplog.text
    
    @pytest.mark.asyncio
    async def test_require_auth_decorator_with_valid_token(self, middleware, valid_token):
        """Test require_auth decorator with valid token"""
        # Mock request
        request = Mock()
        pytest_request.headers = {"Authorization": f"Bearer {valid_token}"}
        
        # Test function
        @middleware.require_auth
        async def test_handler(pytest_request, *args, **kwargs):
            return {"user_id": kwargs.get("user_id")}
        
        result = await test_handler(request)
        assert result == {"user_id": "user123"}
    
    @pytest.mark.asyncio
    async def test_require_auth_decorator_without_auth_header(self, middleware):
        """Test require_auth decorator without Authorization header"""
        # Mock request without auth header
        request = Mock()
        pytest_request.headers = {}
        
        @middleware.require_auth
        async def test_handler(pytest_request, *args, **kwargs):
            return {"success": True}
        
        result = await test_handler(request)
        assert result == ({"error": "Authorization header missing"}, 401)
    
    @pytest.mark.asyncio
    async def test_require_auth_decorator_with_invalid_token(self, middleware):
        """Test require_auth decorator with invalid token"""
        # Mock request with invalid token
        request = Mock()
        pytest_request.headers = {"Authorization": "Bearer invalid.token"}
        
        @middleware.require_auth
        async def test_handler(pytest_request, *args, **kwargs):
            return {"success": True}
        
        result = await test_handler(request)
        assert result == ({"error": "Invalid or expired token"}, 401)


class TestUserContextManager:
    """Test cases for UserContextManager class"""
    
    @pytest.fixture
    def user_id(self):
        return "test_user_123"
    
    @pytest.fixture
    def manager(self, user_id):
        return UserContextManager(user_id)
    
    def test_init(self, manager, user_id):
        """Test manager initialization"""
        assert manager.user_id == user_id
        assert manager._scoped_repositories == {}
        assert manager._scoped_services == {}
    
    def test_get_repository_creates_new(self, manager, user_id):
        """Test getting repository creates new instance"""
        # Mock repository class
        class MockRepository:
            def __init__(self, session, user_id=None):
                self.session = session
                self.user_id = user_id
        
        session = Mock()
        
        with patch('fastmcp.auth.middleware.jwt_auth_middleware.JWTAuthMiddleware') as mock_middleware:
            mock_instance = Mock()
            mock_instance.create_user_scoped_repository.return_value = MockRepository(session, user_id)
            mock_middleware.return_value = mock_instance
            
            repo = manager.get_repository(MockRepository, session)
            
            assert isinstance(repo, MockRepository)
            assert repo.user_id == user_id
            # Check it's cached
            cache_key = f"MockRepository_{id(session)}"
            assert cache_key in manager._scoped_repositories
    
    def test_get_repository_returns_cached(self, manager):
        """Test getting repository returns cached instance"""
        # Mock repository
        class MockRepository:
            pass
        
        session = Mock()
        cached_repo = Mock()
        
        # Pre-populate cache
        cache_key = f"MockRepository_{id(session)}"
        manager._scoped_repositories[cache_key] = cached_repo
        
        repo = manager.get_repository(MockRepository, session)
        assert repo == cached_repo
    
    def test_get_service_creates_new(self, manager, user_id):
        """Test getting service creates new instance"""
        # Mock service class
        class MockService:
            def __init__(self, user_id=None, **deps):
                self.user_id = user_id
                self.deps = deps
        
        with patch('fastmcp.auth.middleware.jwt_auth_middleware.JWTAuthMiddleware') as mock_middleware:
            mock_instance = Mock()
            mock_instance.create_user_scoped_service.return_value = MockService(user_id)
            mock_middleware.return_value = mock_instance
            
            service = manager.get_service(MockService, dep1="value1")
            
            assert isinstance(service, MockService)
            assert service.user_id == user_id
            # Check it's cached
            assert "MockService" in manager._scoped_services
    
    def test_get_service_returns_cached(self, manager):
        """Test getting service returns cached instance"""
        # Mock service
        class MockService:
            pass
        
        cached_service = Mock()
        
        # Pre-populate cache
        manager._scoped_services["MockService"] = cached_service
        
        service = manager.get_service(MockService)
        assert service == cached_service
    
    def test_clear_cache(self, manager):
        """Test clearing cache"""
        # Add some items to cache
        manager._scoped_repositories["test_repo"] = Mock()
        manager._scoped_services["test_service"] = Mock()
        
        # Clear cache
        manager.clear_cache()
        
        assert manager._scoped_repositories == {}
        assert manager._scoped_services == {}


class TestCreateAuthMiddleware:
    """Test cases for create_auth_middleware factory function"""
    
    def test_create_auth_middleware(self):
        """Test creating auth middleware with factory"""
        secret = "test_secret"
        algo = "HS256"
        
        middleware = create_auth_middleware(secret, algo)
        
        assert isinstance(middleware, JWTAuthMiddleware)
        assert middleware.secret_key == secret
        assert middleware.algorithm == algo
    
    def test_create_auth_middleware_default_algorithm(self):
        """Test creating auth middleware with default algorithm"""
        secret = "test_secret"
        
        middleware = create_auth_middleware(secret)
        
        assert isinstance(middleware, JWTAuthMiddleware)
        assert middleware.secret_key == secret
        assert middleware.algorithm == "HS256"