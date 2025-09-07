#!/usr/bin/env python
"""Test and fix tool registration issue"""

import sys
import os

# Add src to path
sys.path.insert(0, '/home/daihungpham/__projects__/agentic-project/dhafnck_mcp_main/src')

# Suppress logs for clarity
import logging
logging.basicConfig(level=logging.ERROR)

def test_and_fix():
    print("=" * 80)
    print("TESTING AND FIXING TOOL REGISTRATION")
    print("=" * 80)
    
    # Import FastMCP
    from fastmcp.server.server import FastMCP
    
    # Create a test server
    server = FastMCP(
        name="Test Server",
        instructions="Test",
        enable_task_management=False
    )
    
    # Test 1: Simple tool registration
    print("\n1. Testing simple tool registration...")
    
    @server.tool(description="Simple test tool")
    def simple_tool(arg: str) -> str:
        return f"Got: {arg}"
    
    print("✓ Simple tool registered")
    
    # Test 2: Tool with complex description
    print("\n2. Testing tool with complex description...")
    
    complex_desc = """
🤖 COMPLEX TOOL - With emojis and formatting

⭐ WHAT IT DOES: Tests complex descriptions
📋 WHEN TO USE: When testing
    """
    
    try:
        @server.tool(description=complex_desc)
        def complex_tool(arg: str) -> str:
            return f"Complex: {arg}"
        print("✓ Complex tool registered")
    except Exception as e:
        print(f"✗ Complex tool failed: {e}")
    
    # Test 3: Test call_agent registration directly
    print("\n3. Testing call_agent registration...")
    
    from fastmcp.task_management.interface.mcp_controllers.call_agent_mcp_controller.call_agent_description import get_call_agent_description, get_call_agent_parameters
    from typing import Annotated
    from pydantic import Field
    
    desc = get_call_agent_description()
    params = get_call_agent_parameters()
    
    print(f"  Description type: {type(desc)}")
    print(f"  Description length: {len(desc)}")
    
    # Try registering with the actual description
    try:
        def call_agent(name_agent: Annotated[str, Field(description=params["name_agent"]["description"])]) -> dict:
            return {"agent": name_agent}
        
        # Register using the same pattern as the controller
        server.tool(description=desc)(call_agent)
        print("✓ call_agent registered successfully!")
    except Exception as e:
        print(f"✗ call_agent registration failed: {e}")
        print(f"  Error type: {type(e)}")
        
        # Try with a simpler description
        print("\n4. Trying with simplified description...")
        simple_desc = "Call an agent by name to execute specialized tasks"
        try:
            server.tool(description=simple_desc)(call_agent)
            print("✓ call_agent registered with simple description!")
        except Exception as e2:
            print(f"✗ Still failed: {e2}")
    
    # Test 4: Check what's in the server's tools
    print("\n5. Checking registered tools...")
    if hasattr(server, '_tools'):
        print(f"✓ Server has {len(server._tools)} tools")
        for name in server._tools:
            print(f"  - {name}")
    elif hasattr(server, '_server') and hasattr(server._server, '_tools'):
        tools = server._server._tools
        print(f"✓ Server has {len(tools)} tools")
        for name in tools:
            print(f"  - {name}")
    else:
        print("✗ Cannot access tools registry")
    
    print("\n" + "=" * 80)
    print("TEST COMPLETE")
    print("=" * 80)

if __name__ == "__main__":
    test_and_fix()