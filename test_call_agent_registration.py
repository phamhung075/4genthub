#!/usr/bin/env python
"""Test script to verify call_agent tool registration"""

import sys
import os
import logging

# Add src to path
sys.path.insert(0, '/home/daihungpham/__projects__/agentic-project/dhafnck_mcp_main/src')

# Set up logging to see what's happening
logging.basicConfig(level=logging.DEBUG, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

def test_call_agent_registration():
    """Test if call_agent tool can be registered properly"""
    
    print("=" * 80)
    print("TESTING CALL_AGENT TOOL REGISTRATION")
    print("=" * 80)
    
    try:
        # Step 1: Import the DDDCompliantMCPTools
        print("\n1. Importing DDDCompliantMCPTools...")
        from fastmcp.task_management.interface.ddd_compliant_mcp_tools import DDDCompliantMCPTools
        print("✓ DDDCompliantMCPTools imported successfully")
        
        # Step 2: Create instance
        print("\n2. Creating DDDCompliantMCPTools instance...")
        tools = DDDCompliantMCPTools()
        print("✓ DDDCompliantMCPTools instance created")
        
        # Step 3: Check if call_agent controller exists
        print("\n3. Checking call_agent controller...")
        if hasattr(tools, '_call_agent_controller'):
            print("✓ _call_agent_controller exists")
            controller = tools._call_agent_controller
            print(f"  Controller type: {type(controller)}")
            print(f"  Has register_tools: {hasattr(controller, 'register_tools')}")
            print(f"  Has call_agent: {hasattr(controller, 'call_agent')}")
        else:
            print("✗ _call_agent_controller NOT FOUND")
            print("  Available attributes:", [attr for attr in dir(tools) if 'agent' in attr.lower()])
        
        # Step 4: Create a mock MCP server to test registration
        print("\n4. Testing tool registration with mock MCP server...")
        from fastmcp.server.server import FastMCP
        
        # Create a minimal mock server
        mock_server = FastMCP(
            name="Test Server",
            instructions="Test server for debugging",
            enable_task_management=False
        )
        
        # Track registered tools
        registered_tools = []
        original_tool = mock_server.tool
        
        def mock_tool_decorator(description=None, **kwargs):
            """Mock decorator to track tool registration"""
            def decorator(func):
                tool_info = {
                    'name': func.__name__,
                    'description': description,
                    'function': func
                }
                registered_tools.append(tool_info)
                print(f"  📌 Tool registered: {func.__name__}")
                return func
            return decorator
        
        # Replace tool decorator temporarily
        mock_server.tool = mock_tool_decorator
        
        # Try to register tools
        print("\n5. Registering all tools...")
        tools.register_tools(mock_server)
        
        # Check what was registered
        print(f"\n6. Total tools registered: {len(registered_tools)}")
        print("\nRegistered tools:")
        for i, tool in enumerate(registered_tools, 1):
            print(f"  {i}. {tool['name']}")
            if 'agent' in tool['name'].lower():
                print(f"     ⭐ Found agent-related tool: {tool['name']}")
        
        # Specifically check for call_agent
        call_agent_found = any(tool['name'] == 'call_agent' for tool in registered_tools)
        if call_agent_found:
            print("\n✅ SUCCESS: call_agent tool was registered!")
        else:
            print("\n❌ PROBLEM: call_agent tool was NOT registered")
            print("\nDebugging call_agent registration specifically...")
            
            # Try to register just the call_agent tool
            if hasattr(tools, '_call_agent_controller'):
                print("\n7. Attempting direct call_agent registration...")
                try:
                    tools._call_agent_controller.register_tools(mock_server)
                    print("  Direct registration completed")
                    
                    # Check if it was added
                    new_tools = [t for t in registered_tools if t not in registered_tools[:len(registered_tools)-1]]
                    if new_tools:
                        print(f"  New tools registered: {[t['name'] for t in new_tools]}")
                    else:
                        print("  No new tools were registered")
                except Exception as e:
                    print(f"  Error during direct registration: {e}")
                    import traceback
                    traceback.print_exc()
        
        # Step 7: Test the actual call_agent method
        print("\n8. Testing call_agent method directly...")
        if hasattr(tools, 'call_agent'):
            print("✓ call_agent method exists on tools instance")
            try:
                # Try calling with a test agent name
                result = tools.call_agent(name_agent="@test_agent")
                print(f"  Method callable, returned: {type(result)}")
            except Exception as e:
                print(f"  Method exists but call failed (expected): {e}")
        else:
            print("✗ call_agent method NOT FOUND on tools instance")
        
        # Step 8: Check the call_agent use case
        print("\n9. Checking CallAgentUseCase...")
        if hasattr(tools, '_call_agent_use_case'):
            use_case = tools._call_agent_use_case
            print(f"✓ CallAgentUseCase exists: {type(use_case)}")
            print(f"  Has execute: {hasattr(use_case, 'execute')}")
        else:
            print("✗ _call_agent_use_case NOT FOUND")
            
    except ImportError as e:
        print(f"\n❌ Import Error: {e}")
        import traceback
        traceback.print_exc()
    except Exception as e:
        print(f"\n❌ Unexpected Error: {e}")
        import traceback
        traceback.print_exc()
    
    print("\n" + "=" * 80)
    print("TEST COMPLETE")
    print("=" * 80)

if __name__ == "__main__":
    test_call_agent_registration()