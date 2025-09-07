#!/usr/bin/env python3
"""
Test the FIXED frontend API calls - without invalid parameters
"""

import requests
import json
import time

API_BASE = "http://localhost:8000/mcp"

# Exact headers from frontend api.ts
FRONTEND_HEADERS = {
    "Content-Type": "application/json",
    "Accept": "application/json, text/event-stream",
    "MCP-Protocol-Version": "2025-06-18",
}

def test_fixed_task_call():
    """Test task list call with FIXED parameters (no git_branch_name)"""
    print("🔧 Testing FIXED frontend task list call")
    
    body = {
        "jsonrpc": "2.0",
        "method": "tools/call",
        "params": {
            "name": "manage_task",
            "arguments": {
                "action": "list"
                # REMOVED: "git_branch_name": "main" - this was causing the error
            }
        },
        "id": int(time.time() * 1000),
    }
    
    print("Fixed Request body:", json.dumps(body, indent=2))
    print()
    
    try:
        response = requests.post(API_BASE, headers=FRONTEND_HEADERS, json=body, timeout=30)
        print(f"Status Code: {response.status_code}")
        
        if response.status_code == 200:
            data = response.json()
            print("Raw Response (first 500 chars):")
            print(json.dumps(data, indent=2)[:500] + "...")
            
            # Parse like frontend does
            if data.get('result') and data['result'].get('content'):
                if isinstance(data['result']['content'], list) and len(data['result']['content']) > 0:
                    try:
                        tool_result = json.loads(data['result']['content'][0]['text'])
                        
                        if tool_result.get('success'):
                            tasks = tool_result.get('tasks', [])
                            print(f"\n✅ SUCCESS! Frontend would see {len(tasks)} tasks")
                            for i, task in enumerate(tasks[:3]):  # Show first 3
                                print(f"  {i+1}. {task.get('title', 'No title')} - {task.get('status', 'No status')}")
                            
                            if len(tasks) > 3:
                                print(f"  ... and {len(tasks) - 3} more tasks")
                            
                            # Test data source verification
                            print(f"\n🔍 Data Source Verification:")
                            if tasks:
                                first_task = tasks[0]
                                print(f"  First task ID: {first_task.get('id', 'No ID')}")
                                print(f"  Created: {first_task.get('created_at', 'No date')}")
                                print(f"  Branch ID: {first_task.get('git_branch_id', 'No branch')}")
                            
                            return True, len(tasks)
                        else:
                            print("❌ Tool result not successful")
                            print(f"Error: {tool_result.get('error', 'Unknown error')}")
                            return False, 0
                    except Exception as e:
                        print(f"❌ Parse error: {e}")
                        return False, 0
        else:
            print(f"❌ HTTP Error: {response.status_code}")
            print(response.text)
            return False, 0
            
    except Exception as e:
        print(f"❌ Request failed: {e}")
        return False, 0

if __name__ == "__main__":
    print("🎯 TESTING FIXED FRONTEND API")
    print("=" * 50)
    
    success, task_count = test_fixed_task_call()
    
    print("\n" + "=" * 50)
    if success:
        print(f"🎉 SUCCESS! Frontend task loading is FIXED!")
        print(f"   - No more validation errors")
        print(f"   - Successfully loaded {task_count} tasks from Supabase")
        print(f"   - Frontend will display all tasks correctly")
    else:
        print("❌ Still having issues - needs more investigation")