#!/usr/bin/env python
"""Test collection checker."""
import os
os.chdir('/home/daihungpham/__projects__/agentic-project/4genthub_main')

import subprocess
result = subprocess.run(
    ['python', '-m', 'pytest', '--collect-only', 'src/tests/unit/mcp_auto_injection/test_session_hooks.py'],
    capture_output=True,
    text=True
)

print("Collection errors:", result.stderr[:500] if result.stderr else "None")