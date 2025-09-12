#!/usr/bin/env python3
"""Test hook authentication system"""

import sys
import os
sys.path.insert(0, '/home/daihungpham/__projects__/agentic-project/dhafnck_mcp_main/src')

# Environment variables should be set in .env file or by the system
# Not hardcoded in the test file
if not os.getenv('HOOK_JWT_SECRET'):
    print("Error: HOOK_JWT_SECRET environment variable not set")
    print("Please set it in your .env file or environment")
    sys.exit(1)

from fastmcp.auth.hook_auth import create_hook_token
import requests

def test_hook_authentication():
    """Test hook authentication with HTTP server"""
    
    # Generate a hook token
    hook_token = create_hook_token('test-hook-user')
    print(f'Generated hook token (first 50 chars): {hook_token[:50]}...')
    print(f'Token length: {len(hook_token)}')
    
    # Test direct HTTP request with hook token
    headers = {
        'Authorization': f'Bearer {hook_token}',
        'Content-Type': 'application/json',
        'Accept': 'application/json, text/event-stream'
    }
    
    payload = {
        'action': 'list',
        'limit': 2
    }
    
    try:
        response = requests.post('http://localhost:8000/mcp/manage_task', json=payload, headers=headers)
        print(f'\nResponse status: {response.status_code}')
        
        if response.status_code == 200:
            print('✅ Hook authentication successful!')
            result = response.json()
            
            # Print result summary
            if 'tasks' in result:
                print(f'Tasks retrieved: {len(result["tasks"])} tasks')
                for task in result['tasks'][:2]:
                    print(f'  - {task.get("title", "Unknown")}: {task.get("status", "Unknown")}')
            elif 'data' in result and 'tasks' in result['data']:
                tasks = result['data']['tasks']
                print(f'Tasks retrieved: {len(tasks)} tasks')
                for task in tasks[:2]:
                    print(f'  - {task.get("title", "Unknown")}: {task.get("status", "Unknown")}')
            else:
                print(f'Result structure: {list(result.keys())}')
        else:
            print(f'❌ Authentication failed')
            print(f'Response: {response.text[:200]}')
    except Exception as e:
        print(f'Error: {e}')

if __name__ == "__main__":
    test_hook_authentication()