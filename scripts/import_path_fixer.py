#!/usr/bin/env python3
"""
Automated script to fix import path issues in all failing test files.

This script reads the failed_tests.txt file and fixes the import path setup
in each test file by calculating the correct parents[N] expression based on
the file's location relative to 4genthub_main/src.
"""

import re
import sys
from pathlib import Path
from typing import List, Tuple, Optional

def calculate_correct_path_expression(test_file_path: Path, target_dir: Path) -> str:
    """
    Calculate the correct Path expression to reach target_dir from test_file_path.
    
    Args:
        test_file_path: Path to the test file
        target_dir: Path to 4genthub_main/src
        
    Returns:
        String expression like "Path(__file__).resolve().parents[2]"
    """
    # Get the directory containing the test file
    test_dir = test_file_path.parent
    
    # Calculate relative path from test_dir to target_dir
    try:
        # Count how many levels up we need to go from test file to reach 4genthub_main/src
        test_parts = test_dir.parts
        target_parts = target_dir.parts
        
        # Find the 4genthub_main part in both paths
        4genthub_index_test = -1
        4genthub_index_target = -1
        
        for i, part in enumerate(test_parts):
            if part == "4genthub_main":
                4genthub_index_test = i
                break
                
        for i, part in enumerate(target_parts):
            if part == "4genthub_main":
                4genthub_index_target = i
                break
        
        if 4genthub_index_test == -1 or 4genthub_index_target == -1:
            raise ValueError("Cannot find 4genthub_main in paths")
        
        # Count levels from test file back to 4genthub_main/src
        # test_parts[4genthub_index_test:] gives us ['4genthub_main', 'src', 'tests', 'unit', 'module', ...]
        # target_parts[4genthub_index_target:] gives us ['4genthub_main', 'src']
        
        test_depth = len(test_parts) - 4genthub_index_test - 1  # -1 because we don't count the file itself
        target_depth = len(target_parts) - 4genthub_index_target - 1
        
        # We need to go up (test_depth - target_depth) levels
        levels_up = test_depth - target_depth
        
        if levels_up <= 0:
            return "Path(__file__).parent"
        elif levels_up == 1:
            return "Path(__file__).parent.parent"
        else:
            return f"Path(__file__).resolve().parents[{levels_up-1}]"
            
    except Exception as e:
        print(f"Error calculating path for {test_file_path}: {e}")
        # Fallback to a reasonable default
        return "Path(__file__).resolve().parents[2]"

def find_and_fix_import_setup(file_content: str, correct_expression: str) -> Tuple[str, bool]:
    """
    Find and fix the import path setup in the file content.
    
    Returns:
        Tuple of (fixed_content, was_modified)
    """
    lines = file_content.split('\n')
    modified = False
    
    # Patterns to look for and fix
    patterns_to_fix = [
        # Pattern 1: project_root = Path(__file__).resolve().parent / "4genthub_main/src"
        (r'project_root\s*=\s*Path\(__file__\)\.resolve\(\)\.parent\s*/\s*["\']4genthub_main/src["\']',
         f'project_root = {correct_expression}'),
        
        # Pattern 2: project_root = Path(__file__).parent / "4genthub_main/src"  
        (r'project_root\s*=\s*Path\(__file__\)\.parent\s*/\s*["\']4genthub_main/src["\']',
         f'project_root = {correct_expression}'),
        
        # Pattern 3: project_root = Path(__file__).parent
        (r'project_root\s*=\s*Path\(__file__\)\.parent\s*$',
         f'project_root = {correct_expression}'),
        
        # Pattern 4: sys.path.insert(0, str(Path(__file__).parent / "4genthub_main/src"))
        (r'sys\.path\.insert\(0,\s*str\(Path\(__file__\)\.parent\s*/\s*["\']4genthub_main/src["\']\)\)',
         f'sys.path.insert(0, str({correct_expression}))'),
        
        # Pattern 5: sys.path.append('/absolute/path/to/4genthub_main/src')
        (r'sys\.path\.append\(["\'][^"\']*4genthub_main/src["\']\)',
         f'sys.path.append(str({correct_expression}))'),
        
        # Pattern 6: sys.path.insert(0, '/absolute/path/to/4genthub_main/src')
        (r'sys\.path\.insert\(0,\s*["\'][^"\']*4genthub_main/src["\']\)',
         f'sys.path.insert(0, str({correct_expression}))'),
        
        # Pattern 7: Any other variations that go directly to parent then add 4genthub_main/src
        (r'Path\(__file__\)[^=\n]*\.parent[^=\n]*/[^=\n]*["\']4genthub_main[/\\]src["\']',
         correct_expression)
    ]
    
    for i, line in enumerate(lines):
        for pattern, replacement in patterns_to_fix:
            if re.search(pattern, line):
                # For patterns that include the full assignment, replace the whole thing
                if 'project_root' in pattern or 'sys.path' in pattern:
                    lines[i] = re.sub(pattern, replacement, line)
                else:
                    # For just the path expression, replace just that part
                    lines[i] = re.sub(pattern, replacement, line)
                modified = True
                print(f"  Fixed line {i+1}: {line.strip()} -> {lines[i].strip()}")
                break
    
    return '\n'.join(lines), modified

def fix_test_file(test_file_path: Path, target_dir: Path) -> bool:
    """
    Fix the import paths in a single test file.
    
    Returns:
        True if file was modified, False otherwise
    """
    try:
        # Read the file
        with open(test_file_path, 'r', encoding='utf-8') as f:
            content = f.read()
        
        # Calculate correct expression
        correct_expr = calculate_correct_path_expression(test_file_path, target_dir)
        
        # Fix the content
        fixed_content, was_modified = find_and_fix_import_setup(content, correct_expr)
        
        if was_modified:
            # Write back the fixed content
            with open(test_file_path, 'w', encoding='utf-8') as f:
                f.write(fixed_content)
            print(f"✅ Fixed: {test_file_path}")
            return True
        else:
            print(f"⏭️  No fix needed: {test_file_path}")
            return False
            
    except Exception as e:
        print(f"❌ Error fixing {test_file_path}: {e}")
        return False

def main():
    """Main function to fix all failing test files."""
    
    # Set up paths
    project_root = Path(__file__).resolve().parent.parent  # Go up from scripts/ to project root
    target_dir = project_root / "4genthub_main" / "src"
    failed_tests_file = project_root / ".test_cache" / "failed_tests.txt"
    
    print("=== AUTOMATED TEST IMPORT PATH FIXER ===")
    print(f"Project root: {project_root}")
    print(f"Target directory: {target_dir}")
    print(f"Failed tests file: {failed_tests_file}")
    print()
    
    # Verify target directory exists
    if not target_dir.exists():
        print(f"❌ Target directory does not exist: {target_dir}")
        sys.exit(1)
    
    # Read failed tests file
    if not failed_tests_file.exists():
        print(f"❌ Failed tests file does not exist: {failed_tests_file}")
        sys.exit(1)
    
    with open(failed_tests_file, 'r') as f:
        failed_test_lines = f.read().strip().split('\n')
    
    # Extract file paths (remove line numbers) and fix incorrect paths
    test_files = []
    for line in failed_test_lines:
        if '→' in line:
            file_path = line.split('→')[1].strip()
        elif line.strip() and not line.strip().endswith('→'):
            # Handle lines without arrow prefix
            file_path = line.strip()
        else:
            continue
        
        # Fix incorrect path: replace 'src/tests/' with '4genthub_main/src/tests/'
        if '/src/tests/' in file_path and '4genthub_main' not in file_path:
            file_path = file_path.replace('/src/tests/', '/4genthub_main/src/tests/')
        
        test_files.append(Path(file_path))
    
    print(f"Found {len(test_files)} test files to fix")
    print()
    
    # Fix each test file
    fixed_count = 0
    skipped_count = 0
    error_count = 0
    
    for test_file in test_files:
        if not test_file.exists():
            print(f"⚠️  File not found: {test_file}")
            error_count += 1
            continue
        
        print(f"Processing: {test_file}")
        
        if fix_test_file(test_file, target_dir):
            fixed_count += 1
        else:
            skipped_count += 1
        print()
    
    # Summary
    print("=== SUMMARY ===")
    print(f"Files processed: {len(test_files)}")
    print(f"Files fixed: {fixed_count}")
    print(f"Files skipped (no changes needed): {skipped_count}")
    print(f"Files with errors: {error_count}")
    
    if fixed_count > 0:
        print(f"\n✅ Successfully fixed {fixed_count} test files!")
        print("You can now run the tests to verify the fixes.")
    else:
        print("\n⚠️  No files were modified. Check if the patterns need adjustment.")

if __name__ == "__main__":
    main()