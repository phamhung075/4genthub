#!/usr/bin/env python3
"""
Debug script to test agent assignment and find the UUID iteration error
"""

import sys
import os
import logging

# Set up logging to see debug messages
logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

# Add the src directory to Python path
sys.path.insert(0, '/home/daihungpham/__projects__/agentic-project/dhafnck_mcp_main/src')

def test_agent_assignment():
    """Test agent assignment with extensive debug logging"""
    print("\n" + "="*80)
    print("TESTING AGENT ASSIGNMENT WITH DEBUG LOGGING")
    print("="*80 + "\n")
    
    try:
        # Import after path is set
        from fastmcp.task_management.application.factories.agent_facade_factory import AgentFacadeFactory
        
        # Test parameters
        project_id = "d0abe880-56e5-477e-b3ab-e778c24d84d6"
        git_branch_id = "df554be9-728e-4aa9-9df3-d6c0ca40af99"
        agent_id = "ee6270c4-2918-5c45-b4a2-b3636d792632"
        
        print(f"Test Parameters:")
        print(f"  project_id: {project_id} (type: {type(project_id)})")
        print(f"  git_branch_id: {git_branch_id} (type: {type(git_branch_id)})")
        print(f"  agent_id: {agent_id} (type: {type(agent_id)})")
        print()
        
        # Create facade
        print("Creating agent facade...")
        factory = AgentFacadeFactory()
        agent_facade = factory.create_agent_facade(project_id=project_id)
        print("Agent facade created successfully")
        print()
        
        # Try to assign agent
        print("Attempting to assign agent to branch...")
        print("Watch the debug logs above for the exact error location!")
        print()
        
        result = agent_facade.assign_agent(
            project_id=project_id,
            agent_id=agent_id,
            git_branch_id=git_branch_id
        )
        
        print(f"Result: {result}")
        
        if result.get("success"):
            print("\n✅ Agent assignment successful!")
        else:
            print(f"\n❌ Agent assignment failed: {result.get('error')}")
            
    except Exception as e:
        print(f"\n❌ Exception occurred: {e}")
        print(f"Exception type: {type(e)}")
        import traceback
        print("\nFull traceback:")
        traceback.print_exc()

if __name__ == "__main__":
    test_agent_assignment()