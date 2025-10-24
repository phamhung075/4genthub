"""Example test file demonstrating TestCleanupFactory usage

This file shows various patterns for using TestCleanupFactory to handle
test pollution in a clean, reusable way. These patterns can be copied
into any test file that needs cleanup.

DO NOT RUN THIS FILE - It's for reference only!
"""

import pytest
import os
from tests.utils.test_cleanup_factory import TestCleanupFactory


# ============================================================================
# PATTERN 1: Environment Variable Cleanup (Most Common)
# ============================================================================
# Use this when your test modifies environment variables

@pytest.fixture(autouse=True)
def cleanup_env():
    """Auto-cleanup environment variables after each test"""
    with TestCleanupFactory.environment_cleanup(['DATABASE_TYPE', 'DATABASE_URL']):
        yield


def test_modifies_environment():
    """Example test that modifies environment variables"""
    # Modify environment - cleanup happens automatically
    os.environ['DATABASE_TYPE'] = 'postgresql'
    os.environ['DATABASE_URL'] = 'postgresql://localhost/testdb'

    # Your test code here
    assert os.environ['DATABASE_TYPE'] == 'postgresql'

    # After test completes, environment is automatically restored


# ============================================================================
# PATTERN 2: Database Connection Cleanup
# ============================================================================
# Use this when your test creates database connections

@pytest.fixture(autouse=True)
def cleanup_database():
    """Auto-cleanup database connections after each test"""
    with TestCleanupFactory.database_cleanup():
        yield


def test_uses_database():
    """Example test that uses database connections"""
    from fastmcp.task_management.infrastructure.database.database_adapter import DatabaseAdapter

    # Use database - connections are automatically closed
    db = DatabaseAdapter.get_instance()
    # Your test code here

    # After test completes, database connections are closed


# ============================================================================
# PATTERN 3: Combined Cleanup (Environment + Database + Config)
# ============================================================================
# Use this when your test pollutes multiple areas

@pytest.fixture(autouse=True)
def cleanup_all():
    """Auto-cleanup environment, database, and config after each test"""
    with TestCleanupFactory.combined_cleanup(
        env_vars=['DATABASE_TYPE', 'DATABASE_URL'],
        cleanup_database=True,
        cleanup_db_config=True
    ):
        yield


def test_full_integration():
    """Example integration test that pollutes multiple areas"""
    # Modify environment
    os.environ['DATABASE_TYPE'] = 'postgresql'

    # Use database
    from fastmcp.task_management.infrastructure.database.database_adapter import DatabaseAdapter
    db = DatabaseAdapter.get_instance()

    # Use database config
    from fastmcp.task_management.infrastructure.database.database_config import DatabaseConfig
    config = DatabaseConfig.get_instance()

    # Your test code here

    # After test completes, everything is automatically cleaned up


# ============================================================================
# PATTERN 4: Temporary Environment Variables (Inline)
# ============================================================================
# Use this when you need temporary environment variables within a test

def test_with_temporary_env():
    """Example test using temporary environment variables"""
    # Set environment variables temporarily
    with TestCleanupFactory.temporary_env_vars(
        DATABASE_TYPE='postgresql',
        DATABASE_URL='postgresql://localhost/testdb'
    ):
        # Environment variables are set only within this context
        assert os.environ['DATABASE_TYPE'] == 'postgresql'

        # Your test code here

    # Environment variables automatically restored after context


# ============================================================================
# PATTERN 5: Generic Singleton Cleanup
# ============================================================================
# Use this when your test uses custom singletons

from tests.utils.test_cleanup_factory import TestCleanupFactory


@pytest.fixture(autouse=True)
def cleanup_custom_singleton():
    """Auto-cleanup custom singleton after each test"""
    from my_module import MySingleton  # Replace with actual import

    with TestCleanupFactory.singleton_cleanup(MySingleton, reset_method='reset_instance'):
        yield


def test_uses_custom_singleton():
    """Example test using custom singleton"""
    from my_module import MySingleton  # Replace with actual import

    # Use singleton
    instance = MySingleton.get_instance()

    # Your test code here

    # After test completes, singleton is automatically reset


# ============================================================================
# PATTERN 6: Multiple Cleanup Fixtures (Selective)
# ============================================================================
# Use this when different tests need different cleanup

# Define separate fixtures for different cleanup needs
@pytest.fixture
def cleanup_env_only():
    """Cleanup only environment variables"""
    with TestCleanupFactory.environment_cleanup(['DATABASE_TYPE']):
        yield


@pytest.fixture
def cleanup_db_only():
    """Cleanup only database connections"""
    with TestCleanupFactory.database_cleanup():
        yield


# Test 1: Uses only environment cleanup
def test_needs_env_cleanup(cleanup_env_only):
    """Example test needing only environment cleanup"""
    os.environ['DATABASE_TYPE'] = 'sqlite'
    # Your test code here


# Test 2: Uses only database cleanup
def test_needs_db_cleanup(cleanup_db_only):
    """Example test needing only database cleanup"""
    from fastmcp.task_management.infrastructure.database.database_adapter import DatabaseAdapter
    db = DatabaseAdapter.get_instance()
    # Your test code here


# Test 3: Uses both cleanups
def test_needs_both_cleanups(cleanup_env_only, cleanup_db_only):
    """Example test needing both cleanups"""
    os.environ['DATABASE_TYPE'] = 'postgresql'
    from fastmcp.task_management.infrastructure.database.database_adapter import DatabaseAdapter
    db = DatabaseAdapter.get_instance()
    # Your test code here


# ============================================================================
# PATTERN 7: Class-Level Fixtures (All Tests in Class)
# ============================================================================
# Use this when all tests in a class need the same cleanup

class TestDatabaseOperations:
    """Example test class with class-level cleanup"""

    @pytest.fixture(autouse=True)
    def cleanup(self):
        """Auto-cleanup for all tests in this class"""
        with TestCleanupFactory.combined_cleanup(
            env_vars=['DATABASE_TYPE', 'DATABASE_URL'],
            cleanup_database=True,
            cleanup_db_config=True
        ):
            yield

    def test_operation_1(self):
        """First test in class - cleanup applied automatically"""
        os.environ['DATABASE_TYPE'] = 'postgresql'
        # Your test code here

    def test_operation_2(self):
        """Second test in class - cleanup applied automatically"""
        os.environ['DATABASE_URL'] = 'postgresql://localhost/db'
        # Your test code here


# ============================================================================
# PATTERN 8: Nested Context Managers (Advanced)
# ============================================================================
# Use this when you need fine-grained control over cleanup order

def test_with_nested_cleanup():
    """Example test with nested cleanup contexts"""
    # Outer context: environment cleanup
    with TestCleanupFactory.environment_cleanup(['DATABASE_TYPE']):
        os.environ['DATABASE_TYPE'] = 'postgresql'

        # Inner context: database cleanup
        with TestCleanupFactory.database_cleanup():
            from fastmcp.task_management.infrastructure.database.database_adapter import DatabaseAdapter
            db = DatabaseAdapter.get_instance()

            # Your test code here

            # Database cleaned up first (inner context exits)

        # Environment cleaned up second (outer context exits)


# ============================================================================
# PATTERN 9: Parameterized Tests with Cleanup
# ============================================================================
# Use this when running parameterized tests that need cleanup

@pytest.fixture(autouse=True)
def cleanup_for_parameterized():
    """Auto-cleanup for parameterized tests"""
    with TestCleanupFactory.environment_cleanup(['TEST_PARAM']):
        yield


@pytest.mark.parametrize('test_value', ['value1', 'value2', 'value3'])
def test_parameterized_with_cleanup(test_value):
    """Example parameterized test with cleanup"""
    # Each parameter run gets automatic cleanup
    os.environ['TEST_PARAM'] = test_value

    # Your test code here
    assert os.environ['TEST_PARAM'] == test_value

    # After each parameter run, environment is cleaned up


# ============================================================================
# PATTERN 10: Conftest Integration (Module-Wide)
# ============================================================================
# Add this to conftest.py to apply cleanup to all tests in a module

# In conftest.py:
"""
import pytest
from tests.utils.test_cleanup_factory import TestCleanupFactory

@pytest.fixture(autouse=True, scope="function")
def auto_cleanup_all_tests():
    '''Auto-cleanup for ALL tests in this module'''
    with TestCleanupFactory.combined_cleanup(
        env_vars=['DATABASE_TYPE', 'DATABASE_URL'],
        cleanup_database=True,
        cleanup_db_config=True
    ):
        yield
"""


# ============================================================================
# ANTI-PATTERNS - DON'T DO THIS
# ============================================================================

# ❌ ANTI-PATTERN 1: Manual cleanup in finally block
def test_manual_cleanup_bad():
    """DON'T DO THIS - Manual cleanup is error-prone"""
    original_value = os.environ.get('DATABASE_TYPE')
    try:
        os.environ['DATABASE_TYPE'] = 'postgresql'
        # Test code
    finally:
        # This is fragile and easy to forget
        if original_value:
            os.environ['DATABASE_TYPE'] = original_value
        else:
            del os.environ['DATABASE_TYPE']


# ✅ GOOD PATTERN: Use factory instead
def test_factory_cleanup_good():
    """DO THIS - Factory handles cleanup automatically"""
    with TestCleanupFactory.environment_cleanup(['DATABASE_TYPE']):
        os.environ['DATABASE_TYPE'] = 'postgresql'
        # Test code - cleanup is guaranteed


# ❌ ANTI-PATTERN 2: No cleanup at all
def test_no_cleanup_bad():
    """DON'T DO THIS - Pollutes environment for other tests"""
    os.environ['DATABASE_TYPE'] = 'postgresql'
    # Test code
    # No cleanup - next test gets polluted environment!


# ✅ GOOD PATTERN: Always use cleanup
@pytest.fixture(autouse=True)
def cleanup():
    with TestCleanupFactory.environment_cleanup(['DATABASE_TYPE']):
        yield


def test_with_cleanup_good():
    """DO THIS - Always cleanup after pollution"""
    os.environ['DATABASE_TYPE'] = 'postgresql'
    # Test code - cleanup is automatic


# ============================================================================
# MIGRATION GUIDE - Converting Old Tests
# ============================================================================

# BEFORE (Old pattern with scattered cleanup logic):
"""
@pytest.fixture(autouse=True)
def old_cleanup():
    original_db_type = os.environ.get('DATABASE_TYPE')
    original_db_url = os.environ.get('DATABASE_URL')

    yield

    if original_db_type:
        os.environ['DATABASE_TYPE'] = original_db_type
    elif 'DATABASE_TYPE' in os.environ:
        del os.environ['DATABASE_TYPE']

    if original_db_url:
        os.environ['DATABASE_URL'] = original_db_url
    elif 'DATABASE_URL' in os.environ:
        del os.environ['DATABASE_URL']

    try:
        from fastmcp.task_management.infrastructure.database.database_adapter import DatabaseAdapter
        db_adapter = DatabaseAdapter.get_instance()
        if db_adapter._engine:
            db_adapter._engine.dispose()
            db_adapter._engine = None
        DatabaseAdapter._instance = None
    except:
        pass
"""

# AFTER (New pattern with factory - much cleaner!):
@pytest.fixture(autouse=True)
def new_cleanup():
    """Cleaner, more maintainable cleanup using factory"""
    with TestCleanupFactory.combined_cleanup(
        env_vars=['DATABASE_TYPE', 'DATABASE_URL'],
        cleanup_database=True
    ):
        yield


# ============================================================================
# SUMMARY - CHOOSING THE RIGHT PATTERN
# ============================================================================
"""
Choose your pattern based on what your test pollutes:

1. Environment variables only → Use environment_cleanup()
2. Database connections only → Use database_cleanup()
3. Multiple areas → Use combined_cleanup()
4. Temporary env within test → Use temporary_env_vars()
5. Custom singleton → Use singleton_cleanup()
6. Different tests need different cleanup → Use separate fixtures
7. All tests in class → Use class-level fixture with autouse=True
8. All tests in module → Add fixture to conftest.py with autouse=True

Key Benefits:
- ✅ No code duplication
- ✅ Consistent cleanup across all tests
- ✅ Easy to add new cleanup types
- ✅ Self-documenting code
- ✅ Guaranteed cleanup even on test failure
- ✅ Can be easily extended for new patterns
"""
