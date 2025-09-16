#!/usr/bin/env python3
"""
Test script to verify logging configuration works in both environments.
"""

import sys
import time
import logging
import pytest
from pathlib import Path

from fastmcp.utilities.logging import setup_comprehensive_logging, get_logging_info
from fastmcp.utilities.environment import get_environment_info, detect_environment


class TestLoggingConfiguration:
    """Test cases for logging configuration."""

    def test_environment_detection(self):
        """Test environment detection works correctly."""
        env_type = detect_environment()
        assert env_type in ["docker", "local"]
        print(f"Detected environment: {env_type}")

    def test_logging_setup(self):
        """Test that logging setup works without errors."""
        # Setup logging
        setup_comprehensive_logging(
            log_level="DEBUG",
            app_name="LoggingTest",
            enable_file_logging=True
        )

        # Get loggers
        fastmcp_logger = logging.getLogger("FastMCP.test")
        root_logger = logging.getLogger("test_logging")

        # Test basic logging
        fastmcp_logger.info("Test message from FastMCP logger")
        root_logger.info("Test message from root logger")

        assert True  # If we get here without exceptions, test passes

    def test_environment_info(self):
        """Test that environment info is collected correctly."""
        env_info = get_environment_info()

        required_keys = [
            'environment_type', 'log_directory', 'log_directory_exists',
            'platform', 'hostname', 'docker_env_exists'
        ]

        for key in required_keys:
            assert key in env_info, f"Missing key: {key}"

        print(f"Environment info: {env_info}")

    def test_logging_info(self):
        """Test that logging info can be retrieved."""
        setup_comprehensive_logging(
            log_level="INFO",
            app_name="LoggingTest",
            enable_file_logging=True
        )

        logging_info = get_logging_info()

        assert 'environment' in logging_info
        assert 'loggers' in logging_info
        assert 'FastMCP' in logging_info['loggers']
        assert 'root' in logging_info['loggers']

        print(f"Logging info: {logging_info}")


def manual_test_logging():
    """Manual test function to verify logging configuration."""
    print("=" * 60)
    print("TESTING DHAFNCKMCP LOGGING CONFIGURATION")
    print("=" * 60)

    # Setup logging
    setup_comprehensive_logging(
        log_level="DEBUG",
        app_name="LoggingTest",
        enable_file_logging=True
    )

    # Get loggers
    fastmcp_logger = logging.getLogger("FastMCP.test")
    root_logger = logging.getLogger("test_logging")

    # Get environment info
    env_info = get_environment_info()
    print(f"\n🌍 Environment Information:")
    print(f"   Environment Type: {env_info['environment_type']}")
    print(f"   Log Directory: {env_info['log_directory']}")
    print(f"   Log Directory Exists: {env_info['log_directory_exists']}")
    print(f"   Log Directory Writable: {env_info['log_directory_writable']}")
    print(f"   Platform: {env_info['platform']}")
    print(f"   Hostname: {env_info['hostname']}")
    print(f"   Docker Env Exists: {env_info['docker_env_exists']}")
    print(f"   Container Env Var: {env_info['container_env_var']}")

    # Get logging info
    try:
        logging_info = get_logging_info()
        print(f"\n📝 Logging Configuration:")
        fastmcp_handlers = logging_info['loggers']['FastMCP']['handlers']
        root_handlers = logging_info['loggers']['root']['handlers']

        print(f"   FastMCP Logger Handlers: {len(fastmcp_handlers)}")
        for i, handler in enumerate(fastmcp_handlers):
            print(f"     Handler {i+1}: {handler['type']} (Level: {handler['level']})")

        print(f"   Root Logger Handlers: {len(root_handlers)}")
        for i, handler in enumerate(root_handlers):
            print(f"     Handler {i+1}: {handler['type']} (Level: {handler['level']})")
    except Exception as e:
        print(f"   Error getting logging info: {e}")

    # Test logging at different levels
    print(f"\n🧪 Testing Log Messages:")
    print(f"   (Check console output and log files for these messages)")

    # Test FastMCP logger
    fastmcp_logger.debug("🔍 Debug message from FastMCP logger")
    fastmcp_logger.info("ℹ️ Info message from FastMCP logger")
    fastmcp_logger.warning("⚠️ Warning message from FastMCP logger")
    fastmcp_logger.error("❌ Error message from FastMCP logger")

    # Test root logger
    root_logger.debug("🔍 Debug message from root logger")
    root_logger.info("ℹ️ Info message from root logger")
    root_logger.warning("⚠️ Warning message from root logger")
    root_logger.error("❌ Error message from root logger")

    # Test multiline message
    fastmcp_logger.info("""📝 Multi-line test message:
    Line 1: Testing multiline logging
    Line 2: Should be properly formatted
    Line 3: In both console and file""")

    # Give time for handlers to write
    time.sleep(0.5)

    # Check if log files exist
    from fastmcp.utilities.environment import get_log_directory
    log_dir = get_log_directory()

    print(f"\n📁 Log Files Status:")
    if log_dir.exists():
        log_files = list(log_dir.glob("*.log*"))
        if log_files:
            print(f"   Found {len(log_files)} log files:")
            for log_file in sorted(log_files):
                size = log_file.stat().st_size if log_file.exists() else 0
                print(f"     - {log_file.name} ({size} bytes)")

                # Show last few lines of log file
                if size > 0:
                    try:
                        with open(log_file, 'r', encoding='utf-8') as f:
                            lines = f.readlines()
                            if lines:
                                print(f"       Last line: {lines[-1].strip()}")
                    except Exception as e:
                        print(f"       Error reading file: {e}")
        else:
            print(f"   ⚠️ No log files found in {log_dir}")
    else:
        print(f"   ❌ Log directory does not exist: {log_dir}")

    print(f"\n✅ Logging test completed!")
    print(f"=" * 60)


if __name__ == "__main__":
    manual_test_logging()