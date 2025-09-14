#!/usr/bin/env python3
"""Run a single test method to diagnose failures"""

import sys
import os
import pytest

# Setup path
sys.path.insert(0, '/home/daihungpham/__projects__/agentic-project/dhafnck_mcp_main/src')
os.chdir('/home/daihungpham/__projects__/agentic-project/dhafnck_mcp_main')

# Set required env var
os.environ["HOOK_JWT_SECRET"] = "test-secret-key-for-hook-auth"

# Run the test
print("Running hook_auth_test.py...")
result = pytest.main([
    'src/tests/auth/hook_auth_test.py',
    '-xvs',
    '--tb=short',
    '--capture=no'
])

print(f"\nTest result: {result}")
sys.exit(result)