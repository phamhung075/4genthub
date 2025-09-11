"""
Unit Tests for Cache Manager

Tests all caching functionality in isolation with comprehensive edge cases
and error handling validation.

Test Coverage:
- Basic cache operations (get/set/delete)
- TTL expiration handling
- Concurrent access thread safety
- Cache cleanup and statistics
- Session-specific caching patterns
- Error handling and resilience
"""

import pytest
import time
import json
import tempfile
import threading
from pathlib import Path
from unittest.mock import Mock, patch, mock_open
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime

# Import cache manager components
from utils.cache_manager import CacheManager, SessionContextCache, get_session_cache


class TestCacheManager:
    """Unit tests for base CacheManager class."""
    
    @pytest.fixture
    def temp_cache_dir(self):
        """Create temporary cache directory for testing."""
        with tempfile.TemporaryDirectory() as temp_dir:
            yield temp_dir
    
    @pytest.fixture
    def cache_manager(self, temp_cache_dir):
        """Create cache manager instance with temp directory."""
        return CacheManager(temp_cache_dir)
    
    def test_cache_initialization(self, temp_cache_dir):
        """Test cache manager initialization."""
        cache = CacheManager(temp_cache_dir)
        
        assert cache.cache_dir == Path(temp_cache_dir)
        assert cache.cache_dir.exists()
        assert hasattr(cache, 'lock')
        assert cache.default_ttl > 0
        assert cache.max_cache_size > 0
    
    def test_cache_initialization_default_dir(self):
        """Test cache initialization with default directory."""
        with patch('pathlib.Path.mkdir') as mock_mkdir:
            cache = CacheManager()
            expected_dir = Path.home() / ".claude" / ".session_cache"
            assert cache.cache_dir == expected_dir
            mock_mkdir.assert_called_once_with(parents=True, exist_ok=True)
    
    def test_cache_set_and_get_success(self, cache_manager):
        """Test successful cache set and get operations."""
        test_data = {"key": "value", "number": 42, "nested": {"inner": "data"}}
        key = "test_key"
        
        # Test set operation
        result = cache_manager.set(key, test_data)
        assert result is True
        
        # Test get operation
        retrieved = cache_manager.get(key)
        assert retrieved == test_data
        
        # Verify cache file was created
        cache_file = cache_manager.cache_dir / f"{cache_manager._hash_key(key)}.json"
        assert cache_file.exists()
    
    def test_cache_get_nonexistent_key(self, cache_manager):
        """Test get operation for non-existent key."""
        result = cache_manager.get("nonexistent_key")
        assert result is None
    
    def test_cache_ttl_expiration(self, cache_manager):
        """Test cache TTL expiration behavior."""
        test_data = {"test": "data"}
        key = "ttl_test_key"
        short_ttl = 1  # 1 second
        
        # Set with short TTL
        cache_manager.set(key, test_data, ttl=short_ttl)
        
        # Should be available immediately
        assert cache_manager.get(key, ttl=short_ttl) == test_data
        
        # Wait for expiration
        time.sleep(short_ttl + 0.1)
        
        # Should be None after expiration
        assert cache_manager.get(key, ttl=short_ttl) is None
        
        # Cache file should be cleaned up
        cache_file = cache_manager.cache_dir / f"{cache_manager._hash_key(key)}.json"
        assert not cache_file.exists()
    
    def test_cache_delete(self, cache_manager):
        """Test cache delete operation."""
        test_data = {"test": "data"}
        key = "delete_test_key"
        
        # Set data
        cache_manager.set(key, test_data)
        assert cache_manager.get(key) == test_data
        
        # Delete data
        result = cache_manager.delete(key)
        assert result is True
        
        # Verify data is gone
        assert cache_manager.get(key) is None
    
    def test_cache_delete_nonexistent_key(self, cache_manager):
        """Test delete operation for non-existent key."""
        result = cache_manager.delete("nonexistent_key")
        assert result is True  # Should not fail
    
    def test_cache_clear_all(self, cache_manager):
        """Test clear all cache operation."""
        # Set multiple cache entries
        test_keys = ["key1", "key2", "key3"]
        for key in test_keys:
            cache_manager.set(key, f"data_{key}")
        
        # Verify all are cached
        for key in test_keys:
            assert cache_manager.get(key) == f"data_{key}"
        
        # Clear all cache
        result = cache_manager.clear_all()
        assert result is True
        
        # Verify all are gone
        for key in test_keys:
            assert cache_manager.get(key) is None
    
    def test_cache_cleanup_expired(self, cache_manager):
        """Test cleanup of expired cache entries."""
        # Set entries with different TTLs
        cache_manager.set("short_ttl", "data1", ttl=1)
        cache_manager.set("long_ttl", "data2", ttl=3600)
        
        # Wait for short TTL to expire
        time.sleep(1.1)
        
        # Run cleanup
        deleted_count = cache_manager.cleanup_expired()
        
        assert deleted_count >= 1  # At least the expired entry
        assert cache_manager.get("short_ttl") is None
        assert cache_manager.get("long_ttl") == "data2"
    
    def test_cache_stats(self, cache_manager):
        """Test cache statistics functionality."""
        # Set some test data
        cache_manager.set("stats_test1", {"data": "test1"})
        cache_manager.set("stats_test2", {"data": "test2"}, ttl=1)
        
        # Wait for one to expire
        time.sleep(1.1)
        
        stats = cache_manager.get_cache_stats()
        
        assert isinstance(stats, dict)
        assert "total_files" in stats
        assert "total_size_bytes" in stats
        assert "expired_files" in stats
        assert "valid_files" in stats
        assert stats["total_files"] >= 2
        assert stats["expired_files"] >= 1
        assert stats["valid_files"] >= 1
    
    def test_concurrent_cache_access(self, cache_manager):
        """Test thread-safe concurrent cache operations."""
        concurrent_workers = 10
        iterations_per_worker = 5
        
        def worker(worker_id):
            """Worker function for concurrent operations."""
            results = []
            for i in range(iterations_per_worker):
                key = f"worker_{worker_id}_item_{i}"
                data = {"worker": worker_id, "item": i, "timestamp": time.time()}
                
                # Set data
                set_result = cache_manager.set(key, data)
                results.append(("set", set_result))
                
                # Get data
                get_result = cache_manager.get(key)
                results.append(("get", get_result == data))
            
            return results
        
        # Execute concurrent workers
        with ThreadPoolExecutor(max_workers=concurrent_workers) as executor:
            futures = [executor.submit(worker, i) for i in range(concurrent_workers)]
            all_results = [f.result() for f in as_completed(futures)]
        
        # Verify all operations succeeded
        for worker_results in all_results:
            for operation, success in worker_results:
                assert success, f"Concurrent {operation} operation failed"
    
    def test_hash_key_consistency(self, cache_manager):
        """Test hash key generation consistency."""
        test_keys = [
            "simple_key",
            "key_with_spaces",
            "key/with/slashes",
            "key@with!special#chars$",
            "very_long_key_" + "x" * 200
        ]
        
        for key in test_keys:
            hash1 = cache_manager._hash_key(key)
            hash2 = cache_manager._hash_key(key)
            
            assert hash1 == hash2, f"Hash inconsistent for key: {key}"
            assert isinstance(hash1, str)
            assert len(hash1) == 32  # MD5 hash length
    
    def test_cache_json_serialization_edge_cases(self, cache_manager):
        """Test JSON serialization of complex data types."""
        test_cases = [
            ("datetime", datetime.now()),
            ("none_value", None),
            ("empty_dict", {}),
            ("empty_list", []),
            ("nested_complex", {
                "list": [1, 2, {"nested": True}],
                "datetime": datetime.now(),
                "none": None
            })
        ]
        
        for description, test_data in test_cases:
            key = f"json_test_{description}"
            
            # Should handle serialization
            result = cache_manager.set(key, test_data)
            assert result is True, f"Failed to serialize {description}"
            
            # Should retrieve correctly (datetime will be string)
            retrieved = cache_manager.get(key)
            if description == "datetime":
                assert isinstance(retrieved, str)
            else:
                assert retrieved == test_data
    
    @patch('builtins.open', side_effect=OSError("Permission denied"))
    def test_cache_file_permission_error(self, mock_open, cache_manager):
        """Test handling of file permission errors."""
        result = cache_manager.set("test_key", {"test": "data"})
        assert result is False
        
        result = cache_manager.get("test_key")
        assert result is None
    
    @patch('json.load', side_effect=json.JSONDecodeError("Invalid JSON", "", 0))
    def test_cache_corrupted_file_handling(self, mock_json_load, cache_manager):
        """Test handling of corrupted cache files."""
        # Create a cache file first
        cache_manager.set("test_key", {"test": "data"})
        
        # Now mock JSON corruption and try to read
        with patch('builtins.open', mock_open(read_data='corrupted json')):
            result = cache_manager.get("test_key")
            assert result is None


class TestSessionContextCache:
    """Unit tests for SessionContextCache specialized functionality."""
    
    @pytest.fixture
    def session_cache(self):
        """Create SessionContextCache instance for testing."""
        with patch('pathlib.Path.mkdir'):
            return SessionContextCache()
    
    def test_session_cache_initialization(self, session_cache):
        """Test SessionContextCache initialization."""
        assert hasattr(session_cache, 'PENDING_TASKS_KEY')
        assert hasattr(session_cache, 'NEXT_TASK_KEY')
        assert hasattr(session_cache, 'PROJECT_CONTEXT_KEY')
        assert hasattr(session_cache, 'GIT_STATUS_KEY')
        assert session_cache.task_cache_ttl > 0
        assert session_cache.git_cache_ttl > 0
    
    def test_pending_tasks_caching(self, session_cache):
        """Test pending tasks caching functionality."""
        test_tasks = [
            {"id": "task1", "title": "Test Task 1", "status": "todo"},
            {"id": "task2", "title": "Test Task 2", "status": "in_progress"}
        ]
        
        with patch.object(session_cache, 'set', return_value=True) as mock_set:
            with patch.object(session_cache, 'get', return_value=test_tasks) as mock_get:
                # Test cache set
                result = session_cache.cache_pending_tasks(test_tasks)
                assert result is True
                mock_set.assert_called_once_with(session_cache.PENDING_TASKS_KEY, test_tasks, session_cache.task_cache_ttl)
                
                # Test cache get
                retrieved = session_cache.get_pending_tasks()
                assert retrieved == test_tasks
                mock_get.assert_called_once_with(session_cache.PENDING_TASKS_KEY, session_cache.task_cache_ttl)
    
    def test_next_task_caching(self, session_cache):
        """Test next task caching with branch ID."""
        branch_id = "branch-uuid-123"
        test_task = {"id": "next-task", "title": "Next Task", "priority": "high"}
        expected_key = session_cache.NEXT_TASK_KEY.format(branch_id=branch_id)
        
        with patch.object(session_cache, 'set', return_value=True) as mock_set:
            with patch.object(session_cache, 'get', return_value=test_task) as mock_get:
                # Test cache set
                result = session_cache.cache_next_task(branch_id, test_task)
                assert result is True
                mock_set.assert_called_once_with(expected_key, test_task, session_cache.task_cache_ttl)
                
                # Test cache get
                retrieved = session_cache.get_next_task(branch_id)
                assert retrieved == test_task
                mock_get.assert_called_once_with(expected_key, session_cache.task_cache_ttl)
    
    def test_git_status_caching(self, session_cache):
        """Test git status caching functionality."""
        git_data = {
            "branch": "main",
            "uncommitted_changes": 3,
            "recent_commits": ["commit1", "commit2"],
            "git_branch_id": "git-branch-uuid"
        }
        
        with patch.object(session_cache, 'set', return_value=True) as mock_set:
            with patch.object(session_cache, 'get', return_value=git_data) as mock_get:
                # Test cache set
                result = session_cache.cache_git_status(git_data)
                assert result is True
                mock_set.assert_called_once_with(session_cache.GIT_STATUS_KEY, git_data, session_cache.git_cache_ttl)
                
                # Test cache get
                retrieved = session_cache.get_git_status()
                assert retrieved == git_data
                mock_get.assert_called_once_with(session_cache.GIT_STATUS_KEY, session_cache.git_cache_ttl)
    
    def test_project_context_caching(self, session_cache):
        """Test project context caching with branch ID."""
        branch_id = "project-branch-456"
        context_data = {
            "project_id": "proj-123",
            "environment": "development",
            "dependencies": ["dep1", "dep2"]
        }
        expected_key = session_cache.PROJECT_CONTEXT_KEY.format(branch_id=branch_id)
        
        with patch.object(session_cache, 'set', return_value=True) as mock_set:
            with patch.object(session_cache, 'get', return_value=context_data) as mock_get:
                # Test cache set
                result = session_cache.cache_project_context(branch_id, context_data)
                assert result is True
                mock_set.assert_called_once_with(expected_key, context_data, session_cache.default_ttl)
                
                # Test cache get
                retrieved = session_cache.get_project_context(branch_id)
                assert retrieved == context_data
                mock_get.assert_called_once_with(expected_key, session_cache.default_ttl)


class TestCacheManagerFactory:
    """Test the factory function for cache manager."""
    
    def test_get_session_cache_factory(self):
        """Test get_session_cache factory function."""
        with patch('utils.cache_manager.SessionContextCache') as mock_session_cache:
            mock_instance = Mock()
            mock_session_cache.return_value = mock_instance
            
            result = get_session_cache()
            
            mock_session_cache.assert_called_once()
            assert result == mock_instance


class TestCacheManagerEnvironmentConfig:
    """Test environment variable configuration handling."""
    
    @patch.dict('os.environ', {
        'SESSION_CACHE_TTL': '7200',
        'SESSION_CACHE_MAX_SIZE': '100',
        'CACHE_CLEANUP_INTERVAL': '43200',
        'TASK_CACHE_TTL': '1800',
        'GIT_CACHE_TTL': '600'
    })
    def test_environment_variable_configuration(self):
        """Test that environment variables are properly loaded."""
        with patch('pathlib.Path.mkdir'):
            cache = CacheManager()
            session_cache = SessionContextCache()
        
        assert cache.default_ttl == 7200
        assert cache.max_cache_size == 100
        assert cache.cleanup_interval == 43200
        assert session_cache.task_cache_ttl == 1800
        assert session_cache.git_cache_ttl == 600
    
    @patch.dict('os.environ', {}, clear=True)
    def test_default_configuration_values(self):
        """Test default values when environment variables are not set."""
        with patch('pathlib.Path.mkdir'):
            cache = CacheManager()
            session_cache = SessionContextCache()
        
        # Test defaults
        assert cache.default_ttl == 3600  # 1 hour
        assert cache.max_cache_size == 50  # 50 MB
        assert cache.cleanup_interval == 86400  # 24 hours
        assert session_cache.task_cache_ttl == 900  # 15 minutes
        assert session_cache.git_cache_ttl == 300  # 5 minutes


@pytest.mark.integration
class TestCacheManagerIntegration:
    """Integration-style tests for cache manager with real file operations."""
    
    def test_full_cache_lifecycle_integration(self):
        """Test complete cache lifecycle with real file operations."""
        with tempfile.TemporaryDirectory() as temp_dir:
            cache = CacheManager(temp_dir)
            
            # Test data
            test_data = {
                "integration_test": True,
                "timestamp": datetime.now().isoformat(),
                "complex_data": {
                    "nested": {"deep": {"value": 42}},
                    "list": [1, 2, 3, {"nested_in_list": True}]
                }
            }
            
            # Full lifecycle test
            key = "integration_test_key"
            
            # 1. Set data
            assert cache.set(key, test_data) is True
            
            # 2. Verify file exists
            cache_file = cache.cache_dir / f"{cache._hash_key(key)}.json"
            assert cache_file.exists()
            
            # 3. Get data
            retrieved = cache.get(key)
            assert retrieved == test_data
            
            # 4. Verify cache stats
            stats = cache.get_cache_stats()
            assert stats["total_files"] >= 1
            assert stats["valid_files"] >= 1
            
            # 5. Delete data
            assert cache.delete(key) is True
            assert not cache_file.exists()
            assert cache.get(key) is None
    
    def test_session_context_cache_real_operations(self):
        """Test SessionContextCache with real operations."""
        with tempfile.TemporaryDirectory() as temp_dir:
            with patch.object(SessionContextCache, '__init__') as mock_init:
                # Mock initialization to use temp directory
                mock_init.return_value = None
                session_cache = SessionContextCache()
                
                # Set up the instance manually
                session_cache.cache_dir = Path(temp_dir)
                session_cache.lock = threading.Lock()
                session_cache.default_ttl = 3600
                session_cache.task_cache_ttl = 900
                session_cache.git_cache_ttl = 300
                session_cache.PENDING_TASKS_KEY = "mcp_pending_tasks"
                session_cache.GIT_STATUS_KEY = "git_status"
                
                # Test real operations
                tasks = [{"id": "real-task", "title": "Real Task"}]
                git_data = {"branch": "main", "changes": 0}
                
                # Test pending tasks
                assert session_cache.cache_pending_tasks(tasks) is True
                assert session_cache.get_pending_tasks() == tasks
                
                # Test git status
                assert session_cache.cache_git_status(git_data) is True
                assert session_cache.get_git_status() == git_data