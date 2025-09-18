#!/usr/bin/env python3
"""
Hook Proxy Creator for Claude Code

This script creates hook proxy files in subdirectories to solve the issue where
Claude Code invokes hooks using relative paths from the current working directory.

Usage:
    python scripts/create_hook_proxies.py [subdirectory]

If no subdirectory is specified, it will create proxies in common locations
like agenthub-frontend.
"""

import sys
import os
from pathlib import Path


def create_hook_proxy(hook_name, target_dir, is_optional=False):
    """
    Create a hook proxy file in the target directory.

    Args:
        hook_name: Name of the hook (e.g., 'pre_tool_use.py')
        target_dir: Directory to create the proxy in
        is_optional: Whether the real hook is optional (for post_tool_use.py)
    """
    proxy_content = f'''#!/usr/bin/env python3
"""
Hook Proxy for Claude Code - Subdirectory Support ({hook_name})

This proxy script solves the issue where Claude Code invokes hooks using relative
paths from the current working directory. When working in subdirectories, the
hook path doesn't resolve correctly.

This proxy:
1. Finds the project root by looking for CLAUDE.md
2. Locates the real hook at the project root
3. Executes it with all original arguments
4. Preserves exit codes and output
"""

import os
import sys
import subprocess
from pathlib import Path


def find_project_root(start_path=None):
    """
    Find the project root by looking for CLAUDE.md file.

    Args:
        start_path: Directory to start search from (defaults to current dir)

    Returns:
        Path to project root or None if not found
    """
    current = Path(start_path or os.getcwd()).resolve()

    # Search upward for CLAUDE.md file
    while current != current.parent:
        if (current / 'CLAUDE.md').exists():
            return current
        current = current.parent

    return None


def main():
    """
    Main proxy function that locates and executes the real hook.
    """
    try:
        # Find the project root
        project_root = find_project_root()
        if not project_root:
            print("Error: Could not find project root (CLAUDE.md not found)", file=sys.stderr)
            sys.exit(1)

        # Locate the real hook
        real_hook_path = project_root / '.claude' / 'hooks' / '{hook_name}'
        if not real_hook_path.exists():
            {'# Hook is optional, silently succeed if not found' if is_optional else 'print(f"Error: Real hook not found at {{real_hook_path}}", file=sys.stderr)'}
            {'sys.exit(0)' if is_optional else 'sys.exit(1)'}

        # Execute the real hook with all original arguments
        # Use subprocess to preserve all behavior including stdout, stderr, and exit codes
        result = subprocess.run([sys.executable, str(real_hook_path)] + sys.argv[1:])
        sys.exit(result.returncode)

    except Exception as e:
        print(f"Hook proxy error: {{e}}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()'''

    # Create the target directory
    hook_dir = target_dir / '.claude' / 'hooks'
    hook_dir.mkdir(parents=True, exist_ok=True)

    # Write the proxy file
    proxy_path = hook_dir / hook_name
    proxy_path.write_text(proxy_content)
    proxy_path.chmod(0o755)

    print(f"Created hook proxy: {proxy_path}")


def main():
    """Main function to create hook proxies."""
    # Get the project root
    project_root = Path(__file__).parent.parent

    # Determine target directories
    if len(sys.argv) > 1:
        target_dirs = [Path(sys.argv[1])]
    else:
        # Default common subdirectories
        target_dirs = [
            project_root / 'agenthub-frontend',
            # Add other common subdirectories here as needed
        ]

    # Create proxies for each target directory
    for target_dir in target_dirs:
        if not target_dir.exists():
            print(f"Warning: Directory {target_dir} does not exist, skipping")
            continue

        print(f"Creating hook proxies in {target_dir}")

        # Create pre_tool_use.py proxy (required)
        create_hook_proxy('pre_tool_use.py', target_dir, is_optional=False)

        # Create post_tool_use.py proxy (optional)
        create_hook_proxy('post_tool_use.py', target_dir, is_optional=True)


if __name__ == "__main__":
    main()