#!/usr/bin/env python3
"""Debug script to test agent assignment and find UUID iteration error"""

import sys
import os

# Add the src directory to Python path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'dhafnck_mcp_main', 'src'))

def test_agent_assignment():
    """Test the exact agent assignment operation that's failing"""
    
    # Import the required components
    from fastmcp.task_management.interface.controllers.git_branch_mcp_controller import GitBranchMCPController
    
    # Create controller
    controller = GitBranchMCPController()
    
    # Test parameters from the failing call
    test_params = {
        "action": "assign_agent",
        "project_id": "ca5a617a-160f-45b4-977e-628fb5651189",
        "git_branch_id": "b7781aac-4996-46fd-a20a-b30cce9d9e0d",
        "agent_id": "@coding_agent"
    }
    
    print(f"Testing agent assignment with: {test_params}")
    
    try:
        # Call the controller method directly
        result = controller.handle(**test_params)
        print(f"Success: {result}")
        
    except Exception as e:
        import traceback
        print(f"Error occurred: {e}")
        print("Full stack trace:")
        traceback.print_exc()
        
        # Try to identify which line is causing the issue
        print("\nAnalyzing traceback...")
        tb = traceback.extract_tb(e.__traceback__)
        for frame in tb:
            if "argument of type 'UUID' is not iterable" in str(e):
                print(f"Error likely in: {frame.filename}:{frame.lineno} - {frame.line}")


if __name__ == "__main__":
    test_agent_assignment()