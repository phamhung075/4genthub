#!/usr/bin/env python3
"""Batch test runner to identify which tests are actually failing"""

import sys
import os
import importlib.util
import traceback

# Setup paths
sys.path.insert(0, './agenthub_main/src')
os.chdir('./agenthub_main')
os.environ["HOOK_JWT_SECRET"] = "test-secret-key-for-hook-auth"

# Read failing tests
with open('./.test_cache/failed_tests.txt', 'r') as f:
    failed_tests = [line.strip() for line in f.readlines()]

print(f"Checking {len(failed_tests)} test files for import errors...\n")

errors_found = {}
success_count = 0

for test_file in failed_tests[:10]:  # Check first 10
    test_path = f"./agenthub_main/{test_file}"

    try:
        # Try to import the test module
        spec = importlib.util.spec_from_file_location("test_module", test_path)
        if spec and spec.loader:
            module = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(module)
            print(f"✓ {test_file}: Imports successful")
            success_count += 1
    except Exception as e:
        error_msg = str(e)
        # Extract the core error message
        if "No module named" in error_msg:
            errors_found[test_file] = f"Import error: {error_msg.split('No module named')[1].split()[0]}"
        elif "cannot import name" in error_msg:
            errors_found[test_file] = f"Import error: {error_msg}"
        else:
            errors_found[test_file] = f"Error: {error_msg[:100]}"
        print(f"✗ {test_file}: {errors_found[test_file]}")

print(f"\nSummary: {success_count}/{10} test files can be imported successfully")
if errors_found:
    print("\nErrors found:")
    for test_file, error in errors_found.items():
        print(f"  - {test_file}: {error}")