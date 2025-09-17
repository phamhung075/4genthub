#!/usr/bin/env python3
"""
Batch test checker - efficiently identify which tests are still failing
"""
import subprocess
import sys
from pathlib import Path

def test_file(test_path):
    """Test a single file and return its status"""
    try:
        result = subprocess.run(
            [sys.executable, "-m", "pytest", test_path, "-q", "--tb=no"],
            capture_output=True,
            text=True,
            timeout=30
        )
        return result.returncode == 0
    except subprocess.TimeoutExpired:
        return False
    except Exception:
        return False

def main():
    """Check all tests in failed_tests.txt and report status"""
    failed_tests_file = Path("/home/daihungpham/__projects__/agentic-project/.test_cache/failed_tests.txt")

    if not failed_tests_file.exists():
        print("No failed_tests.txt file found")
        return

    with open(failed_tests_file, 'r') as f:
        test_lines = f.readlines()

    still_failing = []
    now_passing = []

    for i, line in enumerate(test_lines[:10], 1):  # Test first 10 only for speed
        line = line.strip()
        if line and line.endswith('.py'):
            test_path = line
            # Convert to relative path for pytest
            test_path = test_path.replace("/home/daihungpham/__projects__/agentic-project/dhafnck_mcp_main/", "")

            print(f"Testing {i}/10: {test_path}")

            if test_file(test_path):
                now_passing.append(line)
                print(f"  ✅ PASSING")
            else:
                still_failing.append(line)
                print(f"  ❌ FAILING")

    print(f"\n📊 Results for first 10 tests:")
    print(f"✅ Now passing: {len(now_passing)}")
    print(f"❌ Still failing: {len(still_failing)}")

    if now_passing:
        print(f"\n🎉 Tests that are now passing:")
        for test in now_passing:
            print(f"  {test}")

    if still_failing:
        print(f"\n⚠️  Tests still failing:")
        for test in still_failing:
            print(f"  {test}")

if __name__ == "__main__":
    main()