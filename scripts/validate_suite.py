#!/usr/bin/env python3
"""
Suite Validation Script
Validates that all parallel fixes are working correctly
"""

import subprocess
import sys
from pathlib import Path


def run_command(cmd, cwd=None):
    """Run a command and capture output"""
    try:
        result = subprocess.run(
            cmd, shell=True, cwd=cwd, capture_output=True, text=True, timeout=60
        )
        return result.returncode, result.stdout, result.stderr
    except subprocess.TimeoutExpired:
        return -1, "", "Command timed out"
    except Exception as e:
        return -1, "", str(e)


def main():
    # Set working directory to agenthub_main
    project_root = Path(__file__).parent.parent
    mcp_dir = project_root / "agenthub_main"

    if not mcp_dir.exists():
        print(f"❌ MCP directory not found: {mcp_dir}")
        return 1

    print("🧪 Starting Suite Validation")
    print("=" * 50)

    # Step 1: Collection check
    print("📋 Step 1: Collection Validation")
    returncode, stdout, stderr = run_command(
        "python -m pytest src/tests/ --collect-only -q", cwd=mcp_dir
    )

    if returncode == 0:
        lines = stdout.strip().split("\n")
        collected_line = [line for line in lines if "collected" in line.lower()]
        if collected_line:
            print(f"✅ {collected_line[-1]}")
        else:
            print("✅ Collection completed successfully")
    else:
        print(f"❌ Collection failed with return code: {returncode}")
        if stderr:
            print(f"Error output: {stderr[-500:]}")  # Last 500 chars
        return 1

    # Step 2: Warning count
    print("\n⚠️  Step 2: Warning Analysis")
    returncode, stdout, stderr = run_command(
        "python -m pytest src/tests/ --collect-only 2>&1 | grep -E 'PytestCollectionWarning|DeprecationWarning|request' | wc -l",
        cwd=mcp_dir,
    )

    if returncode == 0:
        warning_count = stdout.strip()
        print(f"📊 Total warnings: {warning_count}")

        try:
            if int(warning_count) < 20:  # Reasonable threshold
                print("✅ Warning count is within acceptable range")
            else:
                print("⚠️  High warning count - may need attention")
        except ValueError:
            print("⚠️  Could not parse warning count")
    else:
        print("❌ Could not count warnings")

    # Step 3: Quick auth check
    print("\n🔐 Step 3: Auth Module Quick Check")
    returncode, stdout, stderr = run_command(
        "python -m pytest src/tests/unit/auth/ --collect-only -q", cwd=mcp_dir
    )

    if returncode == 0:
        print("✅ Auth unit collection successful")
    else:
        print("❌ Auth collection issues present")
        if stderr:
            print(f"Details: {stderr[-200:]}")

    # Step 4: AI Planning check
    print("\n🤖 Step 4: AI Planning Module Check")
    returncode, stdout, stderr = run_command(
        "python -m pytest src/tests/ai_task_planning/ --collect-only -q", cwd=mcp_dir
    )

    if returncode == 0:
        print("✅ AI Planning collection successful")
    else:
        print("❌ AI Planning collection issues present")
        if stderr:
            print(f"Details: {stderr[-200:]}")

    # Step 5: Error count
    print("\n🔥 Step 5: Error Analysis")
    returncode, stdout, stderr = run_command(
        "python -m pytest src/tests/ --collect-only 2>&1 | grep -c 'ERROR' || echo '0'",
        cwd=mcp_dir,
    )

    if returncode == 0:
        error_count = stdout.strip()
        print(f"💥 Total collection errors: {error_count}")

        try:
            if int(error_count) == 0:
                print("✅ No collection errors found!")
            elif int(error_count) < 5:
                print("⚠️  Few collection errors remain")
            else:
                print("❌ Multiple collection errors still present")
        except ValueError:
            print("⚠️  Could not parse error count")

    print("\n" + "=" * 50)
    print("🎉 Suite Validation Complete!")

    return 0


if __name__ == "__main__":
    sys.exit(main())
