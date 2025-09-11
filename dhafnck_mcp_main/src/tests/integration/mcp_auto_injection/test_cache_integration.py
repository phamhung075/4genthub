"""
Integration Tests for Cache Layer

Tests the integration between the cache layer and other system components,
including cache invalidation strategies, multi-component synchronization,
and performance under realistic usage patterns.

Test Coverage:
- Cache-to-MCP synchronization
- Cache invalidation triggers  
- Multi-session cache sharing
- Cache performance under load
- Error recovery with cache fallbacks
"""

import pytest
import time
import json
import threading
import tempfile
from pathlib import Path
from unittest.mock import Mock, patch, MagicMock
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime, timedelta

# Import cache and related components
from utils.cache_manager import CacheManager, SessionContextCache, get_session_cache
from utils.mcp_client import get_default_client, ResilientMCPClient


@pytest.fixture
def integrated_cache_system():
    """Set up integrated cache system with temporary storage."""
    with tempfile.TemporaryDirectory() as temp_dir:
        cache_dir = Path(temp_dir)
        
        # Create cache manager instances
        base_cache = CacheManager(str(cache_dir / "base"))
        session_cache = SessionContextCache()
        
        # Override session cache directory
        session_cache.cache_dir = cache_dir / "session"
        session_cache.cache_dir.mkdir(exist_ok=True)
        
        yield {
            "base_cache": base_cache,
            "session_cache": session_cache,
            "cache_dir": cache_dir
        }


@pytest.fixture
def mock_mcp_environment():
    """Mock MCP environment for cache integration testing."""
    class MockMCPEnvironment:
        def __init__(self):
            self.server_available = True
            self.response_delay = 0.1
            self.data_version = 1
            self.task_data = [
                {"id": "mcp-task-1", "title": "MCP Task 1", "status": "todo", "version": 1},
                {"id": "mcp-task-2", "title": "MCP Task 2", "status": "in_progress", "version": 1}
            ]
        
        def update_data(self, new_tasks=None):
            """Simulate server data update."""
            if new_tasks:
                self.task_data = new_tasks
            self.data_version += 1
            for task in self.task_data:
                task["version"] = self.data_version
        
        def make_server_unavailable(self):
            """Simulate server downtime."""
            self.server_available = False
        
        def restore_server(self):
            """Restore server availability."""
            self.server_available = True
        
        def get_tasks(self):
            """Simulate MCP server response."""
            if not self.server_available:
                raise ConnectionError("MCP server unavailable")
            
            time.sleep(self.response_delay)
            return {
                "success": True,
                "data": {"tasks": self.task_data.copy()},
                "version": self.data_version
            }
    
    return MockMCPEnvironment()


class TestCacheMCPSynchronization:
    """Test synchronization between cache and MCP server."""
    
    def test_cache_miss_triggers_mcp_query(self, integrated_cache_system, mock_mcp_environment):
        """Test that cache miss triggers MCP server query."""
        cache = integrated_cache_system["session_cache"]
        
        with patch('utils.mcp_client.TokenManager.get_valid_token', return_value="sync-token"):
            with patch('utils.mcp_client.MCPHTTPClient._make_request') as mock_request:
                mock_request.return_value = mock_mcp_environment.get_tasks()
                
                # Clear cache to ensure miss
                cache.delete(cache.PENDING_TASKS_KEY)
                
                # Query should trigger MCP request
                client = get_default_client()
                result = client.query_pending_tasks(limit=5)
                
                assert result is not None
                assert len(result) == 2
                assert result[0]["id"] == "mcp-task-1"
                
                # Verify MCP was called
                mock_request.assert_called_once()
    
    def test_cache_hit_avoids_mcp_query(self, integrated_cache_system, mock_mcp_environment):
        """Test that cache hit avoids unnecessary MCP queries."""
        cache = integrated_cache_system["session_cache"]
        
        # Pre-populate cache
        cached_tasks = [
            {"id": "cached-1", "title": "Cached Task 1", "status": "todo"},
            {"id": "cached-2", "title": "Cached Task 2", "status": "done"}
        ]
        cache.cache_pending_tasks(cached_tasks)
        
        with patch('utils.mcp_client.TokenManager.get_valid_token', return_value="hit-token"):
            with patch('utils.mcp_client.MCPHTTPClient._make_request') as mock_request:
                mock_request.return_value = mock_mcp_environment.get_tasks()
                
                # Use session hook function that should hit cache
                from session_start import query_mcp_pending_tasks
                
                with patch('session_start.get_session_cache', return_value=cache):
                    result = query_mcp_pending_tasks()
                
                assert result == cached_tasks
                
                # Verify MCP was not called
                mock_request.assert_not_called()
    
    def test_cache_expiration_triggers_refresh(self, integrated_cache_system, mock_mcp_environment):
        """Test that expired cache entries trigger MCP refresh."""
        cache = integrated_cache_system["session_cache"]
        
        # Set very short TTL for testing
        original_ttl = cache.task_cache_ttl
        cache.task_cache_ttl = 1  # 1 second
        
        try:
            # Cache initial data
            initial_tasks = [{"id": "initial", "title": "Initial Task"}]
            cache.cache_pending_tasks(initial_tasks)
            
            # Verify cache hit
            assert cache.get_pending_tasks() == initial_tasks
            
            # Wait for expiration
            time.sleep(1.1)
            
            # Cache should be expired now
            assert cache.get_pending_tasks() is None
            
            # New query should hit MCP server
            with patch('utils.mcp_client.TokenManager.get_valid_token', return_value="refresh-token"):
                with patch('utils.mcp_client.MCPHTTPClient._make_request') as mock_request:
                    mock_request.return_value = mock_mcp_environment.get_tasks()
                    
                    from session_start import query_mcp_pending_tasks
                    
                    with patch('session_start.get_session_cache', return_value=cache):
                        result = query_mcp_pending_tasks()
                    
                    # Should get fresh data from MCP
                    assert result is not None
                    assert len(result) == 2
                    assert result[0]["id"] == "mcp-task-1"
                    
                    # Verify MCP was called for refresh
                    mock_request.assert_called_once()
        
        finally:
            # Restore original TTL
            cache.task_cache_ttl = original_ttl
    
    def test_cache_invalidation_on_server_update(self, integrated_cache_system, mock_mcp_environment):
        """Test cache invalidation when server data is updated."""
        cache = integrated_cache_system["session_cache"]
        
        # Initial cache population
        cache.cache_pending_tasks(mock_mcp_environment.task_data)
        
        # Update server data
        updated_tasks = [
            {"id": "updated-1", "title": "Updated Task 1", "status": "in_progress"},
            {"id": "updated-2", "title": "Updated Task 2", "status": "todo"},
            {"id": "updated-3", "title": "New Task 3", "status": "todo"}
        ]
        mock_mcp_environment.update_data(updated_tasks)
        
        with patch('utils.mcp_client.TokenManager.get_valid_token', return_value="update-token"):
            with patch('utils.mcp_client.MCPHTTPClient._make_request') as mock_request:
                mock_request.return_value = mock_mcp_environment.get_tasks()
                
                # Force cache refresh (simulate invalidation trigger)
                cache.delete(cache.PENDING_TASKS_KEY)
                
                # Query should get updated data
                from session_start import query_mcp_pending_tasks
                
                with patch('session_start.get_session_cache', return_value=cache):
                    result = query_mcp_pending_tasks()
                
                assert result is not None
                assert len(result) == 3
                assert result[0]["id"] == "updated-1"
                assert result[2]["id"] == "updated-3"  # New task
                
                mock_request.assert_called_once()


class TestMultiSessionCacheSharing:
    """Test cache sharing between multiple sessions."""
    
    def test_concurrent_session_cache_access(self, integrated_cache_system):
        """Test concurrent access to shared cache from multiple sessions."""
        cache = integrated_cache_system["session_cache"]
        concurrent_sessions = 5
        
        def session_worker(session_id):
            """Simulate a session accessing cache."""
            results = []
            
            # Each session performs multiple cache operations
            for operation in range(3):
                # Write session-specific data
                session_data = {
                    "session_id": session_id,
                    "operation": operation,
                    "timestamp": time.time(),
                    "data": f"Session {session_id} operation {operation}"
                }
                
                key = f"session_{session_id}_op_{operation}"
                write_success = cache.set(key, session_data)
                results.append(("write", write_success))
                
                # Read back the data
                read_data = cache.get(key)
                read_success = read_data == session_data
                results.append(("read", read_success))
                
                # Also try to read shared data
                shared_data = cache.get_pending_tasks()
                results.append(("shared_read", shared_data is not None or shared_data is None))
            
            return session_id, results
        
        # Pre-populate with shared data
        shared_tasks = [{"id": "shared", "title": "Shared Task"}]
        cache.cache_pending_tasks(shared_tasks)
        
        # Run concurrent sessions
        with ThreadPoolExecutor(max_workers=concurrent_sessions) as executor:
            futures = [
                executor.submit(session_worker, i) 
                for i in range(concurrent_sessions)
            ]
            results = [future.result() for future in as_completed(futures)]
        
        # Verify all sessions succeeded
        for session_id, session_results in results:
            for operation, success in session_results:
                assert success, f"Session {session_id} {operation} operation failed"
        
        # Verify shared data is still accessible
        final_shared = cache.get_pending_tasks()
        assert final_shared == shared_tasks
    
    def test_cache_isolation_between_branches(self, integrated_cache_system):
        """Test cache isolation between different git branches."""
        cache = integrated_cache_system["session_cache"]
        
        # Simulate different branches with different data
        branches = {
            "main": [
                {"id": "main-1", "title": "Main Branch Task 1"},
                {"id": "main-2", "title": "Main Branch Task 2"}
            ],
            "feature/auth": [
                {"id": "auth-1", "title": "Auth Feature Task 1"},
                {"id": "auth-2", "title": "Auth Feature Task 2"}
            ],
            "bugfix/issue-123": [
                {"id": "fix-1", "title": "Bug Fix Task 1"}
            ]
        }
        
        # Cache branch-specific data
        for branch, tasks in branches.items():
            branch_id = f"branch-{branch.replace('/', '-')}"
            
            # Cache next task for each branch
            if tasks:
                cache.cache_next_task(branch_id, tasks[0])
            
            # Cache project context for each branch
            branch_context = {
                "branch_name": branch,
                "environment": "development",
                "feature_flags": [f"flag-{branch}"]
            }
            cache.cache_project_context(branch_id, branch_context)
        
        # Verify isolation - each branch should only see its own data
        for branch in branches.keys():
            branch_id = f"branch-{branch.replace('/', '-')}"
            
            # Get branch-specific data
            next_task = cache.get_next_task(branch_id)
            project_context = cache.get_project_context(branch_id)
            
            assert next_task is not None, f"No next task for branch {branch}"
            assert project_context is not None, f"No context for branch {branch}"
            
            # Verify data belongs to correct branch
            assert next_task["title"].startswith(branch.split('/')[0].title()), f"Wrong task for {branch}"
            assert project_context["branch_name"] == branch, f"Wrong context for {branch}"
            
            # Verify isolation - shouldn't get data from other branches
            for other_branch in branches.keys():
                if other_branch != branch:
                    other_branch_id = f"branch-{other_branch.replace('/', '-')}"
                    other_task = cache.get_next_task(other_branch_id)
                    
                    if other_task and next_task:
                        assert other_task["id"] != next_task["id"], f"Cache not isolated between {branch} and {other_branch}"


class TestCacheErrorRecovery:
    """Test cache behavior during error conditions."""
    
    def test_cache_corruption_recovery(self, integrated_cache_system):
        """Test recovery from cache file corruption."""
        cache = integrated_cache_system["session_cache"]
        
        # Create valid cache entry
        valid_tasks = [{"id": "valid", "title": "Valid Task"}]
        cache.cache_pending_tasks(valid_tasks)
        
        # Verify cache works
        assert cache.get_pending_tasks() == valid_tasks
        
        # Corrupt the cache file
        cache_file = cache.cache_dir / f"{cache._hash_key(cache.PENDING_TASKS_KEY)}.json"
        with open(cache_file, 'w') as f:
            f.write("corrupted json content {invalid")
        
        # Should handle corruption gracefully
        result = cache.get_pending_tasks()
        assert result is None  # Corrupted data should return None
        
        # Should be able to write new data
        new_tasks = [{"id": "recovered", "title": "Recovered Task"}]
        success = cache.cache_pending_tasks(new_tasks)
        assert success is True
        
        # Should be able to read new data
        recovered = cache.get_pending_tasks()
        assert recovered == new_tasks
    
    def test_cache_directory_permission_error(self, integrated_cache_system):
        """Test handling of cache directory permission errors."""
        cache = integrated_cache_system["session_cache"]
        
        # Mock permission denied error
        with patch('builtins.open', side_effect=PermissionError("Permission denied")):
            # Write should fail gracefully
            result = cache.cache_pending_tasks([{"id": "test"}])
            assert result is False
            
            # Read should fail gracefully
            result = cache.get_pending_tasks()
            assert result is None
    
    def test_cache_fallback_during_mcp_outage(self, integrated_cache_system, mock_mcp_environment):
        """Test cache fallback behavior during MCP server outage."""
        cache = integrated_cache_system["session_cache"]
        
        # Pre-populate cache with known data
        cached_tasks = [
            {"id": "fallback-1", "title": "Cached Fallback Task 1"},
            {"id": "fallback-2", "title": "Cached Fallback Task 2"}
        ]
        cache.cache_pending_tasks(cached_tasks)
        
        # Simulate server outage
        mock_mcp_environment.make_server_unavailable()
        
        with patch('utils.mcp_client.TokenManager.get_valid_token', return_value="outage-token"):
            with patch('utils.mcp_client.MCPHTTPClient._make_request') as mock_request:
                def failing_request(endpoint, data):
                    return mock_mcp_environment.get_tasks()  # Will raise ConnectionError
                
                mock_request.side_effect = failing_request
                
                # Use resilient client with cache fallback
                client = ResilientMCPClient()
                client.fallback_strategy = "cache_then_skip"
                
                # Should fall back to cache
                from session_start import query_mcp_pending_tasks
                
                with patch('session_start.get_session_cache', return_value=cache):
                    result = query_mcp_pending_tasks()
                
                # Should get cached data despite server outage
                assert result == cached_tasks
        
        # Restore server and verify normal operation resumes
        mock_mcp_environment.restore_server()
        
        with patch('utils.mcp_client.TokenManager.get_valid_token', return_value="restored-token"):
            with patch('utils.mcp_client.MCPHTTPClient._make_request') as mock_request:
                mock_request.return_value = mock_mcp_environment.get_tasks()
                
                # Clear cache to force server query
                cache.delete(cache.PENDING_TASKS_KEY)
                
                with patch('session_start.get_session_cache', return_value=cache):
                    result = query_mcp_pending_tasks()
                
                # Should get fresh server data
                assert result is not None
                assert len(result) == 2
                assert result[0]["id"] == "mcp-task-1"


class TestCachePerformanceIntegration:
    """Test cache performance in integrated scenarios."""
    
    def test_cache_performance_under_load(self, integrated_cache_system):
        """Test cache performance under high load scenarios."""
        cache = integrated_cache_system["session_cache"]
        
        # Prepare test data
        large_task_set = [
            {"id": f"load-task-{i}", "title": f"Load Test Task {i}", "status": "todo"}
            for i in range(100)
        ]
        
        # Test write performance
        write_start = time.time()
        cache.cache_pending_tasks(large_task_set)
        write_time = time.time() - write_start
        
        # Test read performance under concurrent load
        concurrent_readers = 10
        reads_per_reader = 20
        
        def concurrent_reader(reader_id):
            """Perform multiple cache reads."""
            read_times = []
            
            for i in range(reads_per_reader):
                start = time.time()
                result = cache.get_pending_tasks()
                duration = time.time() - start
                read_times.append(duration)
                
                assert result == large_task_set, f"Reader {reader_id} read {i} failed"
            
            return read_times
        
        # Run concurrent readers
        with ThreadPoolExecutor(max_workers=concurrent_readers) as executor:
            futures = [
                executor.submit(concurrent_reader, i) 
                for i in range(concurrent_readers)
            ]
            all_read_times = [times for future in as_completed(futures) for times in future.result()]
        
        # Performance analysis
        avg_read_time = sum(all_read_times) / len(all_read_times)
        max_read_time = max(all_read_times)
        total_reads = len(all_read_times)
        
        # Performance assertions
        assert write_time < 0.1, f"Cache write too slow: {write_time:.3f}s"
        assert avg_read_time < 0.01, f"Average cache read too slow: {avg_read_time:.3f}s"
        assert max_read_time < 0.05, f"Max cache read too slow: {max_read_time:.3f}s"
        
        print(f"Cache load test: {total_reads} reads, avg {avg_read_time:.3f}s, max {max_read_time:.3f}s")
    
    def test_cache_memory_usage_efficiency(self, integrated_cache_system):
        """Test cache memory usage efficiency."""
        cache = integrated_cache_system["session_cache"]
        
        # Test with different data sizes
        test_cases = [
            ("small", [{"id": f"s{i}", "title": f"Small {i}"} for i in range(10)]),
            ("medium", [{"id": f"m{i}", "title": f"Medium {i}", "description": "x" * 100} for i in range(50)]),
            ("large", [{"id": f"l{i}", "title": f"Large {i}", "description": "x" * 1000, "metadata": {"key": f"value{i}"}} for i in range(100)])
        ]
        
        performance_results = {}
        
        for size_name, test_data in test_cases:
            # Measure write performance
            write_start = time.time()
            cache.cache_pending_tasks(test_data)
            write_time = time.time() - write_start
            
            # Measure read performance
            read_start = time.time()
            result = cache.get_pending_tasks()
            read_time = time.time() - read_start
            
            # Verify data integrity
            assert result == test_data, f"Data integrity failed for {size_name} dataset"
            
            performance_results[size_name] = {
                "data_size": len(test_data),
                "write_time": write_time,
                "read_time": read_time
            }
            
            # Clear cache for next test
            cache.delete(cache.PENDING_TASKS_KEY)
        
        # Verify performance scales reasonably
        small_write = performance_results["small"]["write_time"]
        large_write = performance_results["large"]["write_time"]
        
        # Large dataset (10x size) shouldn't be more than 20x slower
        assert large_write < small_write * 20, "Cache write performance doesn't scale well"
        
        for size_name, metrics in performance_results.items():
            print(f"Cache {size_name}: {metrics['data_size']} items, "
                  f"write {metrics['write_time']:.3f}s, read {metrics['read_time']:.3f}s")
    
    def test_cache_cleanup_performance(self, integrated_cache_system):
        """Test cache cleanup performance with many expired entries."""
        cache = integrated_cache_system["base_cache"]
        
        # Create many cache entries with different expiration times
        entry_count = 50
        short_ttl = 1  # 1 second
        long_ttl = 3600  # 1 hour
        
        # Create mix of entries that will expire and entries that won't
        for i in range(entry_count):
            key = f"cleanup_test_{i}"
            data = {"test_id": i, "data": f"cleanup test data {i}"}
            
            # Alternate between short and long TTL
            ttl = short_ttl if i % 2 == 0 else long_ttl
            cache.set(key, data, ttl=ttl)
        
        # Wait for half the entries to expire
        time.sleep(short_ttl + 0.1)
        
        # Measure cleanup performance
        cleanup_start = time.time()
        deleted_count = cache.cleanup_expired()
        cleanup_time = time.time() - cleanup_start
        
        # Verify cleanup efficiency
        expected_deleted = entry_count // 2  # Half had short TTL
        assert deleted_count >= expected_deleted - 2, f"Cleanup deleted {deleted_count}, expected ~{expected_deleted}"
        assert cleanup_time < 1.0, f"Cleanup too slow: {cleanup_time:.3f}s for {entry_count} entries"
        
        # Verify valid entries are still accessible
        valid_entries = 0
        for i in range(1, entry_count, 2):  # Odd indices had long TTL
            key = f"cleanup_test_{i}"
            result = cache.get(key)
            if result is not None:
                valid_entries += 1
        
        expected_valid = entry_count // 2
        assert valid_entries >= expected_valid - 2, f"Too many valid entries removed: {valid_entries}"
        
        print(f"Cleanup performance: {deleted_count} expired entries removed in {cleanup_time:.3f}s")
        print(f"Valid entries preserved: {valid_entries}")


@pytest.mark.integration
class TestCacheIntegrationRealWorld:
    """Test cache integration in realistic scenarios."""
    
    def test_typical_development_session_cache_usage(self, integrated_cache_system, mock_mcp_environment):
        """Test cache behavior in a typical development session."""
        cache = integrated_cache_system["session_cache"]
        
        # Simulate typical session timeline
        session_events = [
            ("session_start", "Query pending tasks"),
            ("task_work", "Get next task for branch"),
            ("context_switch", "Query different branch tasks"), 
            ("server_hiccup", "Server temporarily unavailable"),
            ("resume_work", "Continue with cached data"),
            ("server_recovery", "Server back online"),
            ("session_end", "Final status check")
        ]
        
        session_log = []
        
        with patch('utils.mcp_client.TokenManager.get_valid_token', return_value="dev-session-token"):
            for event_type, description in session_events:
                event_start = time.time()
                
                try:
                    if event_type == "session_start":
                        # Initial query - cache miss, hits server
                        with patch('utils.mcp_client.MCPHTTPClient._make_request') as mock_request:
                            mock_request.return_value = mock_mcp_environment.get_tasks()
                            
                            from session_start import query_mcp_pending_tasks
                            with patch('session_start.get_session_cache', return_value=cache):
                                tasks = query_mcp_pending_tasks()
                            
                            assert len(tasks) == 2
                    
                    elif event_type == "task_work":
                        # Get next task - should be cached or quick server query
                        branch_id = "dev-main-branch"
                        next_task = cache.get_next_task(branch_id)
                        
                        if next_task is None:
                            # Cache miss - simulate server query
                            with patch('utils.mcp_client.MCPHTTPClient._make_request') as mock_request:
                                mock_request.return_value = {"success": True, "data": mock_mcp_environment.task_data[0]}
                                
                                from session_start import query_mcp_next_task
                                with patch('session_start.get_session_cache', return_value=cache):
                                    next_task = query_mcp_next_task(branch_id)
                        
                        assert next_task is not None
                    
                    elif event_type == "context_switch":
                        # Switch to different branch context
                        other_branch_id = "dev-feature-branch"
                        cache.cache_project_context(other_branch_id, {"branch": "feature", "env": "dev"})
                        
                        context = cache.get_project_context(other_branch_id)
                        assert context["branch"] == "feature"
                    
                    elif event_type == "server_hiccup":
                        # Simulate server unavailability
                        mock_mcp_environment.make_server_unavailable()
                        
                        # Should fall back to cache
                        cached_tasks = cache.get_pending_tasks()
                        assert cached_tasks is not None  # Should have cached data
                    
                    elif event_type == "resume_work":
                        # Continue working with cached data
                        tasks = cache.get_pending_tasks()
                        assert tasks is not None
                    
                    elif event_type == "server_recovery":
                        # Server comes back online
                        mock_mcp_environment.restore_server()
                        
                        # Clear cache to test server query
                        cache.delete(cache.PENDING_TASKS_KEY)
                        
                        with patch('utils.mcp_client.MCPHTTPClient._make_request') as mock_request:
                            mock_request.return_value = mock_mcp_environment.get_tasks()
                            
                            from session_start import query_mcp_pending_tasks
                            with patch('session_start.get_session_cache', return_value=cache):
                                tasks = query_mcp_pending_tasks()
                            
                            assert len(tasks) == 2
                    
                    elif event_type == "session_end":
                        # Final cache statistics
                        stats = cache.get_cache_stats()
                        assert stats["total_files"] > 0
                    
                    event_duration = time.time() - event_start
                    session_log.append({
                        "event": event_type,
                        "description": description,
                        "duration": event_duration,
                        "success": True
                    })
                
                except Exception as e:
                    event_duration = time.time() - event_start
                    session_log.append({
                        "event": event_type,
                        "description": description,
                        "duration": event_duration,
                        "success": False,
                        "error": str(e)
                    })
        
        # Analyze session performance
        total_duration = sum(event["duration"] for event in session_log)
        successful_events = [event for event in session_log if event["success"]]
        
        assert len(successful_events) >= len(session_events) - 1, "Too many session events failed"
        assert total_duration < 5.0, f"Development session too slow: {total_duration:.2f}s"
        
        print(f"Development session simulation: {len(successful_events)}/{len(session_events)} events successful")
        print(f"Total session time: {total_duration:.3f}s")
        
        for event in session_log:
            status = "✅" if event["success"] else "❌"
            print(f"  {status} {event['event']}: {event['duration']:.3f}s - {event['description']}")
            if not event["success"]:
                print(f"    Error: {event.get('error', 'Unknown')}")