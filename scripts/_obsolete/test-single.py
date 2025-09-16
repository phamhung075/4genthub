#!/usr/bin/env python
"""Quick test runner to check specific test file errors"""
import sys
import os
import pytest

# Add project to path
project_root = "/home/daihungpham/__projects__/agentic-project/dhafnck_mcp_main"
sys.path.insert(0, os.path.join(project_root, "src"))

# Run a specific test file
test_file = sys.argv[1] if len(sys.argv) > 1 else "src/tests/task_management/application/use_cases/context_search_test.py"
os.chdir(project_root)

# Run pytest on the file
exit_code = pytest.main([test_file, "-v", "--tb=short"])
sys.exit(exit_code)