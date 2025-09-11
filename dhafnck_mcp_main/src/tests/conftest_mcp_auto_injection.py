"""
PyTest Configuration for MCP Auto-Injection Tests

Configures pytest for MCP auto-injection system testing with proper
setup, teardown, and test environment configuration.

Configuration Features:
- Test markers for categorization
- Fixture imports and setup
- Performance testing configuration
- Parallel test execution setup
- Test data isolation
"""

import pytest
import sys
import os
import logging
from pathlib import Path

# Add necessary paths for testing
hooks_path = Path(__file__).parent.parent.parent.parent / ".claude" / "hooks"
src_path = Path(__file__).parent.parent / "src"

for path in [hooks_path, src_path]:
    if str(path) not in sys.path:
        sys.path.insert(0, str(path))

# Import all fixtures
from .fixtures.mcp_auto_injection_fixtures import *

# Test environment configuration
os.environ.setdefault("TESTING_MODE", "true")
os.environ.setdefault("SESSION_CACHE_TTL", "60")
os.environ.setdefault("TASK_CACHE_TTL", "30")
os.environ.setdefault("GIT_CACHE_TTL", "15")
os.environ.setdefault("CACHE_CLEANUP_INTERVAL", "300")


def pytest_configure(config):
    """Configure pytest for MCP auto-injection testing."""
    # Register custom markers
    config.addinivalue_line(
        "markers", "unit: Unit tests - test individual components in isolation"
    )
    config.addinivalue_line(
        "markers", "integration: Integration tests - test component interactions"
    )
    config.addinivalue_line(
        "markers", "e2e: End-to-end tests - test complete workflows"
    )
    config.addinivalue_line(
        "markers", "performance: Performance tests - measure timing and throughput"
    )
    config.addinivalue_line(
        "markers", "slow: Slow tests - tests that take more than 10 seconds"
    )
    config.addinivalue_line(
        "markers", "network: Tests requiring network access or mocked network"
    )
    config.addinivalue_line(
        "markers", "cache: Cache-related tests"
    )
    config.addinivalue_line(
        "markers", "auth: Authentication-related tests"
    )
    config.addinivalue_line(
        "markers", "mcp: MCP server communication tests"
    )
    config.addinivalue_line(
        "markers", "git: Git repository integration tests"
    )


def pytest_collection_modifyitems(config, items):
    """Modify test collection to add markers and handle skips."""
    for item in items:
        # Auto-mark tests based on file path
        if "unit" in str(item.fspath):
            item.add_marker(pytest.mark.unit)
        elif "integration" in str(item.fspath):
            item.add_marker(pytest.mark.integration)
        elif "e2e" in str(item.fspath):
            item.add_marker(pytest.mark.e2e)
        
        # Auto-mark performance tests
        if "performance" in item.name or "perf" in item.name:
            item.add_marker(pytest.mark.performance)
        
        # Auto-mark slow tests based on timeout or known patterns
        if any(keyword in item.name.lower() for keyword in ["concurrent", "load", "stress"]):
            item.add_marker(pytest.mark.slow)
        
        # Auto-mark network tests
        if any(keyword in item.name.lower() for keyword in ["server", "auth", "mcp", "keycloak"]):
            item.add_marker(pytest.mark.network)


@pytest.fixture(scope="session", autouse=True)
def setup_test_environment():
    """Set up test environment for MCP auto-injection tests."""
    # Configure logging for tests
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s [%(levelname)s] %(name)s: %(message)s',
        handlers=[
            logging.StreamHandler(),
        ]
    )
    
    # Suppress verbose logs during testing
    logging.getLogger("urllib3").setLevel(logging.WARNING)
    logging.getLogger("requests").setLevel(logging.WARNING)
    
    logger = logging.getLogger("mcp_auto_injection_tests")
    logger.info("Setting up MCP auto-injection test environment")
    
    yield
    
    logger.info("Tearing down MCP auto-injection test environment")


@pytest.fixture(scope="function", autouse=True)
def test_isolation():
    """Ensure test isolation between test runs."""
    # Clear any module-level caches or state
    import importlib
    
    # Modules that might have cached state
    modules_to_reload = [
        "utils.cache_manager",
        "utils.mcp_client", 
        "session_start"
    ]
    
    original_modules = {}
    for module_name in modules_to_reload:
        if module_name in sys.modules:
            original_modules[module_name] = sys.modules[module_name]
    
    yield
    
    # Restore original modules to prevent test pollution
    for module_name, module in original_modules.items():
        sys.modules[module_name] = module


@pytest.fixture(scope="function")
def isolated_temp_environment():
    """Create completely isolated temporary environment for tests."""
    import tempfile
    import shutil
    
    with tempfile.TemporaryDirectory(prefix="mcp_test_") as temp_dir:
        temp_path = Path(temp_dir)
        
        # Create isolated directory structure
        directories = [
            "cache",
            "logs", 
            "config",
            "git_repos",
            "test_data"
        ]
        
        for directory in directories:
            (temp_path / directory).mkdir(parents=True, exist_ok=True)
        
        # Set environment variables for isolation
        original_env = {}
        test_env_vars = {
            "HOME": str(temp_path),
            "XDG_CACHE_HOME": str(temp_path / "cache"),
            "XDG_CONFIG_HOME": str(temp_path / "config"),
            "TMPDIR": str(temp_path / "temp"),
            "AI_DATA": str(temp_path / "logs"),
            "AI_DOCS": str(temp_path / "docs"),
        }
        
        # Backup and set test environment
        for key, value in test_env_vars.items():
            original_env[key] = os.environ.get(key)
            os.environ[key] = value
        
        yield temp_path
        
        # Restore original environment
        for key, original_value in original_env.items():
            if original_value is None:
                os.environ.pop(key, None)
            else:
                os.environ[key] = original_value


# Custom pytest hooks for better test reporting
def pytest_runtest_setup(item):
    """Custom setup for each test."""
    # Log test start
    logger = logging.getLogger("test_runner")
    logger.info(f"Starting test: {item.name}")


def pytest_runtest_teardown(item):
    """Custom teardown for each test."""
    # Log test completion
    logger = logging.getLogger("test_runner")
    logger.info(f"Completed test: {item.name}")


def pytest_runtest_call(pyfuncitem):
    """Custom test call wrapper for timing and error handling."""
    import time
    
    start_time = time.time()
    
    try:
        # Call the actual test
        result = pytest.CallInfo.from_call(
            lambda: pyfuncitem.runtest(), when="call", reraise=True
        )
    except Exception as exc:
        # Log test failure details
        logger = logging.getLogger("test_runner")
        logger.error(f"Test {pyfuncitem.name} failed: {exc}")
        raise
    finally:
        # Log test duration
        duration = time.time() - start_time
        logger = logging.getLogger("test_runner")
        logger.info(f"Test {pyfuncitem.name} duration: {duration:.3f}s")
    
    return result


# Performance test configuration
@pytest.fixture(scope="session")
def performance_thresholds():
    """Performance thresholds for different test types."""
    return {
        "unit_test_max_duration": 1.0,  # 1 second
        "integration_test_max_duration": 5.0,  # 5 seconds
        "e2e_test_max_duration": 30.0,  # 30 seconds
        "cache_operation_max_duration": 0.01,  # 10ms
        "mcp_request_max_duration": 2.0,  # 2 seconds
        "auth_request_max_duration": 3.0,  # 3 seconds
        "session_start_max_duration": 10.0,  # 10 seconds
    }


# Test result tracking
@pytest.fixture(scope="session")
def test_results_tracker():
    """Track test results across the session."""
    class TestResultsTracker:
        def __init__(self):
            self.results = {
                "passed": 0,
                "failed": 0,
                "skipped": 0,
                "errors": 0,
                "performance_violations": 0,
                "test_details": []
            }
        
        def record_result(self, test_name, status, duration=None, error=None):
            """Record a test result."""
            self.results[status] += 1
            self.results["test_details"].append({
                "test_name": test_name,
                "status": status,
                "duration": duration,
                "error": str(error) if error else None,
                "timestamp": time.time()
            })
        
        def get_summary(self):
            """Get test results summary."""
            total_tests = sum(self.results[key] for key in ["passed", "failed", "skipped", "errors"])
            return {
                "total_tests": total_tests,
                "pass_rate": self.results["passed"] / max(total_tests, 1),
                "failure_rate": self.results["failed"] / max(total_tests, 1),
                **self.results
            }
    
    return TestResultsTracker()


# Skip conditions for certain test environments
def pytest_runtest_setup(item):
    """Skip tests based on environment conditions."""
    # Skip network tests if no network access
    if item.get_closest_marker("network"):
        if os.environ.get("SKIP_NETWORK_TESTS", "").lower() in ("true", "1", "yes"):
            pytest.skip("Network tests disabled by environment variable")
    
    # Skip slow tests in fast test mode
    if item.get_closest_marker("slow"):
        if os.environ.get("FAST_TESTS_ONLY", "").lower() in ("true", "1", "yes"):
            pytest.skip("Slow tests disabled in fast test mode")
    
    # Skip performance tests if performance testing is disabled
    if item.get_closest_marker("performance"):
        if os.environ.get("SKIP_PERFORMANCE_TESTS", "").lower() in ("true", "1", "yes"):
            pytest.skip("Performance tests disabled by environment variable")


# Cleanup fixtures
@pytest.fixture(scope="function", autouse=True)
def cleanup_after_test():
    """Clean up after each test to prevent state leakage."""
    yield
    
    # Clear any global state that might affect other tests
    import gc
    gc.collect()
    
    # Reset any module-level variables
    try:
        # Clear caches if they exist
        from utils import cache_manager
        if hasattr(cache_manager, '_cached_instances'):
            cache_manager._cached_instances.clear()
    except ImportError:
        pass
    
    try:
        from utils import mcp_client
        if hasattr(mcp_client, '_default_client'):
            mcp_client._default_client = None
    except ImportError:
        pass