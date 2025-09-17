#!/usr/bin/env python3
"""
Simple test runner to verify pytest collection works.
This script tests if our fixes allow pytest to run without hook interference.
"""

import subprocess
import sys
import os

def main():
    # Change to agenthub_main directory (as fixed in test-menu.sh)
    project_root = "/home/daihungpham/__projects__/agentic-project"
    agenthub_dir = f"{project_root}/agenthub_main"
    
    # Set PYTHONPATH
    env = os.environ.copy()
    env['PYTHONPATH'] = f"{agenthub_dir}/src:{env.get('PYTHONPATH', '')}"
    
    # Change to agenthub_main directory
    os.chdir(agenthub_dir)
    
    # Run pytest collection only
    try:
        result = subprocess.run([
            "python", "-m", "pytest", 
            "src/tests", "--co", "-v"
        ], capture_output=True, text=True, env=env, timeout=30)
        
        print("=== COMPREHENSIVE TEST STATUS ===")
        stdout_lines = result.stdout.split('\n')
        
        # Count different types of issues
        collection_errors = []
        warnings = []
        collected_count = 0
        
        for line in stdout_lines:
            if line.startswith('ERROR'):
                collection_errors.append(line.strip())
            elif 'Warning' in line or 'warning' in line:
                warnings.append(line.strip())
            elif 'collected' in line:
                import re
                match = re.search(r'(\d+) collected', line)
                if match:
                    collected_count = int(match.group(1))
        
        print(f"✅ TESTS COLLECTED: {collected_count}")
        print(f"❌ COLLECTION ERRORS: {len(collection_errors)}")
        print(f"⚠️  WARNINGS: {len(warnings)}")
        
        if collection_errors:
            print(f"\n=== REMAINING {len(collection_errors)} ERRORS ===")
            for i, error in enumerate(collection_errors[:10], 1):  # Show first 10
                print(f"{i}. {error}")
            if len(collection_errors) > 10:
                print(f"... and {len(collection_errors) - 10} more")
        
        if warnings and len(warnings) <= 5:
            print(f"\n=== REMAINING {len(warnings)} WARNINGS ===")
            for warning in warnings:
                print(f"  {warning}")
        elif warnings:
            print(f"\n=== {len(warnings)} WARNINGS (showing first 3) ===")
            for warning in warnings[:3]:
                print(f"  {warning}")
            print(f"  ... and {len(warnings) - 3} more warnings")
        print(f"\n=== RETURN CODE: {result.returncode} ===")
        
        # Count collected tests vs errors
        stdout = result.stdout
        if "collected" in stdout:
            import re
            collected_match = re.search(r'(\d+) collected', stdout)
            if collected_match:
                print(f"\n✅ SUCCESS: {collected_match.group(1)} tests collected!")
        
        error_count = stdout.count("ERROR collecting")
        if error_count > 0:
            print(f"\n❌ {error_count} collection errors found")
        else:
            print(f"\n✅ No collection errors!")
            
    except subprocess.TimeoutExpired:
        print("❌ Test collection timed out")
    except Exception as e:
        print(f"❌ Error running test: {e}")

if __name__ == "__main__":
    main()