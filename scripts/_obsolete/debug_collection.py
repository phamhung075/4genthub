#!/usr/bin/env python3
"""Debug collection issues"""
import sys
import os
from pathlib import Path

# Add the source path
project_root = Path(__file__).parent.parent
mcp_dir = project_root / "dhafnck_mcp_main"
sys.path.insert(0, str(mcp_dir / "src"))

# Set working directory
os.chdir(mcp_dir)

try:
    # Try to import pytest and run collection on a single file
    import pytest
    
    # Collect a simple test file
    result = pytest.main([
        'src/tests/ai_task_planning/domain/entities/planning_request_test.py',
        '--collect-only',
        '-v'
    ])
    
    print(f"Collection result: {result}")
    
except Exception as e:
    print(f"Error during collection: {e}")
    import traceback
    traceback.print_exc()