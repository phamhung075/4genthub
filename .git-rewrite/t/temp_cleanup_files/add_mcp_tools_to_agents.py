#!/usr/bin/env python3
"""
Script to add appropriate MCP tools to agents based on their roles.
Each agent should have access to relevant MCP tools for their tasks.
"""

import os
import yaml
from pathlib import Path
from typing import Dict, List

# Define MCP tools matrix for each agent category
MCP_TOOLS_MATRIX = {
    # Testing agents need browser tools for UI testing
    'testing_agents': {
        'agents': [
            'test_orchestrator_agent',
            'test_case_generator_agent', 
            'functional_tester_agent',
            'exploratory_tester_agent',
            'compliance_testing_agent',
            'lead_testing_agent',
            'performance_load_tester_agent',
            'security_penetration_tester_agent',
            'visual_regression_testing_agent',
            'uat_coordinator_agent'
        ],
        'mcp_tools': [
            'mcp__browsermcp__browser_navigate',
            'mcp__browsermcp__browser_snapshot',
            'mcp__browsermcp__browser_click',
            'mcp__browsermcp__browser_type',
            'mcp__browsermcp__browser_get_console_logs',
            'mcp__browsermcp__browser_screenshot',
            'mcp__browsermcp__browser_wait',
            'mcp__ide__getDiagnostics',
            'mcp__dhafnck_mcp_http__manage_task',
            'mcp__dhafnck_mcp_http__manage_subtask',
            'mcp__sequential-thinking__sequentialthinking'
        ]
    },
    
    # Coding agents need IDE and dhafnck tools
    'coding_agents': {
        'agents': [
            'coding_agent',
            'debugger_agent',
            'code_reviewer_agent',
            'algorithmic_problem_solver_agent',
            'development_orchestrator_agent',
            'devops_agent',
            'prototyping_agent',
            'brainjs_ml_agent'
        ],
        'mcp_tools': [
            'mcp__ide__getDiagnostics',
            'mcp__ide__executeCode',
            'mcp__dhafnck_mcp_http__manage_task',
            'mcp__dhafnck_mcp_http__manage_subtask',
            'mcp__dhafnck_mcp_http__manage_context',
            'mcp__dhafnck_mcp_http__manage_git_branch',
            'mcp__sequential-thinking__sequentialthinking',
            'mcp__browsermcp__browser_navigate',
            'mcp__browsermcp__browser_get_console_logs'
        ]
    },
    
    # UI/Design agents need shadcn and browser tools
    'design_agents': {
        'agents': [
            'ui_designer_agent',
            'ui_designer_expert_shadcn_agent',
            'ux_researcher_agent',
            'design_system_agent',
            'design_qa_analyst',
            'design_qa_analyst_agent',
            'usability_heuristic_agent',
            'graphic_design_agent'
        ],
        'mcp_tools': [
            'mcp__shadcn-ui-server__list-components',
            'mcp__shadcn-ui-server__get-component-docs',
            'mcp__shadcn-ui-server__install-component',
            'mcp__shadcn-ui-server__list-blocks',
            'mcp__shadcn-ui-server__get-block-docs',
            'mcp__shadcn-ui-server__install-blocks',
            'mcp__browsermcp__browser_navigate',
            'mcp__browsermcp__browser_snapshot',
            'mcp__browsermcp__browser_screenshot',
            'mcp__dhafnck_mcp_http__manage_task',
            'mcp__dhafnck_mcp_http__manage_context'
        ]
    },
    
    # Documentation agents need context and task tools
    'documentation_agents': {
        'agents': [
            'documentation_agent',
            'scribe_agent',
            'prd_architect_agent',
            'tech_spec_agent'
        ],
        'mcp_tools': [
            'mcp__dhafnck_mcp_http__manage_task',
            'mcp__dhafnck_mcp_http__manage_context',
            'mcp__dhafnck_mcp_http__manage_project',
            'mcp__sequential-thinking__sequentialthinking',
            'mcp__ide__getDiagnostics'
        ]
    },
    
    # Analysis agents need thinking and context tools
    'analysis_agents': {
        'agents': [
            'deep_research_agent',
            'market_research_agent',
            'mcp_researcher_agent',
            'root_cause_analysis_agent',
            'efficiency_optimization_agent',
            'security_auditor_agent',
            'ethical_review_agent',
            'compliance_scope_agent',
            'technology_advisor_agent',
            'user_feedback_collector_agent',
            'incident_learning_agent',
            'knowledge_evolution_agent'
        ],
        'mcp_tools': [
            'mcp__sequential-thinking__sequentialthinking',
            'mcp__dhafnck_mcp_http__manage_context',
            'mcp__dhafnck_mcp_http__manage_task',
            'mcp__browsermcp__browser_navigate',
            'mcp__browsermcp__browser_snapshot'
        ]
    },
    
    # Orchestration agents need full dhafnck suite
    'orchestration_agents': {
        'agents': [
            'uber_orchestrator_agent',
            'task_deep_manager_agent',
            'task_planning_agent',
            'task_sync_agent',
            'workflow_architect_agent',
            'project_initiator_agent',
            'adaptive_deployment_strategist_agent',
            'swarm_scaler_agent',
            'health_monitor_agent',
            'remediation_agent',
            'mcp_configuration_agent'
        ],
        'mcp_tools': [
            'mcp__dhafnck_mcp_http__manage_task',
            'mcp__dhafnck_mcp_http__manage_subtask',
            'mcp__dhafnck_mcp_http__manage_context',
            'mcp__dhafnck_mcp_http__manage_project',
            'mcp__dhafnck_mcp_http__manage_git_branch',
            'mcp__dhafnck_mcp_http__manage_agent',
            'mcp__dhafnck_mcp_http__call_agent',
            'mcp__dhafnck_mcp_http__manage_rule',
            'mcp__dhafnck_mcp_http__manage_compliance',
            'mcp__dhafnck_mcp_http__manage_connection',
            'mcp__sequential-thinking__sequentialthinking'
        ]
    },
    
    # Marketing agents need browser tools for social media
    'marketing_agents': {
        'agents': [
            'marketing_strategy_orchestrator',
            'marketing_strategy_orchestrator_agent',
            'campaign_manager_agent',
            'content_strategy_agent',
            'seo_sem_agent',
            'social_media_setup_agent',
            'branding_agent',
            'growth_hacking_idea_agent',
            'community_strategy_agent',
            'analytics_setup_agent',
            'video_production_agent'
        ],
        'mcp_tools': [
            'mcp__browsermcp__browser_navigate',
            'mcp__browsermcp__browser_snapshot',
            'mcp__browsermcp__browser_screenshot',
            'mcp__dhafnck_mcp_http__manage_task',
            'mcp__dhafnck_mcp_http__manage_context',
            'mcp__sequential-thinking__sequentialthinking'
        ]
    },
    
    # Concept agents need thinking tools
    'concept_agents': {
        'agents': [
            'idea_generation_agent',
            'idea_refinement_agent',
            'core_concept_agent',
            'elicitation_agent',
            'nlu_processor_agent',
            'generic_purpose_agent'
        ],
        'mcp_tools': [
            'mcp__sequential-thinking__sequentialthinking',
            'mcp__dhafnck_mcp_http__manage_context',
            'mcp__dhafnck_mcp_http__manage_task'
        ]
    },
    
    # System architects need everything
    'system_agents': {
        'agents': [
            'system_architect_agent'
        ],
        'mcp_tools': [
            'mcp__dhafnck_mcp_http__manage_task',
            'mcp__dhafnck_mcp_http__manage_subtask',
            'mcp__dhafnck_mcp_http__manage_context',
            'mcp__dhafnck_mcp_http__manage_project',
            'mcp__dhafnck_mcp_http__manage_git_branch',
            'mcp__dhafnck_mcp_http__manage_agent',
            'mcp__dhafnck_mcp_http__call_agent',
            'mcp__dhafnck_mcp_http__manage_rule',
            'mcp__dhafnck_mcp_http__manage_compliance',
            'mcp__dhafnck_mcp_http__manage_connection',
            'mcp__sequential-thinking__sequentialthinking',
            'mcp__ide__getDiagnostics',
            'mcp__ide__executeCode',
            'mcp__browsermcp__browser_navigate',
            'mcp__browsermcp__browser_snapshot',
            'mcp__shadcn-ui-server__list-components'
        ]
    }
}

def get_agent_mcp_tools(agent_name: str) -> List[str]:
    """Get the appropriate MCP tools for an agent"""
    for category, config in MCP_TOOLS_MATRIX.items():
        if agent_name in config['agents']:
            return config['mcp_tools']
    # Default minimal tools for unknown agents
    return [
        'mcp__dhafnck_mcp_http__manage_task',
        'mcp__dhafnck_mcp_http__manage_context',
        'mcp__sequential-thinking__sequentialthinking'
    ]

def update_agent_mcp_tools(agent_dir: Path, mcp_tools: List[str]) -> bool:
    """Update the capabilities.yaml file with MCP tools"""
    capabilities_file = agent_dir / "capabilities.yaml"
    
    if not capabilities_file.exists():
        print(f"  ⚠️  No capabilities.yaml found for {agent_dir.name}")
        return False
    
    try:
        # Read existing capabilities
        with open(capabilities_file, 'r') as f:
            capabilities = yaml.safe_load(f) or {}
        
        # Update MCP tools
        if 'mcp_tools' not in capabilities:
            capabilities['mcp_tools'] = {}
        
        # Ensure it's enabled
        capabilities['mcp_tools']['enabled'] = True
        
        # Set the tools list
        capabilities['mcp_tools']['tools'] = mcp_tools
        
        # Write updated capabilities
        with open(capabilities_file, 'w') as f:
            yaml.dump(capabilities, f, default_flow_style=False, sort_keys=False)
        
        print(f"  ✅ Added {len(mcp_tools)} MCP tools to {agent_dir.name}")
        return True
        
    except Exception as e:
        print(f"  ❌ Error updating {agent_dir.name}: {str(e)}")
        return False

def main():
    base_path = Path("/home/daihungpham/__projects__/agentic-project/dhafnck_mcp_main/agent-library/agents")
    
    if not base_path.exists():
        print(f"Error: Agent library path not found: {base_path}")
        return
    
    print("=" * 60)
    print("MCP TOOLS ADDITION SCRIPT")
    print("=" * 60)
    
    # Statistics
    total_agents = 0
    updated_agents = 0
    
    # Process each agent
    for agent_dir in sorted(base_path.iterdir()):
        if not agent_dir.is_dir():
            continue
        
        agent_name = agent_dir.name
        total_agents += 1
        
        print(f"\n📁 Processing: {agent_name}")
        
        # Get appropriate MCP tools
        mcp_tools = get_agent_mcp_tools(agent_name)
        
        print(f"  🔧 Adding {len(mcp_tools)} MCP tools")
        
        if update_agent_mcp_tools(agent_dir, mcp_tools):
            updated_agents += 1
    
    # Print summary
    print("\n" + "=" * 60)
    print("SUMMARY")
    print("=" * 60)
    print(f"Total agents processed: {total_agents}")
    print(f"Successfully updated: {updated_agents}")
    
    print("\n✅ MCP tools addition completed!")
    
    # Create a summary report
    report_file = Path("/home/daihungpham/__projects__/agentic-project/mcp_tools_addition_report.md")
    with open(report_file, 'w') as f:
        f.write("# MCP Tools Addition Report\n\n")
        f.write(f"Date: {os.popen('date').read().strip()}\n\n")
        f.write("## Summary\n\n")
        f.write(f"- Total agents: {total_agents}\n")
        f.write(f"- Updated: {updated_agents}\n\n")
        
        f.write("## MCP Tools Matrix\n\n")
        for category, config in MCP_TOOLS_MATRIX.items():
            f.write(f"### {category.replace('_', ' ').title()}\n\n")
            f.write("**Agents:**\n")
            for agent in config['agents']:
                f.write(f"- {agent}\n")
            f.write("\n**MCP Tools:**\n")
            for tool in config['mcp_tools']:
                f.write(f"- `{tool}`\n")
            f.write("\n")
    
    print(f"\n📄 Report saved to: {report_file}")

if __name__ == "__main__":
    main()