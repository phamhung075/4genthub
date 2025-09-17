#!/usr/bin/env python3
"""
Test runner script to run tests individually to avoid SQLAlchemy table redefinition errors
"""
import subprocess
import sys
import os

# Set up environment
os.environ['PYTHONPATH'] = os.path.join(os.getcwd(), 'src')

# List of test files to run
test_files = [
    "src/tests/auth/interface/fastapi_auth_test.py",
    "src/tests/auth/mcp_integration/__init___test.py",
    "src/tests/auth/mcp_integration/repository_filter_test.py",
    "src/tests/auth/middleware/__init___test.py",
    "src/tests/server/auth/auth_test.py",
]

# Run each test file separately
for test_file in test_files:
    if os.path.exists(test_file):
        print(f"\n{'='*60}")
        print(f"Running: {test_file}")
        print(f"{'='*60}")
        
        # Run the test
        result = subprocess.run(
            [sys.executable, "-m", "pytest", test_file, "-v", "--tb=short"],
            capture_output=False
        )
        
        if result.returncode != 0:
            print(f"\n❌ Test failed: {test_file}")
        else:
            print(f"\n✅ Test passed: {test_file}")
    else:
        print(f"\n⚠️  Test file not found: {test_file}")

print("\n" + "="*60)
print("Test run complete!")