"""
Unit Tests for MCP Client

Tests all MCP HTTP client implementations in isolation with comprehensive
edge cases, error handling, and authentication scenarios.

Test Coverage:
- TokenManager authentication and caching
- RateLimiter request throttling
- MCPHTTPClient basic functionality  
- ResilientMCPClient fallback strategies
- OptimizedMCPClient connection pooling
- Error handling and edge cases
"""

import pytest
import time
import json
import tempfile
from pathlib import Path
from unittest.mock import Mock, patch, MagicMock, mock_open
from datetime import datetime, timedelta
import requests
from requests.exceptions import ConnectionError, Timeout, HTTPError

# Import MCP client components
from utils.mcp_client import (
    TokenManager, 
    RateLimiter, 
    MCPHTTPClient,
    ResilientMCPClient,
    OptimizedMCPClient,
    create_mcp_client,
    get_default_client
)


class TestTokenManager:
    """Unit tests for JWT token management."""
    
    @pytest.fixture
    def temp_token_cache(self):
        """Create temporary token cache file."""
        with tempfile.NamedTemporaryFile(mode='w+', delete=False, suffix='.json') as f:
            yield Path(f.name)
        Path(f.name).unlink(missing_ok=True)
    
    @pytest.fixture
    def token_manager(self, temp_token_cache):
        """Create TokenManager instance with test configuration."""
        with patch.object(TokenManager, '__init__', return_value=None):
            tm = TokenManager()
            tm.token_cache_file = temp_token_cache
            tm.token = None
            tm.token_expiry = None
            tm.refresh_before = 60
            tm.keycloak_config = {
                "url": "http://localhost:8080",
                "realm": "dhafnck",
                "client_id": "claude-hooks",
                "client_secret": "test-secret"
            }
            # Add required methods
            tm._load_cached_token = TokenManager._load_cached_token.__get__(tm, TokenManager)
            tm._save_token_to_cache = TokenManager._save_token_to_cache.__get__(tm, TokenManager)
            tm._refresh_token = TokenManager._refresh_token.__get__(tm, TokenManager)
            tm.get_valid_token = TokenManager.get_valid_token.__get__(tm, TokenManager)
            tm.is_token_valid = TokenManager.is_token_valid.__get__(tm, TokenManager)
            yield tm
    
    def test_token_manager_initialization(self, temp_token_cache):
        """Test TokenManager initialization."""
        with patch.object(TokenManager, '_load_cached_token'):
            tm = TokenManager()
            assert hasattr(tm, 'keycloak_config')
            assert hasattr(tm, 'token_cache_file')
            assert hasattr(tm, 'refresh_before')
    
    def test_load_cached_token_success(self, token_manager, temp_token_cache):
        """Test successful token loading from cache."""
        # Create cached token
        cached_data = {
            "token": "cached-jwt-token",
            "expires_at": (datetime.now() + timedelta(hours=1)).timestamp()
        }
        
        with open(temp_token_cache, 'w') as f:
            json.dump(cached_data, f)
        
        # Load token
        token_manager._load_cached_token()
        
        assert token_manager.token == "cached-jwt-token"
        assert token_manager.token_expiry is not None
    
    def test_load_cached_token_expired(self, token_manager, temp_token_cache):
        """Test loading expired cached token."""
        # Create expired cached token
        cached_data = {
            "token": "expired-jwt-token",
            "expires_at": (datetime.now() - timedelta(hours=1)).timestamp()
        }
        
        with open(temp_token_cache, 'w') as f:
            json.dump(cached_data, f)
        
        # Load token - should be ignored
        token_manager._load_cached_token()
        
        assert token_manager.token is None
        assert token_manager.token_expiry is None
    
    def test_load_cached_token_corrupted_file(self, token_manager, temp_token_cache):
        """Test handling of corrupted cache file."""
        # Create corrupted cache file
        with open(temp_token_cache, 'w') as f:
            f.write("invalid json content")
        
        # Should not raise exception
        token_manager._load_cached_token()
        
        assert token_manager.token is None
        assert token_manager.token_expiry is None
    
    def test_load_cached_token_missing_file(self, token_manager):
        """Test loading when cache file doesn't exist."""
        # Ensure file doesn't exist
        assert not token_manager.token_cache_file.exists()
        
        # Should not raise exception
        token_manager._load_cached_token()
        
        assert token_manager.token is None
        assert token_manager.token_expiry is None
    
    def test_save_token_to_cache(self, token_manager):
        """Test saving token to cache file."""
        test_token = "test-jwt-token"
        expires_in = 3600
        
        token_manager.token = test_token
        token_manager.token_expiry = datetime.now() + timedelta(seconds=expires_in)
        
        # Save to cache
        token_manager._save_token_to_cache(test_token, expires_in)
        
        # Verify cache file contents
        assert token_manager.token_cache_file.exists()
        
        with open(token_manager.token_cache_file, 'r') as f:
            cached_data = json.load(f)
        
        assert cached_data["token"] == test_token
        assert "expires_at" in cached_data
    
    @patch('requests.post')
    def test_refresh_token_success(self, mock_post, token_manager):
        """Test successful token refresh."""
        # Mock successful response
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "access_token": "new-jwt-token",
            "expires_in": 3600
        }
        mock_post.return_value = mock_response
        
        # Refresh token
        token_manager._refresh_token()
        
        assert token_manager.token == "new-jwt-token"
        assert token_manager.token_expiry is not None
        
        # Verify request was made correctly
        mock_post.assert_called_once()
        call_args = mock_post.call_args
        assert "auth/realms/dhafnck/protocol/openid-connect/token" in call_args[0][0]
    
    @patch('requests.post')
    def test_refresh_token_http_error(self, mock_post, token_manager):
        """Test token refresh with HTTP error."""
        # Mock HTTP error response
        mock_response = Mock()
        mock_response.status_code = 401
        mock_response.json.return_value = {"error": "invalid_client"}
        mock_post.return_value = mock_response
        
        # Should handle error gracefully
        with pytest.raises(Exception):
            token_manager._refresh_token()
    
    @patch('requests.post', side_effect=requests.exceptions.ConnectionError)
    def test_refresh_token_connection_error(self, mock_post, token_manager):
        """Test token refresh with connection error."""
        with pytest.raises(requests.exceptions.ConnectionError):
            token_manager._refresh_token()
    
    def test_is_token_valid_no_token(self, token_manager):
        """Test token validity when no token exists."""
        token_manager.token = None
        assert not token_manager.is_token_valid()
    
    def test_is_token_valid_expired_token(self, token_manager):
        """Test token validity with expired token."""
        token_manager.token = "expired-token"
        token_manager.token_expiry = datetime.now() - timedelta(minutes=30)
        assert not token_manager.is_token_valid()
    
    def test_is_token_valid_near_expiry(self, token_manager):
        """Test token validity when near expiry (within refresh window)."""
        token_manager.token = "near-expiry-token"
        token_manager.token_expiry = datetime.now() + timedelta(seconds=30)  # Less than refresh_before
        assert not token_manager.is_token_valid()
    
    def test_is_token_valid_good_token(self, token_manager):
        """Test token validity with good token."""
        token_manager.token = "good-token"
        token_manager.token_expiry = datetime.now() + timedelta(hours=1)
        assert token_manager.is_token_valid()
    
    @patch.object(TokenManager, '_refresh_token')
    def test_get_valid_token_needs_refresh(self, mock_refresh, token_manager):
        """Test getting valid token when refresh is needed."""
        token_manager.token = None
        
        # Mock refresh to set token
        def set_token():
            token_manager.token = "refreshed-token"
            token_manager.token_expiry = datetime.now() + timedelta(hours=1)
        
        mock_refresh.side_effect = set_token
        
        result = token_manager.get_valid_token()
        
        assert result == "refreshed-token"
        mock_refresh.assert_called_once()
    
    def test_get_valid_token_already_valid(self, token_manager):
        """Test getting valid token when already valid."""
        token_manager.token = "already-valid-token"
        token_manager.token_expiry = datetime.now() + timedelta(hours=1)
        
        with patch.object(token_manager, '_refresh_token') as mock_refresh:
            result = token_manager.get_valid_token()
            
            assert result == "already-valid-token"
            mock_refresh.assert_not_called()


class TestRateLimiter:
    """Unit tests for request rate limiting."""
    
    def test_rate_limiter_initialization(self):
        """Test RateLimiter initialization."""
        limiter = RateLimiter(max_requests=5, time_window=10)
        
        assert limiter.max_requests == 5
        assert limiter.time_window == 10
        assert hasattr(limiter, 'requests')
        assert hasattr(limiter, 'lock')
    
    def test_allow_request_within_limit(self):
        """Test allowing requests within rate limit."""
        limiter = RateLimiter(max_requests=3, time_window=1)
        
        # Should allow first 3 requests
        for i in range(3):
            assert limiter.allow_request() is True
    
    def test_block_request_over_limit(self):
        """Test blocking requests over rate limit."""
        limiter = RateLimiter(max_requests=2, time_window=1)
        
        # Allow first 2 requests
        assert limiter.allow_request() is True
        assert limiter.allow_request() is True
        
        # Block 3rd request
        assert limiter.allow_request() is False
    
    def test_rate_limit_window_reset(self):
        """Test rate limit window reset after time passes."""
        limiter = RateLimiter(max_requests=2, time_window=1)
        
        # Use up the limit
        assert limiter.allow_request() is True
        assert limiter.allow_request() is True
        assert limiter.allow_request() is False
        
        # Wait for window to reset
        time.sleep(1.1)
        
        # Should allow requests again
        assert limiter.allow_request() is True
    
    def test_rate_limiter_thread_safety(self):
        """Test rate limiter thread safety."""
        limiter = RateLimiter(max_requests=10, time_window=1)
        
        import threading
        from concurrent.futures import ThreadPoolExecutor
        
        results = []
        
        def make_request():
            return limiter.allow_request()
        
        # Make 20 concurrent requests (more than limit)
        with ThreadPoolExecutor(max_workers=5) as executor:
            futures = [executor.submit(make_request) for _ in range(20)]
            results = [f.result() for f in futures]
        
        # Should have exactly 10 allowed requests
        allowed_count = sum(1 for r in results if r)
        assert allowed_count == 10
    
    def test_rate_limiter_cleanup_old_requests(self):
        """Test cleanup of old request timestamps."""
        limiter = RateLimiter(max_requests=5, time_window=1)
        
        # Make some requests
        for _ in range(3):
            limiter.allow_request()
        
        # Wait for requests to become old
        time.sleep(1.1)
        
        # Make new request - should clean up old ones
        assert limiter.allow_request() is True
        
        # Should now have room for more requests
        for _ in range(4):  # Total of 5 including the one above
            assert limiter.allow_request() is True


class TestMCPHTTPClient:
    """Unit tests for basic MCP HTTP client."""
    
    @pytest.fixture
    def mcp_client(self):
        """Create MCPHTTPClient instance with mocked dependencies."""
        with patch('utils.mcp_client.TokenManager') as mock_token_manager:
            with patch('utils.mcp_client.RateLimiter') as mock_rate_limiter:
                mock_tm_instance = Mock()
                mock_rl_instance = Mock()
                mock_token_manager.return_value = mock_tm_instance
                mock_rate_limiter.return_value = mock_rl_instance
                
                client = MCPHTTPClient()
                client.token_manager = mock_tm_instance
                client.rate_limiter = mock_rl_instance
                client.session = Mock(spec=requests.Session)
                
                yield client
    
    def test_mcp_client_initialization(self):
        """Test MCPHTTPClient initialization."""
        with patch('utils.mcp_client.TokenManager') as mock_tm:
            with patch('utils.mcp_client.RateLimiter') as mock_rl:
                client = MCPHTTPClient()
                
                assert hasattr(client, 'token_manager')
                assert hasattr(client, 'rate_limiter')
                assert hasattr(client, 'session')
                assert hasattr(client, 'base_url')
                mock_tm.assert_called_once()
                mock_rl.assert_called_once()
    
    def test_authenticate_success(self, mcp_client):
        """Test successful authentication."""
        mcp_client.token_manager.get_valid_token.return_value = "valid-token"
        
        result = mcp_client.authenticate()
        
        assert result is True
        mcp_client.token_manager.get_valid_token.assert_called_once()
    
    def test_authenticate_failure(self, mcp_client):
        """Test authentication failure."""
        mcp_client.token_manager.get_valid_token.side_effect = Exception("Auth failed")
        
        result = mcp_client.authenticate()
        
        assert result is False
    
    def test_make_request_success(self, mcp_client):
        """Test successful API request."""
        # Setup mocks
        mcp_client.rate_limiter.allow_request.return_value = True
        mcp_client.token_manager.get_valid_token.return_value = "valid-token"
        
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {"success": True, "data": ["task1"]}
        mcp_client.session.post.return_value = mock_response
        
        # Make request
        result = mcp_client._make_request("test/endpoint", {"action": "list"})
        
        assert result == {"success": True, "data": ["task1"]}
        mcp_client.rate_limiter.allow_request.assert_called_once()
        mcp_client.session.post.assert_called_once()
    
    def test_make_request_rate_limited(self, mcp_client):
        """Test request blocked by rate limiter."""
        mcp_client.rate_limiter.allow_request.return_value = False
        
        with pytest.raises(Exception, match="Rate limit exceeded"):
            mcp_client._make_request("test/endpoint", {"action": "list"})
    
    def test_make_request_http_error(self, mcp_client):
        """Test request with HTTP error response."""
        mcp_client.rate_limiter.allow_request.return_value = True
        mcp_client.token_manager.get_valid_token.return_value = "valid-token"
        
        mock_response = Mock()
        mock_response.status_code = 500
        mock_response.text = "Internal Server Error"
        mcp_client.session.post.return_value = mock_response
        
        with pytest.raises(Exception):
            mcp_client._make_request("test/endpoint", {"action": "list"})
    
    def test_make_request_connection_error(self, mcp_client):
        """Test request with connection error."""
        mcp_client.rate_limiter.allow_request.return_value = True
        mcp_client.token_manager.get_valid_token.return_value = "valid-token"
        mcp_client.session.post.side_effect = ConnectionError("Connection failed")
        
        with pytest.raises(ConnectionError):
            mcp_client._make_request("test/endpoint", {"action": "list"})
    
    def test_query_pending_tasks(self, mcp_client):
        """Test querying pending tasks."""
        expected_data = [
            {"id": "task1", "title": "Test Task 1", "status": "todo"},
            {"id": "task2", "title": "Test Task 2", "status": "in_progress"}
        ]
        
        with patch.object(mcp_client, '_make_request', return_value={"data": {"tasks": expected_data}}):
            result = mcp_client.query_pending_tasks(limit=5)
            
            assert result == expected_data
            mcp_client._make_request.assert_called_once_with(
                "manage_task",
                {"action": "list", "status": "todo,in_progress", "limit": 5}
            )
    
    def test_get_next_recommended_task(self, mcp_client):
        """Test getting next recommended task."""
        expected_task = {"id": "next-task", "title": "Next Task", "priority": "high"}
        
        with patch.object(mcp_client, '_make_request', return_value={"data": expected_task}):
            result = mcp_client.get_next_recommended_task("branch-id-123")
            
            assert result == expected_task
            mcp_client._make_request.assert_called_once_with(
                "manage_task",
                {"action": "next", "git_branch_id": "branch-id-123", "include_context": True}
            )


class TestResilientMCPClient:
    """Unit tests for resilient MCP client with fallback strategies."""
    
    @pytest.fixture
    def resilient_client(self):
        """Create ResilientMCPClient with mocked base functionality."""
        with patch.multiple(
            'utils.mcp_client.MCPHTTPClient',
            __init__=Mock(return_value=None),
            authenticate=Mock(return_value=True),
            _make_request=Mock()
        ):
            client = ResilientMCPClient()
            client.fallback_strategy = "cache_then_skip"
            client.max_retries = 3
            client.retry_delay = 0.1
            client.session = Mock()
            client.token_manager = Mock()
            client.rate_limiter = Mock()
            yield client
    
    def test_resilient_client_initialization(self):
        """Test ResilientMCPClient initialization."""
        with patch('utils.mcp_client.MCPHTTPClient.__init__', return_value=None):
            client = ResilientMCPClient()
            
            assert hasattr(client, 'max_retries')
            assert hasattr(client, 'retry_delay')
            assert hasattr(client, 'fallback_strategy')
    
    def test_make_request_with_retries_success(self, resilient_client):
        """Test successful request after retries."""
        expected_response = {"success": True, "data": "test"}
        
        # First two calls fail, third succeeds
        resilient_client._make_request = Mock(side_effect=[
            ConnectionError("First failure"),
            Timeout("Second failure"),
            expected_response
        ])
        
        result = resilient_client._make_request_with_retries("test/endpoint", {"test": "data"})
        
        assert result == expected_response
        assert resilient_client._make_request.call_count == 3
    
    def test_make_request_with_retries_all_fail(self, resilient_client):
        """Test request failure after all retries exhausted."""
        resilient_client._make_request = Mock(side_effect=ConnectionError("Persistent failure"))
        
        with pytest.raises(ConnectionError):
            resilient_client._make_request_with_retries("test/endpoint", {"test": "data"})
        
        assert resilient_client._make_request.call_count == 3  # max_retries
    
    def test_query_pending_tasks_with_fallback_cache(self, resilient_client):
        """Test querying tasks with cache fallback."""
        cached_tasks = [{"id": "cached-task", "title": "Cached Task"}]
        
        # Mock failed request but successful cache fallback
        resilient_client._make_request_with_retries = Mock(side_effect=Exception("Request failed"))
        
        with patch('utils.cache_manager.get_session_cache') as mock_cache:
            mock_cache_instance = Mock()
            mock_cache_instance.get_pending_tasks.return_value = cached_tasks
            mock_cache.return_value = mock_cache_instance
            
            result = resilient_client.query_pending_tasks(limit=5)
            
            assert result == cached_tasks
            mock_cache_instance.get_pending_tasks.assert_called_once()
    
    def test_query_pending_tasks_complete_failure(self, resilient_client):
        """Test querying tasks when both request and cache fail."""
        resilient_client._make_request_with_retries = Mock(side_effect=Exception("Request failed"))
        
        with patch('utils.cache_manager.get_session_cache') as mock_cache:
            mock_cache_instance = Mock()
            mock_cache_instance.get_pending_tasks.return_value = None
            mock_cache.return_value = mock_cache_instance
            
            result = resilient_client.query_pending_tasks(limit=5)
            
            assert result is None


class TestOptimizedMCPClient:
    """Unit tests for optimized MCP client with connection pooling."""
    
    @pytest.fixture
    def optimized_client(self):
        """Create OptimizedMCPClient with mocked dependencies."""
        with patch('utils.mcp_client.MCPHTTPClient.__init__', return_value=None):
            client = OptimizedMCPClient()
            client.session = Mock()
            client.token_manager = Mock()
            client.rate_limiter = Mock()
            client.pool_size = 10
            client.connection_timeout = 5
            yield client
    
    def test_optimized_client_initialization(self):
        """Test OptimizedMCPClient initialization."""
        with patch('utils.mcp_client.MCPHTTPClient.__init__', return_value=None):
            with patch('requests.Session') as mock_session:
                mock_session_instance = Mock()
                mock_session.return_value = mock_session_instance
                
                client = OptimizedMCPClient()
                
                assert hasattr(client, 'pool_size')
                assert hasattr(client, 'connection_timeout')
                # Should configure session adapter
                mock_session_instance.mount.assert_called()
    
    def test_optimized_session_configuration(self, optimized_client):
        """Test that session is properly configured for optimization."""
        # This would test session adapter configuration
        # In a real implementation, we'd verify HTTPAdapter settings
        assert hasattr(optimized_client, 'session')
        assert hasattr(optimized_client, 'pool_size')
        assert optimized_client.pool_size == 10


class TestMCPClientFactory:
    """Unit tests for MCP client factory functions."""
    
    def test_create_mcp_client_basic(self):
        """Test creating basic MCP client."""
        with patch('utils.mcp_client.MCPHTTPClient') as mock_client:
            mock_instance = Mock()
            mock_client.return_value = mock_instance
            
            result = create_mcp_client(client_type="basic")
            
            assert result == mock_instance
            mock_client.assert_called_once()
    
    def test_create_mcp_client_resilient(self):
        """Test creating resilient MCP client."""
        with patch('utils.mcp_client.ResilientMCPClient') as mock_client:
            mock_instance = Mock()
            mock_client.return_value = mock_instance
            
            result = create_mcp_client(client_type="resilient")
            
            assert result == mock_instance
            mock_client.assert_called_once()
    
    def test_create_mcp_client_optimized(self):
        """Test creating optimized MCP client."""
        with patch('utils.mcp_client.OptimizedMCPClient') as mock_client:
            mock_instance = Mock()
            mock_client.return_value = mock_instance
            
            result = create_mcp_client(client_type="optimized")
            
            assert result == mock_instance
            mock_client.assert_called_once()
    
    def test_create_mcp_client_invalid_type(self):
        """Test creating client with invalid type."""
        with pytest.raises(ValueError, match="Unknown client type"):
            create_mcp_client(client_type="invalid")
    
    def test_get_default_client(self):
        """Test getting default client instance."""
        with patch('utils.mcp_client.create_mcp_client') as mock_create:
            mock_instance = Mock()
            mock_create.return_value = mock_instance
            
            result = get_default_client()
            
            assert result == mock_instance
            mock_create.assert_called_once_with(client_type="resilient")


class TestMCPClientIntegrationScenarios:
    """Test integration scenarios and edge cases."""
    
    def test_full_authentication_flow(self):
        """Test complete authentication flow from start to finish."""
        with tempfile.NamedTemporaryFile(mode='w+', delete=False, suffix='.json') as f:
            cache_file = Path(f.name)
        
        try:
            with patch('utils.mcp_client.TokenManager.__init__', return_value=None):
                tm = TokenManager()
                tm.token_cache_file = cache_file
                tm.token = None
                tm.token_expiry = None
                tm.refresh_before = 60
                tm.keycloak_config = {
                    "url": "http://localhost:8080",
                    "realm": "dhafnck",
                    "client_id": "claude-hooks",
                    "client_secret": "test-secret"
                }
                # Add methods
                tm._load_cached_token = TokenManager._load_cached_token.__get__(tm, TokenManager)
                tm._save_token_to_cache = TokenManager._save_token_to_cache.__get__(tm, TokenManager)
                tm._refresh_token = TokenManager._refresh_token.__get__(tm, TokenManager)
                tm.get_valid_token = TokenManager.get_valid_token.__get__(tm, TokenManager)
                tm.is_token_valid = TokenManager.is_token_valid.__get__(tm, TokenManager)
                
                # Mock successful token refresh
                with patch('requests.post') as mock_post:
                    mock_response = Mock()
                    mock_response.status_code = 200
                    mock_response.json.return_value = {
                        "access_token": "integration-test-token",
                        "expires_in": 3600
                    }
                    mock_post.return_value = mock_response
                    
                    # Get valid token - should trigger refresh and caching
                    token = tm.get_valid_token()
                    
                    assert token == "integration-test-token"
                    assert cache_file.exists()
                    
                    # Verify cache contents
                    with open(cache_file, 'r') as f:
                        cached_data = json.load(f)
                    
                    assert cached_data["token"] == "integration-test-token"
        
        finally:
            cache_file.unlink(missing_ok=True)
    
    def test_client_error_recovery_scenarios(self):
        """Test various error recovery scenarios."""
        with patch('utils.mcp_client.MCPHTTPClient.__init__', return_value=None):
            client = ResilientMCPClient()
            client.max_retries = 2
            client.retry_delay = 0.01
            client.session = Mock()
            client.token_manager = Mock()
            client.rate_limiter = Mock()
            
            # Test scenario: Connection error -> Timeout -> Success
            expected_response = {"success": True}
            client._make_request = Mock(side_effect=[
                ConnectionError("Network issue"),
                Timeout("Request timeout"),
                expected_response
            ])
            
            result = client._make_request_with_retries("test/endpoint", {})
            
            assert result == expected_response
            assert client._make_request.call_count == 3