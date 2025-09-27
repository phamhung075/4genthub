#!/usr/bin/env python3
"""
Fix timezone imports for files using datetime.now(timezone.utc)
"""

import os
import re
import glob

def fix_timezone_imports():
    """Fix timezone imports in all Python files"""
    
    # Find all Python files in src directory
    python_files = []
    for root, dirs, files in os.walk('./src'):
        for file in files:
            if file.endswith('.py'):
                python_files.append(os.path.join(root, file))
    
    # Also include script files
    for root, dirs, files in os.walk('./scripts'):
        for file in files:
            if file.endswith('.py'):
                python_files.append(os.path.join(root, file))
    
    fixed_count = 0
    
    for file_path in python_files:
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()
            
            # Check if file uses timezone.utc
            if 'datetime.now(timezone.utc)' in content:
                # Check if timezone is already imported
                has_timezone_import = (
                    'from datetime import timezone' in content or
                    'from datetime import' in content and 'timezone' in content
                )
                
                if not has_timezone_import:
                    # Look for existing datetime import line
                    datetime_import_pattern = r'^(\s*)from datetime import (.*)$'
                    lines = content.split('\n')
                    modified = False
                    
                    for i, line in enumerate(lines):
                        match = re.match(datetime_import_pattern, line)
                        if match:
                            indent = match.group(1)
                            imports = match.group(2)
                            if 'timezone' not in imports:
                                # Add timezone to existing import
                                lines[i] = f"{indent}from datetime import {imports}, timezone"
                                modified = True
                                break
                    
                    # If no datetime import found, add one at the top after other imports
                    if not modified:
                        # Find a good place to insert the import (after other imports)
                        insert_pos = 0
                        for i, line in enumerate(lines):
                            if line.strip().startswith('from ') or line.strip().startswith('import '):
                                insert_pos = i + 1
                            elif line.strip() == '' and insert_pos > 0:
                                continue
                            elif line.strip() != '' and insert_pos > 0:
                                break
                        
                        if insert_pos > 0:
                            lines.insert(insert_pos, 'from datetime import timezone')
                            modified = True
                        else:
                            # Insert at beginning if no imports found
                            lines.insert(0, 'from datetime import timezone')
                            modified = True
                    
                    if modified:
                        # Write back the file
                        new_content = '\n'.join(lines)
                        with open(file_path, 'w', encoding='utf-8') as f:
                            f.write(new_content)
                        
                        print(f"Fixed: {file_path}")
                        fixed_count += 1
                
        except Exception as e:
            print(f"Error processing {file_path}: {e}")
    
    print(f"\nFixed timezone imports in {fixed_count} files")

if __name__ == "__main__":
    os.chdir('./agenthub_main')
    fix_timezone_imports()