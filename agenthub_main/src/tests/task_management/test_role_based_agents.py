#!/usr/bin/env python3
"""
Comprehensive test script for role-based agent tool assignment system.
Tests all agents to verify correct tool permissions based on their roles.
"""

import pytest
from pathlib import Path
from typing import Dict, List, Tuple

from fastmcp.task_management.application.use_cases.call_agent import call_agent

# Define agent role expectations
AGENT_ROLES = {
    # COORDINATORS - Read-only with delegation
    "COORDINATORS": {
        "agents": [
            "security-auditor-agent",
            "deep-research-agent", 
            "task-planning-agent",
            "compliance-scope-agent",
            "ethical-review-agent",
            "root-cause-analysis-agent"
        ],
        "expectations": {
            "can_write": False,
            "can_edit": False,
            "has_task_management": True,
            "has_bash": True  # But restricted to read-only commands
        }
    },
    
    # FILE CREATORS - Full implementation capabilities
    "FILE_CREATORS": {
        "agents": [
            "coding-agent",
            "test-orchestrator-agent",
            "documentation-agent",
            "system-architect-agent",
            "tech_spec_agent",
            "prd_architect_agent"
        ],
        "expectations": {
            "can_write": True,
            "can_edit": True,
            "has_task_management": True,
            "has_bash": True
        }
    },
    
    # SPECIALISTS - Domain-specific tools
    "SPECIALISTS": {
        "agents": [
            "ui-specialist-agent",
            "devops-agent",
            "performance-load-tester-agent",
            "analytics-setup-agent",
            "seo_sem_agent",
            "branding-agent"
        ],
        "expectations": {
            "can_write": True,  # Most specialists can write in their domain
            "can_edit": True,
            "has_task_management": True,
            "has_domain_tools": True  # Should have specialized MCP tools
        }
    }
}


def get_agent_tools(agent_name: str) -> Dict[str, any]:
    """Test an agent and return its tool capabilities."""
    try:
        result = call_agent(agent_name, format='json')
        
        # Check if the call was successful
        if not result.get('success', False):
            return {
                "success": False,
                "agent": agent_name,
                "error": result.get('error', 'Unknown error')
            }
        
        # Extract the agent JSON data
        agent_json = result.get('json', {})
        tools = agent_json.get('tools', [])
        
        # Parse tools - handle both string and list formats
        if isinstance(tools, str):
            tool_list = [t.strip() for t in tools.split(',')]
        else:
            # Already a list
            tool_list = tools if isinstance(tools, list) else []
        
        return {
            "success": True,
            "agent": agent_name,
            "tools": tool_list,
            "can_write": "Write" in tool_list,
            "can_edit": "Edit" in tool_list,
            "has_bash": "Bash" in tool_list,
            "has_task_management": any("manage_task" in t for t in tool_list),
            "has_mcp_tools": any("mcp__" in t for t in tool_list),
            "tool_count": len(tool_list)
        }
    except Exception as e:
        return {
            "success": False,
            "agent": agent_name,
            "error": str(e)
        }


def validate_agent_role(agent_name: str, role: str, expectations: Dict) -> Tuple[bool, List[str]]:
    """Validate an agent against role expectations."""
    result = get_agent_tools(agent_name)
    
    if not result["success"]:
        return False, [f"Failed to test agent: {result['error']}"]
    
    failures = []
    
    # Check each expectation
    for key, expected_value in expectations.items():
        if key == "has_domain_tools":
            # Special case: just check for MCP tools
            if expected_value and not result["has_mcp_tools"]:
                failures.append(f"Expected domain-specific MCP tools but found none")
        elif key in result:
            actual_value = result[key]
            if actual_value != expected_value:
                failures.append(f"{key}: expected {expected_value}, got {actual_value}")
    
    return len(failures) == 0, failures


# Create parameterized tests for each agent
def get_test_params():
    """Generate test parameters for pytest."""
    params = []
    for role, config in AGENT_ROLES.items():
        for agent_name in config["agents"]:
            params.append((agent_name, role, config["expectations"]))
    return params


@pytest.mark.parametrize("agent_name,role,expectations", get_test_params())
def test_agent_tools(agent_name: str, role: str, expectations: Dict):
    """Test that an agent has the correct tools for its role."""
    passed, failures = validate_agent_role(agent_name, role, expectations)
    
    if not passed:
        # Get agent details for debugging
        agent_details = get_agent_tools(agent_name)
        
        failure_message = f"Agent {agent_name} ({role}) failed validation:\n"
        for failure in failures:
            failure_message += f"  - {failure}\n"
        
        if agent_details["success"]:
            failure_message += f"\nAgent details:\n"
            failure_message += f"  - Can Write: {agent_details['can_write']}\n"
            failure_message += f"  - Can Edit: {agent_details['can_edit']}\n"
            failure_message += f"  - Has Task Management: {agent_details['has_task_management']}\n"
            failure_message += f"  - Total Tools: {agent_details['tool_count']}\n"
        else:
            failure_message += f"\nError testing agent: {agent_details['error']}\n"
        
        pytest.fail(failure_message)
    
    # Test passed
    assert passed, f"Agent {agent_name} conforms to {role} role expectations"


def test_all_agents_coverage():
    """Test that we have coverage for a reasonable number of agents."""
    total_agents = sum(len(config["agents"]) for config in AGENT_ROLES.values())
    assert total_agents >= 18, f"Expected at least 18 agents, but only found {total_agents}"


def generate_report(results_summary: List[Dict]) -> str:
    """Generate a detailed markdown report of test results."""
    report = []
    report.append("# Role-Based Agent Tool Assignment Test Report\n")
    report.append(f"**Test Date**: 2025-09-09\n")
    report.append(f"**Total Agents**: {len(results_summary)}\n")
    
    # Group by role
    for role in AGENT_ROLES.keys():
        report.append(f"\n## {role}\n")
        
        role_results = [r for r in results_summary if r["role"] == role]
        
        for result in role_results:
            status = "✅" if result["passed"] else "❌"
            report.append(f"\n### {status} {result['agent']}\n")
            
            if result["details"]["success"]:
                details = result["details"]
                report.append(f"- **Can Write Files**: {details['can_write']}\n")
                report.append(f"- **Can Edit Files**: {details['can_edit']}\n")
                report.append(f"- **Has Task Management**: {details['has_task_management']}\n")
                report.append(f"- **Has MCP Tools**: {details['has_mcp_tools']}\n")
                report.append(f"- **Total Tools**: {details['tool_count']}\n")
            else:
                report.append(f"- **Error**: {result['details']['error']}\n")
    
    return "".join(report)