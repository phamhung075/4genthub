#!/usr/bin/env python
"""Quick test for session_hooks after fix."""
import subprocess

test_file = 'src/tests/unit/mcp_auto_injection/test_session_hooks.py::TestLogSessionStart'

print(f"Testing: {test_file}")
result = subprocess.run(
    ['python', '-m', 'pytest', test_file, '-x', '-v'],
    capture_output=True,
    text=True,
    timeout=20
)

print("Return code:", result.returncode)
if result.returncode == 0:
    print("✅ All TestLogSessionStart tests PASSED!")
else:
    print("❌ Some tests failed. Details:")
    for line in result.stdout.splitlines():
        if 'FAILED' in line or 'PASSED' in line:
            print(line)