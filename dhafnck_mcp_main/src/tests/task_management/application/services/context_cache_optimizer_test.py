"""
Tests for Context Cache Optimizer Service
"""

import pytest
from datetime import datetime, timedelta
from unittest.mock import Mock, patch
import json

from fastmcp.task_management.application.services.context_cache_optimizer import (
    ContextCacheOptimizer,
    CacheEntry,
    CacheStrategy
)


class TestContextCacheOptimizer:
    """Test Context Cache Optimizer functionality"""

    @pytest.fixture
    def optimizer(self):
        """Create cache optimizer instance"""
        return ContextCacheOptimizer(max_size_mb=10, ttl_seconds=3600)

    @pytest.fixture
    def sample_context(self):
        """Sample context data for testing"""
        return {
            "tasks": [
                {
                    "id": "task-1",
                    "title": "Implement feature",
                    "status": "in_progress",
                    "assignees": ["coding-agent"],
                    "details": "Implementation details " * 100  # Make it larger
                }
            ],
            "project": {
                "id": "proj-1",
                "name": "Test Project",
                "description": "A test project for caching"
            }
        }

    def test_cache_initialization(self):
        """Test cache optimizer initialization"""
        optimizer = ContextCacheOptimizer(max_size_mb=5, ttl_seconds=1800)
        assert optimizer.max_size_bytes == 5 * 1024 * 1024
        assert optimizer.ttl_seconds == 1800
        assert len(optimizer.cache) == 0
        assert optimizer.hit_count == 0
        assert optimizer.miss_count == 0

    def test_cache_key_generation(self, optimizer):
        """Test cache key generation"""
        key1 = optimizer._generate_key("task_list", {"status": "open", "page": 1})
        key2 = optimizer._generate_key("task_list", {"page": 1, "status": "open"})
        key3 = optimizer._generate_key("task_list", {"status": "closed", "page": 1})
        
        # Same parameters in different order should produce same key
        assert key1 == key2
        # Different parameters should produce different keys
        assert key1 != key3

    def test_cache_put_and_get(self, optimizer, sample_context):
        """Test putting and getting items from cache"""
        key = "test_key"
        
        # Put item in cache
        optimizer.put(key, sample_context)
        
        # Get item from cache
        result = optimizer.get(key)
        assert result == sample_context
        assert optimizer.hit_count == 1
        assert optimizer.miss_count == 0

    def test_cache_miss(self, optimizer):
        """Test cache miss scenario"""
        result = optimizer.get("non_existent_key")
        assert result is None
        assert optimizer.hit_count == 0
        assert optimizer.miss_count == 1

    def test_cache_expiration(self, optimizer, sample_context):
        """Test cache entry expiration"""
        key = "expiring_key"
        
        # Create optimizer with 1 second TTL
        short_ttl_optimizer = ContextCacheOptimizer(max_size_mb=10, ttl_seconds=1)
        
        # Put item in cache
        short_ttl_optimizer.put(key, sample_context)
        
        # Item should be available immediately
        assert short_ttl_optimizer.get(key) == sample_context
        
        # Mock time to simulate expiration
        with patch('time.time') as mock_time:
            # Set current time to 2 seconds later
            mock_time.return_value = datetime.now().timestamp() + 2
            
            # Item should be expired
            result = short_ttl_optimizer.get(key)
            assert result is None
            assert key not in short_ttl_optimizer.cache

    def test_cache_size_limit(self, optimizer):
        """Test cache size limit enforcement"""
        # Create optimizer with very small size limit (1KB)
        small_optimizer = ContextCacheOptimizer(max_size_mb=0.001, ttl_seconds=3600)
        
        # Create large data
        large_data = {"data": "x" * 2000}  # ~2KB
        
        # Try to put large data
        small_optimizer.put("key1", large_data)
        
        # Cache should be empty as data exceeds limit
        assert len(small_optimizer.cache) == 0

    def test_cache_eviction_lru(self, optimizer):
        """Test LRU eviction when cache is full"""
        # Create optimizer with small size
        small_optimizer = ContextCacheOptimizer(max_size_mb=0.01, ttl_seconds=3600)
        
        # Add multiple items
        for i in range(5):
            data = {"id": i, "data": "x" * 1000}
            small_optimizer.put(f"key_{i}", data)
        
        # Access first items to make them recently used
        small_optimizer.get("key_0")
        small_optimizer.get("key_1")
        
        # Add new item that should trigger eviction
        new_data = {"id": "new", "data": "x" * 1000}
        small_optimizer.put("key_new", new_data)
        
        # Oldest non-accessed items should be evicted
        assert small_optimizer.get("key_new") is not None
        assert small_optimizer.get("key_0") is not None
        assert small_optimizer.get("key_1") is not None

    def test_cache_clear(self, optimizer, sample_context):
        """Test clearing the cache"""
        # Add items to cache
        optimizer.put("key1", sample_context)
        optimizer.put("key2", sample_context)
        
        assert len(optimizer.cache) == 2
        
        # Clear cache
        optimizer.clear()
        
        assert len(optimizer.cache) == 0
        assert optimizer.current_size == 0

    def test_cache_metrics(self, optimizer, sample_context):
        """Test cache metrics calculation"""
        # Perform various operations
        optimizer.put("key1", sample_context)
        optimizer.get("key1")  # Hit
        optimizer.get("key1")  # Hit
        optimizer.get("key2")  # Miss
        optimizer.get("key3")  # Miss
        
        metrics = optimizer.get_cache_stats()
        
        assert isinstance(metrics, dict)
        assert "total_entries" in metrics
        assert "hit_count" in metrics  
        assert "miss_count" in metrics
        assert metrics.current_size_mb > 0
        assert metrics.max_size_mb == 10

    def test_cache_warming(self, optimizer):
        """Test cache warming functionality"""
        preload_data = {
            "frequently_used_1": {"data": "Important data 1"},
            "frequently_used_2": {"data": "Important data 2"},
            "frequently_used_3": {"data": "Important data 3"}
        }
        
        optimizer.warm_cache(preload_data)
        
        # All preloaded data should be available
        for key, value in preload_data.items():
            assert optimizer.get(key) == value

    def test_selective_invalidation(self, optimizer, sample_context):
        """Test selective cache invalidation"""
        # Add various entries
        optimizer.put("task_list_page_1", {"page": 1, "tasks": []})
        optimizer.put("task_list_page_2", {"page": 2, "tasks": []})
        optimizer.put("project_details", {"project": "data"})
        
        # Invalidate only task-related entries
        optimizer.invalidate_pattern("task_list_*")
        
        # Task entries should be gone
        assert optimizer.get("task_list_page_1") is None
        assert optimizer.get("task_list_page_2") is None
        # Project entry should remain
        assert optimizer.get("project_details") is not None

    def test_context_optimization(self, optimizer, sample_context):
        """Test context data optimization before caching"""
        # Add a context with redundant data
        context_with_redundancy = {
            "tasks": sample_context["tasks"] * 3,  # Duplicate tasks
            "metadata": {
                "timestamp": datetime.now().isoformat(),
                "user": "test-user",
                "session": "session-123" * 100  # Large session data
            }
        }
        
        key = "optimized_context"
        optimizer.put(key, context_with_redundancy, optimize=True)
        
        # Retrieved context should be optimized
        retrieved = optimizer.get(key)
        assert retrieved is not None
        # Optimization might remove duplicates or compress data
        assert len(json.dumps(retrieved)) <= len(json.dumps(context_with_redundancy))

    def test_concurrent_access(self, optimizer, sample_context):
        """Test thread-safe concurrent access"""
        import threading
        import time
        
        results = []
        errors = []
        
        def cache_operation(thread_id):
            try:
                # Each thread performs multiple operations
                for i in range(10):
                    key = f"thread_{thread_id}_item_{i}"
                    optimizer.put(key, {"thread": thread_id, "item": i})
                    result = optimizer.get(key)
                    if result:
                        results.append(result)
                    time.sleep(0.001)  # Small delay to increase contention
            except Exception as e:
                errors.append(e)
        
        # Create and start threads
        threads = []
        for i in range(5):
            thread = threading.Thread(target=cache_operation, args=(i,))
            threads.append(thread)
            thread.start()
        
        # Wait for all threads to complete
        for thread in threads:
            thread.join()
        
        # Check results
        assert len(errors) == 0  # No errors should occur
        assert len(results) > 0  # Some results should be retrieved

    def test_adaptive_ttl(self, optimizer):
        """Test adaptive TTL based on access patterns"""
        # Create optimizer with adaptive TTL enabled
        adaptive_optimizer = ContextCacheOptimizer(
            max_size_mb=10, 
            ttl_seconds=3600,
            adaptive_ttl=True
        )
        
        key = "frequently_accessed"
        data = {"important": "data"}
        
        # Put data and access it frequently
        adaptive_optimizer.put(key, data)
        for _ in range(10):
            adaptive_optimizer.get(key)
        
        # Frequently accessed items should have extended TTL
        entry = adaptive_optimizer.cache.get(key)
        assert entry is not None
        # TTL should be extended based on access frequency
        
    def test_compression(self, optimizer):
        """Test data compression for large contexts"""
        # Create large context
        large_context = {
            "tasks": [
                {
                    "id": f"task-{i}",
                    "title": f"Task {i}",
                    "description": "This is a very long description " * 50,
                    "details": "Detailed information " * 100
                }
                for i in range(100)
            ]
        }
        
        key = "compressed_context"
        optimizer.put(key, large_context, compress=True)
        
        # Retrieve and verify
        retrieved = optimizer.get(key)
        assert retrieved == large_context
        
        # Check that compression actually reduced size
        entry = optimizer.cache.get(key)
        if hasattr(entry.data, '__sizeof__'):
            compressed_size = entry.data.__sizeof__()
            original_size = large_context.__sizeof__()
            # Compression should reduce size (this is approximate)
            assert compressed_size < original_size

    def test_cache_persistence(self, optimizer, sample_context, tmp_path):
        """Test cache persistence to disk"""
        # Add data to cache
        optimizer.put("key1", sample_context)
        optimizer.put("key2", {"data": "test"})
        
        # Save cache to disk
        cache_file = tmp_path / "cache.json"
        optimizer.save_to_disk(str(cache_file))
        
        # Create new optimizer and load cache
        new_optimizer = ContextCacheOptimizer(max_size_mb=10, ttl_seconds=3600)
        new_optimizer.load_from_disk(str(cache_file))
        
        # Verify data is restored
        assert new_optimizer.get("key1") == sample_context
        assert new_optimizer.get("key2") == {"data": "test"}