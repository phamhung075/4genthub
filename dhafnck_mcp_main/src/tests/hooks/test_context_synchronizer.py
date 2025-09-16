#!/usr/bin/env python3
"""
Tests for Context Synchronization Module

Tests the real-time context synchronization functionality including:
- Context change tracking and queuing
- Conflict resolution strategies
- Shared cache management
- Performance optimization
- Asynchronous synchronization

Part of subtask: db40a3dd-7ac0-4046-885e-15d762b9283d
"""

import pytest
import asyncio
import time
import json
from unittest.mock import Mock, patch, AsyncMock
from dataclasses import asdict
from datetime import datetime, timedelta

import sys
from pathlib import Path

# Add hooks utils to path for testing
hooks_utils_path = Path(__file__).parent.parent.parent.parent.parent / '.claude' / 'hooks' / 'utils'
sys.path.insert(0, str(hooks_utils_path.absolute()))

try:
    from context_synchronizer import (
        ContextSynchronizer,
        ContextChange,
        ConflictResolver,
        ConflictResolutionStrategy,
        SynchronizationConfig,
        sync_context_change,
        get_global_synchronizer
    )
except ImportError:
    pytest.skip("context_synchronizer module not available", allow_module_level=True)


class TestContextChange:
    """Test ContextChange dataclass functionality."""

    def test_context_change_creation(self):
        """Test creating a ContextChange instance."""
        change = ContextChange(
            change_id="test_123",
            timestamp=time.time(),
            source="pre_tool_hook",
            operation="update",
            context_type="task",
            context_id="task_456",
            changes={"status": "in_progress"},
            priority=3
        )

        assert change.change_id == "test_123"
        assert change.source == "pre_tool_hook"
        assert change.operation == "update"
        assert change.context_type == "task"
        assert change.context_id == "task_456"
        assert change.changes == {"status": "in_progress"}
        assert change.priority == 3
        assert change.requires_sync is True

    def test_context_change_defaults(self):
        """Test ContextChange with default values."""
        change = ContextChange(
            change_id="test_123",
            timestamp=time.time(),
            source="test",
            operation="create",
            context_type="project",
            context_id="proj_456",
            changes={"name": "Test Project"}
        )

        assert change.priority == 1  # Default priority
        assert change.requires_sync is True  # Default sync requirement


class TestSynchronizationConfig:
    """Test SynchronizationConfig functionality."""

    def test_default_config(self):
        """Test default configuration values."""
        config = SynchronizationConfig()

        assert config.enable_real_time_sync is True
        assert config.conflict_resolution == ConflictResolutionStrategy.LATEST_WINS
        assert config.sync_timeout_ms == 2000
        assert config.max_pending_changes == 100
        assert config.batch_sync_interval_ms == 500
        assert config.enable_change_broadcast is True

    def test_custom_config(self):
        """Test custom configuration values."""
        config = SynchronizationConfig(
            enable_real_time_sync=False,
            conflict_resolution=ConflictResolutionStrategy.PRIORITY_BASED,
            sync_timeout_ms=5000,
            max_pending_changes=50
        )

        assert config.enable_real_time_sync is False
        assert config.conflict_resolution == ConflictResolutionStrategy.PRIORITY_BASED
        assert config.sync_timeout_ms == 5000
        assert config.max_pending_changes == 50


class TestConflictResolver:
    """Test conflict resolution strategies."""

    def setup_method(self):
        """Set up test fixtures."""
        self.resolver = ConflictResolver(ConflictResolutionStrategy.LATEST_WINS)

    @pytest.mark.asyncio
    async def test_latest_wins_strategy(self):
        """Test latest wins conflict resolution."""
        # Create conflicting changes for same context
        conflicts = [
            {
                'change_id': 'change_1',
                'timestamp': time.time() - 10,  # Older
                'source': 'source_1',
                'operation': 'update',
                'context_type': 'task',
                'context_id': 'task_123',
                'changes': {'status': 'pending'},
                'priority': 1
            },
            {
                'change_id': 'change_2',
                'timestamp': time.time(),  # Newer
                'source': 'source_2',
                'operation': 'update',
                'context_type': 'task',
                'context_id': 'task_123',
                'changes': {'status': 'in_progress'},
                'priority': 1
            }
        ]

        resolved = await self.resolver.resolve_conflicts(conflicts)

        assert len(resolved) == 1
        assert resolved[0].change_id == 'change_2'  # Latest change wins
        assert resolved[0].changes == {'status': 'in_progress'}

    @pytest.mark.asyncio
    async def test_priority_based_strategy(self):
        """Test priority-based conflict resolution."""
        resolver = ConflictResolver(ConflictResolutionStrategy.PRIORITY_BASED)

        conflicts = [
            {
                'change_id': 'change_1',
                'timestamp': time.time(),
                'source': 'source_1',
                'operation': 'update',
                'context_type': 'task',
                'context_id': 'task_123',
                'changes': {'status': 'pending'},
                'priority': 2  # Lower priority
            },
            {
                'change_id': 'change_2',
                'timestamp': time.time() - 5,  # Older but higher priority
                'source': 'source_2',
                'operation': 'update',
                'context_type': 'task',
                'context_id': 'task_123',
                'changes': {'status': 'in_progress'},
                'priority': 5  # Higher priority
            }
        ]

        resolved = await resolver.resolve_conflicts(conflicts)

        assert len(resolved) == 1
        assert resolved[0].change_id == 'change_2'  # Higher priority wins
        assert resolved[0].changes == {'status': 'in_progress'}

    @pytest.mark.asyncio
    async def test_merge_compatible_strategy(self):
        """Test merge compatible conflict resolution."""
        resolver = ConflictResolver(ConflictResolutionStrategy.MERGE_COMPATIBLE)

        # Non-conflicting field changes
        conflicts = [
            {
                'change_id': 'change_1',
                'timestamp': time.time() - 5,
                'source': 'source_1',
                'operation': 'update',
                'context_type': 'task',
                'context_id': 'task_123',
                'changes': {'status': 'in_progress'},
                'priority': 1
            },
            {
                'change_id': 'change_2',
                'timestamp': time.time(),
                'source': 'source_2',
                'operation': 'update',
                'context_type': 'task',
                'context_id': 'task_123',
                'changes': {'assignee': 'john_doe'},
                'priority': 1
            }
        ]

        resolved = await resolver.resolve_conflicts(conflicts)

        assert len(resolved) == 1
        # Merged changes should contain both updates
        assert 'status' in resolved[0].changes
        assert 'assignee' in resolved[0].changes
        assert resolved[0].changes['status'] == 'in_progress'
        assert resolved[0].changes['assignee'] == 'john_doe'

    @pytest.mark.asyncio
    async def test_merge_fallback_on_conflicts(self):
        """Test merge strategy falls back to latest wins on field conflicts."""
        resolver = ConflictResolver(ConflictResolutionStrategy.MERGE_COMPATIBLE)

        # Conflicting field changes (both update 'status')
        conflicts = [
            {
                'change_id': 'change_1',
                'timestamp': time.time() - 5,
                'source': 'source_1',
                'operation': 'update',
                'context_type': 'task',
                'context_id': 'task_123',
                'changes': {'status': 'pending'},
                'priority': 1
            },
            {
                'change_id': 'change_2',
                'timestamp': time.time(),
                'source': 'source_2',
                'operation': 'update',
                'context_type': 'task',
                'context_id': 'task_123',
                'changes': {'status': 'in_progress'},
                'priority': 1
            }
        ]

        resolved = await resolver.resolve_conflicts(conflicts)

        assert len(resolved) == 1
        # Should fall back to latest wins
        assert resolved[0].change_id == 'change_2'
        assert resolved[0].changes == {'status': 'in_progress'}

    @pytest.mark.asyncio
    async def test_no_conflicts(self):
        """Test conflict resolution with no actual conflicts."""
        conflicts = []

        resolved = await self.resolver.resolve_conflicts(conflicts)

        assert len(resolved) == 0

    def test_resolution_history_tracking(self):
        """Test that conflict resolutions are tracked in history."""
        initial_history_count = len(self.resolver.resolution_history)

        # Simulate logging a resolution
        self.resolver._log_resolution(
            context_key="task:123",
            strategy="latest_wins",
            conflict_count=2,
            winning_change_id="change_456"
        )

        assert len(self.resolver.resolution_history) == initial_history_count + 1

        latest_entry = self.resolver.resolution_history[-1]
        assert latest_entry['context_key'] == "task:123"
        assert latest_entry['strategy'] == "latest_wins"
        assert latest_entry['conflict_count'] == 2
        assert latest_entry['winning_change_id'] == "change_456"

    def test_resolution_history_limit(self):
        """Test that resolution history is limited to prevent memory issues."""
        # Fill history beyond limit
        for i in range(105):  # Exceed the 100 limit
            self.resolver._log_resolution(
                context_key=f"task:{i}",
                strategy="test",
                conflict_count=1,
                winning_change_id=f"change_{i}"
            )

        # Should be limited to 100 entries
        assert len(self.resolver.resolution_history) == 100

        # Should contain the most recent entries
        latest_entry = self.resolver.resolution_history[-1]
        assert "104" in latest_entry['context_key']  # Most recent


class TestContextSynchronizer:
    """Test main ContextSynchronizer functionality."""

    def setup_method(self):
        """Set up test fixtures."""
        config = SynchronizationConfig(
            sync_timeout_ms=1000,  # Shorter timeout for tests
            max_pending_changes=10
        )

        with patch('context_synchronizer.SessionContextCache') as mock_cache_class, \
             patch('context_synchronizer.OptimizedMCPClient') as mock_client_class:

            self.mock_cache = Mock()
            self.mock_client = Mock()
            mock_cache_class.return_value = self.mock_cache
            mock_client_class.return_value = self.mock_client

            self.synchronizer = ContextSynchronizer(config)

    def test_initialization(self):
        """Test ContextSynchronizer initialization."""
        assert self.synchronizer.config.sync_timeout_ms == 1000
        assert self.synchronizer.config.max_pending_changes == 10
        assert len(self.synchronizer.pending_changes) == 0
        assert self.synchronizer.sync_stats['total_syncs'] == 0

    def test_add_context_change(self):
        """Test adding context changes to the queue."""
        change = self.synchronizer.add_context_change(
            source="test",
            operation="update",
            context_type="task",
            context_id="task_123",
            changes={"status": "completed"},
            priority=3
        )

        assert len(self.synchronizer.pending_changes) == 1
        assert change.source == "test"
        assert change.operation == "update"
        assert change.context_type == "task"
        assert change.context_id == "task_123"
        assert change.changes == {"status": "completed"}
        assert change.priority == 3
        assert change.change_id.startswith("test_")

    def test_pending_changes_limit(self):
        """Test that pending changes are limited to prevent memory issues."""
        # Add changes beyond the limit
        for i in range(15):  # Exceed the limit of 10
            self.synchronizer.add_context_change(
                source="test",
                operation="update",
                context_type="task",
                context_id=f"task_{i}",
                changes={"iteration": i}
            )

        # Should be limited to the configured max
        assert len(self.synchronizer.pending_changes) == 10

    @pytest.mark.asyncio
    async def test_sync_context_changes_success(self):
        """Test successful context synchronization."""
        changes = [
            ContextChange(
                change_id="test_1",
                timestamp=time.time(),
                source="test",
                operation="update",
                context_type="task",
                context_id="task_123",
                changes={"status": "completed"}
            )
        ]

        # Mock cache operations
        self.mock_cache.get.return_value = {"existing": "data"}
        self.mock_cache.set.return_value = None

        result = await self.synchronizer.sync_context_changes(changes)

        assert result is True
        assert self.synchronizer.sync_stats['total_syncs'] == 1
        assert self.synchronizer.sync_stats['successful_syncs'] == 1

        # Verify cache was updated
        self.mock_cache.set.assert_called()

    @pytest.mark.asyncio
    async def test_sync_context_changes_with_conflicts(self):
        """Test synchronization with conflicts."""
        # Create conflicting changes
        changes = [
            ContextChange(
                change_id="test_1",
                timestamp=time.time() - 2,
                source="source_1",
                operation="update",
                context_type="task",
                context_id="task_123",
                changes={"status": "pending"}
            ),
            ContextChange(
                change_id="test_2",
                timestamp=time.time(),
                source="source_2",
                operation="update",
                context_type="task",
                context_id="task_123",
                changes={"status": "completed"}
            )
        ]

        self.mock_cache.get.return_value = {}

        result = await self.synchronizer.sync_context_changes(changes)

        assert result is True
        assert self.synchronizer.sync_stats['conflicts_resolved'] > 0

    @pytest.mark.asyncio
    async def test_sync_timeout(self):
        """Test synchronization timeout handling."""
        # Configure very short timeout
        self.synchronizer.config.sync_timeout_ms = 1  # 1ms timeout

        changes = [ContextChange(
            change_id="test_1",
            timestamp=time.time(),
            source="test",
            operation="update",
            context_type="task",
            context_id="task_123",
            changes={"status": "completed"}
        )]

        # Make cache operations slow to trigger timeout
        async def slow_operation(*args, **kwargs):
            await asyncio.sleep(0.1)  # 100ms delay
            return {}

        with patch.object(self.synchronizer, '_apply_changes_to_cache', side_effect=slow_operation):
            result = await self.synchronizer.sync_context_changes(changes)

        assert result is False  # Should fail due to timeout
        assert self.synchronizer.sync_stats['total_syncs'] == 1
        assert self.synchronizer.sync_stats['successful_syncs'] == 0

    @pytest.mark.asyncio
    async def test_sync_pending_changes(self):
        """Test syncing all pending changes."""
        # Add some pending changes
        self.synchronizer.add_context_change(
            source="test1",
            operation="update",
            context_type="task",
            context_id="task_1",
            changes={"status": "in_progress"}
        )
        self.synchronizer.add_context_change(
            source="test2",
            operation="update",
            context_type="task",
            context_id="task_2",
            changes={"assignee": "alice"}
        )

        assert len(self.synchronizer.pending_changes) == 2

        # Mock cache operations
        self.mock_cache.get.return_value = {}

        result = await self.synchronizer.sync_pending_changes()

        assert result is True
        assert len(self.synchronizer.pending_changes) == 0  # Should be cleared

    def test_detect_conflicts(self):
        """Test conflict detection logic."""
        # Create changes with conflicts (same context, close timestamps)
        changes = [
            ContextChange(
                change_id="change_1",
                timestamp=time.time(),
                source="source_1",
                operation="update",
                context_type="task",
                context_id="task_123",
                changes={"status": "pending"}
            ),
            ContextChange(
                change_id="change_2",
                timestamp=time.time() + 1,  # 1 second later (within 5s window)
                source="source_2",
                operation="update",
                context_type="task",
                context_id="task_123",
                changes={"status": "completed"}
            ),
            ContextChange(
                change_id="change_3",
                timestamp=time.time(),
                source="source_3",
                operation="update",
                context_type="project",
                context_id="project_456",
                changes={"name": "Updated"}
            )
        ]

        conflicts = self.synchronizer._detect_conflicts(changes)

        # Should detect 2 conflicts (the task changes)
        assert len(conflicts) == 2
        assert all(c['context_id'] == 'task_123' for c in conflicts)

    def test_detect_no_conflicts_different_contexts(self):
        """Test that changes to different contexts don't conflict."""
        changes = [
            ContextChange(
                change_id="change_1",
                timestamp=time.time(),
                source="source_1",
                operation="update",
                context_type="task",
                context_id="task_123",
                changes={"status": "pending"}
            ),
            ContextChange(
                change_id="change_2",
                timestamp=time.time(),
                source="source_2",
                operation="update",
                context_type="task",
                context_id="task_456",  # Different task
                changes={"status": "completed"}
            )
        ]

        conflicts = self.synchronizer._detect_conflicts(changes)

        assert len(conflicts) == 0  # No conflicts for different contexts

    def test_detect_no_conflicts_time_window(self):
        """Test that changes outside time window don't conflict."""
        changes = [
            ContextChange(
                change_id="change_1",
                timestamp=time.time(),
                source="source_1",
                operation="update",
                context_type="task",
                context_id="task_123",
                changes={"status": "pending"}
            ),
            ContextChange(
                change_id="change_2",
                timestamp=time.time() + 10,  # 10 seconds later (outside 5s window)
                source="source_2",
                operation="update",
                context_type="task",
                context_id="task_123",
                changes={"status": "completed"}
            )
        ]

        conflicts = self.synchronizer._detect_conflicts(changes)

        assert len(conflicts) == 0  # No conflicts outside time window

    def test_get_cache_ttl(self):
        """Test cache TTL determination based on context type."""
        assert self.synchronizer._get_cache_ttl("task") == 900  # 15 minutes
        assert self.synchronizer._get_cache_ttl("subtask") == 600  # 10 minutes
        assert self.synchronizer._get_cache_ttl("branch") == 1800  # 30 minutes
        assert self.synchronizer._get_cache_ttl("project") == 3600  # 1 hour
        assert self.synchronizer._get_cache_ttl("global") == 7200  # 2 hours
        assert self.synchronizer._get_cache_ttl("unknown") == 900  # Default 15 minutes

    def test_sync_statistics_tracking(self):
        """Test synchronization statistics tracking."""
        initial_stats = self.synchronizer.get_sync_statistics()

        assert initial_stats['total_syncs'] == 0
        assert initial_stats['successful_syncs'] == 0
        assert initial_stats['success_rate'] == 0
        assert initial_stats['conflicts_resolved'] == 0
        assert initial_stats['pending_changes_count'] == 0

        # Update stats manually for testing
        self.synchronizer._update_sync_stats(100.5, True)
        self.synchronizer._update_sync_stats(50.0, False)

        updated_stats = self.synchronizer.get_sync_statistics()

        assert updated_stats['total_syncs'] == 2
        assert updated_stats['successful_syncs'] == 1
        assert updated_stats['success_rate'] == 0.5
        assert updated_stats['average_sync_time_ms'] > 0


class TestConvenienceFunctions:
    """Test convenience functions and global synchronizer."""

    def test_sync_context_change_function(self):
        """Test the sync_context_change convenience function."""
        with patch('context_synchronizer.get_global_synchronizer') as mock_get_sync:
            mock_synchronizer = Mock()
            mock_synchronizer.config.enable_real_time_sync = False  # Disable for sync test
            mock_synchronizer.add_context_change.return_value = Mock()
            mock_get_sync.return_value = mock_synchronizer

            result = sync_context_change(
                source="test",
                operation="update",
                context_type="task",
                context_id="task_123",
                changes={"status": "completed"},
                priority=2
            )

            assert result is True
            mock_synchronizer.add_context_change.assert_called_once_with(
                source="test",
                operation="update",
                context_type="task",
                context_id="task_123",
                changes={"status": "completed"},
                priority=2
            )

    def test_get_global_synchronizer_singleton(self):
        """Test that global synchronizer is a singleton."""
        with patch('context_synchronizer.create_context_synchronizer') as mock_create:
            mock_sync = Mock()
            mock_create.return_value = mock_sync

            # First call should create synchronizer
            sync1 = get_global_synchronizer()
            assert sync1 == mock_sync
            mock_create.assert_called_once()

            # Second call should return same instance
            sync2 = get_global_synchronizer()
            assert sync2 == mock_sync
            assert sync1 is sync2
            mock_create.assert_called_once()  # Still only called once


class TestAsyncOperations:
    """Test asynchronous operations and performance."""

    @pytest.mark.asyncio
    async def test_concurrent_synchronization(self):
        """Test concurrent synchronization operations."""
        config = SynchronizationConfig(sync_timeout_ms=5000)

        with patch('context_synchronizer.SessionContextCache') as mock_cache_class, \
             patch('context_synchronizer.OptimizedMCPClient') as mock_client_class:

            mock_cache = Mock()
            mock_client = Mock()
            mock_cache_class.return_value = mock_cache
            mock_client_class.return_value = mock_client
            mock_cache.get.return_value = {}

            synchronizer = ContextSynchronizer(config)

            # Create multiple change sets
            change_sets = [
                [ContextChange(
                    change_id=f"change_{i}_{j}",
                    timestamp=time.time(),
                    source=f"source_{i}",
                    operation="update",
                    context_type="task",
                    context_id=f"task_{i}",
                    changes={"iteration": j}
                ) for j in range(3)]
                for i in range(5)
            ]

            # Run synchronizations concurrently
            tasks = [
                synchronizer.sync_context_changes(changes)
                for changes in change_sets
            ]

            results = await asyncio.gather(*tasks, return_exceptions=True)

            # All should succeed
            assert all(result is True for result in results if not isinstance(result, Exception))
            assert synchronizer.sync_stats['total_syncs'] == 5

    @pytest.mark.asyncio
    async def test_performance_threshold_monitoring(self):
        """Test performance threshold monitoring."""
        config = SynchronizationConfig(performance_threshold_ms=50)  # Very low threshold

        with patch('context_synchronizer.SessionContextCache') as mock_cache_class, \
             patch('context_synchronizer.OptimizedMCPClient') as mock_client_class:

            mock_cache = Mock()
            mock_client = Mock()
            mock_cache_class.return_value = mock_cache
            mock_client_class.return_value = mock_client

            # Make operations slow to exceed threshold
            async def slow_cache_operation(*args, **kwargs):
                await asyncio.sleep(0.1)  # 100ms delay
                return {}

            mock_cache.get.return_value = {}

            synchronizer = ContextSynchronizer(config)

            changes = [ContextChange(
                change_id="slow_change",
                timestamp=time.time(),
                source="test",
                operation="update",
                context_type="task",
                context_id="task_123",
                changes={"status": "slow"}
            )]

            with patch.object(synchronizer, '_apply_changes_to_cache', side_effect=slow_cache_operation):
                with patch('context_synchronizer.logger') as mock_logger:
                    result = await synchronizer.sync_context_changes(changes)

                    # Should log performance warning
                    mock_logger.warning.assert_called()
                    warning_call = mock_logger.warning.call_args[0][0]
                    assert "exceeded threshold" in warning_call


if __name__ == "__main__":
    pytest.main([__file__, "-v"])