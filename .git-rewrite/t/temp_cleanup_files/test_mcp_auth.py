#!/usr/bin/env python3
"""
Test MCP authentication with API token
"""

import requests
import json
import sys

def test_mcp_auth(token):
    """Test MCP authentication with the provided token"""
    
    # MCP main endpoint with initialize method
    url = "http://localhost:8000/mcp/"
    
    headers = {
        "Authorization": f"Bearer {token}",
        "Content-Type": "application/json",
        "Accept": "application/json, text/event-stream"  # MCP needs both
    }
    
    # Test with initialize method
    payload = {
        "jsonrpc": "2.0",
        "method": "initialize",
        "params": {
            "protocolVersion": "0.1.0",
            "capabilities": {}
        },
        "id": 1
    }
    
    print(f"Testing MCP authentication...")
    print(f"URL: {url}")
    print(f"Token (first 50 chars): {token[:50]}...")
    
    try:
        response = requests.post(url, headers=headers, json=payload)
        print(f"Status Code: {response.status_code}")
        
        if response.status_code == 200:
            print("✅ MCP authentication successful!")
            # Handle SSE response
            for line in response.text.strip().split('\n'):
                if line.startswith('data: '):
                    data = json.loads(line[6:])
                    print(f"Response: {json.dumps(data, indent=2)}")
            return True
        else:
            print(f"❌ MCP authentication failed")
            print(f"Response: {response.text}")
            return False
            
    except Exception as e:
        print(f"❌ Error: {e}")
        return False

def test_mcp_tools(token):
    """Test MCP tools endpoint"""
    
    url = "http://localhost:8000/mcp/"
    
    headers = {
        "Authorization": f"Bearer {token}",
        "Content-Type": "application/json",
        "Accept": "application/json, text/event-stream"  # MCP needs both
    }
    
    # Test JSON-RPC request to list tools
    payload = {
        "jsonrpc": "2.0",
        "method": "tools/list",
        "params": {},
        "id": 1
    }
    
    print(f"\nTesting MCP tools endpoint...")
    print(f"URL: {url}")
    
    try:
        response = requests.post(url, headers=headers, json=payload)
        print(f"Status Code: {response.status_code}")
        
        if response.status_code == 200:
            # Handle SSE response
            for line in response.text.strip().split('\n'):
                if line.startswith('data: '):
                    result = json.loads(line[6:])
                    if "result" in result and "tools" in result["result"]:
                        tools = result["result"]["tools"]
                        print(f"✅ MCP tools accessible! Found {len(tools)} tools")
                        print(f"First 3 tools: {[t['name'] for t in tools[:3]]}")
                        return True
                    else:
                        print(f"Response: {json.dumps(result, indent=2)}")
        else:
            print(f"❌ Failed to access MCP tools")
            print(f"Response: {response.text}")
            return False
            
    except Exception as e:
        print(f"❌ Error: {e}")
        return False

if __name__ == "__main__":
    # The token from .mcp.json (update this with your generated token)
    token = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJ0b2tlbl9pZCI6InRva18yYmEwNjFiMjM2Y2NjYjE0IiwidXNlcl9pZCI6IjY1ZDczM2U5LTA0ZDYtNGRkYS05NTM2LTY4OGMzYTU5NDQ4ZSIsInNjb3BlcyI6WyJyZWFkOnRhc2tzIiwid3JpdGU6dGFza3MiLCJyZWFkOmNvbnRleHQiLCJ3cml0ZTpjb250ZXh0IiwicmVhZDphZ2VudHMiLCJ3cml0ZTphZ2VudHMiLCJleGVjdXRlOm1jcCJdLCJleHAiOjE3NTg4NzY2MDksImlhdCI6MTc1NjI4NDYxMCwidHlwZSI6ImFwaV90b2tlbiJ9.r2it2vUEnyVTxzIOMceO-9eFMTwrqIMVP74vX6K9M7k"
    
    print("=" * 60)
    print("MCP Authentication Test")
    print("=" * 60)
    
    # Test authentication
    auth_success = test_mcp_auth(token)
    
    if auth_success:
        # Test tools access
        tools_success = test_mcp_tools(token)
        
        if tools_success:
            print("\n✅ All tests passed! MCP connection is working.")
        else:
            print("\n⚠️ Authentication works but tools access failed.")
    else:
        print("\n❌ Authentication failed. Please check your token.")
    
    print("=" * 60)