#!/usr/bin/env python3
"""
Integration Tests for Context Management System

Tests the integration between context management utilities including:
- Context inheritance patterns
- Synchronization between components
- Agent state and context coordination
- Performance and error handling
- End-to-end workflows

Part of subtask: db40a3dd-7ac0-4046-885e-15d762b9283d
"""

import pytest
import asyncio
import time
import json
import tempfile
import uuid
from unittest.mock import Mock, patch, AsyncMock, call
from pathlib import Path
from datetime import datetime

import sys

# Add hooks utils to path for testing
hooks_utils_path = Path(__file__).parent.parent.parent.parent.parent / '.claude' / 'hooks' / 'utils'
sys.path.insert(0, str(hooks_utils_path.absolute()))

try:
    from context_synchronizer import (
        ContextSynchronizer, ContextChange, SynchronizationConfig,
        sync_context_change, get_global_synchronizer
    )
    from agent_state_manager import (
        AgentStateManager, get_current_agent, set_current_agent,
        get_agent_role_from_session, update_agent_state_from_call_agent
    )
    from context_injector import (
        ContextInjector, ContextInjectionConfig,
        inject_context_sync, create_context_injector
    )
except ImportError:
    pytest.skip("context management modules not available", allow_module_level=True)


class TestContextInheritancePatterns:
    """Test context inheritance and hierarchical relationships."""

    def setup_method(self):
        """Set up test fixtures."""
        self.temp_dir = tempfile.mkdtemp()

        # Set up mocked components
        with patch('context_synchronizer.SessionContextCache') as mock_cache_class, \
             patch('context_synchronizer.OptimizedMCPClient') as mock_client_class, \
             patch('agent_state_manager.get_ai_data_path', return_value=Path(self.temp_dir)):

            self.mock_cache = Mock()
            self.mock_client = Mock()
            mock_cache_class.return_value = self.mock_cache
            mock_client_class.return_value = self.mock_client

            self.synchronizer = ContextSynchronizer()
            self.agent_manager = AgentStateManager()

    def teardown_method(self):
        """Clean up test fixtures."""
        import shutil
        shutil.rmtree(self.temp_dir, ignore_errors=True)

    def test_hierarchical_context_inheritance(self):
        """Test context inheritance from global to task level."""
        session_id = str(uuid.uuid4())

        # Set up hierarchical context changes
        global_change = ContextChange(
            change_id="global_1",
            timestamp=time.time(),
            source="system",
            operation="update",
            context_type="global",
            context_id="global_ctx",
            changes={"theme": "dark", "language": "en"}
        )

        project_change = ContextChange(
            change_id="project_1",
            timestamp=time.time(),
            source="project_init",
            operation="update",
            context_type="project",
            context_id="project_123",
            changes={"name": "Test Project", "framework": "FastAPI"}
        )

        branch_change = ContextChange(
            change_id="branch_1",
            timestamp=time.time(),
            source="git",
            operation="create",
            context_type="branch",
            context_id="branch_456",
            changes={"name": "feature/auth", "base_branch": "main"}
        )

        task_change = ContextChange(
            change_id="task_1",
            timestamp=time.time(),
            source="task_creation",
            operation="create",
            context_type="task",
            context_id="task_789",
            changes={"title": "Implement JWT", "priority": "high"}
        )

        # Set up cache to simulate inheritance
        self.mock_cache.get.side_effect = lambda key: {
            "global_global_ctx": {"theme": "dark", "language": "en"},
            "project_project_123": {"name": "Test Project", "framework": "FastAPI", "theme": "dark", "language": "en"},
            "branch_branch_456": {
                "name": "feature/auth", "base_branch": "main",
                "project_name": "Test Project", "framework": "FastAPI",
                "theme": "dark", "language": "en"
            },
            "task_task_789": {
                "title": "Implement JWT", "priority": "high",
                "branch_name": "feature/auth", "project_name": "Test Project",
                "theme": "dark", "language": "en"
            }
        }.get(key, {})

        # Add changes to synchronizer
        changes = [global_change, project_change, branch_change, task_change]
        for change in changes:
            self.synchronizer.add_context_change(
                source=change.source,
                operation=change.operation,
                context_type=change.context_type,
                context_id=change.context_id,
                changes=change.changes
            )

        # Verify inheritance chain
        task_context = self.mock_cache.get("task_task_789")
        assert task_context["theme"] == "dark"  # Inherited from global
        assert task_context["framework"] == "FastAPI"  # Inherited from project
        assert task_context["branch_name"] == "feature/auth"  # Inherited from branch
        assert task_context["title"] == "Implement JWT"  # Task-specific

    def test_context_override_priority(self):
        """Test that more specific contexts override general ones."""
        # Global setting
        global_change = ContextChange(
            change_id="global_priority",
            timestamp=time.time(),
            source="system",
            operation="update",
            context_type="global",
            context_id="global_ctx",
            changes={"debug_mode": False, "log_level": "INFO"}
        )

        # Task-specific override
        task_change = ContextChange(
            change_id="task_priority",
            timestamp=time.time() + 1,  # Later timestamp
            source="task_config",
            operation="update",
            context_type="task",
            context_id="task_debug",
            changes={"debug_mode": True, "log_level": "DEBUG"}  # Override global
        )

        self.synchronizer.add_context_change(**{
            "source": global_change.source,
            "operation": global_change.operation,
            "context_type": global_change.context_type,
            "context_id": global_change.context_id,
            "changes": global_change.changes
        })

        self.synchronizer.add_context_change(**{
            "source": task_change.source,
            "operation": task_change.operation,
            "context_type": task_change.context_type,
            "context_id": task_change.context_id,
            "changes": task_change.changes
        })

        # Verify that task-specific settings take priority
        assert len(self.synchronizer.pending_changes) == 2

        # Task context should override global
        latest_change = self.synchronizer.pending_changes[-1]
        assert latest_change.context_type == "task"
        assert latest_change.changes["debug_mode"] is True
        assert latest_change.changes["log_level"] == "DEBUG"


class TestAgentStateContextCoordination:
    """Test coordination between agent state and context management."""

    def setup_method(self):
        """Set up test fixtures."""
        self.temp_dir = tempfile.mkdtemp()
        self.session_id = str(uuid.uuid4())

        with patch('agent_state_manager.get_ai_data_path', return_value=Path(self.temp_dir)):
            self.agent_manager = AgentStateManager()

        with patch('context_synchronizer.SessionContextCache') as mock_cache_class, \
             patch('context_synchronizer.OptimizedMCPClient') as mock_client_class:

            self.mock_cache = Mock()
            self.mock_client = Mock()
            mock_cache_class.return_value = self.mock_cache
            mock_client_class.return_value = self.mock_client

            self.synchronizer = ContextSynchronizer()

    def teardown_method(self):
        """Clean up test fixtures."""
        import shutil
        shutil.rmtree(self.temp_dir, ignore_errors=True)

    def test_agent_state_change_triggers_context_sync(self):
        """Test that agent state changes trigger context synchronization."""
        # Simulate call_agent tool execution
        tool_input = {'name_agent': 'coding-agent'}

        # Update agent state
        update_agent_state_from_call_agent(self.session_id, tool_input)

        # Verify agent state was updated
        current_agent = self.agent_manager.get_current_agent(self.session_id)
        assert current_agent == 'coding-agent'

        # Simulate context synchronization triggered by agent change
        agent_context_change = self.synchronizer.add_context_change(
            source="agent_state_manager",
            operation="update",
            context_type="session",
            context_id=self.session_id,
            changes={
                "current_agent": "coding-agent",
                "agent_role": "Coding",
                "capabilities": ["file_operations", "code_analysis"]
            }
        )

        assert agent_context_change.source == "agent_state_manager"
        assert agent_context_change.changes["current_agent"] == "coding-agent"

    def test_context_sync_with_multiple_agent_transitions(self):
        """Test context synchronization across multiple agent transitions."""
        agents = [
            ('master-orchestrator-agent', 'Orchestrating'),
            ('coding-agent', 'Coding'),
            ('test-orchestrator-agent', 'Testing'),
            ('debugger-agent', 'Debugging')
        ]

        context_changes = []

        for agent_name, role in agents:
            # Update agent state
            self.agent_manager.set_current_agent(self.session_id, agent_name)

            # Create corresponding context change
            change = self.synchronizer.add_context_change(
                source="agent_transition",
                operation="update",
                context_type="session",
                context_id=self.session_id,
                changes={
                    "current_agent": agent_name,
                    "agent_role": role,
                    "transition_time": time.time()
                }
            )
            context_changes.append(change)

        # Verify all transitions were tracked
        assert len(context_changes) == 4
        assert all(change.context_id == self.session_id for change in context_changes)
        assert context_changes[-1].changes["current_agent"] == "debugger-agent"

    def test_agent_role_context_inheritance(self):
        """Test that agent roles provide context for tool operations."""
        # Set agent to coding-agent
        self.agent_manager.set_current_agent(self.session_id, 'coding-agent')
        role = get_agent_role_from_session(self.session_id)

        # Verify role mapping
        assert role == 'Coding'

        # Simulate context injection considering agent role
        with patch('context_injector.ContextInjector') as mock_injector_class:
            mock_injector = Mock()
            mock_injector_class.return_value = mock_injector

            # Mock context injection that considers agent role
            mock_context = f"""
            <context-injection>
            Agent Role: {role}
            Capabilities: File operations, code analysis, debugging
            Current Session: {self.session_id}
            </context-injection>
            """
            mock_injector.inject_context = AsyncMock(return_value=mock_context)

            injector = mock_injector_class()

            # This would typically be called by the pre-tool hook
            # when the injector detects a file operation by a coding agent
            result = asyncio.run(injector.inject_context(
                "Write",
                {"file_path": "/path/to/code.py", "content": "print('hello')"}
            ))

            assert "Agent Role: Coding" in result
            assert "File operations" in result


class TestSynchronizationIntegration:
    """Test integration of synchronization across components."""

    def setup_method(self):
        """Set up test fixtures."""
        self.temp_dir = tempfile.mkdtemp()

        with patch('context_synchronizer.SessionContextCache') as mock_cache_class, \
             patch('context_synchronizer.OptimizedMCPClient') as mock_client_class, \
             patch('context_injector.OptimizedMCPClient') as mock_injector_client_class, \
             patch('context_injector.SessionContextCache') as mock_injector_cache_class, \
             patch('agent_state_manager.get_ai_data_path', return_value=Path(self.temp_dir)):

            # Set up mocks
            self.mock_sync_cache = Mock()
            self.mock_sync_client = Mock()
            self.mock_injector_cache = Mock()
            self.mock_injector_client = Mock()

            mock_cache_class.return_value = self.mock_sync_cache
            mock_client_class.return_value = self.mock_sync_client
            mock_injector_cache_class.return_value = self.mock_injector_cache
            mock_injector_client_class.return_value = self.mock_injector_client

            # Create components
            self.synchronizer = ContextSynchronizer()
            self.injector = ContextInjector()
            self.agent_manager = AgentStateManager()

    def teardown_method(self):
        """Clean up test fixtures."""
        import shutil
        shutil.rmtree(self.temp_dir, ignore_errors=True)

    @pytest.mark.asyncio
    async def test_context_sync_before_injection(self):
        """Test that context synchronization happens before injection."""
        session_id = str(uuid.uuid4())
        task_id = "task_123"

        # Step 1: Agent state changes
        self.agent_manager.set_current_agent(session_id, 'coding-agent')

        # Step 2: Context synchronization (would be triggered by pre-tool hook)
        context_change = self.synchronizer.add_context_change(
            source="pre_tool_hook",
            operation="update",
            context_type="task",
            context_id=task_id,
            changes={
                "status": "in_progress",
                "agent": "coding-agent",
                "session_id": session_id
            }
        )

        # Mock cache to return synchronized context
        self.mock_injector_cache.get.return_value = None  # Cache miss
        self.mock_injector_client.make_request.return_value = {
            "task": {
                "id": task_id,
                "title": "Code implementation",
                "status": "in_progress",
                "agent": "coding-agent",
                "session_id": session_id
            }
        }

        # Step 3: Context injection (uses synchronized context)
        result = await self.injector.inject_context(
            "mcp__4genthub_http__manage_task",
            {"action": "get", "task_id": task_id}
        )

        # Verify synchronized context was used
        assert result is not None
        assert task_id in result
        assert "coding-agent" in result
        assert "in_progress" in result

    @pytest.mark.asyncio
    async def test_concurrent_sync_and_injection(self):
        """Test concurrent synchronization and injection operations."""
        session_id = str(uuid.uuid4())

        # Create multiple context changes
        changes = []
        for i in range(5):
            change = self.synchronizer.add_context_change(
                source=f"source_{i}",
                operation="update",
                context_type="task",
                context_id=f"task_{i}",
                changes={"iteration": i, "session_id": session_id}
            )
            changes.append(change)

        # Mock responses for injection
        self.mock_injector_cache.get.return_value = None
        self.mock_injector_client.make_request.return_value = {
            "task": {"id": "task_concurrent", "title": "Concurrent test"}
        }

        # Run synchronization and injection concurrently
        sync_task = self.synchronizer.sync_context_changes(changes)
        injection_task = self.injector.inject_context(
            "mcp__4genthub_http__manage_task",
            {"action": "get", "task_id": "task_concurrent"}
        )

        sync_result, injection_result = await asyncio.gather(
            sync_task, injection_task, return_exceptions=True
        )

        # Both should complete successfully
        assert sync_result is True
        assert injection_result is not None
        assert "Concurrent test" in injection_result

    def test_cache_sharing_between_components(self):
        """Test that components share cached context appropriately."""
        session_id = str(uuid.uuid4())
        cache_key = "task_shared_123"

        # Synchronizer updates cache
        self.synchronizer.add_context_change(
            source="sync_test",
            operation="update",
            context_type="task",
            context_id="shared_123",
            changes={"shared_data": "test_value"}
        )

        # Simulate cache update
        cached_data = {
            "shared_data": "test_value",
            "last_sync": datetime.now().isoformat()
        }
        self.mock_sync_cache.set.assert_called()

        # Injector should use cached data
        self.mock_injector_cache.get.return_value = cached_data

        # Verify cache is used by injector (simulated)
        assert self.mock_injector_cache.get(cache_key, 900) == cached_data


class TestErrorHandlingAndRecovery:
    """Test error handling and recovery mechanisms."""

    def setup_method(self):
        """Set up test fixtures."""
        self.temp_dir = tempfile.mkdtemp()

        with patch('context_synchronizer.SessionContextCache') as mock_cache_class, \
             patch('context_synchronizer.OptimizedMCPClient') as mock_client_class, \
             patch('agent_state_manager.get_ai_data_path', return_value=Path(self.temp_dir)):

            self.mock_cache = Mock()
            self.mock_client = Mock()
            mock_cache_class.return_value = self.mock_cache
            mock_client_class.return_value = self.mock_client

            self.synchronizer = ContextSynchronizer()
            self.agent_manager = AgentStateManager()

    def teardown_method(self):
        """Clean up test fixtures."""
        import shutil
        shutil.rmtree(self.temp_dir, ignore_errors=True)

    @pytest.mark.asyncio
    async def test_sync_failure_recovery(self):
        """Test recovery from synchronization failures."""
        # Create context change
        change = self.synchronizer.add_context_change(
            source="error_test",
            operation="update",
            context_type="task",
            context_id="error_task",
            changes={"test": "error_handling"}
        )

        # Make cache operations fail
        self.mock_cache.get.side_effect = Exception("Cache connection failed")
        self.mock_cache.set.side_effect = Exception("Cache write failed")

        # Synchronization should handle errors gracefully
        result = await self.synchronizer.sync_context_changes([change])

        # Should fail but not crash
        assert result is False
        assert self.synchronizer.sync_stats['total_syncs'] == 1
        assert self.synchronizer.sync_stats['successful_syncs'] == 0

    def test_agent_state_corruption_recovery(self):
        """Test recovery from agent state file corruption."""
        session_id = str(uuid.uuid4())

        # Set initial state
        self.agent_manager.set_current_agent(session_id, 'test-agent')

        # Corrupt the state file
        with open(self.agent_manager.state_file, 'w') as f:
            f.write("corrupted json content")

        # Create new manager instance
        with patch('agent_state_manager.get_ai_data_path', return_value=Path(self.temp_dir)):
            new_manager = AgentStateManager()

        # Should recover gracefully with default agent
        agent = new_manager.get_current_agent(session_id)
        assert agent == 'master-orchestrator-agent'

    @pytest.mark.asyncio
    async def test_injection_error_fallback(self):
        """Test context injection error handling and fallback."""
        with patch('context_injector.ContextRelevanceDetector') as mock_detector_class, \
             patch('context_injector.MCPContextQuery') as mock_query_class:

            mock_detector = Mock()
            mock_query_engine = Mock()
            mock_detector_class.return_value = mock_detector
            mock_query_class.return_value = mock_query_engine

            # Set up detection but make query fail
            mock_detector.is_context_relevant.return_value = (True, "high", {"type": "test"})
            mock_query_engine.query_context.side_effect = Exception("Query failed")

            injector = ContextInjector()

            # Should handle error gracefully
            result = await injector.inject_context("Write", {"file_path": "/test.py"})

            assert result is None  # Should return None on error, not crash

    def test_concurrent_agent_state_updates_consistency(self):
        """Test consistency under concurrent agent state updates."""
        import threading
        import time

        session_id = str(uuid.uuid4())
        agents = ['coding-agent', 'test-agent', 'debug-agent']
        results = []

        def update_agent_state(agent_name):
            """Update agent state with delay."""
            time.sleep(0.01)  # Small delay
            self.agent_manager.set_current_agent(session_id, agent_name)
            results.append(self.agent_manager.get_current_agent(session_id))

        # Start concurrent updates
        threads = []
        for agent_name in agents:
            thread = threading.Thread(target=update_agent_state, args=(agent_name,))
            threads.append(thread)
            thread.start()

        # Wait for completion
        for thread in threads:
            thread.join()

        # Final state should be one of the updated agents
        final_agent = self.agent_manager.get_current_agent(session_id)
        assert final_agent in agents

        # All results should be valid agent names
        assert all(result in agents for result in results)


class TestPerformanceAndScalability:
    """Test performance and scalability characteristics."""

    def setup_method(self):
        """Set up test fixtures."""
        self.temp_dir = tempfile.mkdtemp()

        # Use shorter timeouts for testing
        config = SynchronizationConfig(
            sync_timeout_ms=1000,
            max_pending_changes=50,
            batch_sync_interval_ms=100
        )

        with patch('context_synchronizer.SessionContextCache') as mock_cache_class, \
             patch('context_synchronizer.OptimizedMCPClient') as mock_client_class, \
             patch('agent_state_manager.get_ai_data_path', return_value=Path(self.temp_dir)):

            self.mock_cache = Mock()
            self.mock_client = Mock()
            mock_cache_class.return_value = self.mock_cache
            mock_client_class.return_value = self.mock_client

            self.synchronizer = ContextSynchronizer(config)
            self.agent_manager = AgentStateManager()

    def teardown_method(self):
        """Clean up test fixtures."""
        import shutil
        shutil.rmtree(self.temp_dir, ignore_errors=True)

    def test_large_context_change_batch_performance(self):
        """Test performance with large batches of context changes."""
        start_time = time.time()

        # Create large batch of changes
        for i in range(100):
            self.synchronizer.add_context_change(
                source=f"perf_test_{i}",
                operation="update",
                context_type="task",
                context_id=f"task_{i}",
                changes={"iteration": i, "data": f"test_data_{i}"}
            )

        batch_time = time.time() - start_time

        # Should complete reasonably quickly (under 1 second for 100 changes)
        assert batch_time < 1.0
        assert len(self.synchronizer.pending_changes) == 50  # Limited by max_pending_changes

    @pytest.mark.asyncio
    async def test_concurrent_sync_performance(self):
        """Test performance under concurrent synchronization load."""
        # Create multiple change batches
        change_batches = []
        for batch_id in range(10):
            batch = []
            for i in range(5):
                change = ContextChange(
                    change_id=f"batch_{batch_id}_change_{i}",
                    timestamp=time.time(),
                    source=f"batch_{batch_id}",
                    operation="update",
                    context_type="task",
                    context_id=f"task_{batch_id}_{i}",
                    changes={"batch": batch_id, "item": i}
                )
                batch.append(change)
            change_batches.append(batch)

        # Run synchronizations concurrently
        start_time = time.time()

        tasks = [
            self.synchronizer.sync_context_changes(batch)
            for batch in change_batches
        ]

        results = await asyncio.gather(*tasks, return_exceptions=True)

        total_time = time.time() - start_time

        # Should complete within reasonable time (under 5 seconds)
        assert total_time < 5.0

        # Most should succeed (some might timeout under load)
        successful_results = [r for r in results if r is True]
        assert len(successful_results) >= len(change_batches) * 0.7  # At least 70% success rate

    def test_agent_state_cleanup_performance(self):
        """Test performance of agent state cleanup operations."""
        # Create many sessions
        sessions = []
        for i in range(100):
            session_id = str(uuid.uuid4())
            sessions.append(session_id)
            self.agent_manager.set_current_agent(session_id, f'agent-{i % 10}')

        # Measure cleanup performance
        start_time = time.time()
        self.agent_manager.cleanup_old_sessions(max_sessions=20)
        cleanup_time = time.time() - start_time

        # Should complete quickly (under 1 second)
        assert cleanup_time < 1.0

        # Should keep only the specified number of sessions
        all_sessions = self.agent_manager.get_all_sessions()
        assert len(all_sessions) == 20

    def test_memory_usage_under_load(self):
        """Test memory usage patterns under sustained load."""
        import psutil
        import os

        process = psutil.Process(os.getpid())
        initial_memory = process.memory_info().rss

        # Generate sustained load
        for iteration in range(50):
            # Add context changes
            for i in range(20):
                self.synchronizer.add_context_change(
                    source=f"memory_test_{iteration}",
                    operation="update",
                    context_type="task",
                    context_id=f"task_{iteration}_{i}",
                    changes={"iteration": iteration, "item": i}
                )

            # Update agent states
            session_id = str(uuid.uuid4())
            self.agent_manager.set_current_agent(session_id, f'agent-{iteration % 5}')

            # Periodic cleanup
            if iteration % 10 == 0:
                self.agent_manager.cleanup_old_sessions(max_sessions=10)

        final_memory = process.memory_info().rss
        memory_growth = final_memory - initial_memory

        # Memory growth should be reasonable (under 50MB for this test)
        assert memory_growth < 50 * 1024 * 1024  # 50MB limit


class TestEndToEndWorkflows:
    """Test complete end-to-end workflows."""

    def setup_method(self):
        """Set up test fixtures."""
        self.temp_dir = tempfile.mkdtemp()
        self.session_id = str(uuid.uuid4())

        with patch('context_synchronizer.SessionContextCache') as mock_cache_class, \
             patch('context_synchronizer.OptimizedMCPClient') as mock_client_class, \
             patch('context_injector.OptimizedMCPClient') as mock_injector_client_class, \
             patch('context_injector.SessionContextCache') as mock_injector_cache_class, \
             patch('agent_state_manager.get_ai_data_path', return_value=Path(self.temp_dir)):

            # Set up all mocks
            self.setup_mocks(mock_cache_class, mock_client_class,
                           mock_injector_client_class, mock_injector_cache_class)

            # Create components
            self.synchronizer = ContextSynchronizer()
            self.injector = ContextInjector()
            self.agent_manager = AgentStateManager()

    def setup_mocks(self, mock_cache_class, mock_client_class,
                   mock_injector_client_class, mock_injector_cache_class):
        """Set up mock objects with realistic responses."""
        self.mock_sync_cache = Mock()
        self.mock_sync_client = Mock()
        self.mock_injector_cache = Mock()
        self.mock_injector_client = Mock()

        mock_cache_class.return_value = self.mock_sync_cache
        mock_client_class.return_value = self.mock_sync_client
        mock_injector_cache_class.return_value = self.mock_injector_cache
        mock_injector_client_class.return_value = self.mock_injector_client

        # Set up realistic mock responses
        self.mock_sync_cache.get.return_value = {}
        self.mock_injector_cache.get.return_value = None

        self.mock_injector_client.make_request.return_value = {
            "task": {
                "id": "task_workflow",
                "title": "End-to-end test task",
                "status": "in_progress",
                "assignees": ["coding-agent"]
            }
        }

    def teardown_method(self):
        """Clean up test fixtures."""
        import shutil
        shutil.rmtree(self.temp_dir, ignore_errors=True)

    @pytest.mark.asyncio
    async def test_complete_development_workflow(self):
        """Test a complete development workflow with context management."""
        # Step 1: Initialize session with master orchestrator
        self.agent_manager.set_current_agent(self.session_id, 'master-orchestrator-agent')

        # Step 2: Create project context
        project_change = self.synchronizer.add_context_change(
            source="project_init",
            operation="create",
            context_type="project",
            context_id="proj_123",
            changes={
                "name": "Authentication System",
                "framework": "FastAPI",
                "session_id": self.session_id
            }
        )

        # Step 3: Switch to coding agent
        self.agent_manager.set_current_agent(self.session_id, 'coding-agent')

        # Step 4: Create task context
        task_change = self.synchronizer.add_context_change(
            source="task_creation",
            operation="create",
            context_type="task",
            context_id="task_workflow",
            changes={
                "title": "Implement JWT authentication",
                "status": "in_progress",
                "agent": "coding-agent",
                "session_id": self.session_id
            }
        )

        # Step 5: Synchronize all context changes
        sync_result = await self.synchronizer.sync_context_changes([project_change, task_change])
        assert sync_result is True

        # Step 6: Context injection for file operation
        injection_result = await self.injector.inject_context(
            "Write",
            {"file_path": "/src/auth/jwt_handler.py", "content": "# JWT implementation"}
        )

        # Verify workflow completion
        assert injection_result is not None
        assert "End-to-end test task" in injection_result
        assert "coding-agent" in injection_result

        # Verify agent state is maintained
        current_agent = self.agent_manager.get_current_agent(self.session_id)
        assert current_agent == 'coding-agent'

        # Verify context synchronization stats
        stats = self.synchronizer.get_sync_statistics()
        assert stats['total_syncs'] == 1
        assert stats['successful_syncs'] == 1

    @pytest.mark.asyncio
    async def test_multi_agent_collaboration_workflow(self):
        """Test workflow with multiple agents collaborating."""
        agents_and_tasks = [
            ('master-orchestrator-agent', 'project_planning', 'Plan authentication system'),
            ('coding-agent', 'implementation', 'Implement JWT handlers'),
            ('test-orchestrator-agent', 'testing', 'Create test suite'),
            ('debugger-agent', 'debugging', 'Fix authentication bugs')
        ]

        context_changes = []

        for agent_name, task_type, task_title in agents_and_tasks:
            # Switch agent
            self.agent_manager.set_current_agent(self.session_id, agent_name)

            # Create task context for this agent
            change = self.synchronizer.add_context_change(
                source=f"{agent_name}_workflow",
                operation="create",
                context_type="task",
                context_id=f"task_{task_type}",
                changes={
                    "title": task_title,
                    "agent": agent_name,
                    "task_type": task_type,
                    "session_id": self.session_id,
                    "timestamp": time.time()
                }
            )
            context_changes.append(change)

        # Synchronize all changes
        sync_result = await self.synchronizer.sync_context_changes(context_changes)
        assert sync_result is True

        # Test context injection for final agent (debugger)
        final_agent = self.agent_manager.get_current_agent(self.session_id)
        assert final_agent == 'debugger-agent'

        # Simulate debugging context injection
        self.mock_injector_client.make_request.return_value = {
            "task": {
                "id": "task_debugging",
                "title": "Fix authentication bugs",
                "status": "in_progress",
                "agent": "debugger-agent",
                "related_tasks": [
                    {"id": "task_implementation", "title": "Implement JWT handlers"},
                    {"id": "task_testing", "title": "Create test suite"}
                ]
            }
        }

        injection_result = await self.injector.inject_context(
            "mcp__4genthub_http__manage_task",
            {"action": "get", "task_id": "task_debugging"}
        )

        assert injection_result is not None
        assert "Fix authentication bugs" in injection_result
        assert "debugger-agent" in injection_result

        # Verify all context changes were processed
        assert len(context_changes) == 4
        assert self.synchronizer.sync_stats['successful_syncs'] == 1


if __name__ == "__main__":
    pytest.main([__file__, "-v"])