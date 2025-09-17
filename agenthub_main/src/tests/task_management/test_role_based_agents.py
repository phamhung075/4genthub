#!/usr/bin/env python3
"""
Comprehensive test script for role-based agent tool assignment system.
Tests all agents to verify correct tool permissions based on their roles.
"""

import sys
import json
from pathlib import Path
from typing import Dict, List, Tuple

# Add src to path
sys.path.append(str(Path(__file__).parent.parent.parent))

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
            "ui_designer_expert_shadcn_agent",
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


def test_agent_tools(agent_name: str) -> Dict[str, any]:
    """Test an agent and return its tool capabilities."""
    try:
        result = call_agent(agent_name, format='json')
        tools = result['json']['tools']
        
        # Parse tools string into list
        tool_list = [t.strip() for t in tools.split(',')]
        
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
    result = test_agent_tools(agent_name)
    
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


def run_comprehensive_tests():
    """Run tests on all agents and report results."""
    print("=" * 80)
    print("ROLE-BASED AGENT TOOL ASSIGNMENT VALIDATION")
    print("=" * 80)
    
    all_passed = True
    results_summary = []
    
    for role, config in AGENT_ROLES.items():
        print(f"\n{'=' * 40}")
        print(f"Testing {role}")
        print(f"{'=' * 40}")
        
        agents = config["agents"]
        expectations = config["expectations"]
        
        role_passed = True
        
        for agent_name in agents:
            passed, failures = validate_agent_role(agent_name, role, expectations)
            
            # Get agent details for reporting
            agent_details = test_agent_tools(agent_name)
            
            status = "✅ PASS" if passed else "❌ FAIL"
            print(f"\n{agent_name}: {status}")
            
            if agent_details["success"]:
                print(f"  - Can Write: {agent_details['can_write']}")
                print(f"  - Can Edit: {agent_details['can_edit']}")
                print(f"  - Has Task Management: {agent_details['has_task_management']}")
                print(f"  - Total Tools: {agent_details['tool_count']}")
                
                if not passed:
                    print(f"  - Failures:")
                    for failure in failures:
                        print(f"    • {failure}")
                    role_passed = False
                    all_passed = False
            else:
                print(f"  - Error: {agent_details['error']}")
                role_passed = False
                all_passed = False
            
            results_summary.append({
                "role": role,
                "agent": agent_name,
                "passed": passed,
                "details": agent_details
            })
        
        if role_passed:
            print(f"\n✅ All {role} agents passed validation")
        else:
            print(f"\n❌ Some {role} agents failed validation")
    
    # Print summary
    print("\n" + "=" * 80)
    print("SUMMARY")
    print("=" * 80)
    
    total_agents = sum(len(config["agents"]) for config in AGENT_ROLES.values())
    passed_agents = sum(1 for r in results_summary if r["passed"])
    
    print(f"Total Agents Tested: {total_agents}")
    print(f"Passed: {passed_agents}")
    print(f"Failed: {total_agents - passed_agents}")
    
    if all_passed:
        print("\n🎉 SUCCESS: All agents conform to role-based tool assignments!")
    else:
        print("\n⚠️  WARNING: Some agents need configuration updates")
        print("\nFailed Agents:")
        for r in results_summary:
            if not r["passed"]:
                print(f"  - {r['agent']} ({r['role']})")
    
    return all_passed, results_summary


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


if __name__ == "__main__":
    # Run comprehensive tests
    all_passed, results_summary = run_comprehensive_tests()
    
    # Generate report
    report = generate_report(results_summary)
    
    # Save report to file
    report_path = Path(__file__).parent / "role_based_agents_test_report.md"
    with open(report_path, 'w') as f:
        f.write(report)
    
    print(f"\n📄 Detailed report saved to: {report_path}")
    
    # Exit with appropriate code
    sys.exit(0 if all_passed else 1)