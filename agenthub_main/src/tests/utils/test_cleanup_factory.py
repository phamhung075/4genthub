"""Factory for creating test cleanup fixtures - reusable across test files

This module provides a factory pattern for standardized test cleanup that any
polluting test can use. Instead of scattering cleanup logic across conftest.py
and individual test files, tests can use these context managers to ensure
proper cleanup.

Usage Example:
    ```python
    import pytest
    from tests.utils.test_cleanup_factory import TestCleanupFactory

    @pytest.fixture(autouse=True)
    def cleanup_env():
        with TestCleanupFactory.environment_cleanup(['DATABASE_TYPE', 'DATABASE_URL']):
            yield

    @pytest.fixture(autouse=True)
    def cleanup_db():
        with TestCleanupFactory.database_cleanup():
            yield
    ```
"""

import os
from contextlib import contextmanager


class TestCleanupFactory:
    """Factory for creating standardized test cleanup fixtures

    This factory provides context managers that handle cleanup of test pollution
    in a consistent, reusable way across the entire test suite.
    """

    @staticmethod
    @contextmanager
    def environment_cleanup(vars_to_save: list[str]):
        """Cleanup factory for environment variables

        Saves specified environment variables before test execution and restores
        them after, preventing environment pollution between tests.

        Args:
            vars_to_save: List of environment variable names to save and restore

        Usage in test file:
            ```python
            @pytest.fixture(autouse=True)
            def cleanup_env():
                with TestCleanupFactory.environment_cleanup(['DATABASE_TYPE', 'DATABASE_URL']):
                    yield

            def test_database_config():
                # Modify environment variables
                os.environ['DATABASE_TYPE'] = 'postgresql'
                # ... test code ...
                # Environment automatically restored after test
            ```

        Example:
            >>> with TestCleanupFactory.environment_cleanup(['TEST_VAR']):
            ...     os.environ['TEST_VAR'] = 'modified'
            ...     # TEST_VAR is modified only within context
            ... # TEST_VAR is restored to original value here
        """
        # Save original values of all specified environment variables
        original_env: dict[str, str | None] = {
            var: os.environ.get(var) for var in vars_to_save
        }

        try:
            yield
        finally:
            # Restore original values after test completes
            for var, original_value in original_env.items():
                if original_value is not None:
                    # Variable had a value - restore it
                    os.environ[var] = original_value
                elif var in os.environ:
                    # Variable didn't exist originally - remove it
                    del os.environ[var]

    @staticmethod
    @contextmanager
    def database_cleanup():
        """Cleanup factory for database connections

        Ensures database connections are properly closed after test execution,
        preventing connection leaks and singleton pollution.

        Usage in test file:
            ```python
            @pytest.fixture(autouse=True)
            def cleanup_db():
                with TestCleanupFactory.database_cleanup():
                    yield

            def test_database_operations():
                # Perform database operations
                db = DatabaseAdapter.get_instance()
                # ... test code ...
                # Database connections automatically closed after test
            ```

        Example:
            >>> with TestCleanupFactory.database_cleanup():
            ...     db = DatabaseAdapter.get_instance()
            ...     # Use database
            ... # Database connections closed and singletons reset here
        """
        try:
            yield
        finally:
            # Close database connections and reset singletons
            try:
                from fastmcp.task_management.infrastructure.database.database_adapter import (
                    DatabaseAdapter,
                )

                db_adapter = DatabaseAdapter.get_instance()
                if db_adapter._engine:
                    # Dispose of the engine to close all connections
                    db_adapter._engine.dispose()
                    db_adapter._engine = None

                # Reset the singleton instance to prevent pollution
                DatabaseAdapter._instance = None

            except Exception as e:
                # Log but don't fail - cleanup should be best-effort
                print(f"Warning: Database cleanup encountered error: {e}")

    @staticmethod
    @contextmanager
    def database_config_cleanup():
        """Cleanup factory for DatabaseConfig singleton

        Resets the DatabaseConfig singleton after test execution, preventing
        configuration pollution between tests.

        Usage in test file:
            ```python
            @pytest.fixture(autouse=True)
            def cleanup_db_config():
                with TestCleanupFactory.database_config_cleanup():
                    yield

            def test_database_configuration():
                # Modify database configuration
                config = DatabaseConfig.get_instance()
                # ... test code ...
                # DatabaseConfig singleton automatically reset after test
            ```

        Example:
            >>> with TestCleanupFactory.database_config_cleanup():
            ...     config = DatabaseConfig.get_instance()
            ...     # Use config
            ... # DatabaseConfig singleton reset here
        """
        try:
            yield
        finally:
            try:
                from fastmcp.task_management.infrastructure.database.database_config import (
                    DatabaseConfig,
                )

                # Reset the singleton instance
                DatabaseConfig.reset_instance()

            except Exception as e:
                print(f"Warning: DatabaseConfig cleanup encountered error: {e}")

    @staticmethod
    @contextmanager
    def combined_cleanup(env_vars: list[str], cleanup_database: bool = True, cleanup_db_config: bool = True):
        """Combined cleanup factory for environment, database, and config

        Convenience method that combines multiple cleanup operations in a single
        context manager. This is useful for tests that pollute multiple areas.

        Args:
            env_vars: List of environment variable names to save and restore
            cleanup_database: Whether to cleanup database connections (default: True)
            cleanup_db_config: Whether to cleanup DatabaseConfig singleton (default: True)

        Usage in test file:
            ```python
            @pytest.fixture(autouse=True)
            def cleanup_all():
                with TestCleanupFactory.combined_cleanup(
                    env_vars=['DATABASE_TYPE', 'DATABASE_URL'],
                    cleanup_database=True,
                    cleanup_db_config=True
                ):
                    yield

            def test_full_integration():
                # Test that pollutes environment, database, and config
                os.environ['DATABASE_TYPE'] = 'postgresql'
                db = DatabaseAdapter.get_instance()
                # ... test code ...
                # Everything automatically cleaned up after test
            ```

        Example:
            >>> with TestCleanupFactory.combined_cleanup(['DB_TYPE'], True, True):
            ...     os.environ['DB_TYPE'] = 'test'
            ...     db = DatabaseAdapter.get_instance()
            ...     # Use environment and database
            ... # All cleaned up here
        """
        # Stack multiple context managers
        with TestCleanupFactory.environment_cleanup(env_vars):
            if cleanup_database:
                with TestCleanupFactory.database_cleanup():
                    if cleanup_db_config:
                        with TestCleanupFactory.database_config_cleanup():
                            yield
                    else:
                        yield
            elif cleanup_db_config:
                with TestCleanupFactory.database_config_cleanup():
                    yield
            else:
                yield

    @staticmethod
    @contextmanager
    def singleton_cleanup(singleton_class, reset_method: str = 'reset_instance'):
        """Generic cleanup factory for any singleton pattern

        Provides a generic way to reset any singleton class that follows the
        standard singleton pattern with a reset method.

        Args:
            singleton_class: The singleton class to reset
            reset_method: Name of the reset method (default: 'reset_instance')

        Usage in test file:
            ```python
            from my_module import MySingleton

            @pytest.fixture(autouse=True)
            def cleanup_singleton():
                with TestCleanupFactory.singleton_cleanup(MySingleton):
                    yield

            def test_singleton_behavior():
                instance = MySingleton.get_instance()
                # ... test code ...
                # MySingleton automatically reset after test
            ```

        Example:
            >>> class MySingleton:
            ...     _instance = None
            ...     @classmethod
            ...     def reset_instance(cls):
            ...         cls._instance = None
            >>> with TestCleanupFactory.singleton_cleanup(MySingleton):
            ...     instance = MySingleton()
            ...     # Use singleton
            ... # Singleton reset here
        """
        try:
            yield
        finally:
            try:
                # Call the reset method if it exists
                if hasattr(singleton_class, reset_method):
                    reset_fn = getattr(singleton_class, reset_method)
                    reset_fn()
                else:
                    print(f"Warning: {singleton_class.__name__} does not have {reset_method} method")
            except Exception as e:
                print(f"Warning: Singleton cleanup for {singleton_class.__name__} encountered error: {e}")

    @staticmethod
    @contextmanager
    def temporary_env_vars(**kwargs):
        """Temporarily set environment variables for duration of context

        Convenience method that sets environment variables and automatically
        restores original values afterward.

        Args:
            **kwargs: Environment variables to set (key=value pairs)

        Usage in test:
            ```python
            def test_with_temp_env():
                with TestCleanupFactory.temporary_env_vars(
                    DATABASE_TYPE='postgresql',
                    DATABASE_URL='postgresql://localhost/testdb'
                ):
                    # Environment variables are set
                    assert os.environ['DATABASE_TYPE'] == 'postgresql'
                    # ... test code ...
                # Environment variables automatically restored
            ```

        Example:
            >>> with TestCleanupFactory.temporary_env_vars(TEST_VAR='value'):
            ...     assert os.environ['TEST_VAR'] == 'value'
            ... # TEST_VAR restored to original value here
        """
        # Save original values
        original_values: dict[str, str | None] = {
            key: os.environ.get(key) for key in kwargs.keys()
        }

        try:
            # Set new values
            for key, value in kwargs.items():
                os.environ[key] = str(value)
            yield
        finally:
            # Restore original values
            for key, original_value in original_values.items():
                if original_value is not None:
                    os.environ[key] = original_value
                elif key in os.environ:
                    del os.environ[key]


# Convenience functions for common cleanup patterns
def create_env_cleanup_fixture(env_vars: list[str]):
    """Create a pytest fixture function for environment cleanup

    Factory function that generates a pytest fixture with environment cleanup.

    Args:
        env_vars: List of environment variable names to clean up

    Returns:
        A pytest fixture function

    Usage:
        ```python
        # In conftest.py or test file
        cleanup_db_env = create_env_cleanup_fixture(['DATABASE_TYPE', 'DATABASE_URL'])
        ```
    """
    def fixture_function():
        with TestCleanupFactory.environment_cleanup(env_vars):
            yield

    fixture_function.__name__ = f"cleanup_env_{'_'.join(env_vars[:2])}"
    return fixture_function


def create_combined_cleanup_fixture(env_vars: list[str], cleanup_db: bool = True, cleanup_config: bool = True):
    """Create a pytest fixture function for combined cleanup

    Factory function that generates a pytest fixture with combined cleanup.

    Args:
        env_vars: List of environment variable names to clean up
        cleanup_db: Whether to cleanup database connections
        cleanup_config: Whether to cleanup DatabaseConfig singleton

    Returns:
        A pytest fixture function

    Usage:
        ```python
        # In conftest.py or test file
        cleanup_all = create_combined_cleanup_fixture(
            ['DATABASE_TYPE', 'DATABASE_URL'],
            cleanup_db=True,
            cleanup_config=True
        )
        ```
    """
    def fixture_function():
        with TestCleanupFactory.combined_cleanup(env_vars, cleanup_db, cleanup_config):
            yield

    fixture_function.__name__ = "cleanup_combined"
    return fixture_function
