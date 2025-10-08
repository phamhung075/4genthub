#!/usr/bin/env python3
"""Test script to verify agent assignment fix"""

import requests
import json
from datetime import datetime

BASE_URL = "http://localhost:8000"

# Test data from the comprehensive test report
TEST_PROJECT_ALPHA = "edae2fb3-f37a-48f8-9c0e-41207219cbb2"
ALPHA_BRANCH_1 = "8ee77960-7c30-4498-9d67-584bbcdfd616"

def test_agent_assignment():
    """Test assigning an agent to a branch - the previously failing operation"""

    print("=" * 80)
    print("Testing Agent Assignment to Branch (Previously Failed Operation)")
    print("=" * 80)
    print(f"\nTimestamp: {datetime.now().isoformat()}")
    print(f"Project ID: {TEST_PROJECT_ALPHA}")
    print(f"Branch ID: {ALPHA_BRANCH_1}")
    print(f"Agent: coding-agent")

    # Test assign agent to branch
    print("\n" + "-" * 80)
    print("Test: Assign 'coding-agent' to branch")
    print("-" * 80)

    response = requests.post(
        f"{BASE_URL}/mcp/tools/manage-git-branch",
        json={
            "action": "assign_agent",
            "project_id": TEST_PROJECT_ALPHA,
            "git_branch_id": ALPHA_BRANCH_1,
            "agent_id": "coding-agent"
        },
        headers={
            "Accept": "application/json, text/event-stream",
            "Content-Type": "application/json"
        }
    )

    print(f"Status Code: {response.status_code}")

    try:
        result = response.json()
        print(f"Response: {json.dumps(result, indent=2)}")

        if response.status_code == 200 and result.get("success"):
            print("\n✅ PASS: Agent assignment successful!")
            print("🎉 Bug fix verified - agent assignment now works!")
            return True
        else:
            print("\n❌ FAIL: Agent assignment failed")
            if "error" in result:
                print(f"Error: {result['error']}")
            return False

    except json.JSONDecodeError:
        print(f"Raw response: {response.text}")
        print("\n❌ FAIL: Invalid JSON response")
        return False


if __name__ == "__main__":
    success = test_agent_assignment()
    print("\n" + "=" * 80)
    if success:
        print("🎉 Test Result: SUCCESS - Agent assignment bug is FIXED!")
    else:
        print("❌ Test Result: FAILURE - Agent assignment still has issues")
    print("=" * 80)
    exit(0 if success else 1)
