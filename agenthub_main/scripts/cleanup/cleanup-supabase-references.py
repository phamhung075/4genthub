#!/usr/bin/env python3
"""
Script to clean up Supabase references and backward compatibility code
"""

import os
import re
from pathlib import Path
from typing import List, Tuple

def find_supabase_references(root_dir: str) -> List[Tuple[str, List[str]]]:
    """Find all files with Supabase references"""
    results = []
    path = Path(root_dir)
    
    for file_path in path.rglob("*.py"):
        if "__pycache__" in str(file_path):
            continue
            
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()
                lines = content.split('\n')
                
            supabase_lines = []
            for i, line in enumerate(lines, 1):
                if re.search(r'supabase|Supabase|SUPABASE', line, re.IGNORECASE):
                    supabase_lines.append(f"Line {i}: {line.strip()}")
            
            if supabase_lines:
                results.append((str(file_path), supabase_lines))
                
        except Exception as e:
            print(f"Error reading {file_path}: {e}")
    
    return results

def find_backward_compat_references(root_dir: str) -> List[Tuple[str, List[str]]]:
    """Find all files with backward compatibility references"""
    results = []
    path = Path(root_dir)
    
    patterns = [
        r'backward.*compat',
        r'legacy',
        r'deprecated',
        r'fallback.*user',
        r'default.*user',
        r'allow.*default',
        r'compat.*mode'
    ]
    
    for file_path in path.rglob("*.py"):
        if "__pycache__" in str(file_path):
            continue
            
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()
                lines = content.split('\n')
                
            compat_lines = []
            for i, line in enumerate(lines, 1):
                for pattern in patterns:
                    if re.search(pattern, line, re.IGNORECASE):
                        compat_lines.append(f"Line {i}: {line.strip()}")
                        break
            
            if compat_lines:
                results.append((str(file_path), compat_lines))
                
        except Exception as e:
            print(f"Error reading {file_path}: {e}")
    
    return results

def main():
    """Main function"""
    src_dir = "agenthub_main/src"
    
    print("=" * 80)
    print("SUPABASE REFERENCES ANALYSIS")
    print("=" * 80)
    
    # Find Supabase references
    supabase_refs = find_supabase_references(src_dir)
    
    if supabase_refs:
        print(f"\nFound {len(supabase_refs)} files with Supabase references:\n")
        for file_path, lines in supabase_refs[:10]:  # Show first 10
            print(f"\n📄 {file_path}")
            for line in lines[:3]:  # Show first 3 lines per file
                print(f"  {line}")
    else:
        print("\n✅ No Supabase references found!")
    
    print("\n" + "=" * 80)
    print("BACKWARD COMPATIBILITY REFERENCES ANALYSIS")
    print("=" * 80)
    
    # Find backward compatibility references
    compat_refs = find_backward_compat_references(src_dir)
    
    if compat_refs:
        print(f"\nFound {len(compat_refs)} files with backward compatibility references:\n")
        
        # Filter out test files and comments
        production_files = []
        for file_path, lines in compat_refs:
            if "/tests/" not in file_path:
                # Filter out comment lines
                actual_code = []
                for line in lines:
                    line_content = line.split(": ", 1)[1] if ": " in line else line
                    if not line_content.strip().startswith("#"):
                        actual_code.append(line)
                
                if actual_code:
                    production_files.append((file_path, actual_code))
        
        if production_files:
            print(f"\n⚠️  Found {len(production_files)} production files with compatibility code:\n")
            for file_path, lines in production_files[:10]:
                print(f"\n📄 {file_path}")
                for line in lines[:3]:
                    print(f"  {line}")
        else:
            print("\n✅ No backward compatibility code in production files!")
    else:
        print("\n✅ No backward compatibility references found!")
    
    print("\n" + "=" * 80)
    print("SUMMARY")
    print("=" * 80)
    print(f"Total files with Supabase references: {len(supabase_refs)}")
    print(f"Total files with compatibility references: {len(compat_refs)}")
    
    # List files that need cleanup
    files_to_clean = set()
    for file_path, _ in supabase_refs:
        if "/tests/" not in file_path:
            files_to_clean.add(file_path)
    
    if files_to_clean:
        print(f"\n🔧 Files that need cleanup ({len(files_to_clean)}):")
        for file_path in sorted(files_to_clean)[:20]:
            print(f"  - {file_path}")

if __name__ == "__main__":
    main()
