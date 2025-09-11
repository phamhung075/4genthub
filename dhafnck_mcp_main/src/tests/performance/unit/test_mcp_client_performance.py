"""
Unit Performance Tests for MCP HTTP Client

Tests individual MCP client components for performance metrics:
- Token management performance
- Connection pooling efficiency  
- Rate limiting behavior
- Cache hit rates
- Response time validation
"""

import asyncio
import pytest
import time
import statistics
import json
import os
from unittest.mock import Mock, patch, MagicMock
from pathlib import Path
from concurrent.futures import ThreadPoolExecutor, as_completed
import tempfile
import threading

# Import the components under test
import sys
test_dir = Path(__file__).parent.parent.parent.parent.parent
sys.path.insert(0, str(test_dir / ".claude" / "hooks" / "utils"))

from mcp_client import (
    TokenManager, 
    RateLimiter, 
    MCPHTTPClient,
    ResilientMCPClient,
    OptimizedMCPClient,
    create_mcp_client,
    get_default_client
)

# Import performance test config
from ..mocks.mock_mcp_server import MockMCPServer, MockKeycloakServer
from .. import PERFORMANCE_CONFIG, setup_performance_logger

logger = setup_performance_logger()


class TestTokenManagerPerformance:
    """Performance tests for JWT token management."""
    
    @pytest.fixture
    def token_manager(self):
        """Create token manager with test configuration."""
        with tempfile.TemporaryDirectory() as temp_dir:
            temp_cache = Path(temp_dir) / ".mcp_token_cache"
            
            with patch.object(TokenManager, '__init__') as mock_init:
                mock_init.return_value = None
                tm = TokenManager()
                tm.token_cache_file = temp_cache
                tm.token = None
                tm.token_expiry = None
                tm.refresh_before = 60
                tm.keycloak_config = {
                    "url": "http://localhost:8080",
                    "realm": "dhafnck", 
                    "client_id": "claude-hooks",
                    "client_secret": "test-secret"
                }
                yield tm
    
    @pytest.mark.performance
    def test_token_cache_performance(self, token_manager):
        """Test token caching performance metrics."""
        iterations = PERFORMANCE_CONFIG["test_iterations"]
        
        # Mock successful token response
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "access_token": "test-token",
            "expires_in": 3600
        }
        
        cache_times = []
        read_times = []
        
        with patch('requests.post', return_value=mock_response):
            for i in range(iterations):
                # Test cache write performance
                start_time = time.perf_counter()
                token_manager._refresh_token()
                cache_time = time.perf_counter() - start_time
                cache_times.append(cache_time)
                
                # Test cache read performance
                start_time = time.perf_counter()
                token_manager._load_cached_token()
                read_time = time.perf_counter() - start_time
                read_times.append(read_time)
        
        # Performance assertions
        avg_cache_time = statistics.mean(cache_times)
        avg_read_time = statistics.mean(read_times)
        
        logger.info(f"Token cache write time: {avg_cache_time:.4f}s (avg)")
        logger.info(f"Token cache read time: {avg_read_time:.4f}s (avg)")
        
        # Cache operations should be very fast
        assert avg_cache_time < 0.01, f"Token caching too slow: {avg_cache_time}s"
        assert avg_read_time < 0.005, f"Token reading too slow: {avg_read_time}s"
    
    @pytest.mark.performance
    def test_concurrent_token_access(self, token_manager):
        """Test thread-safe token access performance."""
        concurrent_sessions = PERFORMANCE_CONFIG["concurrent_sessions"]
        
        # Mock successful token response
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "access_token": "test-token", 
            "expires_in": 3600
        }
        
        results = []
        
        def get_token_worker():
            """Worker function for concurrent token access."""
            start_time = time.perf_counter()
            with patch('requests.post', return_value=mock_response):
                token = token_manager.get_valid_token()
            end_time = time.perf_counter()
            return {
                "token": token,
                "duration": end_time - start_time,
                "thread_id": threading.get_ident()
            }
        
        # Execute concurrent token requests
        start_time = time.perf_counter()
        with ThreadPoolExecutor(max_workers=concurrent_sessions) as executor:
            futures = [executor.submit(get_token_worker) for _ in range(concurrent_sessions)]
            results = [future.result() for future in as_completed(futures)]
        total_time = time.perf_counter() - start_time
        
        # Analyze results
        all_successful = all(r["token"] is not None for r in results)
        avg_duration = statistics.mean([r["duration"] for r in results])
        unique_threads = len(set(r["thread_id"] for r in results))
        
        logger.info(f"Concurrent token access: {concurrent_sessions} requests in {total_time:.4f}s")
        logger.info(f"Average request duration: {avg_duration:.4f}s")
        logger.info(f"Unique threads used: {unique_threads}")
        
        # Performance and correctness assertions
        assert all_successful, "Some token requests failed"
        assert avg_duration < 0.1, f"Concurrent token access too slow: {avg_duration}s"
        assert total_time < 1.0, f"Total concurrent execution too slow: {total_time}s"


class TestRateLimiterPerformance:
    """Performance tests for rate limiting functionality."""
    
    @pytest.fixture
    def rate_limiter(self):
        """Create rate limiter for testing."""
        return RateLimiter(max_requests=10, time_window=1)
    
    @pytest.mark.performance
    def test_rate_limit_performance(self, rate_limiter):
        """Test rate limiting performance and accuracy."""
        iterations = 20  # More than limit to test blocking
        
        allowed_count = 0
        blocked_count = 0
        response_times = []
        
        for i in range(iterations):
            start_time = time.perf_counter()
            allowed = rate_limiter.allow_request()
            end_time = time.perf_counter()
            
            response_times.append(end_time - start_time)
            
            if allowed:
                allowed_count += 1
            else:
                blocked_count += 1
        
        avg_response_time = statistics.mean(response_times)
        max_response_time = max(response_times)
        
        logger.info(f"Rate limiter: {allowed_count} allowed, {blocked_count} blocked")
        logger.info(f"Average response time: {avg_response_time:.6f}s")
        logger.info(f"Max response time: {max_response_time:.6f}s")
        
        # Performance assertions
        assert avg_response_time < 0.001, f"Rate limiter too slow: {avg_response_time}s"
        assert max_response_time < 0.005, f"Rate limiter inconsistent: {max_response_time}s"
        
        # Functional assertions
        assert allowed_count == 10, f"Expected 10 allowed, got {allowed_count}"
        assert blocked_count == 10, f"Expected 10 blocked, got {blocked_count}"
    
    @pytest.mark.performance 
    def test_concurrent_rate_limiting(self, rate_limiter):
        """Test rate limiter thread safety under concurrent load."""
        concurrent_requests = 50
        
        def make_request():
            """Worker function for concurrent requests."""
            start_time = time.perf_counter()
            allowed = rate_limiter.allow_request()
            duration = time.perf_counter() - start_time
            return {"allowed": allowed, "duration": duration}
        
        # Execute concurrent requests
        with ThreadPoolExecutor(max_workers=10) as executor:
            futures = [executor.submit(make_request) for _ in range(concurrent_requests)]
            results = [future.result() for future in as_completed(futures)]
        
        allowed_count = sum(1 for r in results if r["allowed"])
        avg_duration = statistics.mean([r["duration"] for r in results])
        
        logger.info(f"Concurrent rate limiting: {allowed_count}/{concurrent_requests} allowed")
        logger.info(f"Average duration: {avg_duration:.6f}s")
        
        # Should still respect rate limit under concurrency
        assert allowed_count <= rate_limiter.max_requests, "Rate limit exceeded under concurrency"
        assert avg_duration < 0.001, f"Concurrent rate limiting too slow: {avg_duration}s"


class TestMCPClientPerformance:
    """Performance tests for MCP HTTP client classes."""
    
    @pytest.fixture
    def mock_server(self):
        """Create mock MCP server for testing."""
        server = MockMCPServer(response_delay=0.1, error_rate=0.0)
        yield server
        server.reset_metrics()
    
    @pytest.mark.performance
    async def test_basic_client_performance(self, mock_server):
        """Test basic MCP client performance metrics."""
        client = MCPHTTPClient()
        
        # Mock authentication
        with patch.object(client, 'authenticate', return_value=True):
            with patch.object(client.session, 'post') as mock_post:
                # Configure mock response
                mock_response = Mock()
                mock_response.status_code = 200
                mock_response.json.return_value = await mock_server.handle_manage_task({
                    "action": "list",
                    "status": "todo",
                    "limit": 5
                })
                mock_post.return_value = mock_response
                
                # Performance test
                iterations = PERFORMANCE_CONFIG["test_iterations"] 
                response_times = []
                
                for i in range(iterations):
                    start_time = time.perf_counter()
                    result = client.query_pending_tasks(limit=5)
                    end_time = time.perf_counter()
                    
                    response_times.append(end_time - start_time)
                    assert result is not None, f"Request {i} failed"
                
                # Analyze performance
                avg_time = statistics.mean(response_times)
                p95_time = statistics.quantiles(response_times, n=20)[18]  # 95th percentile
                
                logger.info(f"Basic client average response time: {avg_time:.4f}s")
                logger.info(f"Basic client P95 response time: {p95_time:.4f}s")
                
                # Performance targets
                assert avg_time < PERFORMANCE_CONFIG["response_time_targets"]["mcp_query"]
                assert p95_time < PERFORMANCE_CONFIG["response_time_targets"]["mcp_query"] * 2
    
    @pytest.mark.performance
    async def test_resilient_client_fallback_performance(self, mock_server):
        """Test resilient client fallback strategy performance."""
        # Configure server with high error rate
        mock_server.configure_behavior(error_rate=0.5)
        
        client = ResilientMCPClient()
        client.fallback_strategy = "cache_then_skip"
        
        with patch.object(client, 'authenticate', return_value=True):
            with patch.object(client.session, 'post') as mock_post:
                
                def mock_post_side_effect(*args, **kwargs):
                    # Simulate intermittent failures
                    if mock_server.should_simulate_error():
                        raise ConnectionError("Simulated connection error")
                    
                    mock_response = Mock()
                    mock_response.status_code = 200
                    mock_response.json.return_value = {"success": True, "data": {"tasks": []}}
                    return mock_response
                
                mock_post.side_effect = mock_post_side_effect
                
                # Test fallback performance
                iterations = 20
                successful_requests = 0
                response_times = []
                
                for i in range(iterations):
                    start_time = time.perf_counter()
                    result = client.query_pending_tasks(limit=5)
                    end_time = time.perf_counter()
                    
                    response_times.append(end_time - start_time)
                    if result is not None:
                        successful_requests += 1
                
                success_rate = successful_requests / iterations
                avg_time = statistics.mean(response_times)
                
                logger.info(f"Resilient client success rate: {success_rate:.2%}")
                logger.info(f"Resilient client average time: {avg_time:.4f}s")
                
                # Should handle failures gracefully without excessive delay
                assert avg_time < PERFORMANCE_CONFIG["response_time_targets"]["mcp_query"] * 3
                assert success_rate > 0.3, "Too many requests failed even with fallbacks"
    
    @pytest.mark.performance
    async def test_optimized_client_performance(self, mock_server):
        """Test optimized client with connection pooling performance."""
        client = OptimizedMCPClient()
        
        with patch.object(client, 'authenticate', return_value=True):
            with patch.object(client.session, 'post') as mock_post:
                
                mock_response = Mock()
                mock_response.status_code = 200
                mock_response.json.return_value = await mock_server.handle_manage_task({
                    "action": "list", 
                    "status": "todo",
                    "limit": 5
                })
                mock_post.return_value = mock_response
                
                # Test connection pooling benefit
                iterations = PERFORMANCE_CONFIG["test_iterations"]
                concurrent_requests = 5
                
                def make_concurrent_requests():
                    """Make multiple concurrent requests."""
                    start_time = time.perf_counter()
                    with ThreadPoolExecutor(max_workers=concurrent_requests) as executor:
                        futures = [
                            executor.submit(client.query_pending_tasks, 5) 
                            for _ in range(concurrent_requests)
                        ]
                        results = [f.result() for f in as_completed(futures)]
                    end_time = time.perf_counter()
                    return end_time - start_time, results
                
                concurrent_times = []
                for i in range(iterations // 5):  # Test concurrent batches
                    duration, results = make_concurrent_requests()
                    concurrent_times.append(duration)
                    assert all(r is not None for r in results), f"Batch {i} had failures"
                
                avg_concurrent_time = statistics.mean(concurrent_times)
                
                logger.info(f"Optimized client concurrent batch time: {avg_concurrent_time:.4f}s")
                
                # Connection pooling should improve concurrent performance
                expected_sequential_time = concurrent_requests * PERFORMANCE_CONFIG["response_time_targets"]["mcp_query"]
                assert avg_concurrent_time < expected_sequential_time * 0.8, "Connection pooling not effective"


class TestCachePerformance:
    """Performance tests for cache hit rates and response times."""
    
    @pytest.mark.performance
    async def test_cache_hit_performance(self, tmp_path):
        """Test cache hit rates and performance under load."""
        # Import cache manager
        cache_dir = tmp_path / "test_cache"
        sys.path.insert(0, str(test_dir / ".claude" / "hooks" / "utils"))
        from cache_manager import CacheManager
        
        cache = CacheManager(str(cache_dir))
        
        # Test data
        test_data = {"tasks": [{"id": "task-1", "title": "Test Task"}]}
        cache_key = "pending_tasks"
        
        # Populate cache
        cache.set(cache_key, test_data, ttl=3600)
        
        # Test cache hit performance
        iterations = PERFORMANCE_CONFIG["test_iterations"]
        hit_times = []
        
        for i in range(iterations):
            start_time = time.perf_counter()
            result = cache.get(cache_key)
            end_time = time.perf_counter()
            
            hit_times.append(end_time - start_time)
            assert result == test_data, f"Cache miss on iteration {i}"
        
        avg_hit_time = statistics.mean(hit_times)
        p95_hit_time = statistics.quantiles(hit_times, n=20)[18]
        
        logger.info(f"Cache hit average time: {avg_hit_time:.6f}s")
        logger.info(f"Cache hit P95 time: {p95_hit_time:.6f}s")
        
        # Cache hits should be extremely fast
        assert avg_hit_time < PERFORMANCE_CONFIG["response_time_targets"]["cache_hit"]
        assert p95_hit_time < PERFORMANCE_CONFIG["response_time_targets"]["cache_hit"] * 2
    
    @pytest.mark.performance
    async def test_concurrent_cache_access(self, tmp_path):
        """Test cache performance under concurrent access."""
        cache_dir = tmp_path / "test_cache_concurrent"
        from cache_manager import CacheManager
        
        cache = CacheManager(str(cache_dir))
        test_data = {"shared_data": "test_value"}
        cache.set("shared_key", test_data)
        
        concurrent_sessions = PERFORMANCE_CONFIG["concurrent_sessions"]
        
        def cache_worker():
            """Worker for concurrent cache access."""
            start_time = time.perf_counter()
            result = cache.get("shared_key")
            duration = time.perf_counter() - start_time
            return {"data": result, "duration": duration}
        
        # Execute concurrent cache access
        with ThreadPoolExecutor(max_workers=concurrent_sessions) as executor:
            futures = [executor.submit(cache_worker) for _ in range(concurrent_sessions)]
            results = [f.result() for f in as_completed(futures)]
        
        # Analyze results
        all_successful = all(r["data"] == test_data for r in results)
        avg_duration = statistics.mean([r["duration"] for r in results])
        
        logger.info(f"Concurrent cache access: {concurrent_sessions} requests")
        logger.info(f"Average duration: {avg_duration:.6f}s")
        
        assert all_successful, "Some concurrent cache reads failed"
        assert avg_duration < PERFORMANCE_CONFIG["response_time_targets"]["cache_hit"] * 2


@pytest.mark.performance
class TestPerformanceRegression:
    """Regression tests to ensure performance doesn't degrade."""
    
    def test_performance_targets_met(self):
        """Validate that all performance targets are achievable."""
        targets = PERFORMANCE_CONFIG["response_time_targets"]
        
        logger.info("Performance Targets:")
        for operation, target in targets.items():
            logger.info(f"  {operation}: {target}s")
        
        # This test serves as documentation and validation
        assert targets["mcp_query"] <= 0.5
        assert targets["cache_hit"] <= 0.01
        assert targets["full_injection"] <= 2.0
    
    def test_token_usage_target(self):
        """Validate token usage target is reasonable."""
        max_tokens = PERFORMANCE_CONFIG["max_tokens_per_injection"]
        
        logger.info(f"Token usage target: <{max_tokens} tokens per injection")
        
        # Validate target is achievable
        assert max_tokens == 100, "Token target should remain at 100 tokens"