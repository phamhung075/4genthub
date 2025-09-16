#!/usr/bin/env python3
"""Simple test runner that respects hook requirements."""
import sys
import os
import subprocess
from pathlib import Path

# Ensure we're in the right directory
os.chdir('/home/daihungpham/__projects__/agentic-project')

# Set environment variables to prevent file creation issues
os.environ['PYTHONDONTWRITEBYTECODE'] = '1'
os.environ['PYTEST_DISABLE_PLUGIN_AUTOLOAD'] = '1'

# Run pytest with minimal file creation
cmd = [
    sys.executable, "-m", "pytest",
    "src/tests/",
    "-x",  # Stop on first failure
    "--tb=short",  # Short traceback
    "-p", "no:cacheprovider",  # Disable cache
    "--no-header",  # No header
    "-q"  # Quiet
]

print("Running tests...")
print("-" * 60)

try:
    result = subprocess.run(cmd, capture_output=True, text=True, timeout=30)
    print(result.stdout)
    if result.stderr:
        print("STDERR:", result.stderr)
    sys.exit(result.returncode)
except subprocess.TimeoutExpired:
    print("Tests timed out after 30 seconds")
    sys.exit(1)
except Exception as e:
    print(f"Error running tests: {e}")
    sys.exit(1)