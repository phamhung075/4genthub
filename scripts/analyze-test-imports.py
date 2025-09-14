#!/usr/bin/env python3
"""Analyze imports from failing test files to find patterns"""

import sys
import os
import re

# Read failing tests list
with open('.test_cache/failed_tests.txt', 'r') as f:
    failed_tests = [line.strip().replace('src/tests/', '') for line in f.readlines()]

print(f"Analyzing {len(failed_tests)} failing test files...")
print("=" * 60)

# Analyze first 10 test files for import issues
issues_found = []
for test_file in failed_tests[:10]:
    test_path = f"dhafnck_mcp_main/src/tests/{test_file}"
    if not os.path.exists(test_path):
        issues_found.append(f"File not found: {test_path}")
        continue

    with open(test_path, 'r') as f:
        content = f.read()

    # Check for common issues
    if 'datetime.utcnow()' in content:
        issues_found.append(f"{test_file}: Uses datetime.utcnow() instead of datetime.now(timezone.utc)")

    if 'pytest_request' in content:
        issues_found.append(f"{test_file}: Uses pytest_request instead of request")

    # Check for missing timezone import when using datetime.now
    if 'datetime.now(' in content and 'from datetime import' in content:
        if 'timezone' not in content:
            issues_found.append(f"{test_file}: Missing timezone import")

print("\nIssues found:")
for issue in issues_found:
    print(f"  - {issue}")

if not issues_found:
    print("  No obvious issues found in first 10 test files")