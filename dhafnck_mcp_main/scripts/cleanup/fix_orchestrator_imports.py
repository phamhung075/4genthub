#!/usr/bin/env python3
"""Fix import paths in orchestrator service files."""

import re
import os
from pathlib import Path

# Base directory for orchestrator services
base_dir = Path("/home/daihungpham/__projects__/agentic-project/dhafnck_mcp_main/src/fastmcp/task_management/application/orchestrators/services")

# Import patterns to fix
replacements = [
    # DTOs should come from application level (3 levels up)
    (r'from \.\.dtos\.', 'from ...dtos.'),
    # Domain should be 4 levels up from orchestrator services
    (r'from \.\.\.domain\.', 'from ....domain.'),
    # Infrastructure should be 4 levels up
    (r'from \.\.\.infrastructure\.', 'from ....infrastructure.'),
    # Use cases should be from application level
    (r'from \.\.\.use_cases\.', 'from ...use_cases.'),
    # Factories from infrastructure
    (r'from \.\.\.factories\.', 'from ....infrastructure.factories.'),
]

def fix_imports(file_path):
    """Fix import paths in a Python file."""
    try:
        with open(file_path, 'r') as f:
            content = f.read()
        
        original = content
        for pattern, replacement in replacements:
            content = re.sub(pattern, replacement, content)
        
        if content != original:
            with open(file_path, 'w') as f:
                f.write(content)
            print(f"Fixed imports in: {file_path.name}")
            return True
        return False
    except Exception as e:
        print(f"Error processing {file_path}: {e}")
        return False

# Process all Python files in the orchestrator services directory
fixed_count = 0
for py_file in base_dir.glob("*.py"):
    if fix_imports(py_file):
        fixed_count += 1

print(f"\nFixed imports in {fixed_count} files")