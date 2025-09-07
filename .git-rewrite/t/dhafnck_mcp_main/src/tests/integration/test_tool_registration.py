#!/usr/bin/env python3
"""Test script to diagnose MCP tool registration issue"""

import sys
import os
import logging

# Set up logging to see all messages
logging.basicConfig(level=logging.DEBUG, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')

# Add src to path
sys.path.insert(0, '/home/daihungpham/agentic-project/dhafnck_mcp_main/src')
os.environ['PYTHONPATH'] = '/home/daihungpham/agentic-project/dhafnck_mcp_main/src'

# Set database paths
os.environ['MCP_DB_PATH'] = '/home/daihungpham/agentic-project/dhafnck_mcp_main/data/dhafnck_mcp.db'

print("=" * 80)
print("Testing MCP Tool Registration")
print("=" * 80)

try:
    print("\n1. Importing FastMCP...")
    from fastmcp.server.server import FastMCP
    print("✅ FastMCP imported successfully")
    
    print("\n2. Creating FastMCP server instance...")
    server = FastMCP(
        name="Test Server",
        instructions="Test server for debugging",
        version="1.0.0",
        enable_task_management=False,
        on_duplicate_tools="ignore"
    )
    print(f"✅ Server created: {server.name}")
    
    print("\n3. Checking initial tools...")
    initial_tools = getattr(server, '_tools', {})
    print(f"   Initial tool count: {len(initial_tools)}")
    for tool_name in list(initial_tools.keys())[:5]:
        print(f"   - {tool_name}")
    
    print("\n4. Importing DDDCompliantMCPTools...")
    from fastmcp.task_management.interface.ddd_compliant_mcp_tools import DDDCompliantMCPTools
    print("✅ DDDCompliantMCPTools imported successfully")
    
    print("\n5. Creating DDDCompliantMCPTools instance...")
    ddd_tools = DDDCompliantMCPTools()
    print("✅ DDDCompliantMCPTools instance created")
    
    print("\n6. Registering DDD tools with server...")
    try:
        ddd_tools.register_tools(server)
        print("✅ DDD tools registration completed")
    except Exception as e:
        print(f"❌ DDD tools registration failed: {e}")
        import traceback
        traceback.print_exc()
    
    print("\n7. Checking registered tools...")
    registered_tools = getattr(server, '_tools', {})
    print(f"   Total tool count: {len(registered_tools)}")
    
    # List all tools
    print("\n   All registered tools:")
    for i, tool_name in enumerate(registered_tools.keys(), 1):
        print(f"   {i:3d}. {tool_name}")
    
    # Check for specific expected tools
    print("\n8. Checking for expected tools...")
    expected_tools = [
        'manage_task',
        'manage_project',
        'manage_git_branch',
        'manage_subtask',
        'manage_context',
        'manage_agent',
        'call_agent',
        'manage_rule'
    ]
    
    for tool in expected_tools:
        if tool in registered_tools:
            print(f"   ✅ {tool} found")
        else:
            print(f"   ❌ {tool} NOT FOUND")
    
    print("\n9. Testing tool schema generation...")
    try:
        # Try to get the schema for tools/list response
        tools_list = []
        for name, tool in registered_tools.items():
            tool_info = {
                "name": name,
                "description": tool.description if hasattr(tool, 'description') else "No description",
                "inputSchema": {}
            }
            tools_list.append(tool_info)
        print(f"   ✅ Generated schema for {len(tools_list)} tools")
    except Exception as e:
        print(f"   ❌ Schema generation failed: {e}")

except Exception as e:
    print(f"\n❌ Test failed with error: {e}")
    import traceback
    traceback.print_exc()

print("\n" + "=" * 80)
print("Test Complete")
print("=" * 80)