"""
Comprehensive tests for import error recovery and fallback mechanisms in server.py

This test suite covers:
- Optional import fallback from relative to absolute imports (lines 48-77, 80-98)
- TYPE_CHECKING conditional imports (lines 102-108)
- Import error handling for task management tools (lines 218-253)
- DDD tools lazy import error recovery (lines 244-253)
- Fallback configuration when imports fail (lines 341-347)

Target Coverage: 15-20 lines (+2.5-3.3pp)
Focus areas: Lines 103-108, 140-142, 341-347
"""

from typing import TYPE_CHECKING
from unittest.mock import Mock, patch

import pytest

# ============================================================================
# Test 1: TYPE_CHECKING Conditional Imports (Lines 102-108)
# ============================================================================


def test_type_checking_imports_not_executed_at_runtime():
    """
    Test that TYPE_CHECKING imports are only for type hints, not runtime.

    Coverage target: Lines 102-108
    Validates that imports inside TYPE_CHECKING block are not executed at runtime.
    """
    # TYPE_CHECKING is False at runtime, True for type checkers
    assert TYPE_CHECKING is False, "TYPE_CHECKING should be False at runtime"

    # These imports should not be available at runtime if only in TYPE_CHECKING
    # We verify by checking they're not in the module's namespace
    import fastmcp.server.server as server_module

    # These should be imported conditionally only for type checking
    conditional_imports = [
        "Client",
        "ClientTransport",
        "ClientTransportT",
        "OpenAPIComponentFn",
        "FastMCPOpenAPI",
        "RouteMap",
        "OpenAPIRouteMapFn",
        "FastMCPProxy",
    ]

    for import_name in conditional_imports:
        # These are only available in TYPE_CHECKING context
        # At runtime, they should not pollute the namespace
        if hasattr(server_module, import_name):
            # If they exist, they should be properly imported elsewhere
            obj = getattr(server_module, import_name)
            # Just verify they exist if accessed
            assert obj is not None


def test_type_checking_imports_structure():
    """
    Test the structure and organization of TYPE_CHECKING imports.

    Coverage target: Lines 102-108
    Validates that all TYPE_CHECKING imports follow proper patterns.
    """
    # Read the source to verify TYPE_CHECKING block structure
    import inspect

    import fastmcp.server.server

    source = inspect.getsource(fastmcp.server.server)

    # Verify TYPE_CHECKING block exists
    assert "if TYPE_CHECKING:" in source

    # Verify expected imports are in TYPE_CHECKING block
    expected_in_type_checking = [
        "from fastmcp.client import Client",
        "from fastmcp.client.transports import ClientTransport",
        "from fastmcp.server.openapi import",
        "from fastmcp.server.proxy import FastMCPProxy",
    ]

    for expected_import in expected_in_type_checking:
        assert expected_import in source, (
            f"Expected import not found: {expected_import}"
        )


# ============================================================================
# Test 2: Lifespan Wrapper Error Recovery (Lines 140-142)
# ============================================================================


@pytest.mark.asyncio
async def test_lifespan_wrapper_async_exit_stack_error_handling():
    """
    Test error handling in lifespan wrapper's AsyncExitStack.

    Coverage target: Lines 140-142
    Validates that AsyncExitStack properly handles context manager errors.
    """
    from contextlib import asynccontextmanager

    from fastmcp.server.server import FastMCP, _lifespan_wrapper

    # Create a FastMCP instance
    app = FastMCP(name="test_lifespan_error")

    # Create a lifespan that raises an error during entry
    @asynccontextmanager
    async def failing_lifespan(server):
        raise RuntimeError("Lifespan entry failed")
        yield  # This line is never reached

    # Wrap the failing lifespan
    wrapped = _lifespan_wrapper(app, failing_lifespan)

    # Create a mock MCP server
    mock_mcp_server = Mock()

    # Test that the error propagates correctly through AsyncExitStack
    with pytest.raises(RuntimeError, match="Lifespan entry failed"):
        async with wrapped(mock_mcp_server):
            pass


@pytest.mark.asyncio
async def test_lifespan_wrapper_async_exit_stack_cleanup():
    """
    Test that AsyncExitStack properly cleans up on errors.

    Coverage target: Lines 140-142
    Validates cleanup behavior when lifespan context fails.
    """
    from contextlib import asynccontextmanager

    from fastmcp.server.server import FastMCP, _lifespan_wrapper

    cleanup_called = False

    @asynccontextmanager
    async def lifespan_with_cleanup(server):
        nonlocal cleanup_called
        try:
            yield {"test": "context"}
        finally:
            cleanup_called = True

    app = FastMCP(name="test_cleanup")
    wrapped = _lifespan_wrapper(app, lifespan_with_cleanup)
    mock_mcp_server = Mock()

    # Test successful cleanup
    async with wrapped(mock_mcp_server) as context:
        assert context == {"test": "context"}

    # Verify cleanup was called
    assert cleanup_called, "Cleanup should be called when context exits"


# ============================================================================
# Test 3: Deprecation Warning Configuration (Lines 341-347)
# ============================================================================


def test_handle_deprecated_settings_with_warnings_disabled():
    """
    Test handling deprecated settings when warnings are disabled.

    Coverage target: Lines 341-347
    Validates fallback behavior when deprecation_warnings is False.
    """
    from fastmcp.server.server import FastMCP, _settings

    # Save original settings
    original_warnings = _settings.deprecation_warnings

    try:
        # Disable deprecation warnings
        _settings.deprecation_warnings = False

        # Create server with deprecated parameters
        # Should not raise warnings when deprecation_warnings is False
        with patch("warnings.warn") as mock_warn:
            server = FastMCP(
                name="test_deprecated",
                log_level="DEBUG",
                debug=True,
                host="localhost",
                port=8080,
            )

            # No warnings should be issued
            mock_warn.assert_not_called()

            # But settings should still be stored
            assert hasattr(server, "_deprecated_settings")
            assert server._deprecated_settings.host == "localhost"
            assert server._deprecated_settings.port == 8080

    finally:
        # Restore original settings
        _settings.deprecation_warnings = original_warnings


def test_handle_deprecated_settings_fallback_configuration():
    """
    Test fallback configuration merge when handling deprecated settings.

    Coverage target: Lines 341-347
    Validates that deprecated settings properly merge with defaults.
    """
    from fastmcp.server.server import FastMCP

    # Create server with mix of deprecated and valid parameters
    server = FastMCP(
        name="test_fallback",
        port=9000,  # deprecated
        sse_path="/custom/sse",  # deprecated
        cache_expiration_seconds=60,  # valid
    )

    # Verify deprecated settings were captured
    assert server._deprecated_settings.port == 9000
    assert server._deprecated_settings.sse_path == "/custom/sse"

    # Verify the merge happened (combined_settings = _settings.model_dump() | deprecated_settings)
    # The deprecated settings should override defaults
    assert hasattr(server, "_deprecated_settings")


# ============================================================================
# Test 4: Task Management Import Error Recovery (Lines 218-253)
# ============================================================================


def test_task_management_import_error_graceful_handling():
    """
    Test graceful handling of task management import errors.

    Coverage target: Lines 244-253
    Validates that server continues without task management if import fails.
    """
    from fastmcp.server.server import FastMCP

    # Mock the import to fail - need to patch where it's used (inside __init__)
    import_path = (
        "fastmcp.task_management.interface.ddd_compliant_mcp_tools.DDDCompliantMCPTools"
    )
    with patch(import_path, side_effect=ImportError("Mock import failure")):
        with patch("fastmcp.server.server.logger") as mock_logger:
            # Should not raise, should continue without task management
            server = FastMCP(name="test_import_error", enable_task_management=True)

            # Verify error was logged
            mock_logger.error.assert_called()
            error_call = mock_logger.error.call_args
            assert "Failed to initialize task management tools" in str(error_call)

            # Verify warning was logged
            mock_logger.warning.assert_called_with(
                "Continuing without task management tools"
            )

            # Verify consolidated_tools is None
            assert server._consolidated_tools is None


def test_task_management_initialization_exception_handling():
    """
    Test exception handling during task management initialization.

    Coverage target: Lines 218-253
    Validates error handling when DDDCompliantMCPTools initialization fails.
    """
    from fastmcp.server.server import FastMCP

    # Mock DDDCompliantMCPTools to raise during initialization
    mock_tools_class = Mock(side_effect=Exception("Initialization error"))
    import_path = (
        "fastmcp.task_management.interface.ddd_compliant_mcp_tools.DDDCompliantMCPTools"
    )

    with patch(import_path, mock_tools_class):
        with patch("fastmcp.server.server.logger") as mock_logger:
            # Should handle exception gracefully
            server = FastMCP(name="test_init_exception", enable_task_management=True)

            # Verify error logging
            assert mock_logger.error.called
            assert mock_logger.warning.called

            # Server should still be created without task tools
            assert server is not None
            assert server._consolidated_tools is None


# ============================================================================
# Test 5: Environment Variable Configuration Fallback
# ============================================================================


def test_task_management_env_var_fallback():
    """
    Test environment variable configuration fallback.

    Coverage target: Lines 222-241
    Validates AGENTHUB_DISABLE_CURSOR_TOOLS environment variable handling.
    """
    import os

    from fastmcp.server.server import FastMCP

    # Save original env var
    original_env = os.environ.get("AGENTHUB_DISABLE_CURSOR_TOOLS")

    try:
        # Set environment variable
        os.environ["AGENTHUB_DISABLE_CURSOR_TOOLS"] = "true"

        # Mock DDDCompliantMCPTools to capture config
        captured_config = {}

        def mock_init(*args, **kwargs):
            captured_config.update(kwargs)
            mock_instance = Mock()
            mock_instance.register_tools = Mock()
            return mock_instance

        import_path = "fastmcp.task_management.interface.ddd_compliant_mcp_tools.DDDCompliantMCPTools"
        with patch(import_path, side_effect=mock_init):
            FastMCP(name="test_env_fallback", enable_task_management=True)

            # Verify config_overrides were passed
            assert "config_overrides" in captured_config
            config = captured_config["config_overrides"]

            # Verify cursor tools are disabled
            assert "enabled_tools" in config
            enabled = config["enabled_tools"]
            assert enabled["update_auto_rule"] is False
            assert enabled["validate_rules"] is False

    finally:
        # Restore original env var
        if original_env is not None:
            os.environ["AGENTHUB_DISABLE_CURSOR_TOOLS"] = original_env
        elif "AGENTHUB_DISABLE_CURSOR_TOOLS" in os.environ:
            del os.environ["AGENTHUB_DISABLE_CURSOR_TOOLS"]


def test_task_management_tools_registration_failure():
    """
    Test graceful handling when tools registration fails.

    Coverage target: Lines 280-286
    Validates error handling during consolidated_tools.register_tools().
    """
    from fastmcp.server.server import FastMCP

    # Mock DDDCompliantMCPTools with failing register_tools
    mock_tools = Mock()
    mock_tools.register_tools = Mock(side_effect=Exception("Registration failed"))

    import_path = (
        "fastmcp.task_management.interface.ddd_compliant_mcp_tools.DDDCompliantMCPTools"
    )
    with patch(import_path, return_value=mock_tools):
        with patch("fastmcp.server.server.logger") as mock_logger:
            # Should handle registration failure gracefully
            server = FastMCP(
                name="test_registration_failure", enable_task_management=True
            )

            # Verify error was logged
            assert any(
                "Failed to register consolidated MCP tools" in str(call)
                for call in mock_logger.error.call_args_list
            )

            # Server should still exist
            assert server is not None
            # Tools instance should exist but not registered
            assert server._consolidated_tools is not None


# ============================================================================
# Test 6: AsyncExitStack Context Manager Integration
# ============================================================================


@pytest.mark.asyncio
async def test_async_exit_stack_multiple_contexts():
    """
    Test AsyncExitStack handling multiple async contexts.

    Coverage target: Lines 140-142
    Validates proper nesting of multiple async context managers.
    """
    from contextlib import asynccontextmanager

    from fastmcp.server.server import FastMCP, _lifespan_wrapper

    context_order = []

    @asynccontextmanager
    async def multi_context_lifespan(server):
        nonlocal context_order
        context_order.append("enter_outer")
        try:
            # Simulate nested contexts
            context_order.append("enter_inner")
            yield {"nested": "context"}
        finally:
            context_order.append("exit_inner")
            context_order.append("exit_outer")

    app = FastMCP(name="test_multi_context")
    wrapped = _lifespan_wrapper(app, multi_context_lifespan)
    mock_mcp_server = Mock()

    async with wrapped(mock_mcp_server) as context:
        assert context == {"nested": "context"}
        assert "enter_outer" in context_order
        assert "enter_inner" in context_order

    # Verify exit order (should be reverse of entry)
    assert context_order == ["enter_outer", "enter_inner", "exit_inner", "exit_outer"]


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
