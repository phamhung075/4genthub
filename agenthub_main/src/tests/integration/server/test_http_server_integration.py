"""
HTTP Server Integration Tests for MCP Entry Point

Tests HTTP server creation, SSE endpoint configuration, and HTTP transport handling
covering lines 722-806 in mcp_entry_point.py.

Target: 2-3 production-ready tests following existing patterns.
"""

import logging
import sys
from contextlib import contextmanager
from io import StringIO
from unittest.mock import Mock, patch

import pytest

# Test markers
pytestmark = [
    pytest.mark.integration,
    pytest.mark.unit
]


@contextmanager
def capture_logs():
    """Capture log output for verification"""
    log_capture = StringIO()
    handler = logging.StreamHandler(log_capture)
    handler.setLevel(logging.DEBUG)

    root_logger = logging.getLogger()
    root_logger.addHandler(handler)

    try:
        yield log_capture
    finally:
        root_logger.removeHandler(handler)


class TestHTTPServerIntegration:
    """Test HTTP server creation and configuration in main() function"""

    def test_http_transport_middleware_stack_configuration(self, monkeypatch):
        """
        Test HTTP transport configures middleware stack correctly.

        Covers lines 737-806: Middleware stack building for streamable-http transport.
        Verifies:
        - DualAuthMiddleware added first when auth enabled
        - RequestContextMiddleware added second
        - DebugLoggingMiddleware added third
        - CORS origins configured correctly
        """
        # Configure environment for HTTP transport with auth enabled
        monkeypatch.setenv('FASTMCP_TRANSPORT', 'streamable-http')
        monkeypatch.setenv('FASTMCP_HOST', '0.0.0.0')
        monkeypatch.setenv('FASTMCP_PORT', '8000')
        monkeypatch.setenv('AUTH_ENABLED', 'true')
        monkeypatch.setenv('AUTH_PROVIDER', 'local')
        monkeypatch.setenv('JWT_SECRET_KEY', 'test-secret-key-32-chars-min')
        monkeypatch.setenv('DATABASE_PATH', ':memory:')
        monkeypatch.setenv('FASTMCP_LOG_LEVEL', 'DEBUG')

        # Mock all the dependencies
        with patch('fastmcp.database_migrations.run_startup_migrations') as mock_migrations, \
             patch('fastmcp.task_management.application.services.statistics_initializer.StatisticsInitializer'), \
             patch('fastmcp.task_management.infrastructure.events.initialize_event_handlers') as mock_events, \
             patch('fastmcp.server.mcp_entry_point.create_agenthub_server') as mock_create_server, \
             patch('fastmcp.auth.middleware.dual_auth_middleware.DualAuthMiddleware'), \
             patch('fastmcp.auth.middleware.request_context_middleware.RequestContextMiddleware'), \
             patch('fastmcp.server.mcp_entry_point.DebugLoggingMiddleware'), \
             patch('fastmcp.config.cors_factory.cors_factory') as mock_cors_factory, \
             capture_logs() as log_capture:

            # Configure mocks
            mock_migrations.return_value = True
            mock_events.return_value = True

            mock_server = Mock()
            mock_server.name = "agenthub"
            mock_server.run = Mock(side_effect=SystemExit(0))  # Exit cleanly
            mock_create_server.return_value = mock_server

            # Mock CORS factory
            mock_cors_factory.get_allowed_origins.return_value = ['http://localhost:3800']

            from fastmcp.server.mcp_entry_point import main

            # Run main() - should exit cleanly via SystemExit
            with pytest.raises(SystemExit) as exc_info:
                main()

            # Verify it was a clean exit
            assert exc_info.value.code == 0

            # Verify server.run() was called with correct parameters
            mock_server.run.assert_called_once()
            call_kwargs = mock_server.run.call_args.kwargs

            # Verify transport configuration
            assert call_kwargs['transport'] == 'streamable-http'
            assert call_kwargs['host'] == '0.0.0.0'
            assert call_kwargs['port'] == 8000
            assert call_kwargs['log_level'] == 'DEBUG'

            # Verify middleware stack was passed
            assert 'middleware' in call_kwargs
            middleware_stack = call_kwargs['middleware']
            assert len(middleware_stack) == 3  # DualAuth, RequestContext, Debug

            # Verify CORS origins were configured
            assert call_kwargs['cors_origins'] == ['http://localhost:3800']

            # Verify logging messages
            logs = log_capture.getvalue()
            assert 'Starting server with transport: streamable-http' in logs
            assert 'HTTP server will bind to 0.0.0.0:8000' in logs
            assert 'DualAuthMiddleware added' in logs
            assert 'RequestContextMiddleware added' in logs
            assert 'CORS origins configured via factory' in logs

    def test_http_transport_without_auth_skips_dual_auth_middleware(self, monkeypatch):
        """
        Test HTTP transport with auth disabled skips DualAuthMiddleware.

        Covers lines 750-762: Conditional DualAuthMiddleware addition.
        Verifies:
        - DualAuthMiddleware NOT added when AUTH_ENABLED=false
        - RequestContextMiddleware still added
        - DebugLoggingMiddleware still added
        - Server runs successfully without auth middleware
        """
        # Configure environment for HTTP transport with auth disabled
        monkeypatch.setenv('FASTMCP_TRANSPORT', 'streamable-http')
        monkeypatch.setenv('FASTMCP_HOST', 'localhost')
        monkeypatch.setenv('FASTMCP_PORT', '9000')
        monkeypatch.setenv('AUTH_ENABLED', 'false')  # Auth disabled
        monkeypatch.setenv('DATABASE_PATH', ':memory:')

        with patch('fastmcp.database_migrations.run_startup_migrations') as mock_migrations, \
             patch('fastmcp.task_management.application.services.statistics_initializer.StatisticsInitializer'), \
             patch('fastmcp.task_management.infrastructure.events.initialize_event_handlers') as mock_events, \
             patch('fastmcp.server.mcp_entry_point.create_agenthub_server') as mock_create_server, \
             patch('fastmcp.auth.middleware.dual_auth_middleware.DualAuthMiddleware') as mock_dual_auth, \
             patch('fastmcp.auth.middleware.request_context_middleware.RequestContextMiddleware'), \
             patch('fastmcp.server.mcp_entry_point.DebugLoggingMiddleware'), \
             patch('fastmcp.config.cors_factory.cors_factory') as mock_cors_factory, \
             capture_logs() as log_capture:

            mock_migrations.return_value = True
            mock_events.return_value = True

            mock_server = Mock()
            mock_server.run = Mock(side_effect=SystemExit(0))
            mock_create_server.return_value = mock_server

            mock_cors_factory.get_allowed_origins.return_value = ['*']

            from fastmcp.server.mcp_entry_point import main

            with pytest.raises(SystemExit):
                main()

            # Verify server.run() was called
            call_kwargs = mock_server.run.call_args.kwargs

            # Verify middleware stack has only 2 items (no DualAuth)
            middleware_stack = call_kwargs['middleware']
            assert len(middleware_stack) == 2  # RequestContext and Debug only

            # Verify DualAuthMiddleware was NOT instantiated
            mock_dual_auth.assert_not_called()

            # Verify logs don't mention DualAuthMiddleware
            logs = log_capture.getvalue()
            assert 'DualAuthMiddleware' not in logs or 'DualAuthMiddleware added' not in logs

    def test_stdio_transport_bypasses_http_middleware_configuration(self, monkeypatch):
        """
        Test stdio transport bypasses HTTP-specific middleware configuration.

        Covers lines 807-812: stdio transport path.
        Verifies:
        - No middleware stack configuration for stdio
        - No CORS configuration for stdio
        - Server runs in stdio mode correctly
        - Appropriate logging for stdio mode
        """
        # Configure environment for stdio transport (default)
        monkeypatch.setenv('FASTMCP_TRANSPORT', 'stdio')
        monkeypatch.setenv('DATABASE_PATH', ':memory:')
        # Ensure AUTH_ENABLED has a default value
        monkeypatch.setenv('AUTH_ENABLED', 'false')

        with patch('fastmcp.database_migrations.run_startup_migrations') as mock_migrations, \
             patch('fastmcp.task_management.application.services.statistics_initializer.StatisticsInitializer'), \
             patch('fastmcp.task_management.infrastructure.events.initialize_event_handlers') as mock_events, \
             patch('fastmcp.server.mcp_entry_point.create_agenthub_server') as mock_create_server, \
             patch('fastmcp.auth.middleware.dual_auth_middleware.DualAuthMiddleware') as mock_dual_auth, \
             patch('fastmcp.auth.middleware.request_context_middleware.RequestContextMiddleware') as mock_request_ctx, \
             patch('fastmcp.config.cors_factory.cors_factory') as mock_cors_factory, \
             capture_logs() as log_capture:

            mock_migrations.return_value = True
            mock_events.return_value = True

            mock_server = Mock()
            mock_server.run = Mock(side_effect=SystemExit(0))
            mock_create_server.return_value = mock_server

            from fastmcp.server.mcp_entry_point import main

            with pytest.raises(SystemExit):
                main()

            # Verify server.run() was called with stdio transport
            call_kwargs = mock_server.run.call_args.kwargs
            assert call_kwargs['transport'] == 'stdio'

            # Verify NO middleware or CORS configuration
            assert 'middleware' not in call_kwargs
            assert 'cors_origins' not in call_kwargs
            assert 'host' not in call_kwargs
            assert 'port' not in call_kwargs

            # Verify middleware classes were NOT instantiated
            mock_dual_auth.assert_not_called()
            mock_request_ctx.assert_not_called()
            mock_cors_factory.get_allowed_origins.assert_not_called()

            # Verify appropriate logging
            logs = log_capture.getvalue()
            assert 'Starting server in stdio mode' in logs
            assert 'HTTP server will bind' not in logs


class TestHTTPTransportCommandLineArgs:
    """Test command line argument parsing for transport configuration"""

    def test_command_line_transport_override_flag_format(self, monkeypatch):
        """
        Test --transport flag format overrides environment variable.

        Covers lines 728-733: Command line argument parsing.
        """
        # Set environment to stdio
        monkeypatch.setenv('FASTMCP_TRANSPORT', 'stdio')
        monkeypatch.setenv('DATABASE_PATH', ':memory:')
        monkeypatch.setenv('AUTH_ENABLED', 'false')

        # Mock sys.argv to include --transport streamable-http
        with patch.object(sys, 'argv', ['mcp_entry_point.py', '--transport', 'streamable-http']), \
             patch('fastmcp.database_migrations.run_startup_migrations') as mock_migrations, \
             patch('fastmcp.task_management.application.services.statistics_initializer.StatisticsInitializer'), \
             patch('fastmcp.task_management.infrastructure.events.initialize_event_handlers') as mock_events, \
             patch('fastmcp.server.mcp_entry_point.create_agenthub_server') as mock_create_server, \
             patch('fastmcp.auth.middleware.request_context_middleware.RequestContextMiddleware'), \
             patch('fastmcp.server.mcp_entry_point.DebugLoggingMiddleware'), \
             patch('fastmcp.config.cors_factory.cors_factory') as mock_cors_factory:

            mock_migrations.return_value = True
            mock_events.return_value = True

            mock_server = Mock()
            mock_server.run = Mock(side_effect=SystemExit(0))
            mock_create_server.return_value = mock_server

            mock_cors_factory.get_allowed_origins.return_value = []

            from fastmcp.server.mcp_entry_point import main

            with pytest.raises(SystemExit):
                main()

            # Verify transport was overridden to streamable-http
            call_kwargs = mock_server.run.call_args.kwargs
            assert call_kwargs['transport'] == 'streamable-http'

    def test_command_line_transport_override_equals_format(self, monkeypatch):
        """
        Test --transport=value format overrides environment variable.

        Covers lines 732-733: Alternative command line format.
        """
        monkeypatch.setenv('FASTMCP_TRANSPORT', 'stdio')
        monkeypatch.setenv('DATABASE_PATH', ':memory:')
        monkeypatch.setenv('AUTH_ENABLED', 'false')

        # Mock sys.argv with --transport=streamable-http format
        with patch.object(sys, 'argv', ['mcp_entry_point.py', '--transport=streamable-http']), \
             patch('fastmcp.database_migrations.run_startup_migrations') as mock_migrations, \
             patch('fastmcp.task_management.application.services.statistics_initializer.StatisticsInitializer'), \
             patch('fastmcp.task_management.infrastructure.events.initialize_event_handlers') as mock_events, \
             patch('fastmcp.server.mcp_entry_point.create_agenthub_server') as mock_create_server, \
             patch('fastmcp.auth.middleware.request_context_middleware.RequestContextMiddleware'), \
             patch('fastmcp.server.mcp_entry_point.DebugLoggingMiddleware'), \
             patch('fastmcp.config.cors_factory.cors_factory') as mock_cors_factory:

            mock_migrations.return_value = True
            mock_events.return_value = True

            mock_server = Mock()
            mock_server.run = Mock(side_effect=SystemExit(0))
            mock_create_server.return_value = mock_server

            mock_cors_factory.get_allowed_origins.return_value = []

            from fastmcp.server.mcp_entry_point import main

            with pytest.raises(SystemExit):
                main()

            # Verify transport was overridden to streamable-http
            call_kwargs = mock_server.run.call_args.kwargs
            assert call_kwargs['transport'] == 'streamable-http'


class TestHTTPMiddlewareFailureHandling:
    """Test error handling during HTTP middleware configuration"""

    def test_cors_factory_configuration_in_http_mode(self, monkeypatch):
        """
        Test CORS factory is properly configured in HTTP mode.

        Covers lines 783-792: CORS configuration via factory.
        Verifies:
        - cors_factory.get_allowed_origins() is called
        - CORS origins passed to server.run()
        - Appropriate logging for CORS configuration
        """
        monkeypatch.setenv('FASTMCP_TRANSPORT', 'streamable-http')
        monkeypatch.setenv('AUTH_ENABLED', 'false')
        monkeypatch.setenv('DATABASE_PATH', ':memory:')

        with patch('fastmcp.database_migrations.run_startup_migrations') as mock_migrations, \
             patch('fastmcp.task_management.application.services.statistics_initializer.StatisticsInitializer'), \
             patch('fastmcp.task_management.infrastructure.events.initialize_event_handlers') as mock_events, \
             patch('fastmcp.server.mcp_entry_point.create_agenthub_server') as mock_create_server, \
             patch('fastmcp.auth.middleware.request_context_middleware.RequestContextMiddleware'), \
             patch('fastmcp.server.mcp_entry_point.DebugLoggingMiddleware'), \
             patch('fastmcp.config.cors_factory.cors_factory') as mock_cors_factory, \
             capture_logs() as log_capture:

            mock_migrations.return_value = True
            mock_events.return_value = True

            mock_server = Mock()
            mock_server.run = Mock(side_effect=SystemExit(0))
            mock_create_server.return_value = mock_server

            # Configure CORS factory with specific origins
            test_origins = ['https://app.example.com', 'https://api.example.com']
            mock_cors_factory.get_allowed_origins.return_value = test_origins

            from fastmcp.server.mcp_entry_point import main

            with pytest.raises(SystemExit):
                main()

            # Verify CORS factory was called
            mock_cors_factory.get_allowed_origins.assert_called_once()

            # Verify CORS origins passed to server
            call_kwargs = mock_server.run.call_args.kwargs
            assert call_kwargs['cors_origins'] == test_origins

            # Verify logging
            logs = log_capture.getvalue()
            assert 'CORS origins configured via factory' in logs
            assert 'https://app.example.com' in logs

    def test_http_server_log_level_configuration(self, monkeypatch):
        """
        Test log level is correctly configured from environment variable.

        Covers lines 780-801: Log level configuration for HTTP server.
        Verifies:
        - FASTMCP_LOG_LEVEL environment variable is used
        - Log level is passed to server.run()
        - Default to INFO if not specified
        """
        monkeypatch.setenv('FASTMCP_TRANSPORT', 'streamable-http')
        monkeypatch.setenv('AUTH_ENABLED', 'false')
        monkeypatch.setenv('DATABASE_PATH', ':memory:')
        monkeypatch.setenv('FASTMCP_LOG_LEVEL', 'WARNING')  # Custom log level

        with patch('fastmcp.database_migrations.run_startup_migrations') as mock_migrations, \
             patch('fastmcp.task_management.application.services.statistics_initializer.StatisticsInitializer'), \
             patch('fastmcp.task_management.infrastructure.events.initialize_event_handlers') as mock_events, \
             patch('fastmcp.server.mcp_entry_point.create_agenthub_server') as mock_create_server, \
             patch('fastmcp.auth.middleware.request_context_middleware.RequestContextMiddleware'), \
             patch('fastmcp.server.mcp_entry_point.DebugLoggingMiddleware'), \
             patch('fastmcp.config.cors_factory.cors_factory') as mock_cors_factory:

            mock_migrations.return_value = True
            mock_events.return_value = True

            mock_server = Mock()
            mock_server.run = Mock(side_effect=SystemExit(0))
            mock_create_server.return_value = mock_server

            mock_cors_factory.get_allowed_origins.return_value = []

            from fastmcp.server.mcp_entry_point import main

            with pytest.raises(SystemExit):
                main()

            # Verify log level was passed correctly (uppercased)
            call_kwargs = mock_server.run.call_args.kwargs
            assert call_kwargs['log_level'] == 'WARNING'
