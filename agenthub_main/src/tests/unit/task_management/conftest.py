"""
Pytest configuration for task_management unit tests.

This module provides fixtures to prevent real database connections in unit tests.
"""

from unittest.mock import MagicMock, patch

import pytest


@pytest.fixture(autouse=True)
def mock_database_config():
    """
    Prevent real database connections in unit tests.

    This fixture automatically mocks DatabaseConfig for all tests in this directory,
    preventing SystemExit errors when tests try to connect to PostgreSQL.

    The mock provides:
    - get_instance() returning a mock DatabaseConfig instance
    - get_session() returning a mock session context manager with execute() support
    - get_database_info() returning mock database information
    """
    with patch(
        "fastmcp.task_management.infrastructure.database.database_config.DatabaseConfig"
    ) as mock_db_class:
        # Create mock instance
        mock_instance = MagicMock()

        # Mock get_session to return a context manager with a mock session
        mock_session = MagicMock()

        # Mock execute to return a mock result with fetchone(), fetchall(), etc.
        mock_result = MagicMock()
        mock_result.fetchone.return_value = (1,)  # For SELECT 1 queries
        mock_result.fetchall.return_value = []
        mock_result.__iter__ = MagicMock(return_value=iter([]))
        mock_session.execute.return_value = mock_result

        # Mock commit and rollback
        mock_session.commit.return_value = None
        mock_session.rollback.return_value = None

        # Make the session work as a context manager
        mock_session.__enter__ = MagicMock(return_value=mock_session)
        mock_session.__exit__ = MagicMock(return_value=False)
        mock_instance.get_session.return_value = mock_session

        # Mock get_database_info
        mock_instance.get_database_info.return_value = {
            "type": "sqlite",
            "path": ":memory:",
            "status": "mocked",
        }

        # Mock get_instance to return our mock instance
        mock_db_class.get_instance.return_value = mock_instance

        # Also mock the direct instantiation
        mock_db_class.return_value = mock_instance

        yield mock_db_class


@pytest.fixture(autouse=True)
def mock_get_db_config():
    """
    Mock the get_db_config() function to prevent database initialization.

    This fixture complements mock_database_config by also mocking the
    get_db_config() helper function that many tests use directly.
    """
    with patch(
        "fastmcp.task_management.infrastructure.database.database_config.get_db_config"
    ) as mock_get_db:
        # Create mock config instance
        mock_config = MagicMock()

        # Mock get_session to return a context manager with a mock session
        mock_session = MagicMock()

        # Mock execute to return a mock result with fetchone(), fetchall(), etc.
        mock_result = MagicMock()
        mock_result.fetchone.return_value = (1,)  # For SELECT 1 queries
        mock_result.fetchall.return_value = []
        mock_result.__iter__ = MagicMock(return_value=iter([]))
        mock_session.execute.return_value = mock_result

        # Mock commit and rollback
        mock_session.commit.return_value = None
        mock_session.rollback.return_value = None

        # Make the session work as a context manager
        mock_session.__enter__ = MagicMock(return_value=mock_session)
        mock_session.__exit__ = MagicMock(return_value=False)
        mock_config.get_session.return_value = mock_session

        # Mock get_database_info
        mock_config.get_database_info.return_value = {
            "type": "sqlite",
            "path": ":memory:",
            "status": "mocked",
        }

        # Return the mock config
        mock_get_db.return_value = mock_config

        yield mock_get_db


@pytest.fixture(autouse=True)
def mock_database_source_manager():
    """
    Mock DatabaseSourceManager to prevent database mode detection.

    This prevents tests from trying to detect whether they should use
    PostgreSQL or SQLite, which can cause connection attempts.
    """
    with patch(
        "fastmcp.task_management.infrastructure.database.database_source_manager.DatabaseSourceManager"
    ) as mock_dsm:
        mock_instance = MagicMock()
        mock_instance.get_mode.return_value = "TEST"
        mock_dsm.get_instance.return_value = mock_instance
        yield mock_dsm


@pytest.fixture(autouse=True)
def mock_database_initializer():
    """
    Mock database initialization functions to prevent schema creation attempts.
    """
    with patch(
        "fastmcp.task_management.infrastructure.database.database_initializer.initialize_database"
    ) as mock_init:
        mock_init.return_value = None
        yield mock_init
