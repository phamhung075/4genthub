#!/usr/bin/env python3
"""Test context injection with HTTP server"""

import sys
import asyncio
import os

# Add hooks utils to path
project_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(__file__)))))
sys.path.insert(0, os.path.join(project_root, '.claude', 'hooks', 'utils'))

import context_injector
import mcp_client

async def test():
    print("=" * 50)
    print("Testing Context Injection System")
    print("=" * 50)
    
    # Test MCP client connection
    client = mcp_client.OptimizedMCPClient()
    auth = client.authenticate()
    print(f'✓ Authentication: {auth}')
    
    # Test making a request
    print("\nTesting MCP endpoint...")
    result = client.make_request('/mcp/manage_task', {'action': 'list', 'limit': 2})
    if result:
        print(f'✓ MCP Request successful!')
        print(f'  Response: {result}')
    else:
        print('✗ MCP Request failed')
    
    # Test context injection
    print("\nTesting context injection...")
    injector = context_injector.create_context_injector()
    context = await injector.inject_context('mcp__dhafnck_mcp_http__manage_task', {'action': 'list'})
    
    if context:
        print('✓ Context injection SUCCESS!')
        print(f'  Context size: {len(context)} bytes')
        if len(context) > 100:
            print('  ✓ Context contains real data!')
            print(f'\nContext preview:\n{context[:500]}...')
        else:
            print('  ✗ Context is minimal/empty')
    else:
        print('✗ No context returned')
    
    print("=" * 50)

if __name__ == "__main__":
    asyncio.run(test())