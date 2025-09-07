#!/usr/bin/env python3
"""Test MCP server access and functionality"""

import requests
import json
import sys

def test_mcp_connection():
    """Test basic MCP server connectivity"""
    base_url = "http://localhost:8000"
    
    # Test health endpoint
    try:
        response = requests.get(f"{base_url}/health")
        print(f"✅ Health check: {response.json()}")
    except Exception as e:
        print(f"❌ Health check failed: {e}")
        return False
    
    # Test MCP endpoint
    try:
        response = requests.get(f"{base_url}/test-mcp")
        result = response.json()
        print(f"MCP Status: {result}")
        
        if "error" in result:
            print(f"⚠️  MCP tools not loaded: {result['error']}")
            return False
        else:
            print("✅ MCP tools loaded successfully")
            return True
    except Exception as e:
        print(f"❌ MCP test failed: {e}")
        return False

def test_task_management():
    """Test task management functionality"""
    base_url = "http://localhost:8000"
    
    # Try different endpoints for task management
    endpoints = [
        "/api/tasks",
        "/api/task/list",
        "/mcp/manage_task",
        "/tools/manage_task",
    ]
    
    for endpoint in endpoints:
        try:
            response = requests.post(
                f"{base_url}{endpoint}",
                json={"action": "list", "user_id": "test-user-123"},
                headers={"Content-Type": "application/json"}
            )
            if response.status_code == 200:
                print(f"✅ Found working endpoint: {endpoint}")
                print(f"Response: {response.json()}")
                return True
            else:
                print(f"❌ {endpoint}: {response.status_code}")
        except Exception as e:
            print(f"❌ {endpoint}: {e}")
    
    return False

if __name__ == "__main__":
    print("Testing MCP Server Access...")
    print("-" * 40)
    
    if test_mcp_connection():
        print("\n✅ MCP server is accessible")
    else:
        print("\n⚠️  MCP tools need to be fixed")
        
    print("\nTesting Task Management...")
    print("-" * 40)
    
    if not test_task_management():
        print("\n⚠️  No working task management endpoint found")
        print("The MCP tools may need to be properly configured")