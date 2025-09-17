#!/usr/bin/env python3
"""
Quick test import checker to identify problematic test files
"""

import os
import sys
import subprocess
from pathlib import Path

def check_test_imports():
    """Check for import issues in test files"""
    test_dir = Path("/home/daihungpham/__projects__/agentic-project/4genthub_main/src/tests")
    errors_found = []
    
    for test_file in test_dir.rglob("*.py"):
        try:
            # Try to compile the file
            result = subprocess.run([
                sys.executable, "-m", "py_compile", str(test_file)
            ], capture_output=True, text=True, timeout=10)
            
            if result.returncode != 0:
                errors_found.append({
                    "file": str(test_file),
                    "error": result.stderr.strip()
                })
                
        except subprocess.TimeoutExpired:
            errors_found.append({
                "file": str(test_file),
                "error": "Compilation timeout"
            })
        except Exception as e:
            errors_found.append({
                "file": str(test_file),
                "error": f"Check failed: {e}"
            })
    
    return errors_found

if __name__ == "__main__":
    print("Checking test imports...")
    errors = check_test_imports()
    
    print(f"\nFound {len(errors)} files with issues:")
    for error in errors[:20]:  # Show first 20 errors
        print(f"\nFile: {error['file']}")
        print(f"Error: {error['error']}")
        
    if len(errors) > 20:
        print(f"\n... and {len(errors) - 20} more errors")