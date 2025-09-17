#!/usr/bin/env python3
"""
Test Runner for Session and State Management Tests

Comprehensive test runner that executes all session and state management tests
with proper setup, teardown, and reporting.

Part of subtask: a160a5a8-e058-4594-8521-1a14121d2b6c
"""

import pytest
import sys
import os
from pathlib import Path
import tempfile
import shutil
import logging
from datetime import datetime

# Add hooks utils to path
hooks_utils_path = Path(__file__).parent.parent.parent.parent.parent / '.claude' / 'hooks' / 'utils'
sys.path.insert(0, str(hooks_utils_path.absolute()))

# Test configuration
TEST_CONFIG = {
    "verbose": True,
    "capture": "no",  # Don't capture output for debugging
    "tb": "short",    # Short traceback format
    "maxfail": 5,     # Stop after 5 failures
    "timeout": 300,   # 5 minute timeout per test
}

def setup_test_environment():
    """Set up the test environment."""
    print("Setting up test environment for session and state management...")

    # Create temporary directory for test data
    temp_dir = tempfile.mkdtemp(prefix="session_state_tests_")
    os.environ['TEST_TEMP_DIR'] = temp_dir

    # Set up logging for tests
    logging.basicConfig(
        level=logging.DEBUG,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        handlers=[
            logging.FileHandler(Path(temp_dir) / 'test.log'),
            logging.StreamHandler()
        ]
    )

    logger = logging.getLogger(__name__)
    logger.info(f"Test environment set up in: {temp_dir}")

    return temp_dir

def teardown_test_environment(temp_dir):
    """Clean up the test environment."""
    print(f"Cleaning up test environment: {temp_dir}")

    try:
        shutil.rmtree(temp_dir)
        print("Test environment cleaned up successfully")
    except Exception as e:
        print(f"Warning: Could not clean up test directory: {e}")

def run_session_tracker_tests():
    """Run session tracker tests."""
    print("\n" + "="*60)
    print("RUNNING SESSION TRACKER TESTS")
    print("="*60)

    test_file = Path(__file__).parent / "test_session_tracker.py"

    args = [
        str(test_file),
        "-v" if TEST_CONFIG["verbose"] else "",
        f"--tb={TEST_CONFIG['tb']}",
        f"--maxfail={TEST_CONFIG['maxfail']}",
        f"--timeout={TEST_CONFIG['timeout']}",
        "-s" if TEST_CONFIG["capture"] == "no" else "",
    ]

    # Remove empty strings
    args = [arg for arg in args if arg]

    result = pytest.main(args)
    return result

def run_role_enforcer_tests():
    """Run role enforcer tests."""
    print("\n" + "="*60)
    print("RUNNING ROLE ENFORCER TESTS")
    print("="*60)

    test_file = Path(__file__).parent / "test_role_enforcer.py"

    args = [
        str(test_file),
        "-v" if TEST_CONFIG["verbose"] else "",
        f"--tb={TEST_CONFIG['tb']}",
        f"--maxfail={TEST_CONFIG['maxfail']}",
        f"--timeout={TEST_CONFIG['timeout']}",
        "-s" if TEST_CONFIG["capture"] == "no" else "",
    ]

    # Remove empty strings
    args = [arg for arg in args if arg]

    result = pytest.main(args)
    return result

def run_integration_tests():
    """Run integration tests."""
    print("\n" + "="*60)
    print("RUNNING INTEGRATION TESTS")
    print("="*60)

    test_file = Path(__file__).parent / "test_session_state_integration.py"

    args = [
        str(test_file),
        "-v" if TEST_CONFIG["verbose"] else "",
        f"--tb={TEST_CONFIG['tb']}",
        f"--maxfail={TEST_CONFIG['maxfail']}",
        f"--timeout={TEST_CONFIG['timeout']}",
        "-s" if TEST_CONFIG["capture"] == "no" else "",
    ]

    # Remove empty strings
    args = [arg for arg in args if arg]

    result = pytest.main(args)
    return result

def run_persistence_tests():
    """Run state persistence tests."""
    print("\n" + "="*60)
    print("RUNNING STATE PERSISTENCE TESTS")
    print("="*60)

    test_file = Path(__file__).parent / "test_state_persistence.py"

    args = [
        str(test_file),
        "-v" if TEST_CONFIG["verbose"] else "",
        f"--tb={TEST_CONFIG['tb']}",
        f"--maxfail={TEST_CONFIG['maxfail']}",
        f"--timeout={TEST_CONFIG['timeout']}",
        "-s" if TEST_CONFIG["capture"] == "no" else "",
    ]

    # Remove empty strings
    args = [arg for arg in args if arg]

    result = pytest.main(args)
    return result

def run_all_tests():
    """Run all session and state management tests."""
    print("="*60)
    print("SESSION AND STATE MANAGEMENT TEST SUITE")
    print(f"Started at: {datetime.now().isoformat()}")
    print("="*60)

    temp_dir = setup_test_environment()

    try:
        results = {}

        # Run individual test suites
        results['session_tracker'] = run_session_tracker_tests()
        results['role_enforcer'] = run_role_enforcer_tests()
        results['integration'] = run_integration_tests()
        results['persistence'] = run_persistence_tests()

        # Print summary
        print("\n" + "="*60)
        print("TEST SUITE SUMMARY")
        print("="*60)

        total_failures = 0
        for test_suite, result in results.items():
            status = "PASSED" if result == 0 else "FAILED"
            print(f"{test_suite.replace('_', ' ').title()}: {status}")
            if result != 0:
                total_failures += 1

        print(f"\nTotal test suites: {len(results)}")
        print(f"Failed test suites: {total_failures}")
        print(f"Overall result: {'PASSED' if total_failures == 0 else 'FAILED'}")
        print(f"Completed at: {datetime.now().isoformat()}")

        return total_failures == 0

    finally:
        teardown_test_environment(temp_dir)

def run_quick_tests():
    """Run a quick subset of tests for development."""
    print("="*60)
    print("QUICK TEST SUITE (Session and State Management)")
    print("="*60)

    temp_dir = setup_test_environment()

    try:
        # Run just the core functionality tests
        test_files = [
            "test_session_tracker.py::TestSessionTracker::test_get_current_session_new",
            "test_session_tracker.py::TestSessionTracker::test_add_modified_file",
            "test_role_enforcer.py::TestRoleEnforcer::test_check_tool_permission_allowed",
            "test_role_enforcer.py::TestRoleEnforcer::test_check_tool_permission_blocked",
            "test_session_state_integration.py::TestSessionStateIntegration::test_session_tracks_role_changes",
        ]

        args = [
            *[str(Path(__file__).parent / test) for test in test_files],
            "-v",
            "--tb=short",
            "-s",
        ]

        result = pytest.main(args)

        print(f"\nQuick test result: {'PASSED' if result == 0 else 'FAILED'}")
        return result == 0

    finally:
        teardown_test_environment(temp_dir)

def check_dependencies():
    """Check if all required dependencies are available."""
    print("Checking test dependencies...")

    missing_deps = []

    # Check for required modules
    required_modules = [
        'pytest',
        'freezegun',
    ]

    for module in required_modules:
        try:
            __import__(module)
            print(f"✓ {module}")
        except ImportError:
            print(f"✗ {module} (missing)")
            missing_deps.append(module)

    # Check for our modules
    our_modules = [
        'session_tracker',
        'role_enforcer',
        'agent_state_manager',
    ]

    for module in our_modules:
        try:
            __import__(module)
            print(f"✓ {module}")
        except ImportError:
            print(f"? {module} (will be skipped)")

    if missing_deps:
        print(f"\nMissing dependencies: {', '.join(missing_deps)}")
        print("Install with: pip install " + " ".join(missing_deps))
        return False

    print("All dependencies available!")
    return True

if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="Run session and state management tests")
    parser.add_argument("--quick", action="store_true", help="Run quick test suite")
    parser.add_argument("--check-deps", action="store_true", help="Check dependencies only")
    parser.add_argument("--verbose", action="store_true", help="Verbose output")
    parser.add_argument("--suite", choices=["session", "role", "integration", "persistence"],
                       help="Run specific test suite")

    args = parser.parse_args()

    if args.verbose:
        TEST_CONFIG["verbose"] = True

    if args.check_deps:
        check_dependencies()
        sys.exit(0)

    # Check dependencies first
    if not check_dependencies():
        print("Cannot run tests due to missing dependencies")
        sys.exit(1)

    try:
        if args.quick:
            success = run_quick_tests()
        elif args.suite:
            temp_dir = setup_test_environment()
            try:
                if args.suite == "session":
                    result = run_session_tracker_tests()
                elif args.suite == "role":
                    result = run_role_enforcer_tests()
                elif args.suite == "integration":
                    result = run_integration_tests()
                elif args.suite == "persistence":
                    result = run_persistence_tests()
                success = result == 0
            finally:
                teardown_test_environment(temp_dir)
        else:
            success = run_all_tests()

        sys.exit(0 if success else 1)

    except KeyboardInterrupt:
        print("\nTests interrupted by user")
        sys.exit(130)
    except Exception as e:
        print(f"\nUnexpected error: {e}")
        sys.exit(1)