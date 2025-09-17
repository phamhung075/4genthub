#!/usr/bin/env python3
"""Test that MCP tools are properly included in the tools field"""

import json
import sys
from pathlib import Path

# Add project root to Python path
project_root = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(project_root))

from fastmcp.task_management.application.use_cases.call_agent import call_agent

def test_mcp_tools_inclusion():
    """Test that MCP tools like mcp__browsermcp__browser_navigate are included in tools"""
    
    # Test with test-orchestrator-agent which should have MCP tools
    result = call_agent("test-orchestrator-agent")
    
    print("=== MCP TOOLS INCLUSION TEST ===")
    print(f"Success: {result['success']}")
    
    if result['success']:
        agent = result['agent']
        
        print(f"\nAgent Name: {agent['name']}")
        print(f"Tools Field: {agent.get('tools', 'NOT PRESENT')}")
        
        # Check if tools contain MCP tools
        tools = agent.get('tools', [])
        mcp_tools_found = []

        expected_mcp_tools = [
            'mcp__browsermcp__browser_navigate',
            'mcp__browsermcp__browser_snapshot',
            'mcp__browsermcp__browser_click',
            'mcp__4genthub_http__manage_task',
            'mcp__sequential-thinking__sequentialthinking'
        ]

        # Handle both list and string formats
        if isinstance(tools, list):
            tools_list = tools
        elif isinstance(tools, str):
            tools_list = [tools] if tools else []
        else:
            tools_list = []

        for mcp_tool in expected_mcp_tools:
            if any(mcp_tool in str(tool) for tool in tools_list):
                mcp_tools_found.append(mcp_tool)
        
        print(f"\n=== MCP TOOLS ANALYSIS ===")
        print(f"Expected MCP Tools: {len(expected_mcp_tools)}")
        print(f"Found MCP Tools: {len(mcp_tools_found)}")
        
        if mcp_tools_found:
            print(f"\n✅ MCP Tools Found in 'tools' field:")
            for tool in mcp_tools_found:
                print(f"  - {tool}")
        else:
            print(f"\n❌ No MCP tools found in 'tools' field")
            
        # Also show capabilities for comparison
        capabilities = result.get('capabilities', [])
        print(f"\n=== CAPABILITIES COMPARISON ===")
        print(f"Capabilities type: {type(capabilities)}")
        print(f"Capabilities content: {capabilities}")
        
        if isinstance(capabilities, list):
            print(f"Capabilities array: {len(capabilities)} tools")
            for cap in capabilities[:5]:  # Show first 5
                print(f"  - {cap}")
            if len(capabilities) > 5:
                print(f"  ... and {len(capabilities) - 5} more")
        else:
            print(f"Capabilities (non-list): {capabilities}")
            
        # Show complete tools field for debugging
        print(f"\n=== COMPLETE TOOLS FIELD ===")
        if 'tools' in agent:
            # Handle both list and string formats
            if isinstance(agent['tools'], list):
                tools_list = agent['tools']
            elif isinstance(agent['tools'], str):
                tools_list = agent['tools'].split(', ') if agent['tools'] else []
            else:
                tools_list = []

            for i, tool in enumerate(tools_list):
                tool_str = str(tool)
                prefix = "✅" if tool_str.startswith('mcp__') else "📝"
                print(f"  {i+1:2d}. {prefix} {tool_str}")
        else:
            print("  No tools field present")
            
        # Show markdown format too (if available)
        print(f"\n=== MARKDOWN FORMAT CHECK ===")
        if 'formats' in result and 'markdown' in result['formats']:
            markdown = result['formats']['markdown']
            lines = markdown.split('\n')

            for line in lines:
                if line.startswith('tools:'):
                    print(f"Markdown tools line: {line}")
                    break
            else:
                print("No tools line found in markdown")
        else:
            print("No 'formats' field in result - skipping markdown check")
            
    else:
        print(f"❌ Error: {result.get('error')}")
        
    return result

if __name__ == "__main__":
    test_mcp_tools_inclusion()