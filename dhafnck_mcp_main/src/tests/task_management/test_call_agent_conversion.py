#!/usr/bin/env python3
"""Test script for call_agent Claude Code format conversion"""

import os
import sys
import logging
from pathlib import Path

# Add project root to Python path
project_root = Path(__file__).resolve().parents[2]  # Go up to src
sys.path.insert(0, str(project_root))

# Import the call_agent function
from fastmcp.task_management.application.use_cases.call_agent import call_agent

def test_agent_conversion():
    """Test converting multiple agents to Claude Code format"""
    logging.basicConfig(level=logging.INFO)
    
    agents_to_test = ["coding-agent", "debugger-agent", "security-auditor-agent"]
    
    for agent_name in agents_to_test:
        print(f"\n{'='*50}")
        print(f"Testing call_agent conversion for {agent_name}...")
        
        # Test with agent
        result = call_agent(agent_name)
        
        print(f"\n=== Call Agent Result for {agent_name} ===")
        print(f"Success: {result['success']}")
        
        if result['success']:
            print(f"\nAgent Name: {result['agent_info']['name']}")
            print(f"Source: {result.get('source', 'unknown')}")
            
            if 'claude_agent_definition' in result:
                print(f"\n=== Claude Code Format (first 500 chars) ===")
                claude_def = result['claude_agent_definition']
                # Show only the frontmatter and beginning of content
                lines = claude_def.split('\n')
                frontmatter_end = -1
                for i, line in enumerate(lines):
                    if i > 0 and line.strip() == '---':
                        frontmatter_end = i + 1
                        break
                
                if frontmatter_end > 0:
                    # Show frontmatter + first few lines of content
                    display_lines = lines[:frontmatter_end + 3]
                    print('\n'.join(display_lines))
                    if len(lines) > frontmatter_end + 3:
                        print("... [content truncated for readability] ...")
                else:
                    print(claude_def[:500] + "..." if len(claude_def) > 500 else claude_def)
            else:
                print("\n❌ No claude_agent_definition in result!")
                
            print(f"\n=== Available Capabilities ===")
            if 'capabilities_summary' in result:
                for key, value in result['capabilities_summary'].items():
                    print(f"  {key}: {value}")
        else:
            print(f"❌ Error: {result.get('error', 'Unknown error')}")
            print(f"Available agents: {result.get('available_agents', [])}")

if __name__ == "__main__":
    test_agent_conversion()