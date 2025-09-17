#!/usr/bin/env python3
"""Test runner that respects file creation rules."""
import sys
import os
import subprocess
from pathlib import Path

# Set environment to prevent file creation in root
os.environ['PYTHONDONTWRITEBYTECODE'] = '1'

# Change to test directory to avoid creating files in root
project_root = Path(__file__).parent.parent
test_dir = project_root / "agenthub_main"
os.chdir(test_dir)

# Create a cache directory in the tests folder
cache_dir = test_dir / "src" / "tests" / ".pytest_cache"
cache_dir.mkdir(exist_ok=True)

# Run pytest with proper configuration
cmd = [
    sys.executable, "-m", "pytest",
    "src/tests/unit/",
    "-x",  # Stop on first failure
    "--tb=short",  # Short traceback
    "--no-header",  # No header
    "-q",  # Quiet mode
    "-p", "no:cacheprovider",  # Disable cache provider
    "--cache-clear"  # Clear cache
]

print(f"Running tests from: {test_dir}")
print(f"Command: {' '.join(cmd)}")
print("-" * 60)

result = subprocess.run(cmd, capture_output=True, text=True)
print(result.stdout)
if result.stderr:
    print("STDERR:", result.stderr)
print(f"Exit code: {result.returncode}")