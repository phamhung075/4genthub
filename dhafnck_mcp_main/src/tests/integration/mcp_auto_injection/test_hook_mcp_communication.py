"""
Integration Tests for Hook-to-MCP Communication

Tests the complete communication flow between session hooks and the MCP server,
including authentication, request/response handling, and error scenarios.

Test Coverage:
- End-to-end hook-to-server communication
- Authentication integration with Keycloak
- Request routing and response parsing
- Error handling and fallback mechanisms
- Performance under load scenarios
"""

import pytest
import asyncio
import json
import time
import tempfile
import subprocess
from pathlib import Path
from unittest.mock import Mock, patch, MagicMock
from concurrent.futures import ThreadPoolExecutor, as_completed
import requests
from datetime import datetime, timedelta

# Import components for integration testing
from utils.mcp_client import get_default_client, ResilientMCPClient, OptimizedMCPClient
from utils.cache_manager import get_session_cache
from session_start import query_mcp_pending_tasks, query_mcp_next_task, load_development_context


@pytest.fixture
def mock_mcp_server():
    """Mock MCP server for integration testing."""
    class MockMCPServer:
        def __init__(self):
            self.request_count = 0
            self.response_delay = 0.1
            self.error_rate = 0.0
            self.responses = {
                "manage_task": {
                    "action_list": {
                        "success": True,
                        "data": {
                            "tasks": [
                                {"id": "task-1", "title": "Integration Test Task 1", "status": "todo", "priority": "high"},
                                {"id": "task-2", "title": "Integration Test Task 2", "status": "in_progress", "priority": "medium"}
                            ]
                        }
                    },
                    "action_next": {
                        "success": True,
                        "data": {
                            "id": "next-task",
                            "title": "Next Recommended Task",
                            "description": "This is the next task to work on",
                            "priority": "urgent"
                        }
                    }
                }
            }
        
        def configure_behavior(self, response_delay=0.1, error_rate=0.0):
            """Configure server behavior for testing."""
            self.response_delay = response_delay
            self.error_rate = error_rate
        
        def handle_request(self, endpoint, data):
            """Handle mock request and return appropriate response."""
            import random
            
            self.request_count += 1
            
            # Simulate network delay
            time.sleep(self.response_delay)
            
            # Simulate errors based on error rate
            if random.random() < self.error_rate:
                raise requests.exceptions.ConnectionError("Simulated server error")
            
            # Route request based on endpoint
            if endpoint == "manage_task":
                action = data.get("action", "list")
                response_key = f"action_{action}"
                return self.responses["manage_task"].get(response_key, {"success": False, "error": "Unknown action"})
            
            return {"success": False, "error": "Unknown endpoint"}
        
        def reset_stats(self):
            """Reset request statistics."""
            self.request_count = 0
    
    return MockMCPServer()


@pytest.fixture  
def temp_cache_environment():
    """Set up temporary cache environment for integration tests."""
    with tempfile.TemporaryDirectory() as temp_dir:
        cache_dir = Path(temp_dir) / "test_cache"
        cache_dir.mkdir(exist_ok=True)
        
        # Mock cache manager to use temp directory
        with patch('utils.cache_manager.SessionContextCache.__init__') as mock_init:
            mock_init.return_value = None
            yield cache_dir


class TestHookMCPBasicCommunication:
    """Test basic hook-to-MCP communication patterns."""
    
    def test_session_start_mcp_integration_success(self, mock_mcp_server, temp_cache_environment):
        """Test complete session start with successful MCP integration."""
        # Mock successful authentication and server responses
        with patch('utils.mcp_client.TokenManager.get_valid_token', return_value="test-token"):
            with patch('utils.mcp_client.MCPHTTPClient._make_request') as mock_request:
                mock_request.side_effect = lambda endpoint, data: mock_mcp_server.handle_request(endpoint, data)
                
                # Test full session start flow
                client = get_default_client()
                
                # Test authentication
                auth_result = client.authenticate()
                assert auth_result is True
                
                # Test pending tasks query
                tasks = client.query_pending_tasks(limit=5)
                assert tasks is not None
                assert len(tasks) == 2
                assert tasks[0]["id"] == "task-1"
                assert tasks[1]["id"] == "task-2"
                
                # Test next task query
                next_task = client.get_next_recommended_task("branch-123")
                assert next_task is not None
                assert next_task["id"] == "next-task"
                assert next_task["title"] == "Next Recommended Task"
                
                # Verify server received correct requests
                assert mock_mcp_server.request_count == 2
    
    def test_session_start_with_cache_integration(self, mock_mcp_server, temp_cache_environment):
        """Test session start with cache hit scenarios."""
        # Setup cache with pre-existing data
        cached_tasks = [
            {"id": "cached-1", "title": "Cached Task 1", "status": "todo"},
            {"id": "cached-2", "title": "Cached Task 2", "status": "in_progress"}
        ]
        
        with patch('utils.cache_manager.get_session_cache') as mock_cache_factory:
            mock_cache = Mock()
            mock_cache.get_pending_tasks.return_value = cached_tasks
            mock_cache.get_next_task.return_value = None  # Cache miss for next task
            mock_cache_factory.return_value = mock_cache
            
            with patch('utils.mcp_client.TokenManager.get_valid_token', return_value="test-token"):
                with patch('utils.mcp_client.MCPHTTPClient._make_request') as mock_request:
                    mock_request.side_effect = lambda endpoint, data: mock_mcp_server.handle_request(endpoint, data)
                    
                    # Query pending tasks - should hit cache
                    result = query_mcp_pending_tasks()
                    assert result == cached_tasks
                    
                    # Verify cache was queried but server wasn't
                    mock_cache.get_pending_tasks.assert_called_once()
                    assert mock_mcp_server.request_count == 0
                    
                    # Query next task - should hit server (cache miss)
                    next_result = query_mcp_next_task("branch-456")
                    assert next_result is not None
                    assert next_result["id"] == "next-task"
                    
                    # Verify server was called for next task
                    assert mock_mcp_server.request_count == 1
                    mock_cache.cache_next_task.assert_called_once()
    
    def test_authentication_integration_flow(self, mock_mcp_server):
        """Test complete authentication integration with Keycloak."""
        # Mock Keycloak token response
        mock_keycloak_response = {
            "access_token": "integration-test-jwt-token",
            "expires_in": 3600,
            "token_type": "Bearer"
        }
        
        with patch('requests.post') as mock_post:
            mock_response = Mock()
            mock_response.status_code = 200
            mock_response.json.return_value = mock_keycloak_response
            mock_post.return_value = mock_response
            
            with patch('utils.mcp_client.MCPHTTPClient._make_request') as mock_request:
                mock_request.side_effect = lambda endpoint, data: mock_mcp_server.handle_request(endpoint, data)
                
                # Create client and test full auth flow
                client = get_default_client()
                
                # Authentication should trigger token refresh
                assert client.authenticate() is True
                
                # Make API request - should use new token
                tasks = client.query_pending_tasks(limit=3)
                assert tasks is not None
                assert len(tasks) == 2
                
                # Verify Keycloak was called for token
                mock_post.assert_called_once()
                call_args = mock_post.call_args
                assert "protocol/openid-connect/token" in call_args[0][0]
                
                # Verify MCP server received request
                assert mock_mcp_server.request_count == 1


class TestHookMCPErrorHandling:
    """Test error handling in hook-to-MCP communication."""
    
    def test_server_unavailable_fallback_to_cache(self, mock_mcp_server, temp_cache_environment):
        """Test fallback to cache when MCP server is unavailable."""
        # Configure server to always fail
        mock_mcp_server.configure_behavior(error_rate=1.0)
        
        # Setup cache with fallback data
        cached_tasks = [{"id": "fallback-1", "title": "Cached Fallback Task"}]
        
        with patch('utils.cache_manager.get_session_cache') as mock_cache_factory:
            mock_cache = Mock()
            mock_cache.get_pending_tasks.return_value = cached_tasks
            mock_cache_factory.return_value = mock_cache
            
            with patch('utils.mcp_client.TokenManager.get_valid_token', return_value="test-token"):
                with patch('utils.mcp_client.MCPHTTPClient._make_request') as mock_request:
                    mock_request.side_effect = lambda endpoint, data: mock_mcp_server.handle_request(endpoint, data)
                    
                    # Use resilient client for fallback testing
                    client = ResilientMCPClient()
                    client.fallback_strategy = "cache_then_skip"
                    
                    # Query should fall back to cache
                    result = query_mcp_pending_tasks()
                    assert result == cached_tasks
                    
                    # Verify cache was used as fallback
                    mock_cache.get_pending_tasks.assert_called_once()
    
    def test_authentication_failure_handling(self, mock_mcp_server):
        """Test handling of authentication failures."""
        # Mock failed Keycloak response
        with patch('requests.post') as mock_post:
            mock_response = Mock()
            mock_response.status_code = 401
            mock_response.json.return_value = {"error": "invalid_client"}
            mock_post.return_value = mock_response
            
            client = get_default_client()
            
            # Authentication should fail gracefully
            assert client.authenticate() is False
            
            # Subsequent requests should handle auth failure
            with pytest.raises(Exception):
                client.query_pending_tasks(limit=5)
    
    def test_partial_server_failure_resilience(self, mock_mcp_server):
        """Test resilience to partial server failures."""
        # Configure intermittent failures (50% error rate)
        mock_mcp_server.configure_behavior(error_rate=0.5)
        
        with patch('utils.mcp_client.TokenManager.get_valid_token', return_value="test-token"):
            with patch('utils.mcp_client.MCPHTTPClient._make_request') as mock_request:
                def request_with_retries(endpoint, data):
                    """Simulate request with retry logic."""
                    max_retries = 3
                    for attempt in range(max_retries):
                        try:
                            return mock_mcp_server.handle_request(endpoint, data)
                        except requests.exceptions.ConnectionError:
                            if attempt == max_retries - 1:
                                raise
                            time.sleep(0.1 * (attempt + 1))  # Exponential backoff
                
                mock_request.side_effect = request_with_retries
                
                # Use resilient client
                client = ResilientMCPClient()
                client.max_retries = 3
                client.retry_delay = 0.1
                
                # Test multiple requests - some should succeed despite failures
                successful_requests = 0
                failed_requests = 0
                
                for i in range(10):
                    try:
                        result = client.query_pending_tasks(limit=5)
                        if result is not None:
                            successful_requests += 1
                    except Exception:
                        failed_requests += 1
                
                # Should have some successful requests despite failures
                assert successful_requests > 0
                print(f"Integration test: {successful_requests} successful, {failed_requests} failed requests")


class TestHookMCPPerformanceIntegration:
    """Test performance characteristics of hook-to-MCP integration."""
    
    def test_concurrent_session_starts(self, mock_mcp_server):
        """Test concurrent session start scenarios."""
        mock_mcp_server.configure_behavior(response_delay=0.05)  # 50ms delay
        
        with patch('utils.mcp_client.TokenManager.get_valid_token', return_value="test-token"):
            with patch('utils.mcp_client.MCPHTTPClient._make_request') as mock_request:
                mock_request.side_effect = lambda endpoint, data: mock_mcp_server.handle_request(endpoint, data)
                
                def simulate_session_start(session_id):
                    """Simulate a session start process."""
                    start_time = time.time()
                    
                    try:
                        client = get_default_client()
                        tasks = client.query_pending_tasks(limit=5)
                        next_task = client.get_next_recommended_task(f"branch-{session_id}")
                        
                        duration = time.time() - start_time
                        return {
                            "session_id": session_id,
                            "success": True,
                            "duration": duration,
                            "tasks_count": len(tasks) if tasks else 0,
                            "has_next_task": next_task is not None
                        }
                    except Exception as e:
                        return {
                            "session_id": session_id,
                            "success": False,
                            "error": str(e),
                            "duration": time.time() - start_time
                        }
                
                # Run concurrent session starts
                concurrent_sessions = 5
                with ThreadPoolExecutor(max_workers=concurrent_sessions) as executor:
                    futures = [
                        executor.submit(simulate_session_start, i) 
                        for i in range(concurrent_sessions)
                    ]
                    results = [future.result() for future in as_completed(futures)]
                
                # Analyze results
                successful_sessions = [r for r in results if r["success"]]
                failed_sessions = [r for r in results if not r["success"]]
                
                assert len(successful_sessions) >= concurrent_sessions // 2, "Too many sessions failed"
                
                # Check performance
                avg_duration = sum(r["duration"] for r in successful_sessions) / len(successful_sessions)
                assert avg_duration < 1.0, f"Sessions too slow: {avg_duration:.2f}s average"
                
                # Verify all successful sessions got data
                for result in successful_sessions:
                    assert result["tasks_count"] > 0, "Session didn't retrieve tasks"
                    assert result["has_next_task"], "Session didn't get next task"
                
                print(f"Concurrent integration test: {len(successful_sessions)}/{concurrent_sessions} sessions successful")
                print(f"Average session duration: {avg_duration:.3f}s")
    
    def test_cache_performance_integration(self, temp_cache_environment):
        """Test cache performance in integration scenarios."""
        # Pre-populate cache with test data
        test_tasks = [
            {"id": f"perf-task-{i}", "title": f"Performance Task {i}", "status": "todo"}
            for i in range(50)  # Larger dataset
        ]
        
        with patch('utils.cache_manager.get_session_cache') as mock_cache_factory:
            # Use real cache operations but mocked file system
            from utils.cache_manager import SessionContextCache
            
            cache = SessionContextCache()
            cache.cache_dir = temp_cache_environment
            cache.lock = Mock()  # Mock lock for testing
            
            mock_cache_factory.return_value = cache
            
            # Test cache write performance
            write_start = time.time()
            cache.cache_pending_tasks(test_tasks)
            write_duration = time.time() - write_start
            
            # Test cache read performance (multiple reads)
            read_times = []
            for i in range(10):
                read_start = time.time()
                result = cache.get_pending_tasks()
                read_times.append(time.time() - read_start)
                
                assert result == test_tasks, f"Cache read {i} failed"
            
            avg_read_time = sum(read_times) / len(read_times)
            
            # Performance assertions
            assert write_duration < 0.1, f"Cache write too slow: {write_duration:.3f}s"
            assert avg_read_time < 0.01, f"Cache read too slow: {avg_read_time:.3f}s"
            
            print(f"Cache performance: write {write_duration:.3f}s, avg read {avg_read_time:.3f}s")
    
    def test_optimized_client_connection_pooling(self, mock_mcp_server):
        """Test connection pooling performance with OptimizedMCPClient."""
        mock_mcp_server.configure_behavior(response_delay=0.02)  # 20ms delay
        
        with patch('utils.mcp_client.TokenManager.get_valid_token', return_value="test-token"):
            with patch('utils.mcp_client.MCPHTTPClient._make_request') as mock_request:
                mock_request.side_effect = lambda endpoint, data: mock_mcp_server.handle_request(endpoint, data)
                
                # Test with optimized client
                client = OptimizedMCPClient()
                
                def make_concurrent_requests():
                    """Make concurrent requests to test connection pooling."""
                    concurrent_requests = 5
                    
                    def single_request():
                        return client.query_pending_tasks(limit=3)
                    
                    start_time = time.time()
                    with ThreadPoolExecutor(max_workers=concurrent_requests) as executor:
                        futures = [executor.submit(single_request) for _ in range(concurrent_requests)]
                        results = [future.result() for future in as_completed(futures)]
                    
                    duration = time.time() - start_time
                    return duration, results
                
                # Test multiple batches of concurrent requests
                batch_times = []
                for batch in range(3):
                    duration, results = make_concurrent_requests()
                    batch_times.append(duration)
                    
                    # All requests should succeed
                    assert all(r is not None for r in results), f"Batch {batch} had failed requests"
                
                avg_batch_time = sum(batch_times) / len(batch_times)
                
                # Connection pooling should keep batch time reasonable
                assert avg_batch_time < 0.5, f"Connection pooling not effective: {avg_batch_time:.3f}s per batch"
                
                print(f"Connection pooling test: {avg_batch_time:.3f}s average per 5-request batch")


class TestHookMCPFullIntegration:
    """Test complete end-to-end integration scenarios."""
    
    def test_complete_session_lifecycle_integration(self, mock_mcp_server, temp_cache_environment):
        """Test complete session lifecycle from start to context injection."""
        # Configure realistic server behavior
        mock_mcp_server.configure_behavior(response_delay=0.1, error_rate=0.1)
        
        with patch('utils.mcp_client.TokenManager.get_valid_token', return_value="lifecycle-token"):
            with patch('utils.mcp_client.MCPHTTPClient._make_request') as mock_request:
                mock_request.side_effect = lambda endpoint, data: mock_mcp_server.handle_request(endpoint, data)
                
                with patch('subprocess.run') as mock_subprocess:
                    # Mock git commands
                    mock_branch = Mock(returncode=0, stdout="integration-branch\n")
                    mock_status = Mock(returncode=0, stdout="M test_file.py\n")
                    mock_log = Mock(returncode=0, stdout="abc123 Integration test commit\n")
                    mock_subprocess.side_effect = [mock_branch, mock_status, mock_log]
                    
                    with patch('pathlib.Path.exists', return_value=False):
                        with patch('session_start.get_recent_issues', return_value=None):
                            # Test complete context loading
                            context = load_development_context("startup")
                            
                            # Verify context contains all expected elements
                            assert "🚀 INITIALIZATION REQUIRED" in context
                            assert "call_agent('master-orchestrator-agent')" in context
                            assert "Session source: startup" in context
                            
                            # Check MCP context injection
                            if mock_mcp_server.request_count > 0:
                                assert "=== MCP LIVE CONTEXT ===" in context
                                assert "📋 **Current Pending Tasks:**" in context
                                assert "Integration Test Task" in context
                            else:
                                assert "⚠️ **MCP Status:** Server unavailable" in context
                            
                            # Check git context
                            assert "🌿 **Git Status:**" in context
                            assert "Branch: integration-branch" in context
                            assert "Uncommitted changes: 1 files" in context
                            
                            # Check performance stats
                            assert "--- Context Generation Stats ---" in context
                            assert "MCP tasks loaded:" in context
                            assert "Git context:" in context
                
                print(f"Full lifecycle integration: {mock_mcp_server.request_count} MCP requests made")
    
    def test_resilience_under_mixed_conditions(self, mock_mcp_server, temp_cache_environment):
        """Test system resilience under mixed success/failure conditions."""
        # Configure mixed conditions - moderate failure rate
        mock_mcp_server.configure_behavior(response_delay=0.05, error_rate=0.3)
        
        # Setup cache with some pre-existing data
        cached_data = [{"id": "cache-resilience", "title": "Cached for Resilience"}]
        
        with patch('utils.cache_manager.get_session_cache') as mock_cache_factory:
            mock_cache = Mock()
            mock_cache.get_pending_tasks.return_value = None  # Force server query
            mock_cache.cache_pending_tasks.return_value = True
            mock_cache_factory.return_value = mock_cache
            
            with patch('utils.mcp_client.TokenManager.get_valid_token', return_value="resilience-token"):
                with patch('utils.mcp_client.MCPHTTPClient._make_request') as mock_request:
                    def resilient_request(endpoint, data):
                        """Request with fallback behavior."""
                        try:
                            return mock_mcp_server.handle_request(endpoint, data)
                        except requests.exceptions.ConnectionError:
                            # Fallback to cached data
                            if endpoint == "manage_task" and data.get("action") == "list":
                                return {"success": True, "data": {"tasks": cached_data}}
                            raise
                    
                    mock_request.side_effect = resilient_request
                    
                    # Test multiple queries with resilient client
                    client = ResilientMCPClient()
                    client.fallback_strategy = "cache_then_skip"
                    
                    successful_queries = 0
                    total_queries = 20
                    
                    for i in range(total_queries):
                        try:
                            result = client.query_pending_tasks(limit=3)
                            if result is not None:
                                successful_queries += 1
                        except Exception:
                            # Some failures are expected
                            pass
                    
                    success_rate = successful_queries / total_queries
                    
                    # Should maintain reasonable success rate despite failures
                    assert success_rate > 0.5, f"Success rate too low: {success_rate:.1%}"
                    
                    print(f"Resilience test: {success_rate:.1%} success rate under mixed conditions")
                    print(f"Total MCP server requests: {mock_mcp_server.request_count}")


@pytest.mark.performance
class TestHookMCPPerformanceTargets:
    """Test performance targets for hook-to-MCP integration."""
    
    def test_session_start_performance_target(self, mock_mcp_server):
        """Test that session start meets performance targets."""
        mock_mcp_server.configure_behavior(response_delay=0.05)  # Realistic network delay
        
        with patch('utils.mcp_client.TokenManager.get_valid_token', return_value="perf-token"):
            with patch('utils.mcp_client.MCPHTTPClient._make_request') as mock_request:
                mock_request.side_effect = lambda endpoint, data: mock_mcp_server.handle_request(endpoint, data)
                
                # Measure session start performance
                start_time = time.time()
                
                # Simulate session start operations
                client = get_default_client()
                client.authenticate()
                
                tasks = client.query_pending_tasks(limit=5)
                next_task = client.get_next_recommended_task("perf-branch")
                
                total_duration = time.time() - start_time
                
                # Performance targets
                TARGET_SESSION_START_TIME = 2.0  # 2 seconds
                
                assert total_duration < TARGET_SESSION_START_TIME, (
                    f"Session start too slow: {total_duration:.3f}s > {TARGET_SESSION_START_TIME}s"
                )
                
                # Verify functionality
                assert tasks is not None, "Session start failed to retrieve tasks"
                assert next_task is not None, "Session start failed to get next task"
                assert len(tasks) > 0, "No tasks retrieved"
                
                print(f"Session start performance: {total_duration:.3f}s (target: {TARGET_SESSION_START_TIME}s)")
    
    def test_token_overhead_performance_target(self, mock_mcp_server):
        """Test that token management overhead meets targets."""
        # Test token management performance impact
        iterations = 10
        
        # Test without token management (mock direct requests)
        start_time = time.time()
        for i in range(iterations):
            mock_mcp_server.handle_request("manage_task", {"action": "list"})
        baseline_time = time.time() - start_time
        
        # Test with full token management
        with patch('utils.mcp_client.TokenManager.get_valid_token', return_value="overhead-token"):
            with patch('utils.mcp_client.MCPHTTPClient._make_request') as mock_request:
                mock_request.side_effect = lambda endpoint, data: mock_mcp_server.handle_request(endpoint, data)
                
                client = get_default_client()
                
                start_time = time.time()
                for i in range(iterations):
                    client.query_pending_tasks(limit=5)
                with_token_time = time.time() - start_time
        
        # Token overhead calculation
        token_overhead = with_token_time - baseline_time
        overhead_per_request = token_overhead / iterations
        
        # Performance target: <10ms overhead per request
        TARGET_TOKEN_OVERHEAD = 0.01  # 10ms
        
        assert overhead_per_request < TARGET_TOKEN_OVERHEAD, (
            f"Token overhead too high: {overhead_per_request:.3f}s > {TARGET_TOKEN_OVERHEAD}s per request"
        )
        
        print(f"Token overhead: {overhead_per_request:.3f}s per request (target: {TARGET_TOKEN_OVERHEAD}s)")
        print(f"Total overhead for {iterations} requests: {token_overhead:.3f}s")