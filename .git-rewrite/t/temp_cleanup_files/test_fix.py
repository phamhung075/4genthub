#!/usr/bin/env python3
"""
Test script to verify the frontend task listing fix
"""

import requests
import json

def test_api_v2_tasks():
    """Test the API v2 tasks endpoint"""
    url = "http://localhost:8000/api/v2/tasks/"
    
    # Try without auth first to verify the route is accessible
    print("Testing API v2 tasks endpoint...")
    try:
        response = requests.get(url, timeout=10)
        print(f"Status Code: {response.status_code}")
        print(f"Response: {response.text[:200]}...")
        
        if response.status_code == 401:
            print("✅ Route is accessible but requires authentication (expected)")
            return True
        elif response.status_code == 404:
            print("❌ Route not found - API v2 routes not registered")
            return False
        else:
            print(f"✅ Route responded with status {response.status_code}")
            return True
            
    except requests.exceptions.ConnectionError:
        print("❌ Could not connect to server")
        return False
    except Exception as e:
        print(f"❌ Error: {e}")
        return False

def test_mcp_manage_task():
    """Test the MCP manage_task endpoint"""
    url = "http://localhost:8000/mcp/"
    
    payload = {
        "jsonrpc": "2.0",
        "id": 1,
        "method": "tools/call", 
        "params": {
            "name": "manage_task",
            "arguments": {
                "action": "list",
                "limit": "3"
            }
        }
    }
    
    headers = {
        "Content-Type": "application/json",
        "Accept": "application/json, text/event-stream"
    }
    
    try:
        print("Testing MCP manage_task endpoint...")
        response = requests.post(url, json=payload, headers=headers, timeout=10)
        print(f"Status Code: {response.status_code}")
        
        if response.status_code == 200:
            result = response.json()
            print("✅ MCP endpoint responding")
            
            # Check if we get the expected structure
            if "result" in result and "content" in result["result"]:
                content = result["result"]["content"]
                if content and len(content) > 0:
                    task_data = json.loads(content[0]["text"])
                    print(f"✅ Task data structure: {list(task_data.keys())}")
                    
                    # Check if tasks is an array (fixed) or nested object (broken)
                    if "tasks" in task_data:
                        if isinstance(task_data["tasks"], list):
                            print("✅ FIXED: tasks is now an array")
                            print(f"✅ Task count: {len(task_data['tasks'])}")
                            return True
                        elif isinstance(task_data["tasks"], dict):
                            print("❌ STILL BROKEN: tasks is still a nested object")
                            print(f"❌ Nested structure: {list(task_data['tasks'].keys())}")
                            return False
            
        return False
        
    except requests.exceptions.ConnectionError:
        print("❌ Could not connect to MCP server")
        return False
    except Exception as e:
        print(f"❌ MCP Error: {e}")
        return False

if __name__ == "__main__":
    print("=" * 60)
    print("Testing Frontend Task Listing Fix")
    print("=" * 60)
    
    # Test API v2 route registration
    api_v2_ok = test_api_v2_tasks()
    print()
    
    # Test MCP endpoint and our fix
    mcp_ok = test_mcp_manage_task()
    print()
    
    print("=" * 60)
    if mcp_ok:
        print("✅ SUCCESS: Fix is working - tasks is now an array!")
    else:
        print("❌ FAILED: Fix not working or server issues")
    print("=" * 60)