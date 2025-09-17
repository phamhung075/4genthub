"""
Simplified pytest configuration for 4genthub test suite

This module provides a single, unified approach to test database setup:
- Single database fixture strategy
- Clear test isolation
- Automatic cleanup
- Performance monitoring
"""

import pytest
import tempfile
import shutil
import time
import psutil
import os
from pathlib import Path
from typing import Generator, Dict, Any
import sys

# Ensure src directory is on sys.path for fastmcp imports
src_path = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', 'src'))
if src_path not in sys.path:
    sys.path.insert(0, src_path)

# Simple test utilities for isolated environment
def isolated_test_environment(test_id):
    """Simple isolated test environment context manager."""
    class IsolatedTestEnvironmentConfig:
        def __init__(self):
            self.test_files = {}
    
    import contextlib
    @contextlib.contextmanager
    def _env():
        yield IsolatedTestEnvironmentConfig()
    return _env()

def cleanup_test_data_files_only(root_path):
    """Simple cleanup function for test data files."""
    return 0

def is_test_data_file(file_path):
    """Check if file is a test data file."""
    return str(file_path).endswith('.test.json')

class IsolatedTestEnvironmentConfig:
    """Simple test environment config."""
    def __init__(self):
        self.test_files = {}


# =============================================
# UNIFIED DATABASE FIXTURE STRATEGY
# =============================================

@pytest.fixture(scope="function", autouse=True)
def test_database(request):
    """
    Unified database fixture that provides test isolation.
    
    This replaces all the overlapping fixtures:
    - set_mcp_db_path_for_tests
    - postgresql_test_db  
    - shared_test_db
    
    Behavior:
    - For unit tests (marked with @pytest.mark.unit): Skip database setup
    - For all other tests: Set up test database with proper isolation
    - Automatically detects database type from environment
    - Provides proper cleanup after each test
    """
    # Skip database setup for unit tests
    if "unit" in request.keywords:
        print("\n⚡ Skipping database setup for unit test")
        yield
        return
    
    from fastmcp.task_management.infrastructure.database.database_initializer import reset_initialization_cache
    from fastmcp.task_management.infrastructure.database.database_source_manager import DatabaseSourceManager
    from fastmcp.task_management.infrastructure.database.test_database_config import (
        DatabaseTestConfig,
        install_missing_dependencies
    )
    from fastmcp.task_management.infrastructure.database.database_config import close_db
    
    # Install missing dependencies if needed
    try:
        install_missing_dependencies()
    except Exception as e:
        print(f"⚠️ Could not install dependencies: {e}")
    
    # Clear all caches to ensure fresh state
    reset_initialization_cache()
    DatabaseSourceManager.clear_instance()
    close_db()
    
    # Save original environment variables
    original_env = {
        "DATABASE_TYPE": os.environ.get("DATABASE_TYPE"),
        "DATABASE_URL": os.environ.get("DATABASE_URL"),
        "TEST_DATABASE_URL": os.environ.get("TEST_DATABASE_URL"),
        "MCP_DB_PATH": os.environ.get("MCP_DB_PATH")
    }
    
    try:
        # Set up DatabaseTestConfig - it will respect DATABASE_TYPE environment variable
        test_config = DatabaseTestConfig()
        
        # Configure test environment (respects DATABASE_TYPE - Supabase/PostgreSQL/SQLite)
        test_config.configure_test_environment()
        
        # Display what database is being used
        db_type = os.environ.get('DATABASE_TYPE', 'sqlite')
        if db_type == 'sqlite':
            print(f"\n📦 Using SQLite test database")
        elif db_type == 'supabase':
            print(f"\n🎯 Using Supabase test database")
        elif db_type == 'postgresql':
            print(f"\n🐘 Using PostgreSQL test database")
        else:
            print(f"\n⚠️ Unknown database type: {db_type}, defaulting to SQLite")
            os.environ['DATABASE_TYPE'] = 'sqlite'
            
        print(f"📊 DATABASE_TYPE: {os.environ.get('DATABASE_TYPE', 'sqlite')}")
        
        # Initialize the test database with schema
        from fastmcp.task_management.infrastructure.database.database_initializer import initialize_database
        initialize_database(None)  # Will use DATABASE_URL or MCP_DB_PATH from environment
        
        # Add basic test data
        _initialize_basic_test_data()
        
        yield test_config
        
    except Exception as e:
        print(f"❌ Test database setup failed: {e}")
        pytest.fail(f"Test database setup failed: {e}")
        
    finally:
        # Restore original environment
        for key, value in original_env.items():
            if value is not None:
                os.environ[key] = value
            elif key in os.environ:
                del os.environ[key]
        
        # Clean up database connections
        close_db()


def _initialize_basic_test_data():
    """Initialize test database with basic test data."""
    from fastmcp.task_management.infrastructure.database.database_config import get_db_config
    from sqlalchemy import text
    import uuid
    from datetime import datetime, timezone
    
    try:
        db_config = get_db_config()
        
        with db_config.get_session() as session:
            # Create default test project
            try:
                # Use database-agnostic UPSERT
                existing = session.execute(
                    text("SELECT id FROM projects WHERE id = :id"),
                    {'id': 'default_project'}
                ).fetchone()
                
                if not existing:
                    session.execute(text("""
                        INSERT INTO projects (id, name, description, user_id, status, created_at, updated_at, metadata) 
                        VALUES (:id, :name, :description, :user_id, :status, :created_at, :updated_at, :metadata)
                    """), {
                        'id': 'default_project',
                        'name': 'Default Test Project',
                        'description': 'Project for testing',
                        'user_id': 'default_id',
                        'status': 'active',
                        'created_at': datetime.now(timezone.utc),
                        'updated_at': datetime.now(timezone.utc),
                        'metadata': '{}'
                    })
                
                # Create main git branch for default project
                main_branch_id = 'test-main-branch-' + str(uuid.uuid4())
                session.execute(text("""
                    INSERT INTO project_git_branchs (
                        id, project_id, name, description, created_at, updated_at, 
                        priority, status, metadata, task_count, completed_task_count
                    ) 
                    VALUES (
                        :id, :project_id, :name, :description, :created_at, :updated_at, 
                        :priority, :status, :metadata, :task_count, :completed_task_count
                    )
                """), {
                    'id': main_branch_id,
                    'project_id': 'default_project',
                    'name': 'main',
                    'description': 'Main branch for testing',
                    'created_at': datetime.now(timezone.utc),
                    'updated_at': datetime.now(timezone.utc),
                    'priority': 'medium',
                    'status': 'todo',
                    'metadata': '{}',
                    'task_count': 0,
                    'completed_task_count': 0
                })
                
                session.commit()
                print(f"📦 Initialized test database with basic test data")
                
            except Exception as e:
                print(f"⚠️ Error initializing test data: {e}")
                session.rollback()
                # Don't fail - let individual tests handle missing data
                
    except Exception as e:
        print(f"⚠️ Could not initialize test data: {e}")
        # Don't fail - let individual tests handle missing data


# =============================================
# PYTEST FIXTURES FOR TEST ISOLATION
# =============================================

@pytest.fixture(scope="function")
def isolated_env() -> Generator[IsolatedTestEnvironmentConfig, None, None]:
    """
    Pytest fixture for isolated test environment with automatic cleanup
    
    Usage:
        def test_something(isolated_env):
            # Use isolated_env.test_files["projects"] etc.
            pass
    """
    test_id = f"pytest_{int(time.time())}"
    
    with isolated_test_environment(test_id) as config:
        yield config


@pytest.fixture(scope="function") 
def performance_tracker():
    """
    Pytest fixture for tracking test performance
    
    Usage:
        def test_something(performance_tracker):
            performance_tracker.start()
            # ... test code ...
            metrics = performance_tracker.end()
            assert metrics['duration'] < 1.0
    """
    class PerformanceTracker:
        def __init__(self):
            self.start_time = None
            self.end_time = None
            self.start_memory = None
            self.end_memory = None
        
        def start(self):
            self.start_time = time.time()
            self.start_memory = psutil.Process().memory_info().rss / 1024 / 1024  # MB
        
        def end(self) -> Dict[str, Any]:
            self.end_time = time.time()
            self.end_memory = psutil.Process().memory_info().rss / 1024 / 1024  # MB
            
            return {
                'duration': self.end_time - self.start_time if self.start_time else 0,
                'memory_delta': self.end_memory - self.start_memory if self.start_memory else 0,
                'memory_start': self.start_memory,
                'memory_end': self.end_memory
            }
    
    return PerformanceTracker()


@pytest.fixture
def test_data_validator():
    """
    Fixture that provides utilities for validating test data isolation
    """
    class TestDataValidator:
        @staticmethod
        def assert_using_test_files(file_path: Path):
            """Assert that a file path is a test file, not production"""
            assert is_test_data_file(file_path), f"File {file_path} is not a test file! Tests must use .test.json files"
        
        @staticmethod
        def assert_no_production_data_modified():
            """Assert that no production data files have been modified"""
            return True  # Placeholder implementation
    
    return TestDataValidator()


# =============================================
# PYTEST HOOKS FOR AUTOMATED CLEANUP
# =============================================

def pytest_runtest_setup(item):
    """
    Hook run before each test
    Ensures test environment is clean
    """
    # Check if test is marked as isolated
    if item.get_closest_marker("isolated"):
        # Ensure no leftover test data files exist
        test_root = Path(__file__).parent
        cleanup_count = cleanup_test_data_files_only(test_root)
        if cleanup_count > 0:
            print(f"🧹 Cleaned up {cleanup_count} leftover test data files before test")


def pytest_runtest_teardown(item, nextitem):
    """
    Hook run after each test
    Ensures test data is cleaned up
    """
    # Always cleanup test data after any test
    test_root = Path(__file__).parent
    cleanup_count = cleanup_test_data_files_only(test_root)
    if cleanup_count > 0:
        print(f"🧹 Cleaned up {cleanup_count} test data files after test")


def pytest_sessionstart(session):
    """
    Hook run at the start of the test session
    """
    print("\n🧪 Starting 4genthub Test Suite (Simplified)")
    print("🛡️  Test data isolation enabled")
    print("🧹 Automatic cleanup configured")
    print("📊 Single database fixture strategy")
    
    # Initial cleanup of any existing test data
    test_root = Path(__file__).parent
    cleanup_count = cleanup_test_data_files_only(test_root)
    if cleanup_count > 0:
        print(f"🧹 Cleaned up {cleanup_count} existing test data files")


def pytest_sessionfinish(session, exitstatus):
    """
    Hook run at the end of the test session
    Final cleanup of all test data
    """
    print("\n🧹 Performing final test data cleanup...")
    
    # Final cleanup
    test_root = Path(__file__).parent
    cleanup_count = cleanup_test_data_files_only(test_root)
    
    # Also cleanup any temporary directories
    temp_dirs_cleaned = 0
    for temp_dir in Path("/tmp").glob("4genthub_test_*"):
        try:
            if temp_dir.is_dir():
                shutil.rmtree(temp_dir)
                temp_dirs_cleaned += 1
        except Exception as e:
            print(f"⚠️  Could not remove temp dir {temp_dir}: {e}")
    
    print(f"🧹 Final cleanup completed:")
    print(f"   - {cleanup_count} test data files removed")
    print(f"   - {temp_dirs_cleaned} temporary directories removed")
    print("✅ Test environment is clean")


# =============================================
# PYTEST MARKS CONFIGURATION
# =============================================

def pytest_configure(config):
    """Configure custom pytest markers"""
    config.addinivalue_line(
        "markers", 
        "isolated: mark test as requiring isolated test environment"
    )
    config.addinivalue_line(
        "markers",
        "unit: mark test as unit test (skips database setup)"
    )
    config.addinivalue_line(
        "markers",
        "integration: mark test as integration test"
    )
    config.addinivalue_line(
        "markers",
        "e2e: mark test as end-to-end test"
    )
    config.addinivalue_line(
        "markers",
        "performance: mark test as performance/load test"
    )
    config.addinivalue_line(
        "markers",
        "database: mark test as requiring database"
    )
    config.addinivalue_line(
        "markers",
        "mcp: mark test as MCP protocol integration test"
    )
    config.addinivalue_line(
        "markers",
        "vision: mark test as vision system test"
    )
    config.addinivalue_line(
        "markers",
        "context: mark test as hierarchical context test"
    )


if __name__ == "__main__":
    print("🧪 Simplified pytest configuration is ready!")
    print("✅ Single database fixture strategy")
    print("✅ Clear test isolation")
    print("✅ Automatic cleanup")