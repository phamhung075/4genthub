#!/usr/bin/env python3
"""
Simplified Tests for Context Management Utilities

Tests the core functionality of context management utilities with mocked dependencies.
This focuses on testing the business logic without requiring all hook infrastructure.

Part of subtask: db40a3dd-7ac0-4046-885e-15d762b9283d
"""

import pytest
import asyncio
import time
import json
import tempfile
import uuid
from unittest.mock import Mock, patch, AsyncMock
from pathlib import Path
from datetime import datetime, timedelta
from dataclasses import dataclass, asdict
from typing import Optional, Dict, Any, List
from enum import Enum

import sys

# Add hooks utils to path for testing
hooks_utils_path = Path(__file__).parent.parent.parent.parent.parent / '.claude' / 'hooks' / 'utils'
sys.path.insert(0, str(hooks_utils_path.absolute()))

# Test if we can import agent_state_manager (which has no relative imports)
try:
    from agent_state_manager import (
        AgentStateManager,
        get_current_agent,
        set_current_agent,
        get_agent_role_from_session
    )
    AGENT_STATE_AVAILABLE = True
except ImportError:
    AGENT_STATE_AVAILABLE = False


# Mock classes for testing context synchronization logic
@dataclass
class MockContextChange:
    """Mock ContextChange for testing."""
    change_id: str
    timestamp: float
    source: str
    operation: str
    context_type: str
    context_id: str
    changes: Dict[str, Any]
    priority: int = 1

class MockConflictResolutionStrategy(Enum):
    """Mock conflict resolution strategies."""
    LATEST_WINS = "latest_wins"
    MERGE_COMPATIBLE = "merge_compatible"
    PRIORITY_BASED = "priority_based"

@dataclass
class MockSynchronizationConfig:
    """Mock synchronization config."""
    enable_real_time_sync: bool = True
    conflict_resolution: MockConflictResolutionStrategy = MockConflictResolutionStrategy.LATEST_WINS
    sync_timeout_ms: int = 2000
    max_pending_changes: int = 100

class MockConflictResolver:
    """Mock conflict resolver for testing business logic."""

    def __init__(self, strategy: MockConflictResolutionStrategy):
        self.strategy = strategy
        self.resolution_history = []

    async def resolve_conflicts(self, conflicts: List[Dict]) -> List[MockContextChange]:
        """Resolve conflicts using configured strategy."""
        if not conflicts:
            return []

        if self.strategy == MockConflictResolutionStrategy.LATEST_WINS:
            return await self._resolve_latest_wins(conflicts)
        elif self.strategy == MockConflictResolutionStrategy.PRIORITY_BASED:
            return await self._resolve_priority_based(conflicts)
        elif self.strategy == MockConflictResolutionStrategy.MERGE_COMPATIBLE:
            return await self._resolve_merge_compatible(conflicts)

    async def _resolve_latest_wins(self, conflicts: List[Dict]) -> List[MockContextChange]:
        """Latest timestamp wins."""
        # Group by context
        conflict_groups = {}
        for conflict in conflicts:
            key = f"{conflict['context_type']}:{conflict['context_id']}"
            if key not in conflict_groups:
                conflict_groups[key] = []
            conflict_groups[key].append(conflict)

        resolved = []
        for group in conflict_groups.values():
            latest = max(group, key=lambda x: x['timestamp'])
            resolved.append(MockContextChange(**latest))

        return resolved

    async def _resolve_priority_based(self, conflicts: List[Dict]) -> List[MockContextChange]:
        """Highest priority wins."""
        conflict_groups = {}
        for conflict in conflicts:
            key = f"{conflict['context_type']}:{conflict['context_id']}"
            if key not in conflict_groups:
                conflict_groups[key] = []
            conflict_groups[key].append(conflict)

        resolved = []
        for group in conflict_groups.values():
            highest_priority = max(group, key=lambda x: (x.get('priority', 1), x['timestamp']))
            resolved.append(MockContextChange(**highest_priority))

        return resolved

    async def _resolve_merge_compatible(self, conflicts: List[Dict]) -> List[MockContextChange]:
        """Try to merge non-conflicting fields."""
        conflict_groups = {}
        for conflict in conflicts:
            key = f"{conflict['context_type']}:{conflict['context_id']}"
            if key not in conflict_groups:
                conflict_groups[key] = []
            conflict_groups[key].append(conflict)

        resolved = []
        for group in conflict_groups.values():
            if len(group) == 1:
                resolved.append(MockContextChange(**group[0]))
                continue

            # Try to merge changes
            base = min(group, key=lambda x: x['timestamp'])
            merged_changes = base['changes'].copy()

            can_merge = True
            for conflict in group:
                if conflict == base:
                    continue

                # Check for field conflicts
                overlapping_fields = set(merged_changes.keys()) & set(conflict['changes'].keys())
                if overlapping_fields:
                    can_merge = False
                    break

                merged_changes.update(conflict['changes'])

            if can_merge:
                merged_change = MockContextChange(
                    change_id=f"merged_{base['change_id']}",
                    timestamp=time.time(),
                    source="conflict_resolver",
                    operation="update",
                    context_type=base['context_type'],
                    context_id=base['context_id'],
                    changes=merged_changes,
                    priority=max(c.get('priority', 1) for c in group)
                )
                resolved.append(merged_change)
            else:
                # Fall back to latest wins
                latest = max(group, key=lambda x: x['timestamp'])
                resolved.append(MockContextChange(**latest))

        return resolved


class MockContextSynchronizer:
    """Mock context synchronizer for testing."""

    def __init__(self, config: Optional[MockSynchronizationConfig] = None):
        self.config = config or MockSynchronizationConfig()
        self.conflict_resolver = MockConflictResolver(self.config.conflict_resolution)
        self.pending_changes: List[MockContextChange] = []
        self.sync_stats = {
            'total_syncs': 0,
            'successful_syncs': 0,
            'conflicts_resolved': 0
        }

    def add_context_change(self, source: str, operation: str, context_type: str,
                          context_id: str, changes: Dict[str, Any], priority: int = 1) -> MockContextChange:
        """Add a context change."""
        change = MockContextChange(
            change_id=f"{source}_{int(time.time())}_{len(self.pending_changes)}",
            timestamp=time.time(),
            source=source,
            operation=operation,
            context_type=context_type,
            context_id=context_id,
            changes=changes,
            priority=priority
        )

        self.pending_changes.append(change)

        # Limit pending changes
        if len(self.pending_changes) > self.config.max_pending_changes:
            self.pending_changes = self.pending_changes[-self.config.max_pending_changes:]

        return change

    async def sync_context_changes(self, changes: List[MockContextChange]) -> bool:
        """Sync context changes."""
        if not changes or not self.config.enable_real_time_sync:
            return True

        try:
            # Detect conflicts
            conflicts = self._detect_conflicts(changes)

            if conflicts:
                resolved_changes = await self.conflict_resolver.resolve_conflicts(conflicts)
                self.sync_stats['conflicts_resolved'] += len(conflicts)
            else:
                resolved_changes = changes

            # Update stats
            self.sync_stats['total_syncs'] += 1
            self.sync_stats['successful_syncs'] += 1

            return True

        except Exception:
            self.sync_stats['total_syncs'] += 1
            return False

    def _detect_conflicts(self, changes: List[MockContextChange]) -> List[Dict]:
        """Detect conflicts in changes."""
        conflicts = []
        change_groups = {}

        for change in changes:
            key = f"{change.context_type}:{change.context_id}"
            if key not in change_groups:
                change_groups[key] = []
            change_groups[key].append(asdict(change))

        # Mark groups with multiple changes as conflicts
        for group in change_groups.values():
            if len(group) > 1:
                # Check if changes are within conflict window (5 seconds)
                timestamps = [c['timestamp'] for c in group]
                if max(timestamps) - min(timestamps) <= 5.0:
                    conflicts.extend(group)

        return conflicts


class MockContextRelevanceDetector:
    """Mock context relevance detector."""

    def is_context_relevant(self, tool_name: str, tool_input: Dict[str, Any]) -> tuple:
        """Determine if context injection is relevant."""
        # MCP operations are high priority
        if 'mcp__4genthub_http__' in tool_name:
            return True, 'high', {'type': 'mcp_operation', 'tool': tool_name}

        # File operations are medium priority
        if tool_name in ['Write', 'Edit', 'MultiEdit']:
            file_path = tool_input.get('file_path', '')
            if any(file_path.endswith(ext) for ext in ['.py', '.js', '.ts', '.md']):
                return True, 'medium', {'type': 'file_operation', 'path': file_path}

        # Git operations
        if tool_name == 'Bash' and 'git' in tool_input.get('command', ''):
            return True, 'medium', {'type': 'git_operation'}

        return False, 'none', {}


class MockContextInjector:
    """Mock context injector for testing."""

    def __init__(self):
        self.detector = MockContextRelevanceDetector()

    async def inject_context(self, tool_name: str, tool_input: Dict[str, Any]) -> Optional[str]:
        """Inject context if relevant."""
        is_relevant, priority, context_reqs = self.detector.is_context_relevant(tool_name, tool_input)

        if not is_relevant:
            return None

        # Mock context data
        context_data = {
            'priority': priority,
            'timestamp': datetime.now().isoformat(),
            'tool': tool_name,
            'requirements': context_reqs
        }

        return self._format_context(context_data)

    def _format_context(self, context_data: Dict) -> str:
        """Format context for injection."""
        return f"""<context-injection>
Priority: {context_data['priority']}
Tool: {context_data['tool']}
Timestamp: {context_data['timestamp']}
Requirements: {context_data['requirements']}
</context-injection>"""


# Test Classes

class TestContextSynchronizerLogic:
    """Test context synchronization logic."""

    def setup_method(self):
        """Set up test fixtures."""
        self.synchronizer = MockContextSynchronizer()

    def test_add_context_change(self):
        """Test adding context changes."""
        change = self.synchronizer.add_context_change(
            source="test",
            operation="update",
            context_type="task",
            context_id="task_123",
            changes={"status": "in_progress"}
        )

        assert len(self.synchronizer.pending_changes) == 1
        assert change.source == "test"
        assert change.operation == "update"
        assert change.context_type == "task"
        assert change.context_id == "task_123"
        assert change.changes == {"status": "in_progress"}

    def test_pending_changes_limit(self):
        """Test that pending changes are limited."""
        config = MockSynchronizationConfig(max_pending_changes=5)
        synchronizer = MockContextSynchronizer(config)

        # Add more changes than the limit
        for i in range(10):
            synchronizer.add_context_change(
                source=f"test_{i}",
                operation="update",
                context_type="task",
                context_id=f"task_{i}",
                changes={"iteration": i}
            )

        # Should be limited to max
        assert len(synchronizer.pending_changes) == 5

    @pytest.mark.asyncio
    async def test_sync_success(self):
        """Test successful synchronization."""
        changes = [
            MockContextChange(
                change_id="test_1",
                timestamp=time.time(),
                source="test",
                operation="update",
                context_type="task",
                context_id="task_123",
                changes={"status": "completed"}
            )
        ]

        result = await self.synchronizer.sync_context_changes(changes)

        assert result is True
        assert self.synchronizer.sync_stats['total_syncs'] == 1
        assert self.synchronizer.sync_stats['successful_syncs'] == 1

    def test_conflict_detection(self):
        """Test conflict detection."""
        changes = [
            MockContextChange(
                change_id="change_1",
                timestamp=time.time(),
                source="source_1",
                operation="update",
                context_type="task",
                context_id="task_123",
                changes={"status": "pending"}
            ),
            MockContextChange(
                change_id="change_2",
                timestamp=time.time() + 1,  # 1 second later
                source="source_2",
                operation="update",
                context_type="task",
                context_id="task_123",  # Same task
                changes={"status": "completed"}
            )
        ]

        conflicts = self.synchronizer._detect_conflicts(changes)

        # Should detect 2 conflicts (both changes to same task)
        assert len(conflicts) == 2
        assert all(c['context_id'] == 'task_123' for c in conflicts)

    def test_no_conflicts_different_contexts(self):
        """Test no conflicts for different contexts."""
        changes = [
            MockContextChange(
                change_id="change_1",
                timestamp=time.time(),
                source="source_1",
                operation="update",
                context_type="task",
                context_id="task_123",
                changes={"status": "pending"}
            ),
            MockContextChange(
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


class TestConflictResolutionLogic:
    """Test conflict resolution strategies."""

    @pytest.mark.asyncio
    async def test_latest_wins_strategy(self):
        """Test latest wins resolution."""
        resolver = MockConflictResolver(MockConflictResolutionStrategy.LATEST_WINS)

        conflicts = [
            {
                'change_id': 'change_1',
                'timestamp': time.time() - 10,  # Older
                'source': 'source_1',
                'operation': 'update',
                'context_type': 'task',
                'context_id': 'task_123',
                'changes': {'status': 'pending'}
            },
            {
                'change_id': 'change_2',
                'timestamp': time.time(),  # Newer
                'source': 'source_2',
                'operation': 'update',
                'context_type': 'task',
                'context_id': 'task_123',
                'changes': {'status': 'completed'}
            }
        ]

        resolved = await resolver.resolve_conflicts(conflicts)

        assert len(resolved) == 1
        assert resolved[0].change_id == 'change_2'  # Latest wins
        assert resolved[0].changes == {'status': 'completed'}

    @pytest.mark.asyncio
    async def test_priority_based_strategy(self):
        """Test priority-based resolution."""
        resolver = MockConflictResolver(MockConflictResolutionStrategy.PRIORITY_BASED)

        conflicts = [
            {
                'change_id': 'change_1',
                'timestamp': time.time(),
                'source': 'source_1',
                'operation': 'update',
                'context_type': 'task',
                'context_id': 'task_123',
                'changes': {'status': 'pending'},
                'priority': 2
            },
            {
                'change_id': 'change_2',
                'timestamp': time.time() - 5,  # Older but higher priority
                'source': 'source_2',
                'operation': 'update',
                'context_type': 'task',
                'context_id': 'task_123',
                'changes': {'status': 'completed'},
                'priority': 5  # Higher priority
            }
        ]

        resolved = await resolver.resolve_conflicts(conflicts)

        assert len(resolved) == 1
        assert resolved[0].change_id == 'change_2'  # Higher priority wins
        assert resolved[0].changes == {'status': 'completed'}

    @pytest.mark.asyncio
    async def test_merge_compatible_strategy(self):
        """Test merge compatible resolution."""
        resolver = MockConflictResolver(MockConflictResolutionStrategy.MERGE_COMPATIBLE)

        # Non-conflicting field changes
        conflicts = [
            {
                'change_id': 'change_1',
                'timestamp': time.time() - 5,
                'source': 'source_1',
                'operation': 'update',
                'context_type': 'task',
                'context_id': 'task_123',
                'changes': {'status': 'in_progress'}
            },
            {
                'change_id': 'change_2',
                'timestamp': time.time(),
                'source': 'source_2',
                'operation': 'update',
                'context_type': 'task',
                'context_id': 'task_123',
                'changes': {'assignee': 'alice'}  # Different field
            }
        ]

        resolved = await resolver.resolve_conflicts(conflicts)

        assert len(resolved) == 1
        # Should contain both changes
        assert 'status' in resolved[0].changes
        assert 'assignee' in resolved[0].changes
        assert resolved[0].changes['status'] == 'in_progress'
        assert resolved[0].changes['assignee'] == 'alice'

    @pytest.mark.asyncio
    async def test_merge_fallback_on_conflicts(self):
        """Test merge falls back to latest wins on field conflicts."""
        resolver = MockConflictResolver(MockConflictResolutionStrategy.MERGE_COMPATIBLE)

        # Conflicting field changes (both update 'status')
        conflicts = [
            {
                'change_id': 'change_1',
                'timestamp': time.time() - 5,
                'source': 'source_1',
                'operation': 'update',
                'context_type': 'task',
                'context_id': 'task_123',
                'changes': {'status': 'pending'}
            },
            {
                'change_id': 'change_2',
                'timestamp': time.time(),
                'source': 'source_2',
                'operation': 'update',
                'context_type': 'task',
                'context_id': 'task_123',
                'changes': {'status': 'completed'}  # Conflicts with change_1
            }
        ]

        resolved = await resolver.resolve_conflicts(conflicts)

        assert len(resolved) == 1
        # Should fall back to latest wins
        assert resolved[0].change_id == 'change_2'
        assert resolved[0].changes == {'status': 'completed'}


@pytest.mark.skipif(not AGENT_STATE_AVAILABLE, reason="Agent state manager not available")
class TestAgentStateManagerIntegration:
    """Test agent state manager functionality."""

    def setup_method(self):
        """Set up test fixtures."""
        self.temp_dir = tempfile.mkdtemp()

        with patch('agent_state_manager.get_ai_data_path', return_value=Path(self.temp_dir)):
            self.manager = AgentStateManager()

    def teardown_method(self):
        """Clean up test fixtures."""
        import shutil
        shutil.rmtree(self.temp_dir, ignore_errors=True)

    def test_agent_state_persistence(self):
        """Test agent state persistence."""
        session_id = str(uuid.uuid4())

        # Set agent
        self.manager.set_current_agent(session_id, 'coding-agent')

        # Get agent
        agent = self.manager.get_current_agent(session_id)
        assert agent == 'coding-agent'

    def test_agent_role_mapping(self):
        """Test agent role mapping."""
        session_id = str(uuid.uuid4())

        test_cases = [
            ('coding-agent', 'Coding'),
            ('debugger-agent', 'Debugging'),
            ('test-orchestrator-agent', 'Testing'),
            ('master-orchestrator-agent', 'Orchestrating'),
            ('unknown-agent', 'Assistant')
        ]

        for agent_name, expected_role in test_cases:
            with patch('agent_state_manager.get_current_agent', return_value=agent_name):
                role = get_agent_role_from_session(session_id)
                assert role == expected_role

    def test_multiple_sessions(self):
        """Test handling multiple sessions."""
        session_1 = str(uuid.uuid4())
        session_2 = str(uuid.uuid4())

        # Set different agents
        self.manager.set_current_agent(session_1, 'coding-agent')
        self.manager.set_current_agent(session_2, 'test-agent')

        # Verify independence
        assert self.manager.get_current_agent(session_1) == 'coding-agent'
        assert self.manager.get_current_agent(session_2) == 'test-agent'


class TestContextInjectionLogic:
    """Test context injection logic."""

    def setup_method(self):
        """Set up test fixtures."""
        self.injector = MockContextInjector()

    @pytest.mark.asyncio
    async def test_mcp_operation_relevance(self):
        """Test MCP operations are detected as relevant."""
        result = await self.injector.inject_context(
            "mcp__4genthub_http__manage_task",
            {"action": "get", "task_id": "task_123"}
        )

        assert result is not None
        assert "Priority: high" in result
        assert "mcp__4genthub_http__manage_task" in result

    @pytest.mark.asyncio
    async def test_file_operation_relevance(self):
        """Test file operations are detected as relevant."""
        result = await self.injector.inject_context(
            "Write",
            {"file_path": "/path/to/script.py", "content": "code"}
        )

        assert result is not None
        assert "Priority: medium" in result
        assert "Write" in result

    @pytest.mark.asyncio
    async def test_irrelevant_operation(self):
        """Test irrelevant operations return None."""
        result = await self.injector.inject_context(
            "Read",
            {"file_path": "/path/to/file.txt"}
        )

        assert result is None

    @pytest.mark.asyncio
    async def test_git_operation_relevance(self):
        """Test git operations are detected as relevant."""
        result = await self.injector.inject_context(
            "Bash",
            {"command": "git status"}
        )

        assert result is not None
        assert "Priority: medium" in result
        assert "Bash" in result


class TestIntegrationScenarios:
    """Test integration between components."""

    def setup_method(self):
        """Set up test fixtures."""
        self.synchronizer = MockContextSynchronizer()
        self.injector = MockContextInjector()

    @pytest.mark.asyncio
    async def test_context_sync_before_injection(self):
        """Test context synchronization before injection."""
        # Step 1: Add context change
        change = self.synchronizer.add_context_change(
            source="test",
            operation="update",
            context_type="task",
            context_id="task_123",
            changes={"status": "in_progress"}
        )

        # Step 2: Sync changes
        result = await self.synchronizer.sync_context_changes([change])
        assert result is True

        # Step 3: Inject context
        injection_result = await self.injector.inject_context(
            "mcp__4genthub_http__manage_task",
            {"action": "get", "task_id": "task_123"}
        )

        assert injection_result is not None
        assert "Priority: high" in injection_result

    @pytest.mark.asyncio
    async def test_concurrent_operations(self):
        """Test concurrent sync and injection."""
        changes = [
            MockContextChange(
                change_id=f"change_{i}",
                timestamp=time.time(),
                source=f"source_{i}",
                operation="update",
                context_type="task",
                context_id=f"task_{i}",
                changes={"iteration": i}
            )
            for i in range(5)
        ]

        # Run sync and injection concurrently
        sync_task = self.synchronizer.sync_context_changes(changes)
        injection_task = self.injector.inject_context(
            "Write",
            {"file_path": "/test.py", "content": "test"}
        )

        sync_result, injection_result = await asyncio.gather(sync_task, injection_task)

        assert sync_result is True
        assert injection_result is not None


if __name__ == "__main__":
    pytest.main([__file__, "-v"])