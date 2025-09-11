"""
Integration Performance Tests for Keycloak Authentication Flow

Tests the complete authentication flow between MCP clients and Keycloak:
- Token acquisition performance
- Token refresh timing
- Authentication reliability under load
- Service account credential validation
- Token cache effectiveness
"""

import asyncio
import pytest
import time
import statistics
import json
import os
from unittest.mock import Mock, patch, AsyncMock
from pathlib import Path
from concurrent.futures import ThreadPoolExecutor, as_completed
import tempfile
import threading

# Import the components under test
import sys
test_dir = Path(__file__).parent.parent.parent.parent.parent
sys.path.insert(0, str(test_dir / ".claude" / "hooks" / "utils"))
sys.path.insert(0, str(test_dir / "dhafnck_mcp_main" / "src"))

from mcp_client import TokenManager, MCPHTTPClient
from fastmcp.auth.service_account import ServiceAccountAuth, ServiceAccountConfig

# Import performance test config and mocks
from ..mocks.mock_mcp_server import MockKeycloakServer
from .. import PERFORMANCE_CONFIG, setup_performance_logger

logger = setup_performance_logger()


class TestKeycloakAuthenticationPerformance:
    """Integration tests for Keycloak authentication performance."""
    
    @pytest.fixture
    def mock_keycloak_server(self):
        """Create mock Keycloak server for testing."""
        return MockKeycloakServer()
    
    @pytest.fixture
    def service_account_config(self):
        """Create test service account configuration."""
        return ServiceAccountConfig(
            keycloak_url="http://localhost:8080",
            realm="dhafnck",
            client_id="claude-hooks",
            client_secret="test-secret",
            scopes=["openid", "profile", "mcp:read", "mcp:write"]
        )
    
    @pytest.mark.performance
    @pytest.mark.asyncio
    async def test_token_acquisition_performance(self, mock_keycloak_server, service_account_config):
        """Test initial token acquisition performance."""
        iterations = 20  # Fewer iterations for integration tests
        acquisition_times = []
        
        for i in range(iterations):
            # Create fresh service account auth for each test
            auth = ServiceAccountAuth(service_account_config)
            
            # Mock the HTTP client to use our mock server
            with patch.object(auth.client, 'post') as mock_post:
                # Configure mock response based on mock server
                token_data = mock_keycloak_server.authenticate_client(
                    "claude-hooks", "test-secret"
                )
                
                mock_response = Mock()
                mock_response.status_code = 200
                mock_response.json.return_value = token_data
                mock_post.return_value = mock_response
                
                # Measure token acquisition time
                start_time = time.perf_counter()
                token = await auth.get_access_token()
                end_time = time.perf_counter()
                
                acquisition_times.append(end_time - start_time)
                assert token is not None, f"Token acquisition failed on iteration {i}"
        
        # Analyze performance
        avg_time = statistics.mean(acquisition_times)
        p95_time = statistics.quantiles(acquisition_times, n=20)[18]
        
        logger.info(f"Token acquisition average time: {avg_time:.4f}s")
        logger.info(f"Token acquisition P95 time: {p95_time:.4f}s")
        
        # Performance assertions
        assert avg_time < PERFORMANCE_CONFIG["response_time_targets"]["token_refresh"]
        assert p95_time < PERFORMANCE_CONFIG["response_time_targets"]["token_refresh"] * 1.5
    
    @pytest.mark.performance
    @pytest.mark.asyncio  
    async def test_token_refresh_performance(self, mock_keycloak_server, service_account_config):
        """Test token refresh performance and caching effectiveness."""
        auth = ServiceAccountAuth(service_account_config)
        
        refresh_times = []
        cache_hit_times = []
        
        with patch.object(auth.client, 'post') as mock_post:
            # Initial token acquisition
            token_data = mock_keycloak_server.authenticate_client(
                "claude-hooks", "test-secret"
            )
            mock_response = Mock()
            mock_response.status_code = 200
            mock_response.json.return_value = token_data
            mock_post.return_value = mock_response
            
            # Get initial token
            await auth.get_access_token()
            
            # Test token refresh performance
            for i in range(10):
                # Force token refresh by clearing current token
                auth._current_token = None
                
                start_time = time.perf_counter()
                token = await auth.get_access_token()
                end_time = time.perf_counter()
                
                refresh_times.append(end_time - start_time)
                assert token is not None
                
                # Test immediate subsequent call (should use cached token)
                start_time = time.perf_counter()
                cached_token = await auth.get_access_token()
                end_time = time.perf_counter()
                
                cache_hit_times.append(end_time - start_time)
                assert cached_token == token, "Token should be cached"
        
        # Analyze performance
        avg_refresh_time = statistics.mean(refresh_times)
        avg_cache_hit_time = statistics.mean(cache_hit_times)
        
        logger.info(f"Token refresh average time: {avg_refresh_time:.4f}s")
        logger.info(f"Token cache hit average time: {avg_cache_hit_time:.6f}s")
        
        # Performance assertions
        assert avg_refresh_time < PERFORMANCE_CONFIG["response_time_targets"]["token_refresh"]
        assert avg_cache_hit_time < PERFORMANCE_CONFIG["response_time_targets"]["cache_hit"]
        
        # Cache should be significantly faster than refresh
        cache_speedup = avg_refresh_time / avg_cache_hit_time
        assert cache_speedup > 10, f"Cache not providing sufficient speedup: {cache_speedup}x"
    
    @pytest.mark.performance
    @pytest.mark.asyncio
    async def test_concurrent_authentication_performance(self, mock_keycloak_server, service_account_config):
        """Test authentication performance under concurrent load."""
        concurrent_sessions = PERFORMANCE_CONFIG["concurrent_sessions"]
        
        async def authenticate_worker():
            """Worker for concurrent authentication."""
            auth = ServiceAccountAuth(service_account_config)
            
            with patch.object(auth.client, 'post') as mock_post:
                token_data = mock_keycloak_server.authenticate_client(
                    "claude-hooks", "test-secret"
                )
                mock_response = Mock()
                mock_response.status_code = 200
                mock_response.json.return_value = token_data
                mock_post.return_value = mock_response
                
                start_time = time.perf_counter()
                token = await auth.get_access_token()
                end_time = time.perf_counter()
                
                return {
                    "token": token,
                    "duration": end_time - start_time,
                    "success": token is not None
                }
        
        # Execute concurrent authentication
        start_time = time.perf_counter()
        tasks = [authenticate_worker() for _ in range(concurrent_sessions)]
        results = await asyncio.gather(*tasks)
        total_time = time.perf_counter() - start_time
        
        # Analyze results
        successful_auths = sum(1 for r in results if r["success"])
        avg_duration = statistics.mean([r["duration"] for r in results])
        success_rate = successful_auths / concurrent_sessions
        
        logger.info(f"Concurrent auth: {successful_auths}/{concurrent_sessions} successful")
        logger.info(f"Total time: {total_time:.4f}s")
        logger.info(f"Average auth time: {avg_duration:.4f}s")
        logger.info(f"Success rate: {success_rate:.2%}")
        
        # Performance and reliability assertions
        assert success_rate >= 0.95, f"Auth success rate too low: {success_rate:.2%}"
        assert avg_duration < PERFORMANCE_CONFIG["response_time_targets"]["token_refresh"] * 2
        assert total_time < 5.0, f"Concurrent auth too slow: {total_time}s"
    
    @pytest.mark.performance
    def test_token_manager_integration_performance(self, mock_keycloak_server):
        """Test TokenManager integration with Keycloak performance."""
        with tempfile.TemporaryDirectory() as temp_dir:
            # Create token manager with test cache directory
            with patch.object(TokenManager, '__init__') as mock_init:
                mock_init.return_value = None
                tm = TokenManager()
                tm.token_cache_file = Path(temp_dir) / ".mcp_token_cache"
                tm.token = None
                tm.token_expiry = None
                tm.refresh_before = 60
                tm.keycloak_config = {
                    "url": "http://localhost:8080",
                    "realm": "dhafnck",
                    "client_id": "claude-hooks",
                    "client_secret": "test-secret"
                }
            
            # Test token manager performance with multiple requests
            iterations = 20
            get_token_times = []
            
            with patch('requests.post') as mock_post:
                # Configure mock response
                token_data = mock_keycloak_server.authenticate_client(
                    "claude-hooks", "test-secret"
                )
                mock_response = Mock()
                mock_response.status_code = 200
                mock_response.json.return_value = token_data
                mock_post.return_value = mock_response
                
                for i in range(iterations):
                    start_time = time.perf_counter()
                    token = tm.get_valid_token()
                    end_time = time.perf_counter()
                    
                    get_token_times.append(end_time - start_time)
                    assert token is not None, f"Token retrieval failed on iteration {i}"
            
            # Analyze performance
            avg_time = statistics.mean(get_token_times)
            
            # Most calls should be cache hits after the first
            cache_hit_times = get_token_times[1:]  # Skip first request
            avg_cache_time = statistics.mean(cache_hit_times) if cache_hit_times else avg_time
            
            logger.info(f"TokenManager average time: {avg_time:.4f}s")
            logger.info(f"TokenManager cache hit time: {avg_cache_time:.6f}s")
            
            # Should be very fast due to caching
            assert avg_cache_time < PERFORMANCE_CONFIG["response_time_targets"]["cache_hit"] * 10


class TestAuthenticationReliability:
    """Tests for authentication reliability under various conditions."""
    
    @pytest.fixture
    def unreliable_keycloak_server(self):
        """Create Keycloak server with reliability issues."""
        server = MockKeycloakServer()
        # Simulate intermittent failures
        original_auth = server.authenticate_client
        
        def unreliable_auth(client_id, client_secret):
            # 20% failure rate
            if time.time() % 1.0 < 0.2:
                return None
            return original_auth(client_id, client_secret)
        
        server.authenticate_client = unreliable_auth
        return server
    
    @pytest.mark.performance 
    def test_authentication_retry_performance(self, unreliable_keycloak_server):
        """Test authentication performance with retry logic."""
        with tempfile.TemporaryDirectory() as temp_dir:
            # Create token manager
            with patch.object(TokenManager, '__init__') as mock_init:
                mock_init.return_value = None
                tm = TokenManager()
                tm.token_cache_file = Path(temp_dir) / ".mcp_token_cache" 
                tm.token = None
                tm.token_expiry = None
                tm.refresh_before = 60
                tm.keycloak_config = {
                    "url": "http://localhost:8080",
                    "realm": "dhafnck",
                    "client_id": "claude-hooks", 
                    "client_secret": "test-secret"
                }
            
            successful_auths = 0
            failed_auths = 0
            retry_times = []
            
            with patch('requests.post') as mock_post:
                def mock_post_side_effect(*args, **kwargs):
                    # Use unreliable server logic
                    token_data = unreliable_keycloak_server.authenticate_client(
                        "claude-hooks", "test-secret"
                    )
                    
                    mock_response = Mock()
                    if token_data:
                        mock_response.status_code = 200
                        mock_response.json.return_value = token_data
                    else:
                        mock_response.status_code = 401
                    return mock_response
                
                mock_post.side_effect = mock_post_side_effect
                
                # Test with retry attempts
                for i in range(30):
                    start_time = time.perf_counter()
                    
                    # Try up to 3 times
                    for attempt in range(3):
                        token = tm.get_valid_token()
                        if token:
                            successful_auths += 1
                            break
                        # Clear token to force retry
                        tm.token = None
                        tm.token_expiry = None
                    else:
                        failed_auths += 1
                    
                    end_time = time.perf_counter()
                    retry_times.append(end_time - start_time)
            
            # Analyze retry performance
            success_rate = successful_auths / (successful_auths + failed_auths)
            avg_retry_time = statistics.mean(retry_times)
            
            logger.info(f"Auth with retries: {successful_auths} success, {failed_auths} failed")
            logger.info(f"Success rate: {success_rate:.2%}")
            logger.info(f"Average retry time: {avg_retry_time:.4f}s")
            
            # Should handle intermittent failures gracefully
            assert success_rate > 0.8, f"Success rate too low with retries: {success_rate:.2%}"
            assert avg_retry_time < PERFORMANCE_CONFIG["response_time_targets"]["token_refresh"] * 3


class TestTokenCacheEffectiveness:
    """Tests for token cache effectiveness and performance impact."""
    
    @pytest.mark.performance
    def test_cache_hit_rate_performance(self, mock_keycloak_server):
        """Test token cache hit rates and performance benefits."""
        with tempfile.TemporaryDirectory() as temp_dir:
            client = MCPHTTPClient()
            client.token_manager.token_cache_file = Path(temp_dir) / ".mcp_token_cache"
            
            cache_hits = 0
            cache_misses = 0
            hit_times = []
            miss_times = []
            
            with patch('requests.post') as mock_post:
                token_data = mock_keycloak_server.authenticate_client(
                    "claude-hooks", "test-secret"
                )
                mock_response = Mock()
                mock_response.status_code = 200
                mock_response.json.return_value = token_data
                mock_post.return_value = mock_response
                
                # First request - cache miss
                start_time = time.perf_counter()
                success = client.authenticate()
                end_time = time.perf_counter()
                
                if success:
                    cache_misses += 1
                    miss_times.append(end_time - start_time)
                
                # Subsequent requests - should be cache hits
                for i in range(20):
                    start_time = time.perf_counter()
                    success = client.authenticate()
                    end_time = time.perf_counter()
                    
                    if success:
                        cache_hits += 1
                        hit_times.append(end_time - start_time)
            
            # Analyze cache effectiveness
            total_requests = cache_hits + cache_misses
            cache_hit_rate = cache_hits / total_requests if total_requests > 0 else 0
            
            avg_hit_time = statistics.mean(hit_times) if hit_times else 0
            avg_miss_time = statistics.mean(miss_times) if miss_times else 0
            
            logger.info(f"Token cache hit rate: {cache_hit_rate:.2%}")
            logger.info(f"Cache hit average time: {avg_hit_time:.6f}s")
            logger.info(f"Cache miss average time: {avg_miss_time:.4f}s")
            
            # Performance assertions
            assert cache_hit_rate >= PERFORMANCE_CONFIG["cache_hit_rate_target"]
            assert avg_hit_time < PERFORMANCE_CONFIG["response_time_targets"]["cache_hit"]
            
            if avg_miss_time > 0 and avg_hit_time > 0:
                speedup = avg_miss_time / avg_hit_time
                logger.info(f"Cache speedup: {speedup:.1f}x")
                assert speedup > 5, f"Cache not providing sufficient speedup: {speedup}x"