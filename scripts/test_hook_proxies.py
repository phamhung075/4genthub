#!/usr/bin/env python3
"""
Test script for hook proxies

This script tests that hook proxies work correctly from subdirectories.
"""

import sys
import subprocess
from pathlib import Path


def test_hook_proxy(test_dir, hook_name):
    """
    Test a hook proxy from a specific directory.

    Args:
        test_dir: Directory to test from
        hook_name: Name of the hook to test
    """
    hook_path = test_dir / '.claude' / 'hooks' / hook_name

    if not hook_path.exists():
        print(f"❌ Hook proxy not found: {hook_path}")
        return False

    # Test that the proxy can find the project root
    test_script = f'''
import sys
sys.path.insert(0, "{hook_path.parent}")
from {hook_name[:-3]} import find_project_root

root = find_project_root()
if root:
    print(f"Found project root: {{root}}")
    real_hook = root / '.claude' / 'hooks' / '{hook_name}'
    print(f"Real hook exists: {{real_hook.exists()}}")
else:
    print("ERROR: Could not find project root")
    sys.exit(1)
'''

    try:
        result = subprocess.run(
            [sys.executable, '-c', test_script],
            cwd=test_dir,
            capture_output=True,
            text=True,
            timeout=10
        )

        if result.returncode == 0:
            print(f"✅ {hook_name} proxy works from {test_dir}")
            print(f"   Output: {result.stdout.strip()}")
            return True
        else:
            print(f"❌ {hook_name} proxy failed from {test_dir}")
            print(f"   Error: {result.stderr.strip()}")
            return False

    except subprocess.TimeoutExpired:
        print(f"⏰ {hook_name} proxy timed out from {test_dir}")
        return False
    except Exception as e:
        print(f"❌ {hook_name} proxy error from {test_dir}: {e}")
        return False


def main():
    """Main test function."""
    project_root = Path(__file__).parent.parent

    # Test directories
    test_dirs = [
        project_root / 'agenthub-frontend',
    ]

    # Test hooks
    hook_names = ['pre_tool_use.py', 'post_tool_use.py']

    print("Testing hook proxies...")
    print("=" * 50)

    all_passed = True

    for test_dir in test_dirs:
        if not test_dir.exists():
            print(f"⚠️  Test directory does not exist: {test_dir}")
            continue

        print(f"\nTesting from directory: {test_dir}")

        for hook_name in hook_names:
            if not test_hook_proxy(test_dir, hook_name):
                all_passed = False

    print("\n" + "=" * 50)
    if all_passed:
        print("✅ All hook proxy tests passed!")
    else:
        print("❌ Some hook proxy tests failed!")
        sys.exit(1)


if __name__ == "__main__":
    main()