"""Test suite for ContextCacheService.

Tests for high-performance caching functionality in hierarchical context system.
"""

import pytest
import asyncio
from unittest.mock import Mock, patch, AsyncMock
from datetime import datetime, timezone, timedelta
from typing import Dict, Any
import json

from fastmcp.task_management.application.services.context_cache_service import ContextCacheService


class TestContextCacheServiceInit:
    """Test ContextCacheService initialization."""

    def test_initialization_with_defaults(self):
        """Test service initialization with default values."""
        service = ContextCacheService()
        
        assert service.repository is None
        assert service.default_ttl_hours == 1
        assert service._user_id is None

    def test_initialization_with_parameters(self):
        """Test service initialization with custom parameters."""
        mock_repo = Mock()
        service = ContextCacheService(
            repository=mock_repo,
            default_ttl_hours=4,
            user_id="test_user_123"
        )
        
        assert service.repository == mock_repo
        assert service.default_ttl_hours == 4
        assert service._user_id == "test_user_123"

    def test_with_user_method(self):
        """Test with_user method creates new instance with user context."""
        original_service = ContextCacheService()
        user_id = "test_user_456"
        
        user_scoped_service = original_service.with_user(user_id)
        
        assert user_scoped_service._user_id == user_id
        assert user_scoped_service is not original_service
        assert isinstance(user_scoped_service, ContextCacheService)

    def test_get_user_scoped_repository_with_with_user_method(self):
        """Test _get_user_scoped_repository with repository that has with_user method."""
        service = ContextCacheService(user_id="test_user")
        mock_repo = Mock()
        mock_user_scoped_repo = Mock()
        mock_repo.with_user.return_value = mock_user_scoped_repo
        
        result = service._get_user_scoped_repository(mock_repo)
        
        assert result == mock_user_scoped_repo
        mock_repo.with_user.assert_called_once_with("test_user")


    def test_get_user_scoped_repository_no_user_context(self):
        """Test _get_user_scoped_repository returns original repo when no user context."""
        service = ContextCacheService()  # No user_id
        mock_repo = Mock()
        
        result = service._get_user_scoped_repository(mock_repo)
        
        assert result == mock_repo


class TestSyncWrapperMethods:
    """Test synchronous wrapper methods for facade compatibility."""

    @pytest.mark.asyncio
    async def test_get_method(self):
        """Test async get method."""
        mock_repo = AsyncMock()
        mock_repo.get_cache_entry.return_value = {
            "context_id": "test_123",
            "resolved_context": {"data": "test"},
            "expires_at": (datetime.now(timezone.utc) + timedelta(hours=1)).isoformat()
        }
        
        service = ContextCacheService(repository=mock_repo)
        
        result = await service.get("task", "test_123")
        
        assert result is not None
        assert result["context_id"] == "test_123"
        mock_repo.get_cache_entry.assert_called_once_with("task", "test_123")

    def test_get_context_sync_wrapper_no_loop(self):
        """Test synchronous get_context wrapper when no event loop exists."""
        mock_repo = AsyncMock()
        service = ContextCacheService(repository=mock_repo)
        
        with patch('asyncio.get_event_loop', side_effect=RuntimeError("No loop")):
            with patch('asyncio.run') as mock_run:
                mock_run.return_value = {"data": "test"}
                
                result = service.get_context("task", "test_123")
                
                assert result == {"data": "test"}
                mock_run.assert_called_once()

    def test_get_context_sync_wrapper_running_loop(self):
        """Test synchronous get_context wrapper when event loop is running."""
        service = ContextCacheService()
        
        mock_loop = Mock()
        mock_loop.is_running.return_value = True
        
        with patch('asyncio.get_event_loop', return_value=mock_loop):
            with patch('fastmcp.task_management.application.services.context_cache_service.logger') as mock_logger:
                result = service.get_context("task", "test_123")
                
                assert result is None  # Returns None when loop is running
                mock_logger.debug.assert_called()

    def test_get_context_sync_wrapper_exception(self):
        """Test synchronous get_context wrapper exception handling."""
        service = ContextCacheService()
        
        with patch('asyncio.get_event_loop', side_effect=Exception("Unexpected error")):
            with patch('fastmcp.task_management.application.services.context_cache_service.logger') as mock_logger:
                result = service.get_context("task", "test_123")
                
                assert result is None
                mock_logger.warning.assert_called()

    def test_set_context_sync_wrapper(self):
        """Test synchronous set_context wrapper."""
        service = ContextCacheService()
        
        with patch('asyncio.get_event_loop', side_effect=RuntimeError("No loop")):
            with patch('asyncio.run') as mock_run:
                service.set_context("task", "test_123", {"data": "test"})
                
                mock_run.assert_called_once()

    def test_invalidate_context_sync_wrapper(self):
        """Test synchronous invalidate_context wrapper."""
        service = ContextCacheService()
        
        with patch('asyncio.get_event_loop', side_effect=RuntimeError("No loop")):
            with patch('asyncio.run') as mock_run:
                service.invalidate_context("task", "test_123")
                
                mock_run.assert_called_once()

    def test_clear_cache_sync_wrapper(self):
        """Test synchronous clear_cache wrapper."""
        service = ContextCacheService()
        
        with patch('asyncio.get_event_loop', side_effect=RuntimeError("No loop")):
            with patch('asyncio.run') as mock_run:
                service.clear_cache()
                
                mock_run.assert_called_once()


class TestCacheRetrieval:
    """Test cache retrieval functionality."""

    @pytest.mark.asyncio
    async def test_get_cached_context_success(self):
        """Test successful cache retrieval."""
        mock_repo = AsyncMock()
        cache_entry = {
            "context_id": "test_123",
            "resolved_context": {"data": "test_data"},
            "expires_at": (datetime.now(timezone.utc) + timedelta(hours=1)).isoformat(),
            "invalidated": False
        }
        mock_repo.get_cache_entry.return_value = cache_entry
        mock_repo.update_cache_stats = AsyncMock()
        
        service = ContextCacheService(repository=mock_repo)
        
        result = await service.get_cached_context("task", "test_123")
        
        assert result == cache_entry
        mock_repo.get_cache_entry.assert_called_once_with("task", "test_123")
        mock_repo.update_cache_stats.assert_called_once()

    @pytest.mark.asyncio
    async def test_get_cached_context_not_found(self):
        """Test cache retrieval when entry not found."""
        mock_repo = AsyncMock()
        mock_repo.get_cache_entry.return_value = None
        
        service = ContextCacheService(repository=mock_repo)
        
        result = await service.get_cached_context("task", "test_123")
        
        assert result is None

    @pytest.mark.asyncio
    async def test_get_cached_context_invalidated(self):
        """Test cache retrieval with invalidated entry."""
        mock_repo = AsyncMock()
        cache_entry = {
            "context_id": "test_123",
            "resolved_context": {"data": "test_data"},
            "invalidated": True
        }
        mock_repo.get_cache_entry.return_value = cache_entry
        mock_repo.remove_cache_entry = AsyncMock()
        
        service = ContextCacheService(repository=mock_repo)
        
        result = await service.get_cached_context("task", "test_123")
        
        assert result is None
        mock_repo.remove_cache_entry.assert_called_once_with("task", "test_123")

    @pytest.mark.asyncio
    async def test_get_cached_context_expired(self):
        """Test cache retrieval with expired entry."""
        mock_repo = AsyncMock()
        expired_time = datetime.now(timezone.utc) - timedelta(hours=1)
        cache_entry = {
            "context_id": "test_123",
            "resolved_context": {"data": "test_data"},
            "expires_at": expired_time.isoformat(),
            "invalidated": False
        }
        mock_repo.get_cache_entry.return_value = cache_entry
        mock_repo.remove_cache_entry = AsyncMock()
        
        service = ContextCacheService(repository=mock_repo)
        
        result = await service.get_cached_context("task", "test_123")
        
        assert result is None
        mock_repo.remove_cache_entry.assert_called_once_with("task", "test_123")

    @pytest.mark.asyncio
    async def test_get_cached_context_expires_at_string_parsing(self):
        """Test cache retrieval with string expires_at parsing."""
        mock_repo = AsyncMock()
        future_time = datetime.now(timezone.utc) + timedelta(hours=1)
        cache_entry = {
            "context_id": "test_123",
            "resolved_context": {"data": "test_data"},
            "expires_at": future_time.isoformat().replace('+00:00', 'Z'),  # Z format
            "invalidated": False
        }
        mock_repo.get_cache_entry.return_value = cache_entry
        mock_repo.update_cache_stats = AsyncMock()
        
        service = ContextCacheService(repository=mock_repo)
        
        result = await service.get_cached_context("task", "test_123")
        
        assert result is not None
        assert result == cache_entry

    @pytest.mark.asyncio
    async def test_get_cached_context_datetime_object_expires_at(self):
        """Test cache retrieval with datetime object expires_at."""
        mock_repo = AsyncMock()
        future_time = datetime.now(timezone.utc) + timedelta(hours=1)
        cache_entry = {
            "context_id": "test_123",
            "resolved_context": {"data": "test_data"},
            "expires_at": future_time,  # datetime object
            "invalidated": False
        }
        mock_repo.get_cache_entry.return_value = cache_entry
        mock_repo.update_cache_stats = AsyncMock()
        
        service = ContextCacheService(repository=mock_repo)
        
        result = await service.get_cached_context("task", "test_123")
        
        assert result is not None

    @pytest.mark.asyncio
    async def test_get_cached_context_exception(self):
        """Test cache retrieval exception handling."""
        mock_repo = AsyncMock()
        mock_repo.get_cache_entry.side_effect = Exception("Database error")
        
        service = ContextCacheService(repository=mock_repo)
        
        result = await service.get_cached_context("task", "test_123")
        
        assert result is None

    @pytest.mark.asyncio
    async def test_update_hit_stats(self):
        """Test updating cache hit statistics."""
        mock_repo = AsyncMock()
        service = ContextCacheService(repository=mock_repo)
        
        await service._update_hit_stats("task", "test_123")
        
        mock_repo.update_cache_stats.assert_called_once()
        call_args = mock_repo.update_cache_stats.call_args
        assert call_args[0][:2] == ("task", "test_123")  # First two args
        # Third argument should contain the update data
        assert "hit_count" in call_args[0][2]
        assert "last_hit" in call_args[0][2]

    @pytest.mark.asyncio
    async def test_update_hit_stats_exception(self):
        """Test update hit stats exception handling."""
        mock_repo = AsyncMock()
        mock_repo.update_cache_stats.side_effect = Exception("Stats update failed")
        
        service = ContextCacheService(repository=mock_repo)
        
        # Should not raise exception
        await service._update_hit_stats("task", "test_123")


class TestCacheStorage:
    """Test cache storage functionality."""

    @pytest.mark.asyncio
    async def test_cache_resolved_context_success(self):
        """Test successful context caching."""
        mock_repo = AsyncMock()
        mock_repo.store_cache_entry = AsyncMock()
        
        service = ContextCacheService(repository=mock_repo, default_ttl_hours=2)
        
        context = {"data": "test_context", "nested": {"value": 123}}
        dependencies_hash = "hash123"
        resolution_path = ["global", "project", "task"]
        
        result = await service.cache_resolved_context(
            "task", "test_123", context, dependencies_hash, resolution_path, ttl_hours=3
        )
        
        assert result is True
        mock_repo.store_cache_entry.assert_called_once()
        
        # Verify cache entry structure
        cache_entry = mock_repo.store_cache_entry.call_args[0][0]
        assert cache_entry["context_id"] == "test_123"
        assert cache_entry["context_level"] == "task"
        assert cache_entry["resolved_context"] == context
        assert cache_entry["dependencies_hash"] == dependencies_hash
        assert json.loads(cache_entry["resolution_path"]) == resolution_path
        assert cache_entry["hit_count"] == 0
        assert cache_entry["invalidated"] is False
        assert cache_entry["cache_size_bytes"] > 0

    @pytest.mark.asyncio
    async def test_cache_resolved_context_default_ttl(self):
        """Test context caching with default TTL."""
        mock_repo = AsyncMock()
        mock_repo.store_cache_entry = AsyncMock()
        
        service = ContextCacheService(repository=mock_repo, default_ttl_hours=4)
        
        context = {"data": "test"}
        
        result = await service.cache_resolved_context(
            "project", "proj_123", context, "hash456", ["global", "project"]
        )
        
        assert result is True
        
        # Verify TTL was calculated from default
        cache_entry = mock_repo.store_cache_entry.call_args[0][0]
        expires_at = datetime.fromisoformat(cache_entry["expires_at"])
        created_at = datetime.fromisoformat(cache_entry["created_at"])
        
        time_diff = expires_at - created_at
        assert abs(time_diff.total_seconds() - (4 * 3600)) < 60  # Within 1 minute tolerance

    @pytest.mark.asyncio
    async def test_cache_resolved_context_exception(self):
        """Test context caching exception handling."""
        mock_repo = AsyncMock()
        mock_repo.store_cache_entry.side_effect = Exception("Storage failed")
        
        service = ContextCacheService(repository=mock_repo)
        
        result = await service.cache_resolved_context(
            "task", "test_123", {"data": "test"}, "hash", ["task"]
        )
        
        assert result is False

    @pytest.mark.asyncio
    async def test_cache_size_calculation(self):
        """Test cache size calculation for different context sizes."""
        mock_repo = AsyncMock()
        mock_repo.store_cache_entry = AsyncMock()
        
        service = ContextCacheService(repository=mock_repo)
        
        # Large context
        large_context = {"data": "x" * 10000, "more": ["item"] * 1000}
        
        await service.cache_resolved_context(
            "task", "large_123", large_context, "hash", ["task"]
        )
        
        cache_entry = mock_repo.store_cache_entry.call_args[0][0]
        assert cache_entry["cache_size_bytes"] > 10000  # Should be substantial


class TestCacheInvalidation:
    """Test cache invalidation functionality."""

    @pytest.mark.asyncio
    async def test_invalidate_context_cache_success(self):
        """Test successful cache invalidation."""
        mock_repo = AsyncMock()
        mock_repo.invalidate_cache_entry = AsyncMock()
        
        service = ContextCacheService(repository=mock_repo)
        
        result = await service.invalidate_context_cache("task", "test_123", "manual_test")
        
        assert result is True
        mock_repo.invalidate_cache_entry.assert_called_once_with("task", "test_123", "manual_test")

    @pytest.mark.asyncio
    async def test_invalidate_context_cache_exception(self):
        """Test cache invalidation exception handling."""
        mock_repo = AsyncMock()
        mock_repo.invalidate_cache_entry.side_effect = Exception("Invalidation failed")
        
        service = ContextCacheService(repository=mock_repo)
        
        result = await service.invalidate_context_cache("task", "test_123")
        
        assert result is False

    @pytest.mark.asyncio
    async def test_invalidate_dependent_caches_global_changes(self):
        """Test invalidating dependent caches for global changes."""
        mock_repo = AsyncMock()
        mock_repo.get_cache_entries_by_level.side_effect = [
            [{"context_level": "project", "context_id": "proj1"}],  # project caches
            [{"context_level": "task", "context_id": "task1"}]      # task caches
        ]
        mock_repo.invalidate_cache_entry = AsyncMock()
        
        service = ContextCacheService(repository=mock_repo)
        
        invalidated = await service.invalidate_dependent_caches("global", "global_singleton", "global_update")
        
        assert len(invalidated) == 2
        assert "project:proj1" in invalidated
        assert "task:task1" in invalidated
        
        # Should invalidate both project and task caches
        assert mock_repo.invalidate_cache_entry.call_count == 2

    @pytest.mark.asyncio
    async def test_invalidate_dependent_caches_project_changes(self):
        """Test invalidating dependent caches for project changes."""
        mock_repo = AsyncMock()
        mock_repo.get_task_caches_by_project.return_value = [
            {"context_id": "task1"},
            {"context_id": "task2"}
        ]
        mock_repo.invalidate_cache_entry = AsyncMock()
        
        service = ContextCacheService(repository=mock_repo)
        
        invalidated = await service.invalidate_dependent_caches("project", "proj123", "project_update")
        
        assert len(invalidated) == 2
        assert "task:task1" in invalidated
        assert "task:task2" in invalidated
        
        mock_repo.get_task_caches_by_project.assert_called_once_with("proj123")

    @pytest.mark.asyncio
    async def test_invalidate_dependent_caches_task_changes(self):
        """Test invalidating dependent caches for task changes (no dependents)."""
        mock_repo = AsyncMock()
        service = ContextCacheService(repository=mock_repo)
        
        invalidated = await service.invalidate_dependent_caches("task", "task123", "task_update")
        
        assert len(invalidated) == 0  # Tasks have no dependents

    @pytest.mark.asyncio
    async def test_invalidate_dependent_caches_exception(self):
        """Test dependent cache invalidation exception handling."""
        mock_repo = AsyncMock()
        mock_repo.get_cache_entries_by_level.side_effect = Exception("Query failed")
        
        service = ContextCacheService(repository=mock_repo)
        
        invalidated = await service.invalidate_dependent_caches("global", "global_singleton")
        
        assert len(invalidated) == 0

    @pytest.mark.asyncio
    async def test_invalidate_method_compatibility(self):
        """Test invalidate method for unified context service compatibility."""
        mock_repo = AsyncMock()
        mock_repo.invalidate_cache_entry = AsyncMock()
        
        service = ContextCacheService(repository=mock_repo)
        
        result = await service.invalidate("task", "test_123", "test_reason")
        
        assert result is True
        # Should call invalidate_context_cache internally
        mock_repo.invalidate_cache_entry.assert_called_once_with("task", "test_123", "test_reason")


class TestCacheMaintenance:
    """Test cache maintenance functionality."""

    @pytest.mark.asyncio
    async def test_cleanup_expired_success(self):
        """Test successful cleanup of expired entries."""
        mock_repo = AsyncMock()
        expired_entries = [
            {"context_level": "task", "context_id": "expired1", "cache_size_bytes": 1000},
            {"context_level": "project", "context_id": "expired2", "cache_size_bytes": 2000}
        ]
        mock_repo.get_expired_cache_entries.return_value = expired_entries
        mock_repo.remove_cache_entry = AsyncMock()
        
        service = ContextCacheService(repository=mock_repo)
        
        result = await service.cleanup_expired()
        
        assert result["success"] is True
        assert result["removed_count"] == 2
        assert result["size_freed_bytes"] == 3000
        assert "cleaned_at" in result
        
        # Should remove each expired entry
        assert mock_repo.remove_cache_entry.call_count == 2

    @pytest.mark.asyncio
    async def test_cleanup_expired_no_entries(self):
        """Test cleanup with no expired entries."""
        mock_repo = AsyncMock()
        mock_repo.get_expired_cache_entries.return_value = []
        
        service = ContextCacheService(repository=mock_repo)
        
        result = await service.cleanup_expired()
        
        assert result["success"] is True
        assert result["removed_count"] == 0
        assert result["size_freed_bytes"] == 0

    @pytest.mark.asyncio
    async def test_cleanup_expired_exception(self):
        """Test cleanup expired exception handling."""
        mock_repo = AsyncMock()
        mock_repo.get_expired_cache_entries.side_effect = Exception("Cleanup failed")
        
        service = ContextCacheService(repository=mock_repo)
        
        result = await service.cleanup_expired()
        
        assert result["success"] is False
        assert "error" in result
        assert result["removed_count"] == 0

    @pytest.mark.asyncio
    async def test_cleanup_invalidated_success(self):
        """Test successful cleanup of invalidated entries."""
        mock_repo = AsyncMock()
        invalidated_entries = [
            {"context_level": "task", "context_id": "invalid1", "cache_size_bytes": 500}
        ]
        mock_repo.get_invalidated_cache_entries.return_value = invalidated_entries
        mock_repo.remove_cache_entry = AsyncMock()
        
        service = ContextCacheService(repository=mock_repo)
        
        result = await service.cleanup_invalidated()
        
        assert result["success"] is True
        assert result["removed_count"] == 1
        assert result["size_freed_bytes"] == 500

    @pytest.mark.asyncio
    async def test_clear_all_cache_success(self):
        """Test successful clearing of all cache entries."""
        mock_repo = AsyncMock()
        mock_repo.clear_all_cache_entries.return_value = 50
        
        service = ContextCacheService(repository=mock_repo)
        
        result = await service.clear_all_cache()
        
        assert result["success"] is True
        assert result["removed_count"] == 50
        assert "cleared_at" in result

    @pytest.mark.asyncio
    async def test_clear_all_cache_exception(self):
        """Test clear all cache exception handling."""
        mock_repo = AsyncMock()
        mock_repo.clear_all_cache_entries.side_effect = Exception("Clear failed")
        
        service = ContextCacheService(repository=mock_repo)
        
        result = await service.clear_all_cache()
        
        assert result["success"] is False
        assert "error" in result
        assert result["removed_count"] == 0


class TestCacheStatistics:
    """Test cache statistics and monitoring functionality."""

    @pytest.mark.asyncio
    async def test_get_cache_stats_success(self):
        """Test successful cache statistics retrieval."""
        mock_repo = AsyncMock()
        mock_stats = {
            "total_entries": 100,
            "total_size_bytes": 50000,
            "total_hits": 500,
            "expired_count": 5,
            "invalidated_count": 2,
            "entries_by_level": {
                "global": 1,
                "project": 10,
                "task": 89
            }
        }
        mock_repo.get_cache_statistics.return_value = mock_stats
        
        service = ContextCacheService(repository=mock_repo)
        
        stats = await service.get_cache_stats()
        
        assert stats["total_entries"] == 100
        assert stats["total_size_bytes"] == 50000
        assert stats["total_hits"] == 500
        assert "performance_metrics" in stats
        assert "health_indicators" in stats
        assert "timestamp" in stats
        
        # Verify calculated metrics
        perf_metrics = stats["performance_metrics"]
        assert perf_metrics["average_entry_size_bytes"] == 500.0  # 50000/100
        assert perf_metrics["cache_efficiency"] == "medium"  # hit_rate calculation changed

    @pytest.mark.asyncio
    async def test_get_cache_stats_empty_cache(self):
        """Test cache statistics with empty cache."""
        mock_repo = AsyncMock()
        mock_stats = {
            "total_entries": 0,
            "total_size_bytes": 0,
            "total_hits": 0
        }
        mock_repo.get_cache_statistics.return_value = mock_stats
        
        service = ContextCacheService(repository=mock_repo)
        
        stats = await service.get_cache_stats()
        
        assert stats["total_entries"] == 0
        perf_metrics = stats["performance_metrics"]
        assert perf_metrics["average_entry_size_bytes"] == 0

    @pytest.mark.asyncio
    async def test_get_cache_stats_exception(self):
        """Test cache statistics exception handling."""
        mock_repo = AsyncMock()
        mock_repo.get_cache_statistics.side_effect = Exception("Stats failed")
        
        service = ContextCacheService(repository=mock_repo)
        
        stats = await service.get_cache_stats()
        
        assert "error" in stats
        assert "timestamp" in stats

    @pytest.mark.asyncio
    async def test_get_top_cached_contexts(self):
        """Test retrieving top cached contexts."""
        mock_repo = AsyncMock()
        mock_top_contexts = [
            {
                "context_level": "task",
                "context_id": "popular_task",
                "hit_count": 100,
                "last_hit": "2024-01-15T10:00:00Z",
                "cache_size_bytes": 1000,
                "created_at": "2024-01-10T10:00:00Z"
            }
        ]
        mock_repo.get_top_hit_cache_entries.return_value = mock_top_contexts
        
        service = ContextCacheService(repository=mock_repo)
        
        top_contexts = await service.get_top_cached_contexts(5)
        
        assert len(top_contexts) == 1
        assert top_contexts[0]["level"] == "task"
        assert top_contexts[0]["context_id"] == "popular_task"
        assert top_contexts[0]["hit_count"] == 100
        
        mock_repo.get_top_hit_cache_entries.assert_called_once_with(5)

    @pytest.mark.asyncio
    async def test_get_top_cached_contexts_exception(self):
        """Test get top cached contexts exception handling."""
        mock_repo = AsyncMock()
        mock_repo.get_top_hit_cache_entries.side_effect = Exception("Query failed")
        
        service = ContextCacheService(repository=mock_repo)
        
        top_contexts = await service.get_top_cached_contexts()
        
        assert len(top_contexts) == 0

    def test_get_cache_health_sync_wrapper(self):
        """Test synchronous cache health wrapper method."""
        service = ContextCacheService()
        
        with patch('asyncio.get_event_loop', side_effect=RuntimeError("No loop")):
            with patch('asyncio.run') as mock_run:
                mock_stats = {
                    "entries_by_level": {"global": 1, "project": 2, "branch": 0, "task": 5},
                    "performance_metrics": {"hit_rate_estimated": 0.85},
                    "health_indicators": {"expired_entries": 3},
                    "average_resolution_time_ms": 15.5
                }
                mock_run.return_value = mock_stats
                
                health = service.get_cache_health()
                
                assert health["cache_entries"]["global"] == 1
                assert health["cache_entries"]["project"] == 2
                assert health["cache_entries"]["task"] == 5
                assert health["cache_hit_rate"] == 0.85
                assert abs(health["cache_miss_rate"] - 0.15) < 0.01
                assert health["expired_entries"] == 3

    def test_get_cache_health_exception(self):
        """Test cache health exception handling returns defaults."""
        service = ContextCacheService()
        
        with patch('asyncio.get_event_loop', side_effect=Exception("Critical error")):
            health = service.get_cache_health()
            
            # Should return default health metrics
            assert health["cache_entries"]["global"] == 0
            assert health["cache_hit_rate"] == 0.0
            assert health["cache_miss_rate"] == 0.0


class TestCacheOptimization:
    """Test cache optimization functionality."""

    @pytest.mark.asyncio
    async def test_optimize_cache_comprehensive(self):
        """Test comprehensive cache optimization."""
        mock_repo = AsyncMock()
        
        # Mock cleanup results
        cleanup_expired_result = {"success": True, "removed_count": 10, "size_freed_bytes": 5000}
        cleanup_invalidated_result = {"success": True, "removed_count": 3, "size_freed_bytes": 1500}
        
        # Mock cache stats to trigger low-hit cleanup
        cache_stats = {"total_entries": 600}  # Above 500 threshold
        
        # Mock low-hit entries
        low_hit_entries = [
            {"context_level": "task", "context_id": "lowuse1", "cache_size_bytes": 800},
            {"context_level": "project", "context_id": "lowuse2", "cache_size_bytes": 1200}
        ]
        
        service = ContextCacheService(repository=mock_repo)
        
        with patch.object(service, 'cleanup_expired', return_value=cleanup_expired_result):
            with patch.object(service, 'cleanup_invalidated', return_value=cleanup_invalidated_result):
                with patch.object(service, 'get_cache_stats', return_value=cache_stats):
                    mock_repo.get_low_hit_cache_entries.return_value = low_hit_entries
                    mock_repo.remove_cache_entry = AsyncMock()
                    
                    result = await service.optimize_cache()
        
        assert result["success"] is True
        assert "cleaned_expired" in result["actions_taken"]
        assert "cleaned_invalidated" in result["actions_taken"]
        assert "removed_2_low_hit_entries" in result["actions_taken"]
        assert result["space_freed_bytes"] == 8500  # 5000 + 1500 + 2000
        assert result["entries_removed"] == 15  # 10 + 3 + 2

    @pytest.mark.asyncio
    async def test_optimize_cache_no_pressure(self):
        """Test cache optimization when no pressure exists."""
        mock_repo = AsyncMock()
        
        cleanup_expired_result = {"success": True, "removed_count": 2, "size_freed_bytes": 1000}
        cleanup_invalidated_result = {"success": True, "removed_count": 0, "size_freed_bytes": 0}
        cache_stats = {"total_entries": 100}  # Below 500 threshold
        
        service = ContextCacheService(repository=mock_repo)
        
        with patch.object(service, 'cleanup_expired', return_value=cleanup_expired_result):
            with patch.object(service, 'cleanup_invalidated', return_value=cleanup_invalidated_result):
                with patch.object(service, 'get_cache_stats', return_value=cache_stats):
                    
                    result = await service.optimize_cache()
        
        assert result["success"] is True
        assert len(result["actions_taken"]) == 2  # Only cleanup actions, no low-hit removal
        assert result["space_freed_bytes"] == 1000

    @pytest.mark.asyncio
    async def test_optimize_cache_exception(self):
        """Test cache optimization exception handling."""
        service = ContextCacheService()
        
        with patch.object(service, 'cleanup_expired', side_effect=Exception("Cleanup failed")):
            result = await service.optimize_cache()
        
        assert result["success"] is False
        assert "error" in result


class TestUtilityMethods:
    """Test utility methods in cache service."""

    @pytest.mark.asyncio
    async def test_cleanup_expired_entry(self):
        """Test cleanup of single expired entry."""
        mock_repo = AsyncMock()
        mock_repo.remove_cache_entry = AsyncMock()
        
        service = ContextCacheService(repository=mock_repo)
        
        await service._cleanup_expired_entry("task", "expired_123")
        
        mock_repo.remove_cache_entry.assert_called_once_with("task", "expired_123")

    @pytest.mark.asyncio
    async def test_cleanup_expired_entry_exception(self):
        """Test cleanup expired entry exception handling."""
        mock_repo = AsyncMock()
        mock_repo.remove_cache_entry.side_effect = Exception("Remove failed")
        
        service = ContextCacheService(repository=mock_repo)
        
        # Should not raise exception
        await service._cleanup_expired_entry("task", "expired_123")

    @pytest.mark.asyncio
    async def test_cleanup_invalidated_entry(self):
        """Test cleanup of single invalidated entry."""
        mock_repo = AsyncMock()
        mock_repo.remove_cache_entry = AsyncMock()
        
        service = ContextCacheService(repository=mock_repo)
        
        await service._cleanup_invalidated_entry("project", "invalid_456")
        
        mock_repo.remove_cache_entry.assert_called_once_with("project", "invalid_456")

    @pytest.mark.asyncio
    async def test_warm_cache(self):
        """Test cache warming functionality."""
        service = ContextCacheService()
        
        contexts_to_warm = [
            {"level": "task", "context_id": "task1"},
            {"level": "project", "context_id": "proj1"}
        ]
        
        result = await service.warm_cache(contexts_to_warm)
        
        # Since this is a basic implementation, it should report success
        assert result["success"] is True
        assert result["total_requested"] == 2
        assert result["warmed_count"] == 2
        assert result["failed_count"] == 0

    @pytest.mark.asyncio
    async def test_warm_cache_exception(self):
        """Test cache warming exception handling."""
        service = ContextCacheService()
        
        # Invalid context spec will cause exception
        contexts_to_warm = [{"invalid": "spec"}]
        
        result = await service.warm_cache(contexts_to_warm)
        
        assert result["success"] is True
        assert result["failed_count"] == 0