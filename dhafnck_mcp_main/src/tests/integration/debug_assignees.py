#!/usr/bin/env python3
"""
Debug script to test assignees validation logic
"""

import sys
import os

# Add the source path to sys.path
sys.path.append('/home/daihungpham/__projects__/agentic-project/dhafnck_mcp_main/src')

from fastmcp.task_management.domain.enums.agent_roles import AgentRole, resolve_legacy_role

def test_agent_validation():
    """Test different assignee formats"""
    
    test_assignees = [
        "coding_agent",
        "@coding_agent", 
        "CODING",
        "@CODING",
        "coding-agent",
        "@coding-agent",
        "test_orchestrator_agent",
        "@test_orchestrator_agent"
    ]
    
    print("=== Testing AgentRole validation ===")
    print(f"Available roles: {len(AgentRole.get_all_roles())}")
    print("First 10 roles:", AgentRole.get_all_roles()[:10])
    print()
    
    for assignee in test_assignees:
        print(f"Testing assignee: '{assignee}'")
        
        # Test is_valid_role
        clean_assignee = assignee.lstrip('@')
        is_valid = AgentRole.is_valid_role(clean_assignee)
        print(f"  AgentRole.is_valid_role('{clean_assignee}'): {is_valid}")
        
        # Test resolve_legacy_role
        resolved = resolve_legacy_role(assignee)
        print(f"  resolve_legacy_role('{assignee}'): {resolved}")
        
        # Test if resolved is valid
        if resolved:
            resolved_clean = resolved.lstrip('@')
            resolved_valid = AgentRole.is_valid_role(resolved_clean)
            print(f"  AgentRole.is_valid_role('{resolved_clean}'): {resolved_valid}")
        
        print()

if __name__ == "__main__":
    test_agent_validation()