#!/usr/bin/env python3
"""
Test script to verify agent name resolution is working correctly.
Tests various agent name formats and ensures they resolve to kebab-case.
"""

import sys
from pathlib import Path

# Add the project source to path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from fastmcp.task_management.application.use_cases.agent_mappings import resolve_agent_name

def test_agent_name_resolution():
    """Test various agent name formats."""
    
    test_cases = [
        # @ prefix with underscores -> kebab-case
        ("@coding_agent", "coding-agent"),
        ("@debugger_agent", "debugger-agent"),
        ("@system_architect_agent", "system-architect-agent"),
        
        # Underscore format -> kebab-case
        ("coding_agent", "coding-agent"),
        ("debugger_agent", "debugger-agent"),
        ("task_planning_agent", "task-planning-agent"),
        
        # Already kebab-case -> stays kebab-case
        ("coding-agent", "coding-agent"),
        ("master-orchestrator-agent", "master-orchestrator-agent"),
        ("analytics-setup-agent", "analytics-setup-agent"),
        
        # Deprecated names -> mapped to new agents
        ("tech_spec_agent", "documentation-agent"),
        ("tech-spec-agent", "documentation-agent"),
        ("mcp_researcher_agent", "deep-research-agent"),
        ("idea_generation_agent", "creative-ideation-agent"),
        
        # Special cases
        ("master_orchestrator_agent", "master-orchestrator-agent"),
        ("llm_ai_agents_research", "llm-ai-agents-research"),
        
        # Unknown agents should be standardized
        ("some_new_agent", "some-new-agent"),
        ("@another_test_agent", "another-test-agent"),
    ]
    
    print("=" * 80)
    print("AGENT NAME RESOLUTION TEST")
    print("=" * 80)
    
    passed = 0
    failed = 0
    
    for input_name, expected_output in test_cases:
        actual_output = resolve_agent_name(input_name)
        status = "✅ PASS" if actual_output == expected_output else "❌ FAIL"
        
        if actual_output == expected_output:
            passed += 1
        else:
            failed += 1
        
        print(f"{status}: '{input_name}' -> '{actual_output}' (expected: '{expected_output}')")
    
    print("\n" + "=" * 80)
    print(f"RESULTS: {passed} passed, {failed} failed")
    print("=" * 80)
    
    if failed > 0:
        print("\n⚠️  Some tests failed. Please review the agent_mappings.py implementation.")
        return False
    else:
        print("\n✅ All tests passed! Agent name resolution is working correctly.")
        return True

if __name__ == "__main__":
    success = test_agent_name_resolution()
    sys.exit(0 if success else 1)