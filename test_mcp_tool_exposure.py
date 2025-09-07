#!/usr/bin/env python
"""Test script to verify what tools are exposed via MCP protocol"""

import sys
import os
import json
import asyncio

# Add src to path
sys.path.insert(0, '/home/daihungpham/__projects__/agentic-project/dhafnck_mcp_main/src')

async def test_mcp_tools():
    """Test what tools are exposed via MCP protocol"""
    
    print("=" * 80)
    print("TESTING MCP TOOL EXPOSURE")
    print("=" * 80)
    
    try:
        # Import and create server exactly as done in mcp_entry_point.py
        from fastmcp.server.mcp_entry_point import create_dhafnck_mcp_server
        
        print("\n1. Creating DhafnckMCP server...")
        server = create_dhafnck_mcp_server()
        print("✓ Server created")
        
        # Get the internal MCP server
        print("\n2. Accessing internal MCP server...")
        if hasattr(server, '_server'):
            mcp_server = server._server
            print(f"✓ MCP server found: {type(mcp_server)}")
            
            # Check registered tools
            print("\n3. Checking registered tools...")
            if hasattr(mcp_server, '_tools'):
                tools = mcp_server._tools
                print(f"✓ Found {len(tools)} tools")
                
                print("\n4. Tool names:")
                for tool_name in sorted(tools.keys()):
                    print(f"  - {tool_name}")
                    if 'agent' in tool_name.lower():
                        print(f"    ⭐ Agent-related tool found!")
                
                # Check specifically for call_agent
                if 'call_agent' in tools:
                    print("\n✅ SUCCESS: call_agent is in the tools registry!")
                    tool = tools['call_agent']
                    print(f"  Tool type: {type(tool)}")
                    if hasattr(tool, 'description'):
                        print(f"  Description: {tool.description[:100]}...")
                else:
                    print("\n❌ PROBLEM: call_agent is NOT in the tools registry")
                    print("\nAgent-related tools found:")
                    agent_tools = [name for name in tools.keys() if 'agent' in name.lower()]
                    for tool in agent_tools:
                        print(f"  - {tool}")
            else:
                print("✗ No _tools attribute found on MCP server")
        else:
            print("✗ No _server attribute found on FastMCP server")
            
        # Also check what the server would report via capabilities
        print("\n5. Checking server capabilities...")
        if hasattr(server, 'list_tools'):
            print("✓ Server has list_tools method")
            # This would be called by MCP client to discover tools
            # Note: Can't call directly as it needs MCP protocol context
        
    except Exception as e:
        print(f"\n❌ Error: {e}")
        import traceback
        traceback.print_exc()
    
    print("\n" + "=" * 80)
    print("TEST COMPLETE")
    print("=" * 80)

if __name__ == "__main__":
    # Run async test
    asyncio.run(test_mcp_tools())