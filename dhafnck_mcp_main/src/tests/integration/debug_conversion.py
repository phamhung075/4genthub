#!/usr/bin/env python3
"""
Debug script to test the exact conversion logic
"""

def test_conversion():
    """Test the exact conversion logic from task controller"""
    
    # This simulates exactly what happens in task_mcp_controller.py lines 222-228
    assignees = "coding_agent,test_orchestrator_agent"
    
    print(f"Original assignees: {assignees}")
    print(f"Type: {type(assignees)}")
    
    # Handle flexible input types for parameters that can be string, list, or comma-separated
    if assignees is not None and isinstance(assignees, str):
        # Convert string to list - support both single values and comma-separated values
        if ',' in assignees:
            assignees = [a.strip() for a in assignees.split(',') if a.strip()]
        else:
            # Single assignee - convert to list
            assignees = [assignees.strip()] if assignees.strip() else []
    
    print(f"Converted assignees: {assignees}")
    print(f"Type: {type(assignees)}")
    print(f"Length: {len(assignees)}")
    print(f"Validation check (not assignees or len(assignees) == 0): {not assignees or len(assignees) == 0}")
    
    # Test the values
    for i, assignee in enumerate(assignees):
        print(f"  [{i}]: '{assignee}' (type: {type(assignee)})")

if __name__ == "__main__":
    test_conversion()