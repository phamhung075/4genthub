"""
Performance Test Configuration and Fixtures

Provides shared fixtures and configuration for performance testing suite.
"""

import pytest
import tempfile
import asyncio
from pathlib import Path
from unittest.mock import Mock, patch

# Import performance test components
from .mocks.mock_mcp_server import create_performance_test_server, MockMCPServerManager
from . import PERFORMANCE_CONFIG, setup_performance_logger


@pytest.fixture(scope="session")
def performance_logger():
    """Setup performance testing logger."""
    return setup_performance_logger()


@pytest.fixture(scope="session") 
def event_loop():
    """Create event loop for async tests."""
    loop = asyncio.new_event_loop()
    yield loop
    loop.close()


@pytest.fixture
def temp_cache_dir():
    """Create temporary directory for cache testing."""
    with tempfile.TemporaryDirectory() as temp_dir:
        yield Path(temp_dir)


@pytest.fixture
def mock_mcp_server():
    """Create mock MCP server for controlled testing."""
    server = create_performance_test_server(
        response_delay=0.05,
        error_rate=0.0
    )
    yield server
    server.reset_metrics()


@pytest.fixture
def high_latency_server():
    """Create high latency server for stress testing."""
    from .mocks.mock_mcp_server import create_high_latency_server
    server = create_high_latency_server()
    yield server
    server.reset_metrics()


@pytest.fixture 
def unreliable_server():
    """Create unreliable server for fallback testing."""
    from .mocks.mock_mcp_server import create_unreliable_server
    server = create_unreliable_server()
    yield server
    server.reset_metrics()


@pytest.fixture(scope="session", autouse=True)
def cleanup_mock_servers():
    """Cleanup all mock servers after test session."""
    yield
    MockMCPServerManager().cleanup_all()


# Mark all tests in this package as performance tests
def pytest_configure(config):
    """Configure pytest for performance testing."""
    config.addinivalue_line(
        "markers", "performance: mark test as performance test"
    )


def pytest_collection_modifyitems(config, items):
    """Automatically mark all tests in performance package."""
    for item in items:
        if "performance" in str(item.fspath):
            item.add_marker(pytest.mark.performance)