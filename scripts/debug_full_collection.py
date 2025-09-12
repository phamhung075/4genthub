#!/usr/bin/env python3
"""Debug full collection issues"""
import sys
import os
import subprocess
from pathlib import Path

# Add the source path
project_root = Path(__file__).parent.parent
mcp_dir = project_root / "dhafnck_mcp_main"

def main():
    print("🧪 Debug Full Collection")
    print("=" * 50)
    
    os.chdir(mcp_dir)
    
    # Try different collection strategies
    strategies = [
        ("AI Task Planning Only", "src/tests/ai_task_planning/"),
        ("Unit Tests Only", "src/tests/unit/"),
        ("Integration Tests Only", "src/tests/integration/"), 
        ("All Tests", "src/tests/")
    ]
    
    for name, path in strategies:
        print(f"\n📋 Testing: {name}")
        try:
            result = subprocess.run([
                sys.executable, "-m", "pytest", 
                path, 
                "--collect-only", 
                "-q",
                "--tb=short"
            ], 
            capture_output=True, 
            text=True, 
            timeout=30
            )
            
            if result.returncode == 0:
                # Count collected tests
                lines = result.stdout.strip().split('\n')
                collected_line = [line for line in lines if 'collected' in line.lower()]
                if collected_line:
                    print(f"✅ {collected_line[-1]}")
                else:
                    print("✅ Collection successful")
            else:
                print(f"❌ Failed (code: {result.returncode})")
                # Show first few lines of stderr
                if result.stderr:
                    error_lines = result.stderr.strip().split('\n')[:10]
                    for line in error_lines:
                        if line.strip():
                            print(f"   {line}")
                            
        except subprocess.TimeoutExpired:
            print("⏰ Collection timed out")
        except Exception as e:
            print(f"💥 Exception: {e}")
    
    print("\n" + "=" * 50)
    print("🎯 Collection Analysis Complete")

if __name__ == "__main__":
    main()