#!/usr/bin/env python
"""Quick test diagnostics for iteration 34."""
import subprocess
import sys

# Test one file at a time
test_file = 'src/tests/unit/mcp_auto_injection/test_session_hooks.py'

print(f"Testing: {test_file}")
result = subprocess.run(
    ['python', '-m', 'pytest', test_file, '-x', '--tb=line', '-v'],
    capture_output=True,
    text=True,
    timeout=20
)

print("Return code:", result.returncode)
print("\nFailed tests (if any):")
for line in result.stdout.splitlines():
    if 'FAILED' in line or 'ERROR' in line:
        print(line)

# Show error details
if result.returncode != 0:
    print("\n\nError details:")
    error_lines = []
    capture = False
    for line in result.stdout.splitlines():
        if 'FAILED' in line or 'ERROR' in line:
            capture = True
        if capture:
            error_lines.append(line)
            if len(error_lines) > 50:  # Limit output
                break
    print('\n'.join(error_lines[:50]))