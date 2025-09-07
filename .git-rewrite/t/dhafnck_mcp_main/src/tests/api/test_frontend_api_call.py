#!/usr/bin/env python3
"""
Test the exact API calls that the frontend makes
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

def test_frontend_project_call():
    """Test exact frontend project list call"""
    print("🔧 Testing frontend project list call")
    
    body = {
        "jsonrpc": "2.0",
        "method": "tools/call",
        "params": {
            "name": "manage_project",
            "arguments": {"action": "list"}
        },
        "id": int(time.time() * 1000),
    }
    
    print("Request body:", json.dumps(body, indent=2))
    print("Headers:", FRONTEND_HEADERS)
    print()
    
    try:
        response = requests.post(API_BASE, headers=FRONTEND_HEADERS, json=body, timeout=30)
        print(f"Status Code: {response.status_code}")
        
        if response.status_code == 200:
            data = response.json()
            print("Raw Response:")
            print(json.dumps(data, indent=2)[:800] + "...")
            
            # Parse like frontend does
            if data.get('result') and data['result'].get('content'):
                if isinstance(data['result']['content'], list) and len(data['result']['content']) > 0:
                    try:
                        tool_result = json.loads(data['result']['content'][0]['text'])
                        print("\nParsed Tool Result:")
                        print(json.dumps(tool_result, indent=2)[:500] + "...")
                        
                        if tool_result.get('success'):
                            projects = tool_result.get('projects', [])
                            print(f"\n✅ Frontend would see {len(projects)} projects")
                            for i, project in enumerate(projects[:3]):  # Show first 3
                                print(f"  {i+1}. {project.get('name', 'No name')} (ID: {project.get('id', 'No ID')})")
                        else:
                            print("❌ Tool result not successful")
                    except Exception as e:
                        print(f"❌ Parse error: {e}")
        else:
            print(f"❌ HTTP Error: {response.status_code}")
            print(response.text)
            
    except Exception as e:
        print(f"❌ Request failed: {e}")

def test_frontend_task_call():
    """Test exact frontend task list call"""
    print("\n🔧 Testing frontend task list call")
    
    body = {
        "jsonrpc": "2.0",
        "method": "tools/call",
        "params": {
            "name": "manage_task",
            "arguments": {
                "action": "list",
                "git_branch_name": "main"  # Default from frontend
            }
        },
        "id": int(time.time() * 1000),
    }
    
    print("Request body:", json.dumps(body, indent=2))
    print()
    
    try:
        response = requests.post(API_BASE, headers=FRONTEND_HEADERS, json=body, timeout=30)
        print(f"Status Code: {response.status_code}")
        
        if response.status_code == 200:
            data = response.json()
            print("Raw Response:")
            print(json.dumps(data, indent=2)[:500] + "...")
            
            # Parse like frontend does
            if data.get('result') and data['result'].get('content'):
                if isinstance(data['result']['content'], list) and len(data['result']['content']) > 0:
                    try:
                        tool_result = json.loads(data['result']['content'][0]['text'])
                        
                        if tool_result.get('success'):
                            tasks = tool_result.get('tasks', [])
                            print(f"\n✅ Frontend would see {len(tasks)} tasks")
                            for i, task in enumerate(tasks[:3]):  # Show first 3
                                print(f"  {i+1}. {task.get('title', 'No title')} - {task.get('status', 'No status')}")
                        else:
                            print("❌ Tool result not successful")
                            print(f"Error: {tool_result.get('error', 'Unknown error')}")
                    except Exception as e:
                        print(f"❌ Parse error: {e}")
        else:
            print(f"❌ HTTP Error: {response.status_code}")
            print(response.text)
            
    except Exception as e:
        print(f"❌ Request failed: {e}")

if __name__ == "__main__":
    print("🧪 TESTING FRONTEND API CALLS")
    print("=" * 50)
    test_frontend_project_call()
    test_frontend_task_call()