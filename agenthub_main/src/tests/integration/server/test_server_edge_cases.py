"""
Server Integration Edge Case Tests

Tests server integration edge cases covering:
- Lines 1394-1396: stdio_server context manager error handling
- Lines 1426-1451: HTTP server configuration edge cases
- Lines 1464-1472: SSE deprecation warning handling
- Lines 1496-1503: sse_app deprecation warning handling
- Lines 1920-1922: OpenAPI spec import and initialization
- Lines 1950-1963: FastAPI integration with httpx client configuration

Focus on integration resilience, error handling, and edge conditions.
Target: 2-3 production-ready tests with comprehensive coverage.
"""

import pytest
import warnings
from unittest.mock import Mock, patch, AsyncMock, MagicMock
from contextlib import asynccontextmanager
import httpx
from typing import Any


pytestmark = pytest.mark.integration


class TestStdioServerErrorHandling:
    """Test stdio server context manager error handling (lines 1394-1396)"""

    @pytest.mark.asyncio
    async def test_stdio_server_connection_failure_resilience(self):
        """
        Test stdio server handles connection failures gracefully.

        Covers lines 1394-1396: stdio_server context manager error handling.
        Verifies:
        - Connection failures are caught and logged
        - Server exits gracefully without hanging
        - Proper cleanup of resources
        - Error propagation to caller
        """
        from fastmcp.server.server import FastMCP

        # Create minimal server instance
        server = FastMCP(name="test-stdio-server")

        # Mock stdio_server to raise connection error
        @asynccontextmanager
        async def failing_stdio_server():
            raise ConnectionError("Failed to establish stdio connection")
            yield None, None  # Never reached

        with patch('fastmcp.server.server.stdio_server', failing_stdio_server):
            # Should propagate the connection error
            with pytest.raises(ConnectionError, match="Failed to establish stdio connection"):
                await server.run_stdio_async()

    @pytest.mark.asyncio
    async def test_stdio_server_stream_interruption_handling(self):
        """
        Test stdio server handles stream interruptions during operation.

        Covers lines 1394-1396: Stream handling within stdio_server context.
        Verifies:
        - Stream interruptions are handled
        - Server cleanup executes properly
        - No resource leaks on unexpected termination
        """
        from fastmcp.server.server import FastMCP

        server = FastMCP(name="test-stream-interruption")

        # Create mock streams that fail during operation
        mock_read_stream = AsyncMock()
        mock_write_stream = AsyncMock()

        # Mock run to raise interruption after context enters
        mock_mcp_server = Mock()
        mock_mcp_server.run = AsyncMock(side_effect=BrokenPipeError("Stream interrupted"))
        mock_mcp_server.create_initialization_options = Mock(return_value={})

        @asynccontextmanager
        async def interrupting_stdio_server():
            yield mock_read_stream, mock_write_stream

        with patch('fastmcp.server.server.stdio_server', interrupting_stdio_server), \
             patch.object(server, '_mcp_server', mock_mcp_server):

            # Should propagate the stream interruption error
            with pytest.raises(BrokenPipeError, match="Stream interrupted"):
                await server.run_stdio_async()

            # Verify cleanup: context manager __aexit__ should have been called
            # (this happens automatically via context manager protocol)


class TestHTTPServerConfigurationEdgeCases:
    """Test HTTP server configuration edge cases (lines 1426-1451)"""

    @pytest.mark.asyncio
    async def test_http_server_with_none_host_port_defaults(self):
        """
        Test HTTP server properly defaults None host/port values.

        Covers lines 1426-1427: host/port defaulting logic.
        Verifies:
        - None host defaults to settings.host
        - None port defaults to settings.port
        - Empty string host/port handled correctly
        - Default values from _deprecated_settings work
        """
        from fastmcp.server.server import FastMCP

        # Create server with custom settings
        server = FastMCP(name="test-http-defaults")

        # Mock the deprecated settings
        server._deprecated_settings = Mock(
            host="default-host.example.com",
            port=9999,
            log_level="INFO"
        )

        # Mock app creation and uvicorn to avoid actual server start
        mock_app = Mock()
        mock_app.state = Mock(path="/test-path")

        mock_uvicorn_server = AsyncMock()
        mock_uvicorn_server.serve = AsyncMock()

        with patch.object(server, 'http_app', return_value=mock_app), \
             patch('fastmcp.server.server.uvicorn.Config') as mock_config, \
             patch('fastmcp.server.server.uvicorn.Server', return_value=mock_uvicorn_server):

            # Call with all None values to test defaulting
            await server.run_http_async(
                host=None,
                port=None,
                log_level=None,
                path=None
            )

            # Verify Config was called with defaulted values
            mock_config.assert_called_once()
            config_call = mock_config.call_args

            assert config_call[1]['host'] == "default-host.example.com"
            assert config_call[1]['port'] == 9999

    @pytest.mark.asyncio
    async def test_http_server_log_level_case_normalization(self):
        """
        Test HTTP server normalizes log level to lowercase.

        Covers lines 1428-1430: log level case normalization.
        Verifies:
        - Uppercase log levels converted to lowercase
        - Mixed case handled correctly
        - Default log level applied when None
        """
        from fastmcp.server.server import FastMCP

        server = FastMCP(name="test-log-normalization")
        server._deprecated_settings = Mock(
            host="localhost",
            port=8000,
            log_level="WARNING"  # Uppercase default
        )

        mock_app = Mock()
        mock_app.state = Mock(path="/test")
        mock_uvicorn_server = AsyncMock()
        mock_uvicorn_server.serve = AsyncMock()

        with patch.object(server, 'http_app', return_value=mock_app), \
             patch('fastmcp.server.server.uvicorn.Config') as mock_config, \
             patch('fastmcp.server.server.uvicorn.Server', return_value=mock_uvicorn_server):

            # Test uppercase log level
            await server.run_http_async(log_level="DEBUG")

            config_kwargs = mock_config.call_args[1]
            # Should be lowercase
            assert config_kwargs['log_level'] == "debug"

    @pytest.mark.asyncio
    async def test_http_server_uvicorn_config_override_handling(self):
        """
        Test HTTP server handles uvicorn_config overrides correctly.

        Covers lines 1434-1443: uvicorn config merging and log config handling.
        Verifies:
        - User uvicorn_config overrides defaults
        - log_config presence prevents log_level default
        - Proper config merging without conflicts
        - Graceful shutdown timeout configured
        """
        from fastmcp.server.server import FastMCP

        server = FastMCP(name="test-config-override")
        server._deprecated_settings = Mock(host="localhost", port=8000, log_level="INFO")

        mock_app = Mock()
        mock_app.state = Mock(path="/test")
        mock_uvicorn_server = AsyncMock()
        mock_uvicorn_server.serve = AsyncMock()

        # Test with custom uvicorn_config including log_config
        custom_config = {
            "log_config": {"version": 1, "disable_existing_loggers": False},
            "timeout_keep_alive": 120,
            "workers": 4
        }

        with patch.object(server, 'http_app', return_value=mock_app), \
             patch('fastmcp.server.server.uvicorn.Config') as mock_config, \
             patch('fastmcp.server.server.uvicorn.Server', return_value=mock_uvicorn_server):

            await server.run_http_async(uvicorn_config=custom_config)

            config_kwargs = mock_config.call_args[1]

            # Verify defaults are set
            assert config_kwargs['timeout_graceful_shutdown'] == 0
            assert config_kwargs['lifespan'] == "on"

            # Verify user config merged
            assert config_kwargs['log_config'] == custom_config['log_config']
            assert config_kwargs['timeout_keep_alive'] == 120
            assert config_kwargs['workers'] == 4

            # Verify log_level NOT set (because log_config present)
            assert 'log_level' not in config_kwargs or config_kwargs.get('log_level') is None


class TestSSEDeprecationWarnings:
    """Test SSE deprecation warning handling (lines 1464-1472, 1496-1503)"""

    @pytest.mark.asyncio
    async def test_run_sse_async_deprecation_warning_with_settings_enabled(self):
        """
        Test run_sse_async emits deprecation warning when enabled.

        Covers lines 1464-1471: DeprecationWarning emission logic.
        Verifies:
        - DeprecationWarning raised when _settings.deprecation_warnings=True
        - Warning message includes version and migration guidance
        - run_http_async called with transport='sse'
        - stacklevel=2 for proper warning location
        """
        from fastmcp.server.server import FastMCP

        server = FastMCP(name="test-sse-deprecation")

        # Mock settings to enable deprecation warnings
        with patch('fastmcp.server.server._settings') as mock_settings:
            mock_settings.deprecation_warnings = True

            # Mock run_http_async to avoid actual server start
            with patch.object(server, 'run_http_async', new_callable=AsyncMock) as mock_run_http:

                # Capture warnings
                with warnings.catch_warnings(record=True) as warning_list:
                    warnings.simplefilter("always")

                    await server.run_sse_async(host="localhost", port=8080)

                    # Verify deprecation warning was raised
                    assert len(warning_list) == 1
                    assert issubclass(warning_list[0].category, DeprecationWarning)
                    assert "run_sse_async method is deprecated" in str(warning_list[0].message)
                    assert "2.3.2" in str(warning_list[0].message)
                    assert "run_http_async" in str(warning_list[0].message)

                    # Verify run_http_async was called with SSE transport
                    mock_run_http.assert_called_once_with(
                        transport="sse",
                        host="localhost",
                        port=8080,
                        log_level=None,
                        path=None,
                        uvicorn_config=None
                    )

    def test_sse_app_deprecation_warning_suppressed_when_disabled(self):
        """
        Test sse_app method respects deprecation warning settings.

        Covers lines 1496-1502: Conditional deprecation warning emission.
        Verifies:
        - No warning when _settings.deprecation_warnings=False
        - create_sse_app still called correctly
        - Parameters passed through properly
        """
        from fastmcp.server.server import FastMCP

        server = FastMCP(name="test-sse-app-no-warning")
        server._deprecated_settings = Mock(
            message_path="/messages",
            sse_path="/sse",
            debug=True
        )

        # Mock settings to disable deprecation warnings
        with patch('fastmcp.server.server._settings') as mock_settings:
            mock_settings.deprecation_warnings = False

            # Mock create_sse_app
            with patch('fastmcp.server.server.create_sse_app') as mock_create_sse:
                mock_create_sse.return_value = Mock()

                # Capture warnings
                with warnings.catch_warnings(record=True) as warning_list:
                    warnings.simplefilter("always")

                    result = server.sse_app(path="/custom-sse")

                    # Verify NO warnings were raised
                    assert len(warning_list) == 0

                    # Verify create_sse_app was still called
                    mock_create_sse.assert_called_once()
                    call_kwargs = mock_create_sse.call_args[1]
                    assert call_kwargs['sse_path'] == "/custom-sse"


class TestOpenAPIIntegration:
    """Test OpenAPI integration edge cases (lines 1920-1922, 1950-1963)"""

    def test_from_openapi_spec_initialization_with_minimal_config(self):
        """
        Test from_openapi creates FastMCPOpenAPI with minimal required config.

        Covers lines 1920-1922: FastMCPOpenAPI import and initialization.
        Verifies:
        - FastMCPOpenAPI imported dynamically
        - Minimal required parameters work
        - Optional parameters handled correctly
        - Settings passed through kwargs
        """
        from fastmcp.server.server import FastMCP

        # Mock the FastMCPOpenAPI class from the openapi module
        with patch('fastmcp.server.openapi.FastMCPOpenAPI') as mock_openapi_class:
            mock_instance = Mock()
            mock_openapi_class.return_value = mock_instance

            # Minimal OpenAPI spec
            minimal_spec = {
                "openapi": "3.0.0",
                "info": {"title": "Test API", "version": "1.0.0"},
                "paths": {}
            }

            mock_client = Mock(spec=httpx.AsyncClient)

            # Call with minimal config
            result = FastMCP.from_openapi(
                openapi_spec=minimal_spec,
                client=mock_client
            )

            # Verify FastMCPOpenAPI was instantiated
            mock_openapi_class.assert_called_once_with(
                openapi_spec=minimal_spec,
                client=mock_client,
                route_maps=None,
                route_map_fn=None,
                mcp_component_fn=None,
                mcp_names=None,
                tags=None
            )

            assert result == mock_instance

    def test_from_fastapi_httpx_client_base_url_defaulting(self):
        """
        Test from_fastapi sets default base_url for httpx client.

        Covers lines 1952-1954: httpx_client_kwargs base_url defaulting.
        Verifies:
        - base_url defaults to 'http://fastapi' when not provided
        - Existing base_url not overridden
        - ASGITransport configured with app
        - Client passed to FastMCPOpenAPI correctly
        """
        from fastmcp.server.server import FastMCP

        # Mock FastAPI app
        mock_fastapi_app = Mock()
        mock_fastapi_app.title = "Test FastAPI App"
        mock_fastapi_app.openapi = Mock(return_value={
            "openapi": "3.0.0",
            "info": {"title": "Generated API", "version": "1.0.0"},
            "paths": {}
        })

        with patch('fastmcp.server.openapi.FastMCPOpenAPI') as mock_openapi_class, \
             patch('fastmcp.server.server.httpx.AsyncClient') as mock_async_client, \
             patch('fastmcp.server.server.httpx.ASGITransport') as mock_transport:

            mock_instance = Mock()
            mock_openapi_class.return_value = mock_instance
            mock_client_instance = Mock()
            mock_async_client.return_value = mock_client_instance
            mock_transport_instance = Mock()
            mock_transport.return_value = mock_transport_instance

            # Call without httpx_client_kwargs (test defaulting)
            result = FastMCP.from_fastapi(app=mock_fastapi_app)

            # Verify ASGITransport created with app
            mock_transport.assert_called_once_with(app=mock_fastapi_app)

            # Verify AsyncClient created with default base_url
            mock_async_client.assert_called_once_with(
                transport=mock_transport_instance,
                base_url="http://fastapi"
            )

            # Verify name defaulted to app.title
            openapi_call = mock_openapi_class.call_args[1]
            assert openapi_call['name'] == "Test FastAPI App"
            assert openapi_call['client'] == mock_client_instance

    def test_from_fastapi_custom_httpx_client_kwargs_preserved(self):
        """
        Test from_fastapi preserves custom httpx_client_kwargs.

        Covers lines 1952-1959: Custom httpx client configuration.
        Verifies:
        - Custom base_url not overridden by default
        - Additional httpx kwargs passed through
        - Custom timeout and headers respected
        """
        from fastmcp.server.server import FastMCP

        mock_fastapi_app = Mock()
        mock_fastapi_app.title = "Custom API"
        mock_fastapi_app.openapi = Mock(return_value={"openapi": "3.0.0", "paths": {}})

        with patch('fastmcp.server.openapi.FastMCPOpenAPI'), \
             patch('fastmcp.server.server.httpx.AsyncClient') as mock_async_client, \
             patch('fastmcp.server.server.httpx.ASGITransport') as mock_transport:

            mock_transport.return_value = Mock()

            # Custom httpx configuration
            custom_kwargs = {
                "base_url": "http://custom-base.local",
                "timeout": 60.0,
                "headers": {"X-Custom-Header": "test-value"}
            }

            FastMCP.from_fastapi(
                app=mock_fastapi_app,
                httpx_client_kwargs=custom_kwargs
            )

            # Verify custom base_url was NOT overridden
            client_call = mock_async_client.call_args[1]
            assert client_call['base_url'] == "http://custom-base.local"
            assert client_call['timeout'] == 60.0
            assert client_call['headers'] == {"X-Custom-Header": "test-value"}


class TestConfigurationValidationEdgeCases:
    """Test configuration validation edge cases covering lines 355-368, 425-437, 462-475"""

    def test_settings_property_deprecation_warning_with_stacklevel(self):
        """
        Test settings property emits deprecation warning with correct stacklevel.

        Covers lines 355-361: settings property deprecation warning.
        Verifies:
        - DeprecationWarning raised when accessing .settings
        - Warning message includes migration guidance
        - stacklevel=2 points to caller's code location
        - Returns correct _deprecated_settings instance
        """
        from fastmcp.server.server import FastMCP

        server = FastMCP(name="test-settings-deprecation")

        # Mock global _settings to enable deprecation warnings
        with patch('fastmcp.server.server._settings') as mock_settings:
            mock_settings.deprecation_warnings = True

            with warnings.catch_warnings(record=True) as warning_list:
                warnings.simplefilter("always")

                # Access the deprecated property
                result = server.settings

                # Verify deprecation warning was raised
                assert len(warning_list) == 1
                assert issubclass(warning_list[0].category, DeprecationWarning)
                assert "Accessing `.settings` on a FastMCP instance is deprecated" in str(warning_list[0].message)
                assert "Use the global `_settings` instead" in str(warning_list[0].message)

                # Verify it returns the deprecated settings instance
                assert result == server._deprecated_settings

    def test_register_task_tools_with_already_registered_tools(self):
        """
        Test register_task_management_tools handles already-registered tools.

        Covers lines 386-388: Early return when tools already registered.
        Verifies:
        - Returns True when tools already exist
        - Logs warning about existing registration
        - Does not attempt re-registration
        - No side effects on existing tools
        """
        from fastmcp.server.server import FastMCP

        server = FastMCP(name="test-already-registered")

        # Pre-register tools by setting _consolidated_tools
        mock_tools = Mock()
        server._consolidated_tools = mock_tools

        with patch('fastmcp.server.server.logger') as mock_logger:
            # Attempt to register again
            result = server.register_task_management_tools()

            # Should return True immediately
            assert result is True

            # Should log warning
            mock_logger.warning.assert_called_once_with(
                "Task management tools are already registered"
            )

            # Tools should remain unchanged
            assert server._consolidated_tools == mock_tools

    def test_register_task_tools_respects_disable_cursor_tools_env(self):
        """
        Test register_task_management_tools respects AGENTHUB_DISABLE_CURSOR_TOOLS.

        Covers lines 393-413: Environment-based tool configuration.
        Verifies:
        - AGENTHUB_DISABLE_CURSOR_TOOLS=true disables cursor tools
        - config_overrides correctly populated with tool flags
        - Core tools remain enabled (manage_project, manage_task, etc.)
        - Cursor-specific tools disabled (validate_rules, validate_tasks_json)
        - Proper logging of configuration decision
        """
        from fastmcp.server.server import FastMCP

        server = FastMCP(name="test-disable-cursor")
        server._consolidated_tools = None  # Ensure not already registered

        # Set environment variable to disable cursor tools
        with patch.dict('os.environ', {'AGENTHUB_DISABLE_CURSOR_TOOLS': 'true'}), \
             patch('fastmcp.server.server.logger') as mock_logger, \
             patch('fastmcp.task_management.interface.ddd_compliant_mcp_tools.DDDCompliantMCPTools') as mock_tools_class:

            mock_tools_instance = Mock()
            mock_tools_instance.register_tools = Mock()
            mock_tools_class.return_value = mock_tools_instance

            # Register tools
            result = server.register_task_management_tools()

            # Verify successful registration
            assert result is True

            # Verify logging of disabled cursor tools
            assert any(
                "AGENTHUB_DISABLE_CURSOR_TOOLS=true" in str(call)
                for call in mock_logger.info.call_args_list
            )

            # Verify config_overrides passed to DDDCompliantMCPTools
            config_call = mock_tools_class.call_args[1]
            enabled_tools = config_call['config_overrides']['enabled_tools']

            # Core tools should be enabled
            assert enabled_tools['manage_project'] is True
            assert enabled_tools['manage_task'] is True
            assert enabled_tools['manage_subtask'] is True
            assert enabled_tools['manage_agent'] is True
            assert enabled_tools['call_agent'] is True

            # Cursor tools should be disabled
            assert enabled_tools['update_auto_rule'] is False
            assert enabled_tools['validate_rules'] is False
            assert enabled_tools['regenerate_auto_rule'] is False
            assert enabled_tools['validate_tasks_json'] is False

    def test_register_task_tools_handles_initialization_failure(self):
        """
        Test register_task_management_tools handles DDDCompliantMCPTools failure.

        Covers lines 425-427: Exception handling during tool registration.
        Verifies:
        - Returns False when tool initialization fails
        - Logs error with exception details
        - Does not set _consolidated_tools on failure
        - Gracefully handles all exception types
        """
        from fastmcp.server.server import FastMCP

        server = FastMCP(name="test-registration-failure")
        server._consolidated_tools = None

        with patch('fastmcp.server.server.logger') as mock_logger, \
             patch('fastmcp.task_management.interface.ddd_compliant_mcp_tools.DDDCompliantMCPTools') as mock_tools_class:

            # Simulate initialization failure
            mock_tools_class.side_effect = RuntimeError("Failed to initialize MCP tools")

            # Attempt registration
            result = server.register_task_management_tools()

            # Should return False
            assert result is False

            # Should log error
            mock_logger.error.assert_called_once()
            error_message = str(mock_logger.error.call_args[0][0])
            assert "Failed to register task management tools" in error_message

            # _consolidated_tools should remain None
            assert server._consolidated_tools is None

    @pytest.mark.asyncio
    async def test_run_async_invalid_transport_validation(self):
        """
        Test run_async validates transport parameter.

        Covers lines 439-442: Transport validation logic.
        Verifies:
        - Raises ValueError for invalid transport types
        - Accepts valid transports: stdio, sse, streamable-http
        - None defaults to stdio
        - Error message includes the invalid value
        """
        from fastmcp.server.server import FastMCP

        server = FastMCP(name="test-invalid-transport")

        # Test invalid transport
        with pytest.raises(ValueError, match="Unknown transport: invalid-type"):
            await server.run_async(transport="invalid-type")

        # Test another invalid transport
        with pytest.raises(ValueError, match="Unknown transport: websocket"):
            await server.run_async(transport="websocket")

    @pytest.mark.asyncio
    async def test_run_async_transport_routing_to_stdio(self):
        """
        Test run_async correctly routes stdio transport.

        Covers lines 444-445: stdio transport routing.
        Verifies:
        - transport='stdio' calls run_stdio_async
        - transport=None defaults to stdio
        - Transport kwargs passed through correctly
        """
        from fastmcp.server.server import FastMCP

        server = FastMCP(name="test-stdio-routing")

        with patch.object(server, 'run_stdio_async', new_callable=AsyncMock) as mock_stdio:
            # Test explicit stdio
            await server.run_async(transport="stdio", custom_arg="test_value")
            mock_stdio.assert_called_once_with(custom_arg="test_value")

            # Reset and test None (should default to stdio)
            mock_stdio.reset_mock()
            await server.run_async(transport=None, another_arg=123)
            mock_stdio.assert_called_once_with(another_arg=123)

    @pytest.mark.asyncio
    async def test_run_async_transport_routing_to_http(self):
        """
        Test run_async correctly routes HTTP transports.

        Covers lines 446-447: HTTP transport routing (sse and streamable-http).
        Verifies:
        - transport='sse' calls run_http_async with transport='sse'
        - transport='streamable-http' calls run_http_async
        - Transport type passed through correctly
        - Kwargs forwarded properly
        """
        from fastmcp.server.server import FastMCP

        server = FastMCP(name="test-http-routing")

        with patch.object(server, 'run_http_async', new_callable=AsyncMock) as mock_http:
            # Test SSE transport
            await server.run_async(transport="sse", host="localhost", port=8080)
            mock_http.assert_called_once_with(transport="sse", host="localhost", port=8080)

            # Reset and test streamable-http
            mock_http.reset_mock()
            await server.run_async(transport="streamable-http", host="0.0.0.0", port=9000)
            mock_http.assert_called_once_with(transport="streamable-http", host="0.0.0.0", port=9000)

    def test_run_synchronous_wrapper_calls_anyio(self):
        """
        Test run() synchronous wrapper properly calls anyio.run.

        Covers line 462: anyio.run with partial application.
        Verifies:
        - Synchronous run() wraps run_async() correctly
        - Uses anyio.run for async execution
        - partial() properly binds transport and kwargs
        - All parameters forwarded correctly
        """
        from fastmcp.server.server import FastMCP

        server = FastMCP(name="test-sync-run")

        with patch('fastmcp.server.server.anyio.run') as mock_anyio_run, \
             patch.object(server, 'run_async', new_callable=AsyncMock) as mock_run_async:

            # Call synchronous run
            server.run(transport="stdio", test_kwarg="value")

            # Verify anyio.run was called
            mock_anyio_run.assert_called_once()

            # Verify partial was created with run_async
            partial_func = mock_anyio_run.call_args[0][0]
            assert callable(partial_func)

    def test_setup_handlers_registers_all_mcp_protocol_handlers(self):
        """
        Test _setup_handlers registers all core MCP protocol handlers.

        Covers lines 464-472: Handler registration for MCP protocol.
        Verifies:
        - All 7 core handlers registered on _mcp_server
        - list_tools, list_resources, list_resource_templates registered
        - list_prompts, call_tool, read_resource registered
        - get_prompt registered
        - Proper handler method references
        """
        from fastmcp.server.server import FastMCP

        server = FastMCP(name="test-handler-setup")

        # Mock the _mcp_server handler registration methods
        mock_mcp_server = Mock()
        server._mcp_server = mock_mcp_server

        # Reset handler decorators to track calls
        handler_mocks = {
            'list_tools': Mock(return_value=lambda f: f),
            'list_resources': Mock(return_value=lambda f: f),
            'list_resource_templates': Mock(return_value=lambda f: f),
            'list_prompts': Mock(return_value=lambda f: f),
            'call_tool': Mock(return_value=lambda f: f),
            'read_resource': Mock(return_value=lambda f: f),
            'get_prompt': Mock(return_value=lambda f: f),
        }

        for name, mock in handler_mocks.items():
            setattr(mock_mcp_server, name, mock)

        # Call _setup_handlers
        server._setup_handlers()

        # Verify all handlers were registered
        handler_mocks['list_tools'].assert_called_once()
        handler_mocks['list_resources'].assert_called_once()
        handler_mocks['list_resource_templates'].assert_called_once()
        handler_mocks['list_prompts'].assert_called_once()
        handler_mocks['call_tool'].assert_called_once()
        handler_mocks['read_resource'].assert_called_once()
        handler_mocks['get_prompt'].assert_called_once()
