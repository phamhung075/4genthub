#!/usr/bin/env python3
"""Fix import paths in orchestrator services."""

import os
import re
from pathlib import Path

def fix_imports_in_file(filepath):
    """Fix import paths in a single file."""
    with open(filepath, 'r') as f:
        content = f.read()
    
    # Fix the relative imports from ...infrastructure to ....infrastructure
    pattern = r'from \.\.\.infrastructure'
    replacement = r'from ....infrastructure'
    
    new_content = re.sub(pattern, replacement, content)
    
    if new_content != content:
        with open(filepath, 'w') as f:
            f.write(new_content)
        print(f"Fixed: {filepath}")
        return True
    return False

def main():
    """Main function to fix all import issues."""
    services_dir = Path('src/fastmcp/task_management/application/orchestrators/services')
    
    if not services_dir.exists():
        print(f"Directory not found: {services_dir}")
        return
    
    fixed_count = 0
    for py_file in services_dir.glob('*.py'):
        if fix_imports_in_file(py_file):
            fixed_count += 1
    
    print(f"\nFixed {fixed_count} files")

if __name__ == '__main__':
    main()
