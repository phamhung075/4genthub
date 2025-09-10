#!/usr/bin/env python3
"""
Debug script to test the full task creation flow
"""

import sys
sys.path.append('/home/daihungpham/__projects__/agentic-project/dhafnck_mcp_main/src')

def test_string_to_list_conversion():
    """Test the string to list conversion logic from task_mcp_controller.py"""
    
    test_assignees_inputs = [
        "coding_agent",
        "@coding_agent",
        "coding_agent,test_orchestrator_agent",
        "@coding_agent,@test_orchestrator_agent",
        "coding_agent, test_orchestrator_agent",  # with spaces
    ]
    
    print("=== Testing String to List Conversion ===")
    
    for assignees_input in test_assignees_inputs:
        print(f"\nInput: '{assignees_input}'")
        
        # Simulate the conversion logic from task_mcp_controller.py lines 222-228
        assignees = assignees_input
        if assignees is not None and isinstance(assignees, str):
            # Convert string to list - support both single values and comma-separated values
            if ',' in assignees:
                assignees = [a.strip() for a in assignees.split(',') if a.strip()]
            else:
                # Single assignee - convert to list
                assignees = [assignees.strip()] if assignees.strip() else []
        
        print(f"Output: {assignees}")
        print(f"Type: {type(assignees)}")
        print(f"Length: {len(assignees) if isinstance(assignees, list) else 'N/A'}")
        
        # Test if this would pass the validation in crud_handler.py line 60
        validation_passes = assignees and len(assignees) > 0
        print(f"Would pass validation (not assignees or len(assignees) == 0): {not validation_passes}")

def test_task_validation():
    """Test the task entity validation"""
    
    from fastmcp.task_management.domain.entities.task import Task
    
    print("\n=== Testing Task Entity Validation ===")
    
    # Test with different assignee formats
    test_cases = [
        ["coding_agent"],
        ["@coding_agent"], 
        ["coding-agent"],
        ["@coding-agent"],
        ["coding_agent", "test_orchestrator_agent"],
        ["@coding_agent", "@test_orchestrator_agent"]
    ]
    
    for assignees in test_cases:
        print(f"\nTesting assignees: {assignees}")
        try:
            dummy_task = Task(title="test", description="test")
            validated_assignees = dummy_task.validate_assignee_list(assignees)
            print(f"  Validation successful: {validated_assignees}")
        except ValueError as e:
            print(f"  Validation failed: {e}")

if __name__ == "__main__":
    test_string_to_list_conversion()
    test_task_validation()