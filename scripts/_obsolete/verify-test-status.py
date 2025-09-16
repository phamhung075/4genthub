#!/usr/bin/env python3
"""Verify test status by comparing test files with cache"""

import os
import hashlib

# Read cache files
with open('.test_cache/failed_tests.txt', 'r') as f:
    failed_tests = [line.strip() for line in f.readlines()]

with open('.test_cache/passed_tests.txt', 'r') as f:
    passed_tests = [line.strip() for line in f.readlines() if line.strip()]

with open('.test_cache/test_hashes.txt', 'r') as f:
    test_hashes = {}
    for line in f.readlines():
        if ':' in line:
            test_file, hash_val = line.strip().split(':', 1)
            test_hashes[test_file] = hash_val

print(f"Test Cache Status:")
print(f"  Failed tests: {len(failed_tests)}")
print(f"  Passed tests: {len(passed_tests)}")
print(f"  Test hashes: {len(test_hashes)}")
print()

# Check if any failed tests are also in passed tests
overlap = set(failed_tests) & set(passed_tests)
if overlap:
    print(f"WARNING: {len(overlap)} tests are in both failed and passed lists:")
    for test in sorted(overlap)[:5]:
        print(f"  - {test}")

# Check file modification status for failed tests
print("\nChecking if failed test files have been modified since last run...")
modified_count = 0
for test_file in failed_tests[:10]:
    full_path = f"dhafnck_mcp_main/{test_file}"
    if os.path.exists(full_path):
        with open(full_path, 'rb') as f:
            current_hash = hashlib.md5(f.read()).hexdigest()

        cached_hash = test_hashes.get(test_file)
        if cached_hash and cached_hash != current_hash:
            print(f"  ✓ {test_file}: Modified (needs re-testing)")
            modified_count += 1

if modified_count > 0:
    print(f"\n{modified_count} test files have been modified and should be re-tested")