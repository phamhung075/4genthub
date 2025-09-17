#!/usr/bin/env python3
"""
Tests for Context Injection Module

Tests the real-time context injection functionality including:
- Context relevance detection
- MCP context queries
- Asynchronous injection operations
- Performance optimization
- Cache management

Part of subtask: db40a3dd-7ac0-4046-885e-15d762b9283d
"""

import pytest
import asyncio
import time
import json
import tempfile
from unittest.mock import Mock, patch, AsyncMock, call
from pathlib import Path
from datetime import datetime

import sys

# Add hooks utils to path for testing
hooks_utils_path = Path(__file__).parent.parent.parent.parent.parent / '.claude' / 'hooks' / 'utils'
sys.path.insert(0, str(hooks_utils_path.absolute()))

try:
    from context_injector import (
        ContextInjector,
        ContextRelevanceDetector,
        MCPContextQuery,
        ContextInjectionConfig,
        create_context_injector,
        inject_context_sync
    )
except ImportError:
    pytest.skip("context_injector module not available", allow_module_level=True)


class TestContextInjectionConfig:
    """Test ContextInjectionConfig functionality."""

    def test_default_config(self):
        """Test default configuration values."""
        config = ContextInjectionConfig()

        assert config.performance_threshold_ms == 500
        assert config.cache_ttl_seconds == 900
        assert config.max_mcp_requests == 5
        assert config.enable_async_injection is True
        assert config.fallback_strategy == "cache_then_skip"

    def test_custom_config(self):
        """Test custom configuration values."""
        config = ContextInjectionConfig(
            performance_threshold_ms=1000,
            cache_ttl_seconds=1800,
            max_mcp_requests=10,
            enable_async_injection=False,
            fallback_strategy="skip"
        )

        assert config.performance_threshold_ms == 1000
        assert config.cache_ttl_seconds == 1800
        assert config.max_mcp_requests == 10
        assert config.enable_async_injection is False
        assert config.fallback_strategy == "skip"


class TestContextRelevanceDetector:
    """Test context relevance detection functionality."""

    def setup_method(self):
        """Set up test fixtures."""
        self.detector = ContextRelevanceDetector()

    def test_mcp_task_operations_relevant(self):
        """Test that MCP task operations are detected as relevant."""
        tool_name = "mcp__agenthub_http__manage_task"
        tool_input = {"action": "get", "task_id": "task_123"}

        is_relevant, priority, context_reqs = self.detector.is_context_relevant(tool_name, tool_input)

        assert is_relevant is True
        assert priority == "high"
        assert context_reqs["type"] == "mcp_operation"
        assert context_reqs["tool_name"] == tool_name
        assert context_reqs["action"] == "get"
        assert context_reqs["task_id"] == "task_123"

    def test_mcp_subtask_operations_relevant(self):
        """Test that MCP subtask operations are detected as relevant."""
        tool_name = "mcp__agenthub_http__manage_subtask"
        tool_input = {"action": "create", "task_id": "task_456"}

        is_relevant, priority, context_reqs = self.detector.is_context_relevant(tool_name, tool_input)

        assert is_relevant is True
        assert priority == "high"
        assert context_reqs["type"] == "mcp_operation"
        assert context_reqs["tool_name"] == tool_name
        assert context_reqs["action"] == "create"

    def test_mcp_context_operations_relevant(self):
        """Test that MCP context operations are detected as relevant."""
        tool_name = "mcp__agenthub_http__manage_context"
        tool_input = {"action": "resolve", "context_id": "ctx_789", "level": "project"}

        is_relevant, priority, context_reqs = self.detector.is_context_relevant(tool_name, tool_input)

        assert is_relevant is True
        assert priority == "high"
        assert context_reqs["type"] == "mcp_operation"
        assert context_reqs["context_id"] == "ctx_789"
        assert context_reqs["level"] == "project"

    def test_file_operations_relevant(self):
        """Test that file operations on relevant files are detected."""
        test_cases = [
            ("Write", {"file_path": "/path/to/script.py", "content": "code"}),
            ("Edit", {"file_path": "/path/to/component.tsx", "old_string": "old", "new_string": "new"}),
            ("MultiEdit", {"file_path": "/path/to/config.js", "edits": []}),
        ]

        for tool_name, tool_input in test_cases:
            is_relevant, priority, context_reqs = self.detector.is_context_relevant(tool_name, tool_input)

            assert is_relevant is True
            assert priority == "medium"
            assert context_reqs["type"] == "file_operation"
            assert "file_path" in context_reqs

    def test_git_operations_relevant(self):
        """Test that git operations are detected as relevant."""
        tool_name = "Bash"
        git_commands = [
            "git status",
            "git commit -m 'message'",
            "git branch feature",
            "git diff HEAD~1",
            "git log --oneline"
        ]

        for command in git_commands:
            tool_input = {"command": command}
            is_relevant, priority, context_reqs = self.detector.is_context_relevant(tool_name, tool_input)

            assert is_relevant is True
            assert priority == "medium"
            assert context_reqs["type"] == "git_operation"
            assert context_reqs["command"] == command

    def test_search_operations_relevant(self):
        """Test that search operations with relevant patterns are detected."""
        test_cases = [
            ("Grep", {"pattern": "todo", "path": "."}),
            ("Grep", {"pattern": "fixme", "glob": "*.py"}),
            ("Grep", {"pattern": "bug report", "path": "src/"}),
            ("Glob", {"pattern": "**/*.py"}),
            ("Glob", {"pattern": "**/*.test.js"}),
        ]

        for tool_name, tool_input in test_cases:
            is_relevant, priority, context_reqs = self.detector.is_context_relevant(tool_name, tool_input)

            assert is_relevant is True
            assert priority == "low"
            assert context_reqs["type"] == "search_operation"

    def test_irrelevant_operations(self):
        """Test that irrelevant operations are not detected."""
        test_cases = [
            ("Read", {"file_path": "/path/to/file.txt"}),
            ("Bash", {"command": "ls -la"}),
            ("Grep", {"pattern": "normal search"}),
            ("Unknown", {"param": "value"}),
        ]

        for tool_name, tool_input in test_cases:
            is_relevant, priority, context_reqs = self.detector.is_context_relevant(tool_name, tool_input)

            assert is_relevant is False
            assert priority == "none"
            assert context_reqs == {}

    def test_file_extension_filtering(self):
        """Test that only relevant file extensions trigger context injection."""
        relevant_extensions = ['.py', '.js', '.ts', '.md', '.sh', '.sql', '.jsx', '.tsx']
        irrelevant_extensions = ['.txt', '.log', '.tmp', '.bak']

        for ext in relevant_extensions:
            tool_input = {"file_path": f"/path/to/file{ext}", "content": "test"}
            is_relevant, _, _ = self.detector.is_context_relevant("Write", tool_input)
            assert is_relevant is True

        for ext in irrelevant_extensions:
            tool_input = {"file_path": f"/path/to/file{ext}", "content": "test"}
            is_relevant, _, _ = self.detector.is_context_relevant("Write", tool_input)
            assert is_relevant is False

    def test_mcp_action_filtering(self):
        """Test that only relevant MCP actions trigger context injection."""
        tool_name = "mcp__agenthub_http__manage_task"

        relevant_actions = ['get', 'update', 'complete', 'next', 'list', 'search']
        irrelevant_actions = ['invalid', 'unknown', 'create']  # create not in list for this tool

        for action in relevant_actions:
            tool_input = {"action": action, "task_id": "test"}
            is_relevant, _, _ = self.detector.is_context_relevant(tool_name, tool_input)
            assert is_relevant is True

        for action in irrelevant_actions:
            tool_input = {"action": action, "task_id": "test"}
            is_relevant, _, _ = self.detector.is_context_relevant(tool_name, tool_input)
            assert is_relevant is False


class TestMCPContextQuery:
    """Test MCP context query functionality."""

    def setup_method(self):
        """Set up test fixtures."""
        # Create config and manually override test_mode after __post_init__ runs
        self.config = ContextInjectionConfig()
        # Force test_mode to False to enable MCP mocking in tests
        self.config.test_mode = False

        with patch('context_injector.OptimizedMCPClient') as mock_client_class, \
             patch('context_injector.SessionContextCache') as mock_cache_class:

            self.mock_client = Mock()
            self.mock_cache = Mock()
            mock_client_class.return_value = self.mock_client
            mock_cache_class.return_value = self.mock_cache

            self.query_engine = MCPContextQuery(self.config)

    @pytest.mark.asyncio
    async def test_query_context_cache_hit(self):
        """Test context query with cache hit."""
        context_requirements = {
            "type": "mcp_operation",
            "tool_name": "mcp__agenthub_http__manage_task",
            "action": "get",
            "task_id": "task_123"
        }

        cached_data = {"task": {"id": "task_123", "title": "Test Task"}}
        self.mock_cache.get.return_value = cached_data

        result = await self.query_engine.query_context(context_requirements)

        assert result == cached_data
        self.mock_cache.get.assert_called_once()
        self.mock_client.make_request.assert_not_called()  # Should not query MCP

    @pytest.mark.asyncio
    async def test_query_mcp_operation_context(self):
        """Test querying context for MCP operations."""
        context_requirements = {
            "type": "mcp_operation",
            "tool_name": "mcp__agenthub_http__manage_task",
            "action": "get",
            "task_id": "task_123"
        }

        task_data = {"id": "task_123", "title": "Test Task", "status": "in_progress"}
        self.mock_client.make_request.return_value = {"task": task_data}
        self.mock_cache.get.return_value = None  # Cache miss

        result = await self.query_engine.query_context(context_requirements)

        # The test should handle both test mode enabled and disabled scenarios
        if self.config.test_mode:
            # In test mode, task context retrieval is skipped, so result should be None
            assert result is None
        else:
            # In normal mode, we should get the mocked result
            assert result is not None
            assert "mcp_operation" in result
            assert "task" in result
            assert result["task"] == task_data

            # Verify MCP was queried only if not in test mode
            self.mock_client.make_request.assert_called_with(
                "/mcp/manage_task",
                {
                    "action": "get",
                    "task_id": "task_123",
                    "include_context": True
                }
            )

        # Verify result was cached only if we got a result
        if result is not None:
            self.mock_cache.set.assert_called()
        else:
            # In test mode, nothing should be cached when result is None
            self.mock_cache.set.assert_not_called()

    @pytest.mark.asyncio
    async def test_query_file_context(self):
        """Test querying context for file operations."""
        context_requirements = {
            "type": "file_operation",
            "file_path": "/path/to/script.py",
            "file_extension": ".py",
            "operation_type": "write"
        }

        self.mock_cache.get.return_value = None  # Cache miss

        # Mock documentation path check
        with patch.object(self.query_engine, '_get_documentation_path') as mock_doc_path:
            mock_doc_path.return_value = None  # No documentation

            result = await self.query_engine.query_context(context_requirements)

        assert result is not None
        assert "file_operation" in result
        assert result["file_operation"]["path"] == "/path/to/script.py"
        assert result["file_operation"]["extension"] == ".py"
        assert result["file_operation"]["type"] == "write"

    @pytest.mark.asyncio
    async def test_query_git_context(self):
        """Test querying context for git operations."""
        context_requirements = {
            "type": "git_operation",
            "command": "git status",
            "needs_git_status": True,
            "needs_branch_info": False
        }

        self.mock_cache.get.return_value = None  # Cache miss
        self.mock_cache.get_git_status.return_value = {"status": "clean", "cached": True}

        result = await self.query_engine.query_context(context_requirements)

        assert result is not None
        assert "git_operation" in result
        assert result["git_operation"]["command"] == "git status"
        assert "git_status" in result
        assert result["git_status"]["status"] == "clean"

    @pytest.mark.asyncio
    async def test_query_search_context(self):
        """Test querying context for search operations."""
        context_requirements = {
            "type": "search_operation",
            "pattern": "todo",
            "search_path": ".",
            "file_filter": "*.py"
        }

        self.mock_cache.get.return_value = None  # Cache miss

        result = await self.query_engine.query_context(context_requirements)

        assert result is not None
        assert "search_operation" in result
        assert result["search_operation"]["pattern"] == "todo"
        assert result["search_operation"]["path"] == "."
        assert result["search_operation"]["filter"] == "*.py"

    @pytest.mark.asyncio
    async def test_query_context_error_handling(self):
        """Test error handling in context queries."""
        context_requirements = {
            "type": "mcp_operation",
            "tool_name": "mcp__agenthub_http__manage_task",
            "action": "get",
            "task_id": "task_123"
        }

        self.mock_cache.get.return_value = None  # Cache miss
        self.mock_client.make_request.side_effect = Exception("MCP connection failed")

        result = await self.query_engine.query_context(context_requirements)

        assert result is None  # Should return None on error

    @pytest.mark.asyncio
    async def test_get_recent_tasks(self):
        """Test getting recent tasks from MCP."""
        tasks_data = [
            {"id": "task_1", "title": "Task 1", "status": "in_progress"},
            {"id": "task_2", "title": "Task 2", "status": "in_progress"}
        ]
        self.mock_client.make_request.return_value = {"tasks": tasks_data}

        result = await self.query_engine._get_recent_tasks(limit=2)

        assert result == tasks_data
        self.mock_client.make_request.assert_called_with(
            "/mcp/manage_task",
            {
                "action": "list",
                "limit": 2,
                "status": "in_progress"
            }
        )

    @pytest.mark.asyncio
    async def test_get_task_context_different_response_formats(self):
        """Test handling different MCP response formats for task context."""
        task_data = {"id": "task_123", "title": "Test Task"}

        # Test different response formats
        response_formats = [
            {"task": task_data},  # Direct task key
            {"data": {"task": task_data}},  # Nested under data
            {"success": True, "data": {"task": task_data}},  # Success wrapper
        ]

        for response in response_formats:
            self.mock_client.make_request.return_value = response

            result = await self.query_engine._get_task_context("task_123")

            assert result == task_data

    def test_documentation_path_calculation(self):
        """Test documentation path calculation."""
        # Test valid relative path
        with patch('pathlib.Path.cwd', return_value=Path('/project')):
            doc_path = self.query_engine._get_documentation_path('/project/src/utils.py')

            expected_path = Path('/project/ai_docs/_absolute_docs/src/utils.py.md')
            assert doc_path == expected_path

        # Test invalid path (outside project)
        with patch('pathlib.Path.cwd', return_value=Path('/project')):
            doc_path = self.query_engine._get_documentation_path('/other/project/file.py')
            assert doc_path is None

    def test_cache_key_creation(self):
        """Test cache key creation from context requirements."""
        requirements = {
            "type": "mcp_operation",
            "tool_name": "test_tool",
            "action": "get",
            "task_id": "123"
        }

        key1 = self.query_engine._create_cache_key(requirements)
        key2 = self.query_engine._create_cache_key(requirements)

        # Same requirements should produce same key
        assert key1 == key2

        # Different requirements should produce different key
        requirements2 = requirements.copy()
        requirements2["task_id"] = "456"
        key3 = self.query_engine._create_cache_key(requirements2)

        assert key1 != key3


class TestContextInjector:
    """Test main ContextInjector functionality."""

    def setup_method(self):
        """Set up test fixtures."""
        self.config = ContextInjectionConfig(performance_threshold_ms=100)

        with patch('context_injector.ContextRelevanceDetector') as mock_detector_class, \
             patch('context_injector.MCPContextQuery') as mock_query_class:

            self.mock_detector = Mock()
            self.mock_query_engine = Mock()
            # Make query_context async
            self.mock_query_engine.query_context = AsyncMock()
            mock_detector_class.return_value = self.mock_detector
            mock_query_class.return_value = self.mock_query_engine

            self.injector = ContextInjector(self.config)

    @pytest.mark.asyncio
    async def test_inject_context_not_relevant(self):
        """Test context injection when tool is not relevant."""
        tool_name = "Read"
        tool_input = {"file_path": "/path/to/file.txt"}

        self.mock_detector.is_context_relevant.return_value = (False, "none", {})

        result = await self.injector.inject_context(tool_name, tool_input)

        assert result is None
        self.mock_detector.is_context_relevant.assert_called_once_with(tool_name, tool_input)
        self.mock_query_engine.query_context.assert_not_called()

    @pytest.mark.asyncio
    async def test_inject_context_success(self):
        """Test successful context injection."""
        tool_name = "mcp__agenthub_http__manage_task"
        tool_input = {"action": "get", "task_id": "task_123"}

        context_reqs = {
            "type": "mcp_operation",
            "tool_name": tool_name,
            "action": "get",
            "task_id": "task_123"
        }

        context_data = {
            "task": {
                "id": "task_123",
                "title": "Test Task",
                "status": "in_progress",
                "priority": "high",
                "assignees": ["alice"],
                "details": "Task details here"
            }
        }

        self.mock_detector.is_context_relevant.return_value = (True, "high", context_reqs)
        self.mock_query_engine.query_context.return_value = context_data

        result = await self.injector.inject_context(tool_name, tool_input)

        assert result is not None
        assert "<context-injection>" in result
        assert "Priority: high" in result
        assert "Task ID**: task_123" in result
        assert "Title**: Test Task" in result
        assert "Status**: in_progress" in result

        self.mock_detector.is_context_relevant.assert_called_once_with(tool_name, tool_input)
        self.mock_query_engine.query_context.assert_called_once_with(context_reqs)

    @pytest.mark.asyncio
    async def test_inject_context_no_data(self):
        """Test context injection when no context data is available."""
        tool_name = "Edit"
        tool_input = {"file_path": "/path/to/script.py"}

        context_reqs = {"type": "file_operation"}

        self.mock_detector.is_context_relevant.return_value = (True, "medium", context_reqs)
        self.mock_query_engine.query_context.return_value = None

        result = await self.injector.inject_context(tool_name, tool_input)

        assert result is None

    @pytest.mark.asyncio
    async def test_inject_context_error_handling(self):
        """Test error handling in context injection."""
        tool_name = "Write"
        tool_input = {"file_path": "/path/to/script.py"}

        context_reqs = {"type": "file_operation"}

        self.mock_detector.is_context_relevant.return_value = (True, "medium", context_reqs)
        self.mock_query_engine.query_context.side_effect = Exception("Query failed")

        result = await self.injector.inject_context(tool_name, tool_input)

        assert result is None  # Should handle error gracefully

    @pytest.mark.asyncio
    async def test_performance_threshold_monitoring(self):
        """Test performance threshold monitoring."""
        tool_name = "mcp__agenthub_http__manage_task"
        tool_input = {"action": "get"}

        context_reqs = {"type": "mcp_operation"}
        context_data = {"task": {"id": "123"}}

        self.mock_detector.is_context_relevant.return_value = (True, "high", context_reqs)

        # Make query_context slow to exceed threshold
        async def slow_query(*args, **kwargs):
            await asyncio.sleep(0.2)  # 200ms delay (exceeds 100ms threshold)
            return context_data

        self.mock_query_engine.query_context.side_effect = slow_query

        with patch('context_injector.logger') as mock_logger:
            result = await self.injector.inject_context(tool_name, tool_input)

            # Should log performance warning
            mock_logger.warning.assert_called()
            warning_call = mock_logger.warning.call_args[0][0]
            assert "exceeded threshold" in warning_call

        assert result is not None  # Should still return result

    def test_format_context_injection_task_context(self):
        """Test formatting context injection with task context."""
        context_data = {
            "task": {
                "id": "task_123",
                "title": "Implement feature",
                "status": "in_progress",
                "priority": "high",
                "assignees": ["alice", "bob"],
                "details": "Detailed implementation requirements here"
            }
        }

        result = self.injector._format_context_injection(context_data, "high")

        assert "<context-injection>" in result
        assert "Priority: high" in result
        assert "## Current Task Context:" in result
        assert "**Task ID**: task_123" in result
        assert "**Title**: Implement feature" in result
        assert "**Status**: in_progress" in result
        assert "**Priority**: high" in result
        assert "**Assignees**: alice, bob" in result
        assert "### Task Details:" in result
        assert "Detailed implementation requirements here" in result
        assert "</context-injection>" in result

    def test_format_context_injection_git_branch_context(self):
        """Test formatting context injection with git branch context."""
        context_data = {
            "git_branch": {
                "id": "branch_456",
                "git_branch_name": "feature/auth",
                "git_branch_description": "Authentication feature branch"
            }
        }

        result = self.injector._format_context_injection(context_data, "medium")

        assert "## Git Branch Context:" in result
        assert "**Branch ID**: branch_456" in result
        assert "**Name**: feature/auth" in result
        assert "**Description**: Authentication feature branch" in result

    def test_format_context_injection_documentation_context(self):
        """Test formatting context injection with documentation context."""
        context_data = {
            "documentation": {
                "exists": True,
                "path": "/project/ai_docs/_absolute_docs/src/utils.py.md",
                "last_modified": "2023-01-01T12:00:00"
            }
        }

        result = self.injector._format_context_injection(context_data, "low")

        assert "## Documentation Context:" in result
        assert "**Exists**: True" in result
        assert "**Path**: /project/ai_docs/_absolute_docs/src/utils.py.md" in result
        assert "**Last Modified**: 2023-01-01T12:00:00" in result

    def test_format_context_injection_related_tasks(self):
        """Test formatting context injection with related tasks."""
        context_data = {
            "related_tasks": [
                {"title": "Setup database", "status": "completed"},
                {"title": "Create API endpoints", "status": "in_progress"},
                {"title": "Write tests", "status": "pending"}
            ]
        }

        result = self.injector._format_context_injection(context_data, "medium")

        assert "## Related Tasks:" in result
        assert "**Setup database** (completed)" in result
        assert "**Create API endpoints** (in_progress)" in result
        assert "**Write tests** (pending)" in result

    def test_format_context_injection_git_status(self):
        """Test formatting context injection with git status."""
        context_data = {
            "git_status": {
                "status": "dirty",
                "cached": False
            }
        }

        result = self.injector._format_context_injection(context_data, "medium")

        assert "## Git Status:" in result
        assert "**Status**: dirty" in result
        assert "**Cached**: False" in result

    def test_format_context_injection_long_task_details(self):
        """Test formatting with long task details (should truncate)."""
        long_details = "a" * 1000  # 1000 characters

        context_data = {
            "task": {
                "id": "task_123",
                "title": "Test Task",
                "details": long_details
            }
        }

        result = self.injector._format_context_injection(context_data, "high")

        # Should truncate to 500 characters plus "..."
        assert len([line for line in result.split('\n') if 'aaa' in line][0]) <= 504  # 500 + "..."
        assert "..." in result

    def test_format_context_injection_limit_related_tasks(self):
        """Test that related tasks are limited to 3 most relevant."""
        context_data = {
            "related_tasks": [
                {"title": f"Task {i}", "status": "pending"}
                for i in range(10)  # 10 tasks
            ]
        }

        result = self.injector._format_context_injection(context_data, "medium")

        # Should only show first 3 tasks
        task_lines = [line for line in result.split('\n') if line.startswith('- **Task')]
        assert len(task_lines) == 3


class TestConvenienceFunctions:
    """Test convenience functions."""

    def test_create_context_injector(self):
        """Test context injector factory function."""
        # Test with default config
        injector = create_context_injector()
        assert isinstance(injector, ContextInjector)
        assert injector.config.performance_threshold_ms == 500  # Default

        # Test with custom config
        custom_config = ContextInjectionConfig(performance_threshold_ms=1000)
        injector = create_context_injector(custom_config)
        assert injector.config.performance_threshold_ms == 1000

    def test_inject_context_sync(self):
        """Test synchronous wrapper for context injection."""
        with patch('context_injector.create_context_injector') as mock_create:
            mock_injector = Mock()
            mock_injector.inject_context = AsyncMock(return_value="<context-injection>Test</context-injection>")
            mock_create.return_value = mock_injector

            result = inject_context_sync("Write", {"file_path": "/test.py"})

            assert result == "<context-injection>Test</context-injection>"
            mock_injector.inject_context.assert_called_once_with("Write", {"file_path": "/test.py"})

    def test_inject_context_sync_error_handling(self):
        """Test error handling in synchronous wrapper."""
        with patch('context_injector.create_context_injector') as mock_create:
            mock_injector = Mock()
            mock_injector.inject_context = AsyncMock(side_effect=Exception("Injection failed"))
            mock_create.return_value = mock_injector

            result = inject_context_sync("Write", {"file_path": "/test.py"})

            assert result is None  # Should return None on error

    def test_inject_context_sync_timeout(self):
        """Test timeout handling in synchronous wrapper."""
        with patch('context_injector.create_context_injector') as mock_create:
            # Create slow async function that takes longer than 1 second timeout
            async def slow_injection(*args, **kwargs):
                await asyncio.sleep(2)  # 2 seconds
                return "result"

            mock_injector = Mock()
            mock_injector.inject_context = slow_injection
            mock_create.return_value = mock_injector

            result = inject_context_sync("Write", {"file_path": "/test.py"})

            assert result is None  # Should return None on timeout


class TestIntegrationScenarios:
    """Test integration scenarios combining multiple components."""

    @pytest.mark.asyncio
    async def test_end_to_end_task_context_injection(self):
        """Test end-to-end context injection for task operations."""
        # Create real instances without mocking
        config = ContextInjectionConfig(cache_ttl_seconds=1)
        # Force test_mode to False to enable MCP mocking in tests
        config.test_mode = False

        with patch('context_injector.OptimizedMCPClient') as mock_client_class, \
             patch('context_injector.SessionContextCache') as mock_cache_class:

            mock_client = Mock()
            mock_cache = Mock()
            mock_client_class.return_value = mock_client
            mock_cache_class.return_value = mock_cache

            # Set up mock responses
            task_data = {
                "id": "task_123",
                "title": "Implement authentication",
                "status": "in_progress",
                "priority": "high",
                "assignees": ["alice"],
                "details": "Implement JWT authentication system"
            }

            mock_cache.get.return_value = None  # Cache miss
            mock_client.make_request.return_value = {"task": task_data}

            injector = ContextInjector(config)

            # Test injection
            result = await injector.inject_context(
                "mcp__agenthub_http__manage_task",
                {"action": "get", "task_id": "task_123"}
            )

            # Verify result
            assert result is not None
            assert "<context-injection>" in result
            assert "Task ID**: task_123" in result
            assert "Implement authentication" in result
            assert "in_progress" in result
            assert "alice" in result

            # Verify MCP was called
            mock_client.make_request.assert_called_once()

            # Verify caching
            mock_cache.set.assert_called_once()

    @pytest.mark.asyncio
    async def test_performance_under_load(self):
        """Test context injection performance under concurrent load."""
        config = ContextInjectionConfig(performance_threshold_ms=1000)
        # Force test_mode to False to enable MCP mocking in tests
        config.test_mode = False

        with patch('context_injector.OptimizedMCPClient') as mock_client_class, \
             patch('context_injector.SessionContextCache') as mock_cache_class:

            mock_client = Mock()
            mock_cache = Mock()
            mock_client_class.return_value = mock_client
            mock_cache_class.return_value = mock_cache

            # Set up fast responses
            mock_cache.get.return_value = None
            mock_client.make_request.return_value = {"task": {"id": "123", "title": "Test"}}

            injector = ContextInjector(config)

            # Run multiple injections concurrently
            tasks = []
            for i in range(10):
                task = injector.inject_context(
                    "mcp__agenthub_http__manage_task",
                    {"action": "get", "task_id": f"task_{i}"}
                )
                tasks.append(task)

            results = await asyncio.gather(*tasks)

            # All should complete successfully
            assert all(result is not None for result in results)
            assert all("<context-injection>" in result for result in results)


if __name__ == "__main__":
    pytest.main([__file__, "-v"])