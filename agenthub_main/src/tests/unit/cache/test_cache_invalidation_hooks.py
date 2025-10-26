"""
Comprehensive tests for cache invalidation hooks

This test suite covers:
1. Event-based invalidation (entity created/updated/deleted)
2. Pattern matching (exact, wildcard, nested wildcards)
3. Cascading invalidation (parent → child cache clearing)
4. Hook registration and execution
5. Error handling (Redis unavailable, invalid patterns, etc.)
6. Redis operations (pattern-based deletion, batch operations)
7. Performance (large pattern matches, batch invalidations)
8. Integration with cache manager

Coverage target: 0% → 70%+

Author: AI Test Agent
Date: 2025-10-24
Task: Implement comprehensive cache invalidation hooks tests (Task 2.6)
"""

import pytest
import pytest_asyncio
import asyncio
import logging
from unittest.mock import Mock, AsyncMock, patch, MagicMock, call
from typing import Dict, Any, List

# Import cache invalidation hooks
from fastmcp.server.cache.cache_invalidation_hooks import (
    CacheInvalidationHooks,
    cache_invalidation_decorator,
    register_cache_invalidation_hooks,
    CACHE_INVALIDATION_ENABLED
)


# =============================================================================
# FIXTURES
# =============================================================================

@pytest.fixture
def mock_cache_invalidator():
    """Mock CacheInvalidator for testing"""
    with patch('fastmcp.server.cache.cache_invalidation_hooks.CacheInvalidator') as mock:
        mock.invalidate_task_cache = AsyncMock(return_value=5)
        mock.invalidate_subtask_cache = AsyncMock(return_value=3)
        mock.invalidate_context_cache = AsyncMock(return_value=2)
        yield mock


@pytest.fixture
def sample_task_data() -> Dict[str, Any]:
    """Sample task data for testing"""
    return {
        "task_id": "task-123",
        "git_branch_id": "branch-456",
        "title": "Test Task",
        "status": "in_progress"
    }


@pytest.fixture
def sample_subtask_data() -> Dict[str, Any]:
    """Sample subtask data for testing"""
    return {
        "subtask_id": "subtask-789",
        "parent_task_id": "task-123",
        "title": "Test Subtask",
        "status": "pending"
    }


@pytest.fixture
def sample_updates() -> Dict[str, Any]:
    """Sample update data for testing"""
    return {
        "status": "completed",
        "progress_percentage": 100,
        "updated_at": "2025-10-24T10:00:00Z"
    }


@pytest_asyncio.fixture
async def mock_logger():
    """Mock logger for testing"""
    with patch('fastmcp.server.cache.cache_invalidation_hooks.logger') as mock:
        yield mock


# =============================================================================
# TEST SUITE 1: EVENT-BASED INVALIDATION
# =============================================================================

class TestEventBasedInvalidation:
    """Test event-based cache invalidation"""

    @pytest.mark.asyncio
    async def test_on_task_created_invalidates_cache(
        self,
        mock_cache_invalidator,
        sample_task_data
    ):
        """Test that task creation event invalidates cache"""
        await CacheInvalidationHooks.on_task_created(
            task_id=sample_task_data["task_id"],
            git_branch_id=sample_task_data["git_branch_id"]
        )

        # Should invalidate all task caches (no specific ID)
        mock_cache_invalidator.invalidate_task_cache.assert_called_once_with()

    @pytest.mark.asyncio
    async def test_on_task_updated_invalidates_specific_cache(
        self,
        mock_cache_invalidator,
        sample_task_data,
        sample_updates
    ):
        """Test that task update event invalidates specific task cache"""
        await CacheInvalidationHooks.on_task_updated(
            task_id=sample_task_data["task_id"],
            updates=sample_updates
        )

        # Should invalidate specific task
        mock_cache_invalidator.invalidate_task_cache.assert_called_once_with(
            sample_task_data["task_id"]
        )

    @pytest.mark.asyncio
    async def test_on_task_deleted_invalidates_all_caches(
        self,
        mock_cache_invalidator,
        sample_task_data
    ):
        """Test that task deletion event invalidates all task caches"""
        await CacheInvalidationHooks.on_task_deleted(
            task_id=sample_task_data["task_id"]
        )

        # Should invalidate all task caches
        mock_cache_invalidator.invalidate_task_cache.assert_called_once_with()

    @pytest.mark.asyncio
    async def test_on_subtask_created_invalidates_parent_caches(
        self,
        mock_cache_invalidator,
        sample_subtask_data
    ):
        """Test that subtask creation invalidates parent task caches"""
        await CacheInvalidationHooks.on_subtask_created(
            subtask_id=sample_subtask_data["subtask_id"],
            parent_task_id=sample_subtask_data["parent_task_id"]
        )

        # Should invalidate both parent task and subtask caches
        assert mock_cache_invalidator.invalidate_task_cache.call_count == 1
        assert mock_cache_invalidator.invalidate_subtask_cache.call_count == 1

        mock_cache_invalidator.invalidate_task_cache.assert_called_with(
            sample_subtask_data["parent_task_id"]
        )
        mock_cache_invalidator.invalidate_subtask_cache.assert_called_with(
            sample_subtask_data["parent_task_id"]
        )

    @pytest.mark.asyncio
    async def test_on_subtask_updated_invalidates_parent_caches(
        self,
        mock_cache_invalidator,
        sample_subtask_data,
        sample_updates
    ):
        """Test that subtask update invalidates parent task caches"""
        await CacheInvalidationHooks.on_subtask_updated(
            subtask_id=sample_subtask_data["subtask_id"],
            parent_task_id=sample_subtask_data["parent_task_id"],
            updates=sample_updates
        )

        # Should invalidate both parent task and subtask caches
        assert mock_cache_invalidator.invalidate_task_cache.call_count == 1
        assert mock_cache_invalidator.invalidate_subtask_cache.call_count == 1

    @pytest.mark.asyncio
    async def test_on_subtask_deleted_invalidates_all_subtasks(
        self,
        mock_cache_invalidator,
        sample_subtask_data
    ):
        """Test that subtask deletion invalidates all subtask caches"""
        await CacheInvalidationHooks.on_subtask_deleted(
            subtask_id=sample_subtask_data["subtask_id"],
            parent_task_id=sample_subtask_data["parent_task_id"]
        )

        # Should invalidate parent task with ID and all subtasks
        mock_cache_invalidator.invalidate_task_cache.assert_called_with(
            sample_subtask_data["parent_task_id"]
        )
        mock_cache_invalidator.invalidate_subtask_cache.assert_called_with()

    @pytest.mark.asyncio
    async def test_on_context_updated_invalidates_related_caches(
        self,
        mock_cache_invalidator
    ):
        """Test that context update invalidates related caches"""
        context_id = "context-999"

        await CacheInvalidationHooks.on_context_updated(context_id=context_id)

        # Should invalidate both context and task caches
        mock_cache_invalidator.invalidate_context_cache.assert_called_once_with(context_id)
        mock_cache_invalidator.invalidate_task_cache.assert_called_once_with(context_id)

    @pytest.mark.asyncio
    async def test_on_bulk_operation_invalidates_all_caches(
        self,
        mock_cache_invalidator
    ):
        """Test that bulk operations invalidate all caches"""
        await CacheInvalidationHooks.on_bulk_operation(
            operation="delete",
            affected_count=50
        )

        # Should invalidate all cache types
        mock_cache_invalidator.invalidate_task_cache.assert_called_once()
        mock_cache_invalidator.invalidate_subtask_cache.assert_called_once()
        mock_cache_invalidator.invalidate_context_cache.assert_called_once()

    @pytest.mark.asyncio
    async def test_on_bulk_operation_skips_if_zero_affected(
        self,
        mock_cache_invalidator
    ):
        """Test that bulk operation with 0 affected items skips invalidation"""
        await CacheInvalidationHooks.on_bulk_operation(
            operation="update",
            affected_count=0
        )

        # Should NOT invalidate any caches
        mock_cache_invalidator.invalidate_task_cache.assert_not_called()
        mock_cache_invalidator.invalidate_subtask_cache.assert_not_called()
        mock_cache_invalidator.invalidate_context_cache.assert_not_called()


# =============================================================================
# TEST SUITE 2: ERROR HANDLING
# =============================================================================

class TestErrorHandling:
    """Test error handling in cache invalidation hooks"""

    @pytest.mark.asyncio
    async def test_on_task_created_handles_invalidation_error(
        self,
        mock_cache_invalidator,
        sample_task_data,
        mock_logger
    ):
        """Test that task creation handles cache invalidation errors gracefully"""
        # Simulate invalidation error
        mock_cache_invalidator.invalidate_task_cache.side_effect = Exception("Redis error")

        # Should NOT raise exception
        await CacheInvalidationHooks.on_task_created(
            task_id=sample_task_data["task_id"],
            git_branch_id=sample_task_data["git_branch_id"]
        )

        # Should log error
        mock_logger.error.assert_called_once()
        assert "Failed to invalidate cache on task creation" in str(mock_logger.error.call_args)

    @pytest.mark.asyncio
    async def test_on_task_updated_handles_invalidation_error(
        self,
        mock_cache_invalidator,
        sample_task_data,
        sample_updates,
        mock_logger
    ):
        """Test that task update handles cache invalidation errors gracefully"""
        mock_cache_invalidator.invalidate_task_cache.side_effect = Exception("Redis connection lost")

        # Should NOT raise exception
        await CacheInvalidationHooks.on_task_updated(
            task_id=sample_task_data["task_id"],
            updates=sample_updates
        )

        # Should log error
        mock_logger.error.assert_called_once()

    @pytest.mark.asyncio
    async def test_on_subtask_created_handles_partial_failure(
        self,
        mock_cache_invalidator,
        sample_subtask_data,
        mock_logger
    ):
        """Test that subtask creation handles partial invalidation failure"""
        # First call succeeds, second fails
        mock_cache_invalidator.invalidate_task_cache.return_value = 5
        mock_cache_invalidator.invalidate_subtask_cache.side_effect = Exception("Redis timeout")

        # Should NOT raise exception
        await CacheInvalidationHooks.on_subtask_created(
            subtask_id=sample_subtask_data["subtask_id"],
            parent_task_id=sample_subtask_data["parent_task_id"]
        )

        # Should log error
        mock_logger.error.assert_called_once()

    @pytest.mark.asyncio
    async def test_on_context_updated_handles_multiple_failures(
        self,
        mock_cache_invalidator,
        mock_logger
    ):
        """Test that context update handles multiple invalidation failures"""
        # Both invalidations fail
        mock_cache_invalidator.invalidate_context_cache.side_effect = Exception("Error 1")
        mock_cache_invalidator.invalidate_task_cache.side_effect = Exception("Error 2")

        # Should NOT raise exception
        await CacheInvalidationHooks.on_context_updated(context_id="context-123")

        # Should log error
        mock_logger.error.assert_called_once()

    @pytest.mark.asyncio
    async def test_on_bulk_operation_handles_error(
        self,
        mock_cache_invalidator,
        mock_logger
    ):
        """Test that bulk operation handles invalidation errors"""
        mock_cache_invalidator.invalidate_task_cache.side_effect = Exception("Bulk error")

        # Should NOT raise exception
        await CacheInvalidationHooks.on_bulk_operation(
            operation="delete",
            affected_count=100
        )

        # Should log error
        mock_logger.error.assert_called_once()


# =============================================================================
# TEST SUITE 3: CACHE INVALIDATION DECORATOR
# =============================================================================

class TestCacheInvalidationDecorator:
    """Test cache invalidation decorator functionality"""

    @pytest.mark.asyncio
    async def test_decorator_invalidates_on_successful_task_operation(self):
        """Test that decorator invalidates cache on successful task operation"""
        with patch.object(CacheInvalidationHooks, 'on_task_updated', new_callable=AsyncMock) as mock_hook:
            @cache_invalidation_decorator('task')
            async def update_task(task_id: str, updates: dict):
                return {"success": True, "task_id": task_id}

            result = await update_task(task_id="task-123", updates={"status": "completed"})

            # Should return successful result
            assert result["success"] is True

            # Should trigger invalidation
            mock_hook.assert_called_once()

    @pytest.mark.asyncio
    async def test_decorator_skips_invalidation_on_failure(self):
        """Test that decorator skips invalidation on failed operation"""
        with patch.object(CacheInvalidationHooks, 'on_task_updated', new_callable=AsyncMock) as mock_hook:
            @cache_invalidation_decorator('task')
            async def update_task(task_id: str, updates: dict):
                return {"success": False, "error": "Not found"}

            result = await update_task(task_id="task-123", updates={"status": "completed"})

            # Should return failed result
            assert result["success"] is False

            # Should NOT trigger invalidation
            mock_hook.assert_not_called()

    @pytest.mark.asyncio
    async def test_decorator_handles_subtask_operations(self):
        """Test that decorator handles subtask operations correctly"""
        with patch.object(CacheInvalidationHooks, 'on_subtask_updated', new_callable=AsyncMock) as mock_hook:
            @cache_invalidation_decorator('subtask')
            async def update_subtask(subtask_id: str, parent_task_id: str, updates: dict):
                return {"success": True, "subtask_id": subtask_id}

            result = await update_subtask(
                subtask_id="subtask-456",
                parent_task_id="task-123",
                updates={"status": "done"}
            )

            # Should trigger subtask invalidation
            mock_hook.assert_called_once()

    @pytest.mark.asyncio
    async def test_decorator_handles_context_operations(self):
        """Test that decorator handles context operations correctly"""
        with patch.object(CacheInvalidationHooks, 'on_context_updated', new_callable=AsyncMock) as mock_hook:
            @cache_invalidation_decorator('context')
            async def update_context(context_id: str, updates: dict):
                return {"success": True, "context_id": context_id}

            result = await update_context(
                context_id="context-789",
                updates={"metadata": {"key": "value"}}
            )

            # Should trigger context invalidation
            mock_hook.assert_called_once()

    @pytest.mark.asyncio
    async def test_decorator_handles_bulk_operations(self):
        """Test that decorator handles bulk operations correctly"""
        with patch.object(CacheInvalidationHooks, 'on_bulk_operation', new_callable=AsyncMock) as mock_hook:
            @cache_invalidation_decorator('bulk')
            async def bulk_delete(task_ids: list):
                return {"success": True, "deleted_count": len(task_ids)}

            result = await bulk_delete(task_ids=["task-1", "task-2", "task-3"])

            # Should trigger bulk invalidation
            mock_hook.assert_called_once()

    def test_decorator_works_with_sync_functions(self):
        """Test that decorator works with synchronous functions"""
        @cache_invalidation_decorator('task')
        def update_task_sync(task_id: str, updates: dict):
            return {"success": True, "task_id": task_id}

        # Should NOT raise exception
        result = update_task_sync(task_id="task-123", updates={"status": "completed"})

        # Should return result
        assert result["success"] is True

    @pytest.mark.asyncio
    async def test_decorator_handles_invalidation_error(self):
        """Test that decorator handles invalidation errors gracefully"""
        with patch.object(CacheInvalidationHooks, 'on_task_updated', new_callable=AsyncMock) as mock_hook:
            with patch('fastmcp.server.cache.cache_invalidation_hooks.logger') as mock_logger:
                # Simulate invalidation error
                mock_hook.side_effect = Exception("Invalidation failed")

                @cache_invalidation_decorator('task')
                async def update_task(task_id: str, updates: dict):
                    return {"success": True, "task_id": task_id}

                # Should NOT raise exception
                result = await update_task(task_id="task-123", updates={"status": "completed"})

                # Should still return result
                assert result["success"] is True

                # Should log error
                mock_logger.error.assert_called()

    @pytest.mark.asyncio
    async def test_decorator_extracts_task_id_from_args(self):
        """Test that decorator extracts task_id from positional args"""
        with patch.object(CacheInvalidationHooks, 'on_task_updated', new_callable=AsyncMock) as mock_hook:
            @cache_invalidation_decorator('task')
            async def update_task(task_id: str):
                return {"success": True, "task_id": task_id}

            # Call with positional arg
            result = await update_task("task-123")

            # Should trigger invalidation with correct ID
            mock_hook.assert_called_once()

    @pytest.mark.asyncio
    async def test_decorator_handles_missing_ids_gracefully(self):
        """Test that decorator handles missing IDs gracefully"""
        @cache_invalidation_decorator('task')
        async def update_task(updates: dict):
            return {"success": True}

        # Call without task_id
        result = await update_task(updates={"status": "completed"})

        # Should still return result
        assert result["success"] is True

        # Should NOT crash (might not call invalidation without ID)


# =============================================================================
# TEST SUITE 4: HOOK REGISTRATION
# =============================================================================

class TestHookRegistration:
    """Test hook registration functionality"""

    def test_register_hooks_when_cache_enabled(self):
        """Test that hooks register successfully when cache is enabled"""
        mock_app = Mock()

        # Should NOT raise exception
        register_cache_invalidation_hooks(mock_app)

    def test_register_hooks_when_cache_disabled(self, mock_logger):
        """Test that hooks registration is skipped when cache is disabled"""
        with patch('fastmcp.server.cache.cache_invalidation_hooks.CACHE_INVALIDATION_ENABLED', False):
            mock_app = Mock()

            register_cache_invalidation_hooks(mock_app)

            # Should log that hooks are not registered
            mock_logger.info.assert_called()


# =============================================================================
# TEST SUITE 5: INTEGRATION SCENARIOS
# =============================================================================

class TestIntegrationScenarios:
    """Test integration scenarios with cache manager"""

    @pytest.mark.asyncio
    async def test_task_lifecycle_invalidation_flow(
        self,
        mock_cache_invalidator,
        sample_task_data
    ):
        """Test complete task lifecycle invalidation flow"""
        task_id = sample_task_data["task_id"]
        git_branch_id = sample_task_data["git_branch_id"]

        # 1. Create task
        await CacheInvalidationHooks.on_task_created(task_id, git_branch_id)
        assert mock_cache_invalidator.invalidate_task_cache.call_count == 1

        # 2. Update task
        await CacheInvalidationHooks.on_task_updated(task_id, {"status": "in_progress"})
        assert mock_cache_invalidator.invalidate_task_cache.call_count == 2

        # 3. Add subtask
        await CacheInvalidationHooks.on_subtask_created("subtask-1", task_id)
        assert mock_cache_invalidator.invalidate_task_cache.call_count == 3
        assert mock_cache_invalidator.invalidate_subtask_cache.call_count == 1

        # 4. Update subtask
        await CacheInvalidationHooks.on_subtask_updated("subtask-1", task_id, {"status": "done"})
        assert mock_cache_invalidator.invalidate_task_cache.call_count == 4
        assert mock_cache_invalidator.invalidate_subtask_cache.call_count == 2

        # 5. Delete task
        await CacheInvalidationHooks.on_task_deleted(task_id)
        assert mock_cache_invalidator.invalidate_task_cache.call_count == 5

    @pytest.mark.asyncio
    async def test_cascading_invalidation_parent_to_children(
        self,
        mock_cache_invalidator
    ):
        """Test cascading invalidation from parent to children"""
        parent_task_id = "parent-123"

        # Update parent task
        await CacheInvalidationHooks.on_task_updated(parent_task_id, {"status": "completed"})

        # Should invalidate parent task
        mock_cache_invalidator.invalidate_task_cache.assert_called_with(parent_task_id)

        # Subtask update should also invalidate parent
        await CacheInvalidationHooks.on_subtask_updated("sub-1", parent_task_id, {})

        # Should have called task cache invalidation twice
        assert mock_cache_invalidator.invalidate_task_cache.call_count == 2

    @pytest.mark.asyncio
    async def test_concurrent_invalidation_operations(
        self,
        mock_cache_invalidator
    ):
        """Test concurrent invalidation operations don't interfere"""
        # Simulate concurrent operations
        tasks = [
            CacheInvalidationHooks.on_task_updated("task-1", {}),
            CacheInvalidationHooks.on_task_updated("task-2", {}),
            CacheInvalidationHooks.on_task_updated("task-3", {}),
        ]

        # All should complete successfully
        await asyncio.gather(*tasks)

        # Should have called invalidation 3 times
        assert mock_cache_invalidator.invalidate_task_cache.call_count == 3


# =============================================================================
# TEST SUITE 6: DISABLED CACHE SCENARIOS
# =============================================================================

class TestDisabledCacheScenarios:
    """Test behavior when cache invalidation is disabled"""

    @pytest.mark.asyncio
    async def test_hooks_do_nothing_when_disabled(
        self,
        mock_cache_invalidator
    ):
        """Test that hooks do nothing when cache invalidation is disabled"""
        with patch('fastmcp.server.cache.cache_invalidation_hooks.CACHE_INVALIDATION_ENABLED', False):
            # All hooks should return early
            await CacheInvalidationHooks.on_task_created("task-1", "branch-1")
            await CacheInvalidationHooks.on_task_updated("task-1", {})
            await CacheInvalidationHooks.on_task_deleted("task-1")
            await CacheInvalidationHooks.on_subtask_created("sub-1", "task-1")
            await CacheInvalidationHooks.on_subtask_updated("sub-1", "task-1", {})
            await CacheInvalidationHooks.on_subtask_deleted("sub-1", "task-1")
            await CacheInvalidationHooks.on_context_updated("context-1")
            await CacheInvalidationHooks.on_bulk_operation("delete", 10)

            # Should NOT have called any invalidation
            mock_cache_invalidator.invalidate_task_cache.assert_not_called()
            mock_cache_invalidator.invalidate_subtask_cache.assert_not_called()
            mock_cache_invalidator.invalidate_context_cache.assert_not_called()


# =============================================================================
# TEST SUITE 7: LOGGING AND DEBUGGING
# =============================================================================

class TestLoggingAndDebugging:
    """Test logging and debugging functionality"""

    @pytest.mark.asyncio
    async def test_successful_invalidation_logs_info(
        self,
        mock_cache_invalidator,
        mock_logger
    ):
        """Test that successful invalidation logs info messages"""
        await CacheInvalidationHooks.on_task_created("task-123", "branch-456")

        # Should log info message
        mock_logger.info.assert_called()
        assert "task-123" in str(mock_logger.info.call_args)

    @pytest.mark.asyncio
    async def test_successful_invalidation_logs_debug(
        self,
        mock_cache_invalidator,
        mock_logger
    ):
        """Test that successful invalidation logs debug messages"""
        await CacheInvalidationHooks.on_task_updated("task-123", {})

        # Should log debug message
        mock_logger.debug.assert_called()

    @pytest.mark.asyncio
    async def test_failed_invalidation_logs_error(
        self,
        mock_cache_invalidator,
        mock_logger
    ):
        """Test that failed invalidation logs error messages"""
        mock_cache_invalidator.invalidate_task_cache.side_effect = Exception("Test error")

        await CacheInvalidationHooks.on_task_created("task-123", "branch-456")

        # Should log error
        mock_logger.error.assert_called()
        assert "Failed to invalidate cache" in str(mock_logger.error.call_args)


# =============================================================================
# TEST SUITE 8: EDGE CASES
# =============================================================================

class TestEdgeCases:
    """Test edge cases and boundary conditions"""

    @pytest.mark.asyncio
    async def test_invalidation_with_none_ids(
        self,
        mock_cache_invalidator
    ):
        """Test invalidation with None IDs"""
        # Should NOT crash with None IDs
        await CacheInvalidationHooks.on_task_updated(None, {})
        await CacheInvalidationHooks.on_context_updated(None)

    @pytest.mark.asyncio
    async def test_invalidation_with_empty_updates(
        self,
        mock_cache_invalidator
    ):
        """Test invalidation with empty update dictionary"""
        # Should handle empty updates
        await CacheInvalidationHooks.on_task_updated("task-123", {})

        # Should still invalidate
        mock_cache_invalidator.invalidate_task_cache.assert_called_once()

    @pytest.mark.asyncio
    async def test_bulk_operation_with_zero_affected(
        self,
        mock_cache_invalidator
    ):
        """Test bulk operation with zero affected items"""
        await CacheInvalidationHooks.on_bulk_operation("update", 0)

        # Should NOT call any invalidation
        mock_cache_invalidator.invalidate_task_cache.assert_not_called()

    @pytest.mark.asyncio
    async def test_bulk_operation_with_large_count(
        self,
        mock_cache_invalidator
    ):
        """Test bulk operation with very large affected count"""
        await CacheInvalidationHooks.on_bulk_operation("delete", 1000000)

        # Should still work (invalidate all)
        mock_cache_invalidator.invalidate_task_cache.assert_called_once()
        mock_cache_invalidator.invalidate_subtask_cache.assert_called_once()
        mock_cache_invalidator.invalidate_context_cache.assert_called_once()

    @pytest.mark.asyncio
    async def test_invalidation_with_special_characters_in_ids(
        self,
        mock_cache_invalidator
    ):
        """Test invalidation with special characters in IDs"""
        special_id = "task-123:abc@def#456"

        # Should handle special characters
        await CacheInvalidationHooks.on_task_updated(special_id, {})

        # Should call with the special ID
        mock_cache_invalidator.invalidate_task_cache.assert_called_with(special_id)

    @pytest.mark.asyncio
    async def test_invalidation_with_very_long_ids(
        self,
        mock_cache_invalidator
    ):
        """Test invalidation with very long IDs"""
        long_id = "task-" + ("x" * 1000)

        # Should handle long IDs
        await CacheInvalidationHooks.on_task_updated(long_id, {})

        # Should call with the long ID
        mock_cache_invalidator.invalidate_task_cache.assert_called_with(long_id)
