"""
Server Lifecycle Error Handling Tests

Production-ready tests for server startup failures, shutdown errors,
lifecycle exceptions, and async error propagation focusing on real-world scenarios.

Target Coverage: Lines 767-785, 793-803, 810-838, 848-858, 867-885
Focus: Resilient server lifecycle error handling

Test Categories:
1. Server startup exceptions and error propagation
2. Transport configuration failures
3. Graceful shutdown handling
4. Configuration and environment errors
"""

import pytest
import os
import sys
import logging
from unittest.mock import Mock, patch, MagicMock, call
from io import StringIO
from contextlib import contextmanager


# Test markers
pytestmark = [
    pytest.mark.integration,
    pytest.mark.unit  # Skip database setup since we're testing error handling
]


@contextmanager
def capture_logs():
    """Capture log output for verification"""
    log_capture = StringIO()
    handler = logging.StreamHandler(log_capture)
    handler.setLevel(logging.DEBUG)

    root_logger = logging.getLogger()
    original_level = root_logger.level
    root_logger.setLevel(logging.DEBUG)
    root_logger.addHandler(handler)

    fastmcp_logger = logging.getLogger('fastmcp')
    fastmcp_logger.addHandler(handler)

    try:
        yield log_capture
    finally:
        root_logger.removeHandler(handler)
        fastmcp_logger.removeHandler(handler)
        root_logger.setLevel(original_level)


class TestServerStartupExceptions:
    """Test exception handling during server.run() calls"""

    def test_server_run_with_port_binding_error(self, monkeypatch):
        """Test server.run() exception caught and logged (lines 796-820)"""
        monkeypatch.setenv('DATABASE_PATH', ':memory:')
        monkeypatch.setenv('FASTMCP_TRANSPORT', 'streamable-http')
        monkeypatch.setenv('FASTMCP_PORT', '8000')

        with patch('fastmcp.task_management.infrastructure.database.init_database.init_database'), \
             patch('fastmcp.task_management.infrastructure.database.schema_validator.validate_schema_on_startup'), \
             patch('fastmcp.task_management.infrastructure.database.database_config.get_db_config') as mock_get_db, \
             patch('asyncio.run') as mock_async, \
             patch('fastmcp.server.server.FastMCP') as mock_fastmcp, \
             patch('fastmcp.utilities.logging.setup_comprehensive_logging'), \
             patch('fastmcp.task_management.interface.ddd_compliant_mcp_tools.DDDCompliantMCPTools'), \
             patch('fastmcp.config.ToolRegistry') as mock_registry, \
             patch('fastmcp.config.create_authentication_tools'), \
             patch('fastmcp.auth.AuthMiddleware'), \
             patch('fastmcp.connection_management.interface.ddd_compliant_connection_tools.register_ddd_connection_tools'), \
             patch('fastmcp.websocket.fastapi_integration.setup_websocket_integration'), \
             patch('fastmcp.database_migrations.run_startup_migrations') as mock_migrations, \
             patch('fastmcp.task_management.application.services.statistics_initializer.StatisticsInitializer'), \
             patch('fastmcp.task_management.infrastructure.events.initialize_event_handlers') as mock_events, \
             patch('starlette.middleware.Middleware'), \
             patch('fastmcp.config.cors_factory.cors_factory.get_allowed_origins') as mock_cors, \
             capture_logs() as log_capture:

            mock_db_config = Mock()
            mock_db_config.engine = Mock()
            mock_get_db.return_value = mock_db_config
            mock_async.return_value = True
            mock_migrations.return_value = True
            mock_events.return_value = True
            mock_cors.return_value = ["http://localhost:3800"]

            mock_server = Mock()
            mock_server.name = "agenthub"
            mock_server.http_app.return_value = Mock()
            # Simulate port binding failure
            mock_server.run.side_effect = OSError("[Errno 98] Address already in use")
            mock_fastmcp.return_value = mock_server

            mock_tool_reg = Mock()
            mock_tool_reg.mount_tools_to_server.return_value = {
                'mounted_tools': 1,
                'disabled_tools': 0,
                'dependency_failures': 0
            }
            mock_registry.return_value = mock_tool_reg

            from fastmcp.server.mcp_entry_point import main

            # Should exit with code 1
            with pytest.raises(SystemExit) as exc_info:
                main()

            assert exc_info.value.code == 1

            # Verify error was logged (lines 817-819)
            logs = log_capture.getvalue()
            assert "Server error" in logs
            assert "Address already in use" in logs

    def test_server_run_with_permission_error(self, monkeypatch):
        """Test server.run() handles permission denied errors"""
        monkeypatch.setenv('DATABASE_PATH', ':memory:')
        monkeypatch.setenv('FASTMCP_TRANSPORT', 'streamable-http')
        monkeypatch.setenv('FASTMCP_PORT', '80')  # Privileged port

        with patch('fastmcp.task_management.infrastructure.database.init_database.init_database'), \
             patch('fastmcp.task_management.infrastructure.database.schema_validator.validate_schema_on_startup'), \
             patch('fastmcp.task_management.infrastructure.database.database_config.get_db_config') as mock_get_db, \
             patch('asyncio.run') as mock_async, \
             patch('fastmcp.server.server.FastMCP') as mock_fastmcp, \
             patch('fastmcp.utilities.logging.setup_comprehensive_logging'), \
             patch('fastmcp.task_management.interface.ddd_compliant_mcp_tools.DDDCompliantMCPTools'), \
             patch('fastmcp.config.ToolRegistry') as mock_registry, \
             patch('fastmcp.config.create_authentication_tools'), \
             patch('fastmcp.auth.AuthMiddleware'), \
             patch('fastmcp.connection_management.interface.ddd_compliant_connection_tools.register_ddd_connection_tools'), \
             patch('fastmcp.websocket.fastapi_integration.setup_websocket_integration'), \
             patch('fastmcp.database_migrations.run_startup_migrations') as mock_migrations, \
             patch('fastmcp.task_management.application.services.statistics_initializer.StatisticsInitializer'), \
             patch('fastmcp.task_management.infrastructure.events.initialize_event_handlers') as mock_events, \
             patch('starlette.middleware.Middleware'), \
             patch('fastmcp.config.cors_factory.cors_factory.get_allowed_origins') as mock_cors, \
             capture_logs() as log_capture:

            mock_db_config = Mock()
            mock_db_config.engine = Mock()
            mock_get_db.return_value = mock_db_config
            mock_async.return_value = True
            mock_migrations.return_value = True
            mock_events.return_value = True
            mock_cors.return_value = ["http://localhost:3800"]

            mock_server = Mock()
            mock_server.name = "agenthub"
            mock_server.http_app.return_value = Mock()
            mock_server.run.side_effect = PermissionError("Permission denied to bind to port 80")
            mock_fastmcp.return_value = mock_server

            mock_tool_reg = Mock()
            mock_tool_reg.mount_tools_to_server.return_value = {
                'mounted_tools': 1,
                'disabled_tools': 0,
                'dependency_failures': 0
            }
            mock_registry.return_value = mock_tool_reg

            from fastmcp.server.mcp_entry_point import main

            with pytest.raises(SystemExit) as exc_info:
                main()

            assert exc_info.value.code == 1

            logs = log_capture.getvalue()
            assert "Server error" in logs
            assert "Permission denied" in logs


class TestGracefulShutdown:
    """Test graceful shutdown scenarios (lines 814-820)"""

    def test_keyboard_interrupt_graceful_shutdown(self, monkeypatch):
        """Test KeyboardInterrupt is handled gracefully (line 814-815)"""
        monkeypatch.setenv('DATABASE_PATH', ':memory:')
        monkeypatch.setenv('FASTMCP_TRANSPORT', 'streamable-http')

        with patch('fastmcp.task_management.infrastructure.database.init_database.init_database'), \
             patch('fastmcp.task_management.infrastructure.database.schema_validator.validate_schema_on_startup'), \
             patch('fastmcp.task_management.infrastructure.database.database_config.get_db_config') as mock_get_db, \
             patch('asyncio.run') as mock_async, \
             patch('fastmcp.server.server.FastMCP') as mock_fastmcp, \
             patch('fastmcp.utilities.logging.setup_comprehensive_logging'), \
             patch('fastmcp.task_management.interface.ddd_compliant_mcp_tools.DDDCompliantMCPTools'), \
             patch('fastmcp.config.ToolRegistry') as mock_registry, \
             patch('fastmcp.config.create_authentication_tools'), \
             patch('fastmcp.auth.AuthMiddleware'), \
             patch('fastmcp.connection_management.interface.ddd_compliant_connection_tools.register_ddd_connection_tools'), \
             patch('fastmcp.websocket.fastapi_integration.setup_websocket_integration'), \
             patch('fastmcp.database_migrations.run_startup_migrations') as mock_migrations, \
             patch('fastmcp.task_management.application.services.statistics_initializer.StatisticsInitializer'), \
             patch('fastmcp.task_management.infrastructure.events.initialize_event_handlers') as mock_events, \
             patch('starlette.middleware.Middleware'), \
             patch('fastmcp.config.cors_factory.cors_factory.get_allowed_origins') as mock_cors, \
             capture_logs() as log_capture:

            mock_db_config = Mock()
            mock_db_config.engine = Mock()
            mock_get_db.return_value = mock_db_config
            mock_async.return_value = True
            mock_migrations.return_value = True
            mock_events.return_value = True
            mock_cors.return_value = ["http://localhost:3800"]

            mock_server = Mock()
            mock_server.name = "agenthub"
            mock_server.http_app.return_value = Mock()
            # Simulate user interruption
            mock_server.run.side_effect = KeyboardInterrupt()
            mock_fastmcp.return_value = mock_server

            mock_tool_reg = Mock()
            mock_tool_reg.mount_tools_to_server.return_value = {
                'mounted_tools': 1,
                'disabled_tools': 0,
                'dependency_failures': 0
            }
            mock_registry.return_value = mock_tool_reg

            from fastmcp.server.mcp_entry_point import main

            # Should exit gracefully without error code
            main()

            # Verify graceful shutdown message
            logs = log_capture.getvalue()
            assert "Server stopped by user" in logs


class TestTransportConfiguration:
    """Test transport mode configuration and failures (lines 793-812)"""

    def test_stdio_transport_successful_run(self, monkeypatch):
        """Test stdio transport mode executes successfully (lines 808-812)"""
        monkeypatch.setenv('DATABASE_PATH', ':memory:')
        monkeypatch.setenv('FASTMCP_TRANSPORT', 'stdio')

        with patch('fastmcp.task_management.infrastructure.database.init_database.init_database'), \
             patch('fastmcp.task_management.infrastructure.database.schema_validator.validate_schema_on_startup'), \
             patch('fastmcp.task_management.infrastructure.database.database_config.get_db_config') as mock_get_db, \
             patch('asyncio.run') as mock_async, \
             patch('fastmcp.server.server.FastMCP') as mock_fastmcp, \
             patch('fastmcp.utilities.logging.setup_comprehensive_logging'), \
             patch('fastmcp.task_management.interface.ddd_compliant_mcp_tools.DDDCompliantMCPTools'), \
             patch('fastmcp.config.ToolRegistry') as mock_registry, \
             patch('fastmcp.config.create_authentication_tools'), \
             patch('fastmcp.auth.AuthMiddleware'), \
             patch('fastmcp.connection_management.interface.ddd_compliant_connection_tools.register_ddd_connection_tools'), \
             patch('fastmcp.websocket.fastapi_integration.setup_websocket_integration'), \
             patch('fastmcp.database_migrations.run_startup_migrations') as mock_migrations, \
             patch('fastmcp.task_management.application.services.statistics_initializer.StatisticsInitializer'), \
             patch('fastmcp.task_management.infrastructure.events.initialize_event_handlers') as mock_events, \
             capture_logs() as log_capture:

            mock_db_config = Mock()
            mock_db_config.engine = Mock()
            mock_get_db.return_value = mock_db_config
            mock_async.return_value = True
            mock_migrations.return_value = True
            mock_events.return_value = True

            mock_server = Mock()
            mock_server.name = "agenthub"
            mock_server.http_app.return_value = Mock()
            # Simulate successful stdio mode
            mock_server.run.side_effect = SystemExit(0)
            mock_fastmcp.return_value = mock_server

            mock_tool_reg = Mock()
            mock_tool_reg.mount_tools_to_server.return_value = {
                'mounted_tools': 1,
                'disabled_tools': 0,
                'dependency_failures': 0
            }
            mock_registry.return_value = mock_tool_reg

            from fastmcp.server.mcp_entry_point import main

            with pytest.raises(SystemExit) as exc_info:
                main()

            # Verify stdio mode was used (lines 809-812)
            logs = log_capture.getvalue()
            assert "stdio mode" in logs
            # Verify server.run was called with correct transport
            mock_server.run.assert_called_once_with(transport="stdio")

    def test_http_transport_with_full_configuration(self, monkeypatch):
        """Test HTTP transport with complete configuration (lines 796-806)"""
        monkeypatch.setenv('DATABASE_PATH', ':memory:')
        monkeypatch.setenv('FASTMCP_TRANSPORT', 'streamable-http')
        monkeypatch.setenv('FASTMCP_HOST', '127.0.0.1')
        monkeypatch.setenv('FASTMCP_PORT', '9000')
        monkeypatch.setenv('FASTMCP_LOG_LEVEL', 'DEBUG')

        with patch('fastmcp.task_management.infrastructure.database.init_database.init_database'), \
             patch('fastmcp.task_management.infrastructure.database.schema_validator.validate_schema_on_startup'), \
             patch('fastmcp.task_management.infrastructure.database.database_config.get_db_config') as mock_get_db, \
             patch('asyncio.run') as mock_async, \
             patch('fastmcp.server.server.FastMCP') as mock_fastmcp, \
             patch('fastmcp.utilities.logging.setup_comprehensive_logging'), \
             patch('fastmcp.task_management.interface.ddd_compliant_mcp_tools.DDDCompliantMCPTools'), \
             patch('fastmcp.config.ToolRegistry') as mock_registry, \
             patch('fastmcp.config.create_authentication_tools'), \
             patch('fastmcp.auth.AuthMiddleware'), \
             patch('fastmcp.connection_management.interface.ddd_compliant_connection_tools.register_ddd_connection_tools'), \
             patch('fastmcp.websocket.fastapi_integration.setup_websocket_integration'), \
             patch('fastmcp.database_migrations.run_startup_migrations') as mock_migrations, \
             patch('fastmcp.task_management.application.services.statistics_initializer.StatisticsInitializer'), \
             patch('fastmcp.task_management.infrastructure.events.initialize_event_handlers') as mock_events, \
             patch('starlette.middleware.Middleware') as mock_middleware, \
             patch('fastmcp.config.cors_factory.cors_factory.get_allowed_origins') as mock_cors, \
             capture_logs() as log_capture:

            mock_db_config = Mock()
            mock_db_config.engine = Mock()
            mock_get_db.return_value = mock_db_config
            mock_async.return_value = True
            mock_migrations.return_value = True
            mock_events.return_value = True
            mock_cors.return_value = ["http://localhost:3800", "http://localhost:3000"]

            mock_server = Mock()
            mock_server.name = "agenthub"
            mock_server.http_app.return_value = Mock()
            mock_server.run.side_effect = SystemExit(0)
            mock_fastmcp.return_value = mock_server

            mock_tool_reg = Mock()
            mock_tool_reg.mount_tools_to_server.return_value = {
                'mounted_tools': 1,
                'disabled_tools': 0,
                'dependency_failures': 0
            }
            mock_registry.return_value = mock_tool_reg

            from fastmcp.server.mcp_entry_point import main

            with pytest.raises(SystemExit):
                main()

            # Verify HTTP configuration (lines 796-806)
            logs = log_capture.getvalue()
            assert "streamable-http" in logs
            assert "127.0.0.1:9000" in logs
            assert "CORS origins configured" in logs

            # Verify server.run called with correct parameters
            call_args = mock_server.run.call_args
            assert call_args[1]['transport'] == 'streamable-http'
            assert call_args[1]['host'] == '127.0.0.1'
            assert call_args[1]['port'] == 9000
            assert call_args[1]['log_level'] == 'DEBUG'
            assert 'middleware' in call_args[1]
            assert 'cors_origins' in call_args[1]
