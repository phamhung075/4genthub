#!/usr/bin/env python3
"""
Script to fix import path issues in the 4genthub test suite
"""

import os
import re
from pathlib import Path

def fix_infrastructure_imports():
    """Fix ....infrastructure imports to ...infrastructure in application/services and application/orchestrators/services"""
    
    # Paths that need fixing (from application/services/* or application/orchestrators/services/*)
    base_path = Path("/home/daihungpham/__projects__/agentic-project/4genthub_main/src/fastmcp/task_management/application")
    
    patterns_to_fix = [
        # From application/services/* to infrastructure (3 levels up)
        (base_path / "services", r"from \.\.\.\.infrastructure", "from ...infrastructure"),
        # From application/orchestrators/services/* to infrastructure (4 levels up) 
        (base_path / "orchestrators" / "services", r"from \.\.\.\.infrastructure", "from ...infrastructure"),
    ]
    
    files_fixed = 0
    
    for directory, old_pattern, new_replacement in patterns_to_fix:
        if not directory.exists():
            print(f"Directory {directory} does not exist, skipping...")
            continue
            
        print(f"Processing directory: {directory}")
        
        for py_file in directory.rglob("*.py"):
            try:
                with open(py_file, 'r', encoding='utf-8') as f:
                    content = f.read()
                
                # Check if file contains the pattern we want to fix
                if re.search(old_pattern, content):
                    print(f"Fixing imports in: {py_file}")
                    
                    # Replace the import pattern
                    new_content = re.sub(old_pattern, new_replacement, content)
                    
                    # Write back the fixed content
                    with open(py_file, 'w', encoding='utf-8') as f:
                        f.write(new_content)
                    
                    files_fixed += 1
                    
            except Exception as e:
                print(f"Error processing {py_file}: {e}")
    
    print(f"Fixed imports in {files_fixed} files")

if __name__ == "__main__":
    fix_infrastructure_imports()
    print("Import fixing completed!")
