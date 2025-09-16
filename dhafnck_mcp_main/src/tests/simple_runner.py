#!/usr/bin/env python3
"""Direct test runner without pytest to avoid hook issues."""
import sys
import os
from pathlib import Path
import unittest
import importlib

# Setup path
project_root = Path(__file__).parent.parent.parent  # dhafnck_mcp_main
src_path = project_root / "src"
sys.path.insert(0, str(src_path))

# Set test environment
os.environ['TESTING'] = 'true'
os.environ['PYTHONDONTWRITEBYTECODE'] = '1'

def run_test_imports():
    """Try to import test modules to find failures."""
    test_results = []

    # List of test files to check
    test_files = [
        "tests.shared.infrastructure.messaging.event_bus_test",
        "tests.monitoring_validation_test",
        "tests.integration.test_service_account_auth",
    ]

    for test_module in test_files:
        try:
            print(f"Importing {test_module}...")
            module = importlib.import_module(test_module)
            test_results.append((test_module, "OK", None, module))
            print(f"  ✓ Success")
        except ImportError as e:
            test_results.append((test_module, "IMPORT_ERROR", str(e), None))
            print(f"  ✗ Import Error: {e}")
        except Exception as e:
            test_results.append((test_module, "ERROR", str(e), None))
            print(f"  ✗ Error: {e}")

    return test_results

def run_unittest_tests(test_module):
    """Run unittest tests from a module."""
    loader = unittest.TestLoader()
    suite = loader.loadTestsFromModule(test_module)
    runner = unittest.TextTestRunner(verbosity=1)
    result = runner.run(suite)
    return result.wasSuccessful(), len(result.failures), len(result.errors)

def main():
    print("=" * 60)
    print("Direct Test Runner")
    print("=" * 60)

    results = run_test_imports()

    print("\n" + "=" * 60)
    print("Import Summary:")
    print("=" * 60)

    ok_count = sum(1 for _, status, _, _ in results if status == "OK")
    fail_count = len(results) - ok_count

    print(f"Total: {len(results)} modules")
    print(f"Import Success: {ok_count}")
    print(f"Import Failed: {fail_count}")

    if fail_count > 0:
        print("\nFailed imports:")
        for module, status, error, _ in results:
            if status != "OK":
                print(f"  - {module}: {error}")
        return 1

    # Run tests for successfully imported modules
    print("\n" + "=" * 60)
    print("Running Tests:")
    print("=" * 60)

    total_tests = 0
    failed_tests = 0
    error_tests = 0

    for module_name, status, _, module in results:
        if status == "OK" and module:
            print(f"\nTesting {module_name}...")
            try:
                success, failures, errors = run_unittest_tests(module)
                if not success:
                    failed_tests += failures
                    error_tests += errors
                    print(f"  ✗ Failures: {failures}, Errors: {errors}")
                else:
                    print(f"  ✓ All tests passed")
            except Exception as e:
                print(f"  ✗ Error running tests: {e}")
                error_tests += 1

    print("\n" + "=" * 60)
    print("Final Summary:")
    print("=" * 60)
    print(f"Failed tests: {failed_tests}")
    print(f"Error tests: {error_tests}")

    return 0 if (failed_tests == 0 and error_tests == 0) else 1

if __name__ == "__main__":
    sys.exit(main())