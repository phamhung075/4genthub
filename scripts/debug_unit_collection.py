#!/usr/bin/env python3
"""Debug unit test collection issues"""
import sys
import os
import subprocess
from pathlib import Path

# Add the source path
project_root = Path(__file__).parent.parent
mcp_dir = project_root / "dhafnck_mcp_main"

def test_path_collection(test_path, name):
    """Test collection for a specific path"""
    print(f"\n📋 Testing: {name}")
    try:
        result = subprocess.run([
            sys.executable, "-m", "pytest", 
            test_path, 
            "--collect-only", 
            "-q",
            "--tb=line"
        ], 
        capture_output=True, 
        text=True, 
        timeout=20
        )
        
        if result.returncode == 0:
            lines = result.stdout.strip().split('\n')
            collected_line = [line for line in lines if 'collected' in line.lower()]
            if collected_line:
                print(f"✅ {collected_line[-1]}")
            else:
                print("✅ Collection successful")
            return True
        else:
            print(f"❌ Failed (code: {result.returncode})")
            # Show stderr
            if result.stderr:
                error_lines = result.stderr.strip().split('\n')
                for line in error_lines[-5:]:  # Last 5 lines
                    if line.strip() and 'ERROR' in line:
                        print(f"   🔥 {line}")
            return False
            
    except subprocess.TimeoutExpired:
        print("⏰ Collection timed out")
        return False
    except Exception as e:
        print(f"💥 Exception: {e}")
        return False

def main():
    print("🧪 Debug Unit Test Collection")
    print("=" * 50)
    
    os.chdir(mcp_dir)
    
    # Test each unit test subdirectory individually
    unit_subdirs = [
        ("src/tests/unit/auth/", "Auth Unit Tests"),
        ("src/tests/unit/task_management/", "Task Management Unit Tests"),
        ("src/tests/ai_task_planning/", "AI Task Planning Tests"),
    ]
    
    results = {}
    for path, name in unit_subdirs:
        results[name] = test_path_collection(path, name)
    
    print("\n" + "=" * 50)
    print("📊 Summary:")
    for name, success in results.items():
        status = "✅ PASS" if success else "❌ FAIL"
        print(f"   {status} {name}")
    
    # If auth unit tests fail, drill down further
    if not results.get("Auth Unit Tests", False):
        print("\n🔍 Drilling into Auth Unit Tests...")
        auth_subdirs = [
            ("src/tests/unit/auth/application/", "Auth Application"),
            ("src/tests/unit/auth/interface/", "Auth Interface"),
            ("src/tests/unit/auth/middleware/", "Auth Middleware"),
        ]
        for path, name in auth_subdirs:
            test_path_collection(path, name)

if __name__ == "__main__":
    main()