"""
Unit tests for MCP Entry Point error paths and edge cases

Tests covering lines 657-703 in mcp_entry_point.py:
- Error condition handling
- Duplicate handling
- Parameter validation errors
"""

import logging
import os
from unittest.mock import MagicMock, Mock, patch

import pytest

from fastmcp.server.mcp_entry_point import main


class TestMCPEntryPointErrorPaths:
    """Test error paths and edge cases in MCP entry point initialization"""

    @patch('fastmcp.server.mcp_entry_point.create_agenthub_server')
    @patch('fastmcp.task_management.infrastructure.events.initialize_event_handlers')
    @patch('fastmcp.task_management.application.services.statistics_initializer.StatisticsInitializer.initialize')
    @patch('fastmcp.database_migrations.run_startup_migrations')
    def test_database_migration_failure_continues_execution(
        self,
        mock_migrations,
        mock_stats,
        mock_event_handlers,
        mock_create_server
    ):
        """Test that database migration failures log warning but don't stop server startup

        Covers lines 663-673: Migration error handling with non-blocking failure
        """
        # Arrange
        mock_migrations.side_effect = Exception("Database connection failed")
        mock_stats.return_value = None
        mock_event_handlers.return_value = True
        mock_server = MagicMock()
        # Make server.run() raise KeyboardInterrupt to stop the blocking call
        mock_server.run.side_effect = KeyboardInterrupt()
        mock_create_server.return_value = mock_server

        # Setup a mock logger to capture the warning
        with patch('fastmcp.server.mcp_entry_point.logging.getLogger') as mock_get_logger:
            mock_logger = Mock()
            mock_get_logger.return_value = mock_logger

            # Act
            main()  # Will catch KeyboardInterrupt internally

            # Assert
            # Verify migration was attempted
            mock_migrations.assert_called_once()

            # Verify warning was logged
            warning_calls = [
                call for call in mock_logger.warning.call_args_list
                if 'Could not run database migrations' in str(call)
            ]
            assert len(warning_calls) > 0, "Expected warning not logged"

            # Verify subsequent initialization steps still executed
            mock_stats.assert_called_once()
            mock_event_handlers.assert_called_once()
            mock_create_server.assert_called_once()

    @patch('fastmcp.server.mcp_entry_point.create_agenthub_server')
    @patch('fastmcp.task_management.infrastructure.events.initialize_event_handlers')
    @patch('fastmcp.task_management.application.services.statistics_initializer.StatisticsInitializer.initialize')
    @patch('fastmcp.database_migrations.run_startup_migrations')
    def test_statistics_initialization_failure_continues_execution(
        self,
        mock_migrations,
        mock_stats,
        mock_event_handlers,
        mock_create_server,
        caplog
    ):
        """Test that statistics initialization failures log warning but don't stop server

        Covers lines 675-683: Statistics initialization error handling
        """
        # Arrange
        mock_migrations.return_value = True
        mock_stats.side_effect = Exception("Redis connection failed")
        mock_event_handlers.return_value = True
        mock_server = MagicMock()
        mock_server.run.side_effect = KeyboardInterrupt()
        mock_create_server.return_value = mock_server

        with caplog.at_level(logging.WARNING):
            # Act
            main()

            # Assert
            # Verify statistics initialization was attempted
            mock_stats.assert_called_once()

            # Verify warning was logged but execution continued
            assert any(
                "Could not initialize branch statistics tracking" in record.message
                for record in caplog.records
            )

            # Verify subsequent steps still executed
            mock_event_handlers.assert_called_once()
            mock_create_server.assert_called_once()

    @patch('fastmcp.server.mcp_entry_point.create_agenthub_server')
    @patch('fastmcp.task_management.infrastructure.events.initialize_event_handlers')
    @patch('fastmcp.task_management.application.services.statistics_initializer.StatisticsInitializer.initialize')
    @patch('fastmcp.database_migrations.run_startup_migrations')
    def test_event_handler_initialization_false_raises_runtime_error(
        self,
        mock_migrations,
        mock_stats,
        mock_event_handlers,
        mock_create_server,
        caplog
    ):
        """Test that event handler initialization returning False raises RuntimeError

        Covers lines 686-695: Event handler FAIL FAST mode - return False scenario
        Critical path: Event handlers are mandatory, failure must stop server
        """
        # Arrange
        mock_migrations.return_value = True
        mock_stats.return_value = None
        mock_event_handlers.return_value = False  # Initialization failed

        with caplog.at_level(logging.ERROR):
            # Act & Assert
            # The RuntimeError gets caught by main()'s exception handler which calls sys.exit(1)
            with pytest.raises(SystemExit) as exc_info:
                main()

            # Verify exit code is 1 (failure)
            assert exc_info.value.code == 1

            # Verify error was logged
            error_logs = [
                record for record in caplog.records
                if record.levelname == "ERROR"
            ]
            assert any(
                "Domain event handler initialization failed" in record.message
                for record in error_logs
            )
            assert any(
                "SERVER CANNOT START" in record.message
                for record in error_logs
            )

            # Verify server was NOT created (fail fast)
            mock_create_server.assert_not_called()

    @patch('fastmcp.server.mcp_entry_point.create_agenthub_server')
    @patch('fastmcp.task_management.infrastructure.events.initialize_event_handlers')
    @patch('fastmcp.task_management.application.services.statistics_initializer.StatisticsInitializer.initialize')
    @patch('fastmcp.database_migrations.run_startup_migrations')
    def test_event_handler_initialization_exception_raises_runtime_error(
        self,
        mock_migrations,
        mock_stats,
        mock_event_handlers,
        mock_create_server,
        caplog
    ):
        """Test that event handler initialization exception raises RuntimeError with chain

        Covers lines 696-701: Event handler exception handling with FAIL FAST mode
        Critical path: Exception during event handler init must stop server with details
        """
        # Arrange
        mock_migrations.return_value = True
        mock_stats.return_value = None
        original_error = Exception("Event bus configuration invalid")
        mock_event_handlers.side_effect = original_error

        with caplog.at_level(logging.ERROR):
            # Act & Assert
            # The RuntimeError gets caught by main()'s exception handler which calls sys.exit(1)
            with pytest.raises(SystemExit) as exc_info:
                main()

            # Verify exit code is 1 (failure)
            assert exc_info.value.code == 1

            # Verify comprehensive error logging
            error_logs = [
                record for record in caplog.records
                if record.levelname == "ERROR"
            ]
            assert any(
                "CRITICAL: Failed to initialize domain event handlers" in record.message
                for record in error_logs
            )
            assert any(
                "SERVER CANNOT START" in record.message
                for record in error_logs
            )
            assert any(
                "Event handlers are mandatory" in record.message
                for record in error_logs
            )

            # Verify server was NOT created (fail fast)
            mock_create_server.assert_not_called()

    @patch('fastmcp.server.mcp_entry_point.create_agenthub_server')
    @patch('fastmcp.task_management.infrastructure.events.initialize_event_handlers')
    @patch('fastmcp.task_management.application.services.statistics_initializer.StatisticsInitializer.initialize')
    @patch('fastmcp.database_migrations.run_startup_migrations')
    def test_combined_non_critical_failures_with_critical_success(
        self,
        mock_migrations,
        mock_stats,
        mock_event_handlers,
        mock_create_server,
        caplog
    ):
        """Test that multiple non-critical failures don't prevent server start if critical succeeds

        Edge case: Combines lines 663-683 (non-critical) with 686-701 (critical)
        Validates priority: Critical components must work, non-critical can fail
        """
        # Arrange
        mock_migrations.side_effect = Exception("Migration failed")
        mock_stats.side_effect = Exception("Stats failed")
        mock_event_handlers.return_value = True  # Critical component succeeds
        mock_server = MagicMock()
        mock_server.run.side_effect = KeyboardInterrupt()
        mock_create_server.return_value = mock_server

        with caplog.at_level(logging.WARNING):
            # Act
            main()

            # Assert
            # Verify both non-critical failures were logged
            warnings = [
                record for record in caplog.records
                if record.levelname == "WARNING"
            ]
            assert any(
                "Could not run database migrations" in record.message
                for record in warnings
            )
            assert any(
                "Could not initialize branch statistics tracking" in record.message
                for record in warnings
            )

            # Verify server still created (critical component succeeded)
            mock_create_server.assert_called_once()

    @patch('fastmcp.server.mcp_entry_point.create_agenthub_server')
    @patch('fastmcp.task_management.infrastructure.events.initialize_event_handlers')
    @patch('fastmcp.task_management.application.services.statistics_initializer.StatisticsInitializer.initialize')
    @patch('fastmcp.database_migrations.run_startup_migrations')
    def test_logger_initialization_before_error_handling(
        self,
        mock_migrations,
        mock_stats,
        mock_event_handlers,
        mock_create_server,
        caplog
    ):
        """Test that logger is initialized before any error handling occurs

        Covers line 657: Logger initialization at function start
        Validates that all subsequent error messages can be properly logged
        """
        # Arrange
        mock_migrations.side_effect = Exception("Test error")
        mock_stats.return_value = None
        mock_event_handlers.return_value = True
        mock_server = MagicMock()
        mock_server.run.side_effect = KeyboardInterrupt()
        mock_create_server.return_value = mock_server

        with caplog.at_level(logging.DEBUG):
            # Act
            main()

            # Assert
            # Verify logger captured the error (proves logger was initialized first)
            assert len(caplog.records) > 0
            assert any(
                "Could not run database migrations" in record.message
                for record in caplog.records
            )

            # Verify logger name is correct (from line 657)
            assert any(
                record.name == "fastmcp.server.mcp_entry_point"
                for record in caplog.records
            )


class TestMCPEntryPointParameterValidation:
    """Test parameter validation and edge cases"""

    @patch('fastmcp.server.mcp_entry_point.create_agenthub_server')
    @patch('fastmcp.task_management.infrastructure.events.initialize_event_handlers')
    @patch('fastmcp.task_management.application.services.statistics_initializer.StatisticsInitializer.initialize')
    @patch('fastmcp.database_migrations.run_startup_migrations')
    def test_environment_variable_defaults_applied(
        self,
        mock_migrations,
        mock_stats,
        mock_event_handlers,
        mock_create_server
    ):
        """Test that environment variable defaults are properly applied

        Covers line 661: os.environ.setdefault for FASTMCP_LOG_LEVEL
        """
        # Arrange
        # Clear any existing value
        if "FASTMCP_LOG_LEVEL" in os.environ:
            del os.environ["FASTMCP_LOG_LEVEL"]

        mock_migrations.return_value = True
        mock_stats.return_value = None
        mock_event_handlers.return_value = True
        mock_server = MagicMock()
        mock_server.run.side_effect = KeyboardInterrupt()
        mock_create_server.return_value = mock_server

        # Act
        main()

        # Assert
        assert os.environ.get("FASTMCP_LOG_LEVEL") == "DEBUG"


class TestMCPEntryPointDuplicateHandling:
    """Test duplicate operation handling and idempotency"""

    @patch('fastmcp.server.mcp_entry_point.create_agenthub_server')
    @patch('fastmcp.task_management.infrastructure.events.initialize_event_handlers')
    @patch('fastmcp.task_management.application.services.statistics_initializer.StatisticsInitializer.initialize')
    @patch('fastmcp.database_migrations.run_startup_migrations')
    def test_migrations_called_exactly_once(
        self,
        mock_migrations,
        mock_stats,
        mock_event_handlers,
        mock_create_server
    ):
        """Test that database migrations are called exactly once during startup

        Validates duplicate prevention in initialization sequence
        """
        # Arrange
        mock_migrations.return_value = True
        mock_stats.return_value = None
        mock_event_handlers.return_value = True
        mock_server = MagicMock()
        mock_server.run.side_effect = KeyboardInterrupt()
        mock_create_server.return_value = mock_server

        # Act
        main()

        # Assert
        assert mock_migrations.call_count == 1

    @patch('fastmcp.server.mcp_entry_point.create_agenthub_server')
    @patch('fastmcp.task_management.infrastructure.events.initialize_event_handlers')
    @patch('fastmcp.task_management.application.services.statistics_initializer.StatisticsInitializer.initialize')
    @patch('fastmcp.database_migrations.run_startup_migrations')
    def test_statistics_initializer_called_exactly_once(
        self,
        mock_migrations,
        mock_stats,
        mock_event_handlers,
        mock_create_server
    ):
        """Test that statistics initializer is called exactly once during startup

        Validates duplicate prevention in statistics initialization
        """
        # Arrange
        mock_migrations.return_value = True
        mock_stats.return_value = None
        mock_event_handlers.return_value = True
        mock_server = MagicMock()
        mock_server.run.side_effect = KeyboardInterrupt()
        mock_create_server.return_value = mock_server

        # Act
        main()

        # Assert
        assert mock_stats.call_count == 1

    @patch('fastmcp.server.mcp_entry_point.create_agenthub_server')
    @patch('fastmcp.task_management.infrastructure.events.initialize_event_handlers')
    @patch('fastmcp.task_management.application.services.statistics_initializer.StatisticsInitializer.initialize')
    @patch('fastmcp.database_migrations.run_startup_migrations')
    def test_event_handlers_called_exactly_once(
        self,
        mock_migrations,
        mock_stats,
        mock_event_handlers,
        mock_create_server
    ):
        """Test that event handlers are initialized exactly once during startup

        Validates duplicate prevention in event handler initialization
        """
        # Arrange
        mock_migrations.return_value = True
        mock_stats.return_value = None
        mock_event_handlers.return_value = True
        mock_server = MagicMock()
        mock_server.run.side_effect = KeyboardInterrupt()
        mock_create_server.return_value = mock_server

        # Act
        main()

        # Assert
        assert mock_event_handlers.call_count == 1
