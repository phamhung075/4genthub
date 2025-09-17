#!/usr/bin/env python3
"""Fix test imports after services were moved to orchestrators directory"""

import os
import re
from pathlib import Path

def fix_imports_in_file(file_path):
    """Fix imports in a single file"""
    with open(file_path, 'r') as f:
        content = f.read()
    
    # Replace the import paths
    original_content = content
    content = re.sub(
        r'from fastmcp\.task_management\.application\.services\.',
        'from fastmcp.task_management.application.services.',
        content
    )
    
    # Also fix any relative imports that might exist
    content = re.sub(
        r'from \.\.\.\.application\.services\.',
        'from ....application.services.',
        content
    )
    
    if content != original_content:
        with open(file_path, 'w') as f:
            f.write(content)
        return True
    return False

def main():
    """Main function to fix all test imports"""
    test_dir = Path('/home/daihungpham/__projects__/agentic-project/4genthub_main/src/tests')
    
    fixed_files = []
    
    # Walk through all Python files in the tests directory
    for py_file in test_dir.rglob('*.py'):
        if '__pycache__' not in str(py_file):
            if fix_imports_in_file(py_file):
                fixed_files.append(py_file)
                print(f"Fixed imports in: {py_file}")
    
    print(f"\nFixed {len(fixed_files)} files")
    return fixed_files

if __name__ == '__main__':
    main()