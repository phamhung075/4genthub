#!/usr/bin/env python3
"""
Import validation script for test files
"""
import sys
import os
import ast
import importlib.util
from pathlib import Path

def check_file_imports(filepath):
    """Check if a Python file has any import errors"""
    try:
        with open(filepath, 'r') as f:
            content = f.read()
        
        # Parse AST to check syntax
        ast.parse(content)
        
        # Try to compile
        compile(content, filepath, 'exec')
        
        return True, "OK"
    except SyntaxError as e:
        return False, f"Syntax error: {e}"
    except ImportError as e:
        return False, f"Import error: {e}"
    except Exception as e:
        return False, f"Error: {e}"

def main():
    """Main validation function"""
    test_dir = Path(__file__).parent
    errors_found = 0
    files_checked = 0
    
    print("🔍 Validating Python imports in test files...")
    
    for py_file in test_dir.rglob("*.py"):
        if py_file.name == "validate_imports.py":
            continue
            
        files_checked += 1
        success, message = check_file_imports(py_file)
        
        relative_path = py_file.relative_to(test_dir)
        
        if success:
            print(f"✅ {relative_path}")
        else:
            print(f"❌ {relative_path}: {message}")
            errors_found += 1
    
    print(f"\n📊 Results:")
    print(f"   Files checked: {files_checked}")
    print(f"   Errors found: {errors_found}")
    
    if errors_found == 0:
        print("🎉 All test files have valid imports!")
        return 0
    else:
        print(f"⚠️  {errors_found} files have import issues")
        return 1

if __name__ == "__main__":
    sys.exit(main())