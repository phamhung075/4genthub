#!/usr/bin/env python3
"""
Test different task list parameters to find the correct ones
"""

import requests
import json
import time

API_BASE = "http://localhost:8000/mcp"
HEADERS = {
    "Content-Type": "application/json",
    "Accept": "application/json, text/event-stream",
    "MCP-Protocol-Version": "2025-06-18",
}

def test_task_parameters():
    """Test different parameter combinations for task listing"""
    
    test_cases = [
        {"action": "list"},  # No additional params
        {"action": "list", "git_branch_id": "main"},  # Try git_branch_id
        {"action": "list", "project_id": "default_project"},  # Try project_id
        {"action": "list", "git_branch_id": "main", "project_id": "default_project"},  # Both
        {"action": "list", "branch_name": "main"},  # Try branch_name
    ]
    
    for i, args in enumerate(test_cases):
        print(f"\n🧪 Test Case {i+1}: {args}")
        print("-" * 40)
        
        body = {
            "jsonrpc": "2.0",
            "method": "tools/call",
            "params": {
                "name": "manage_task",
                "arguments": args
            },
            "id": int(time.time() * 1000) + i,
        }
        
        try:
            response = requests.post(API_BASE, headers=HEADERS, json=body, timeout=10)
            
            if response.status_code == 200:
                data = response.json()
                
                if data.get('result') and data['result'].get('isError'):
                    print(f"❌ Error: {data['result']['content'][0]['text'][:100]}...")
                elif data.get('result') and data['result'].get('content'):
                    try:
                        tool_result = json.loads(data['result']['content'][0]['text'])
                        if tool_result.get('success'):
                            tasks = tool_result.get('tasks', [])
                            print(f"✅ SUCCESS: Found {len(tasks)} tasks")
                            if tasks:
                                print(f"  First task: {tasks[0].get('title', 'No title')}")
                        else:
                            print(f"❌ Tool failed: {tool_result.get('error', 'Unknown error')}")
                    except json.JSONDecodeError:
                        print("❌ JSON decode failed")
                        print(f"Raw: {data['result']['content'][0]['text'][:100]}...")
            else:
                print(f"❌ HTTP {response.status_code}: {response.text[:100]}...")
                
        except Exception as e:
            print(f"❌ Request failed: {e}")

if __name__ == "__main__":
    print("🔍 FINDING CORRECT TASK LIST PARAMETERS")
    print("=" * 50)
    test_task_parameters()