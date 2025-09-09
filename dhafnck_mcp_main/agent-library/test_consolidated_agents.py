#!/usr/bin/env python3
"""
Test script to validate all consolidated agents after optimization.
Tests both new consolidated agents and backward compatibility.
"""

import sys
import os
import json
from pathlib import Path
from typing import Dict, List, Tuple

# Add the src directory to the path
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from fastmcp.task_management.application.use_cases.call_agent import CallAgentUseCase

def test_agent(agent_name: str, test_type: str = "new") -> Tuple[bool, str]:
    """Test a single agent."""
    try:
        use_case = CallAgentUseCase()
        result = use_case.execute(agent_name)
        
        # Handle new response format with 'agent' field
        if 'success' in result and result['success']:
            agent_data = result.get('agent', {})
        else:
            agent_data = result
        
        # Check for required fields
        if 'name' not in agent_data or 'tools' not in agent_data:
            return False, f"Missing required fields: {list(agent_data.keys())}"
        
        result = agent_data  # Use agent_data for the rest of the checks
        
        # Check tools are properly loaded
        if not isinstance(result['tools'], list):
            return False, f"Tools is not a list: {type(result['tools'])}"
        
        # For consolidated agents, check they have enhanced capabilities
        if test_type == "consolidated":
            enhanced_agents = {
                'documentation_agent': ['tech_spec', 'prd', 'api'],
                'deep_research_agent': ['mcp', 'technology', 'research'],
                'creative_ideation_agent': ['generation', 'refinement', 'brainstorm'],
                'marketing_strategy_orchestrator_agent': ['seo', 'growth', 'content'],
                'debugger_agent': ['debug', 'remediation', 'fix'],
                'devops_agent': ['swarm', 'deployment', 'mcp', 'docker']
            }
            
            if agent_name in enhanced_agents:
                description = result.get('description', '').lower()
                keywords = enhanced_agents[agent_name]
                found_keywords = [kw for kw in keywords if kw in description]
                if len(found_keywords) < 2:
                    return False, f"Missing enhanced capabilities. Found keywords: {found_keywords}"
        
        return True, "Success"
    except Exception as e:
        return False, str(e)

def main():
    """Test all agents after consolidation."""
    print("=" * 80)
    print("TESTING CONSOLIDATED AGENTS")
    print("=" * 80)
    
    # Test new consolidated agents
    consolidated_agents = [
        'documentation_agent',
        'deep_research_agent', 
        'creative_ideation_agent',
        'marketing_strategy_orchestrator_agent',
        'debugger_agent',
        'devops_agent'
    ]
    
    print("\n1. Testing Consolidated Agents (Enhanced Versions):")
    print("-" * 40)
    
    all_passed = True
    for agent in consolidated_agents:
        success, message = test_agent(agent, "consolidated")
        status = "✅ PASS" if success else "❌ FAIL"
        print(f"  {agent:40s} {status}")
        if not success:
            print(f"    Error: {message}")
            all_passed = False
    
    # Test backward compatibility with deprecated names
    deprecated_mappings = {
        'tech_spec_agent': 'documentation_agent',
        'prd_architect_agent': 'documentation_agent',
        'mcp_researcher_agent': 'deep_research_agent',
        'idea_generation_agent': 'creative_ideation_agent',
        'idea_refinement_agent': 'creative_ideation_agent',
        'seo_sem_agent': 'marketing_strategy_orchestrator_agent',
        'growth_hacking_idea_agent': 'marketing_strategy_orchestrator_agent',
        'content_strategy_agent': 'marketing_strategy_orchestrator_agent',
        'remediation_agent': 'debugger_agent',
        'swarm_scaler_agent': 'devops_agent',
        'adaptive_deployment_strategist_agent': 'devops_agent',
        'mcp_configuration_agent': 'devops_agent'
    }
    
    print("\n2. Testing Backward Compatibility (Deprecated Names):")
    print("-" * 40)
    
    for deprecated, expected in deprecated_mappings.items():
        try:
            use_case = CallAgentUseCase()
            result = use_case.execute(deprecated)
            
            # Handle new response format
            if 'success' in result and result['success']:
                agent_data = result.get('agent', {})
            else:
                agent_data = result
            
            # Check if it maps to the correct new agent
            actual_name = agent_data.get('name', '').lower().replace('-', '_')
            expected_name = expected.lower()
            
            if expected_name in actual_name or actual_name == expected_name:
                print(f"  {deprecated:40s} ✅ Maps to {expected}")
            else:
                print(f"  {deprecated:40s} ❌ Wrong mapping: {actual_name}")
                all_passed = False
        except Exception as e:
            print(f"  {deprecated:40s} ❌ Error: {str(e)}")
            all_passed = False
    
    # Test renamed agents
    renamed_agents = {
        'uber_orchestrator_agent': 'master_orchestrator_agent',
        'brainjs_ml_agent': 'ml_specialist_agent',
        'ui_designer_expert_shadcn_agent': 'ui_specialist_agent'
    }
    
    print("\n3. Testing Renamed Agents:")
    print("-" * 40)
    
    for old_name, new_name in renamed_agents.items():
        # Test old name maps to new
        try:
            use_case = CallAgentUseCase()
            result = use_case.execute(old_name)
            
            # Handle new response format
            if 'success' in result and result['success']:
                agent_data = result.get('agent', {})
            else:
                agent_data = result
                
            actual_name = agent_data.get('name', '').lower().replace('-', '_')
            
            if new_name in actual_name or actual_name == new_name:
                print(f"  {old_name:40s} ✅ Maps to {new_name}")
            else:
                print(f"  {old_name:40s} ❌ Wrong mapping: {actual_name}")
                all_passed = False
        except Exception as e:
            print(f"  {old_name:40s} ❌ Error: {str(e)}")
            all_passed = False
    
    # Count total active agents
    agents_dir = Path(__file__).parent / "agents"
    active_agents = len(list(agents_dir.glob("*"))) if agents_dir.exists() else 0
    
    print("\n" + "=" * 80)
    print("SUMMARY:")
    print(f"  Active Agents: {active_agents} (target: 30)")
    print(f"  Deprecated Agents Archived: 12")
    print(f"  Test Result: {'✅ ALL TESTS PASSED' if all_passed else '❌ SOME TESTS FAILED'}")
    print("=" * 80)
    
    return 0 if all_passed else 1

if __name__ == "__main__":
    sys.exit(main())