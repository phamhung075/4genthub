#!/usr/bin/env python3
"""Test script to validate assignees parameter fix"""

import sys
import os

# Add the project path to sys.path
project_path = "/home/daihungpham/__projects__/agentic-project/dhafnck_mcp_main/src"
sys.path.insert(0, project_path)

def test_agent_role_validation():
    """Test AgentRole validation directly"""
    try:
        from fastmcp.task_management.domain.enums.agent_roles import AgentRole, resolve_legacy_role
        
        print("=== Testing AgentRole Validation ===")
        
        # Test cases
        test_cases = [
            "coding-agent",
            "coding-agent", 
            "test-orchestrator-agent",
            "test-orchestrator-agent",
            "@coding-agent",  # Invalid format
            "@test-orchestrator-agent",  # Invalid format
            "@invalid_agent"
        ]
        
        for test_case in test_cases:
            print(f"\nTesting: '{test_case}'")
            
            # Clean the assignee
            clean_assignee = test_case.strip().lstrip('@')
            print(f"  Cleaned: '{clean_assignee}'")
            
            # Check if valid
            is_valid = AgentRole.is_valid_role(clean_assignee)
            print(f"  Is valid role: {is_valid}")
            
            # Try legacy resolution
            resolved = resolve_legacy_role(test_case)
            print(f"  Legacy resolved: {resolved}")
            
            # Final verdict
            if is_valid:
                final_assignee = f"@{clean_assignee}" if not test_case.startswith("@") else test_case
                print(f"  ✅ VALID: {final_assignee}")
            elif resolved and AgentRole.is_valid_role(resolved):
                final_assignee = f"@{resolved}"
                print(f"  ✅ VALID (resolved): {final_assignee}")
            else:
                print(f"  ❌ INVALID")
                
        # Test the validation logic from CRUD handler
        print("\n=== Testing CRUD Handler Logic ===")
        assignees = ["coding-agent", "test-orchestrator-agent"]
        
        validated_assignees = []
        invalid_assignees = []
        
        for assignee in assignees:
            if assignee and assignee.strip():
                clean_assignee = assignee.strip()
                
                # Try to resolve legacy role names
                resolved_assignee = resolve_legacy_role(clean_assignee)
                if resolved_assignee:
                    if not resolved_assignee.startswith("@"):
                        resolved_assignee = f"@{resolved_assignee}"
                    validated_assignees.append(resolved_assignee)
                    print(f"Resolved legacy assignee '{assignee}' to '{resolved_assignee}'")
                elif AgentRole.is_valid_role(clean_assignee.lstrip('@')):
                    if not clean_assignee.startswith("@"):
                        clean_assignee = f"@{clean_assignee}"
                    validated_assignees.append(clean_assignee)
                    print(f"Validated assignee: '{clean_assignee}'")
                elif clean_assignee.startswith("@") and AgentRole.is_valid_role(clean_assignee[1:]):
                    validated_assignees.append(clean_assignee)
                    print(f"Validated assignee with @ prefix: '{clean_assignee}'")
                else:
                    invalid_assignees.append(assignee)
                    print(f"Invalid assignee: '{assignee}'")
        
        print(f"\nValidated assignees: {validated_assignees}")
        print(f"Invalid assignees: {invalid_assignees}")
        
        if validated_assignees and not invalid_assignees:
            print("✅ CRUD Handler validation would PASS")
        else:
            print("❌ CRUD Handler validation would FAIL")
        
    except Exception as e:
        print(f"Error during testing: {e}")
        import traceback
        traceback.print_exc()

def test_available_roles():
    """Test what roles are actually available"""
    try:
        from fastmcp.task_management.domain.enums.agent_roles import AgentRole
        
        print("=== Available Agent Roles ===")
        all_roles = AgentRole.get_all_roles()
        print(f"Total roles: {len(all_roles)}")
        
        for role in sorted(all_roles)[:20]:  # Show first 20
            print(f"  - {role}")
        
        if len(all_roles) > 20:
            print(f"  ... and {len(all_roles) - 20} more")
            
        # Check specific roles we're testing
        test_roles = ["coding-agent", "test-orchestrator-agent"]
        print(f"\nChecking test roles:")
        for role in test_roles:
            exists = role in all_roles
            print(f"  - {role}: {'✅ EXISTS' if exists else '❌ MISSING'}")
            
    except Exception as e:
        print(f"Error getting available roles: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    print("Testing Assignees Parameter Fix\n")
    test_available_roles()
    print("\n" + "="*50 + "\n")
    test_agent_role_validation()