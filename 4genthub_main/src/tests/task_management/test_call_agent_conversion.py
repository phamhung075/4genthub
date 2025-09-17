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
            # The agent is now in result['agent'] not result['agent_info']
            agent = result.get('agent', {})
            print(f"\nAgent Name: {agent.get('name', 'unknown')}")
            print(f"Source: {result.get('source', 'unknown')}")

            # Display the agent JSON structure
            if agent:
                print(f"\n=== Agent Structure ===")
                print(f"Name: {agent.get('name')}")
                print(f"Description: {agent.get('description')}")
                print(f"Tools: {agent.get('tools', [])}")
                print(f"Category: {agent.get('category', 'N/A')}")
                print(f"Version: {agent.get('version', 'N/A')}")

                # Show first 500 chars of system prompt
                system_prompt = agent.get('system_prompt', '')
                if system_prompt:
                    print(f"\n=== System Prompt (first 500 chars) ===")
                    print(system_prompt[:500] + "..." if len(system_prompt) > 500 else system_prompt)
            else:
                print("\n❌ No agent data in result!")

            # Test markdown format as well
            markdown_result = call_agent(agent_name, format="markdown")
            if markdown_result.get('success') and markdown_result.get('markdown'):
                print(f"\n=== Markdown Format Available ===")
                markdown_content = markdown_result['markdown']
                lines = markdown_content.split('\n')[:15]  # Show first 15 lines
                print('\n'.join(lines))
                if len(markdown_content.split('\n')) > 15:
                    print("... [content truncated for readability] ...")
        else:
            print(f"❌ Error: {result.get('error', 'Unknown error')}")
            print(f"Available agents: {result.get('available_agents', [])}")

if __name__ == "__main__":
    test_agent_conversion()