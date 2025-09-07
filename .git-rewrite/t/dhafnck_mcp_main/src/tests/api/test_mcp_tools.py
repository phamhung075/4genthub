#!/usr/bin/env python3
"""
Test MCP Tools - Direct API Testing
Tests the MCP server running at localhost:8000 to diagnose frontend data loading issues
"""

import requests
import json
import time

# Configuration
API_BASE = "http://localhost:8000/mcp"
HEADERS = {
    "Content-Type": "application/json",
    "Accept": "application/json, text/event-stream",
    "MCP-Protocol-Version": "2025-06-18",
}

def mcp_call(tool_name, arguments, timeout=10):
    """Make an MCP tool call"""
    rpc_id = int(time.time() * 1000)  # Use timestamp as ID
    
    body = {
        "jsonrpc": "2.0",
        "method": "tools/call",
        "params": {
            "name": tool_name,
            "arguments": arguments
        },
        "id": rpc_id,
    }
    
    print(f"🔧 Calling {tool_name} with args: {arguments}")
    
    try:
        response = requests.post(API_BASE, headers=HEADERS, json=body, timeout=timeout)
        print(f"📡 HTTP Status: {response.status_code}")
        
        if response.status_code == 200:
            data = response.json()
            if 'result' in data and 'content' in data['result']:
                if isinstance(data['result']['content'], list) and len(data['result']['content']) > 0:
                    try:
                        tool_result = json.loads(data['result']['content'][0]['text'])
                        return tool_result
                    except json.JSONDecodeError as e:
                        print(f"❌ JSON decode error: {e}")
                        print(f"Raw content: {data['result']['content'][0]['text'][:200]}...")
                        return {"error": "JSON decode failed", "raw": data['result']['content'][0]['text']}
            return data
        else:
            print(f"❌ HTTP Error: {response.text}")
            return {"error": f"HTTP {response.status_code}", "message": response.text}
            
    except requests.exceptions.Timeout:
        print(f"⏰ Timeout after {timeout} seconds")
        return {"error": "timeout"}
    except Exception as e:
        print(f"❌ Request failed: {str(e)}")
        return {"error": str(e)}

def test_server_health():
    """Test server health endpoint"""
    print("\n🏥 TESTING SERVER HEALTH")
    print("=" * 50)
    try:
        response = requests.get("http://localhost:8000/health", timeout=5)
        if response.status_code == 200:
            health_data = response.json()
            print("✅ Server is healthy!")
            print(f"Status: {health_data.get('status')}")
            print(f"Version: {health_data.get('version')}")
            print(f"Uptime: {health_data.get('connections', {}).get('uptime_seconds', 'unknown')} seconds")
            return True
        else:
            print(f"❌ Health check failed: HTTP {response.status_code}")
            return False
    except Exception as e:
        print(f"❌ Health check error: {e}")
        return False

def test_project_management():
    """Test project management"""
    print("\n📋 TESTING PROJECT MANAGEMENT")
    print("=" * 50)
    
    # List projects
    result = mcp_call("manage_project", {"action": "list"})
    print("Projects list result:")
    print(json.dumps(result, indent=2)[:500] + "..." if len(str(result)) > 500 else json.dumps(result, indent=2))
    
    if result and result.get("success"):
        projects = result.get("projects", result.get("data", {}).get("projects", []))
        print(f"✅ Found {len(projects)} projects")
        return projects
    else:
        print(f"❌ Project listing failed: {result}")
        return []

def test_task_management():
    """Test task management"""
    print("\n📝 TESTING TASK MANAGEMENT")
    print("=" * 50)
    
    # List tasks
    result = mcp_call("manage_task", {"action": "list"})
    print("Tasks list result:")
    print(json.dumps(result, indent=2)[:500] + "..." if len(str(result)) > 500 else json.dumps(result, indent=2))
    
    if result and result.get("success"):
        tasks = result.get("tasks", result.get("data", {}).get("tasks", []))
        print(f"✅ Found {len(tasks)} tasks")
        return tasks
    else:
        print(f"❌ Task listing failed: {result}")
        return []

def test_context_management():
    """Test context management"""
    print("\n🧠 TESTING CONTEXT MANAGEMENT")
    print("=" * 50)
    
    # Test global context
    result = mcp_call("manage_context", {
        "action": "resolve",
        "level": "global",
        "context_id": "global_singleton"
    })
    print("Global context result:")
    print(json.dumps(result, indent=2)[:300] + "..." if len(str(result)) > 300 else json.dumps(result, indent=2))

def run_all_tests():
    """Run all MCP tests"""
    print("🚀 STARTING MCP SERVER DIAGNOSTIC TESTS")
    print("=" * 60)
    
    # Test 1: Server Health
    server_healthy = test_server_health()
    if not server_healthy:
        print("❌ Server health check failed - stopping tests")
        return
    
    # Test 2: Project Management  
    projects = test_project_management()
    
    # Test 3: Task Management
    tasks = test_task_management()
    
    # Test 4: Context Management
    test_context_management()
    
    # Summary
    print("\n📊 TEST SUMMARY")
    print("=" * 50)
    print(f"✅ Server Health: {'OK' if server_healthy else 'FAILED'}")
    print(f"📋 Projects Found: {len(projects)}")
    print(f"📝 Tasks Found: {len(tasks)}")
    
    if server_healthy and (projects or tasks):
        print("🎯 MCP SERVER IS WORKING!")
        print("🔍 ISSUE: Frontend may have connection/configuration problems")
    else:
        print("❌ MCP SERVER HAS ISSUES!")
        print("🔧 ISSUE: Backend database or MCP tool problems")

if __name__ == "__main__":
    run_all_tests()