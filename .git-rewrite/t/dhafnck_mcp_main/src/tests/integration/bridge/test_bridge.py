#!/usr/bin/env python3
"""Test script to simulate Claude Desktop MCP communication"""
import json
import os
import subprocess
import sys
import time

# Get the project root directory
project_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

def send_request(proc, request):
    """Send a request and get response"""
    print(f"Sending: {json.dumps(request)}")
    proc.stdin.write(json.dumps(request) + '\n')
    proc.stdin.flush()
    
    # Read response
    response_line = proc.stdout.readline()
    if response_line:
        response = json.loads(response_line.strip())
        print(f"Received: {json.dumps(response, indent=2)}")
        return response
    return None

def main():
    # Start the bridge process
    bridge_path = os.path.join(project_root, 'src', 'mcp_bridge.py')
    proc = subprocess.Popen(
        [sys.executable, bridge_path],
        stdin=subprocess.PIPE,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
        bufsize=0
    )
    
    try:
        # Wait a bit for startup
        time.sleep(1)
        
        # Test 1: Initialize
        print("\n=== Testing Initialize ===")
        init_request = {
            "jsonrpc": "2.0",
            "method": "initialize",
            "params": {
                "protocolVersion": "2024-11-05",
                "capabilities": {
                    "tools": {},
                    "roots": {
                        "listChanged": True
                    },
                    "sampling": {}
                },
                "clientInfo": {
                    "name": "test-client",
                    "version": "1.0.0"
                }
            },
            "id": 1
        }
        response = send_request(proc, init_request)
        
        # Test 2: List tools
        print("\n=== Testing tools/list ===")
        tools_request = {
            "jsonrpc": "2.0",
            "method": "tools/list",
            "params": {},
            "id": 2
        }
        response = send_request(proc, tools_request)
        
        # Test 3: Call a tool
        print("\n=== Testing tool call (manage_connection health_check) ===")
        tool_call = {
            "jsonrpc": "2.0",
            "method": "tools/call",
            "params": {
                "name": "manage_connection",
                "arguments": {
                    "action": "health_check"
                }
            },
            "id": 3
        }
        response = send_request(proc, tool_call)
        
    finally:
        # Clean up
        proc.terminate()
        proc.wait()
        
        # Show any stderr output
        stderr_output = proc.stderr.read()
        if stderr_output:
            print(f"\nStderr output:\n{stderr_output}")

if __name__ == "__main__":
    main()