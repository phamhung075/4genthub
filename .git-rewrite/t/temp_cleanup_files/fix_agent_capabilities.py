#!/usr/bin/env python3
"""
Script to fix agent capabilities based on their roles.
Each agent should have appropriate permissions for their tasks.
"""

import os
import yaml
from pathlib import Path
from typing import Dict, List, Tuple

# Define agent categories and their required permissions
AGENT_PERMISSION_MATRIX = {
    # Testing agents - need to read code and write tests
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
        'file_operations': {
            'enabled': True,
            'permissions': {
                'read': True,
                'write': True,
                'create': True,
                'delete': False  # Testing agents shouldn't delete files
            }
        },
        'command_execution': {
            'enabled': True,
            'restrictions': ['sandbox_mode'],
            'allowed_commands': [
                'stat', 'ls -l', 'git log', 'git diff',
                'diff', 'find', 'date', 'npm test',
                'pytest', 'jest', 'playwright'
            ]
        }
    },
    
    # Coding/Development agents - need full file operations
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
        'file_operations': {
            'enabled': True,
            'permissions': {
                'read': True,
                'write': True,
                'create': True,
                'delete': True  # Coding agents may need to refactor/delete
            }
        },
        'command_execution': {
            'enabled': True,
            'restrictions': ['sandbox_mode'],
            'allowed_commands': [
                'git', 'npm', 'yarn', 'pnpm', 'python',
                'node', 'docker', 'make', 'cargo'
            ]
        }
    },
    
    # Documentation agents - need to read code and write docs
    'documentation_agents': {
        'agents': [
            'documentation_agent',
            'scribe_agent',
            'prd_architect_agent',
            'tech_spec_agent'
        ],
        'file_operations': {
            'enabled': True,
            'permissions': {
                'read': True,
                'write': True,
                'create': True,
                'delete': False
            }
        },
        'command_execution': {
            'enabled': True,
            'restrictions': ['sandbox_mode'],
            'allowed_commands': ['git log', 'ls', 'find']
        }
    },
    
    # Design/UI agents - need to read and create design files
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
        'file_operations': {
            'enabled': True,
            'permissions': {
                'read': True,
                'write': True,
                'create': True,
                'delete': False
            }
        },
        'command_execution': {
            'enabled': True,
            'restrictions': ['sandbox_mode'],
            'allowed_commands': ['npm', 'yarn', 'pnpm']
        }
    },
    
    # Analysis/Research agents - mainly need read access
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
        'file_operations': {
            'enabled': True,
            'permissions': {
                'read': True,
                'write': False,  # Analysis agents typically don't write
                'create': False,
                'delete': False
            }
        },
        'command_execution': {
            'enabled': True,
            'restrictions': ['sandbox_mode'],
            'allowed_commands': ['git log', 'grep', 'find', 'stat']
        }
    },
    
    # Orchestration/Management agents - need various permissions
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
        'file_operations': {
            'enabled': True,
            'permissions': {
                'read': True,
                'write': True,
                'create': True,
                'delete': False
            }
        },
        'command_execution': {
            'enabled': True,
            'restrictions': ['sandbox_mode'],
            'allowed_commands': ['git', 'docker', 'kubectl', 'terraform']
        }
    },
    
    # Marketing/Content agents - need to create content
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
        'file_operations': {
            'enabled': True,
            'permissions': {
                'read': True,
                'write': True,
                'create': True,
                'delete': False
            }
        },
        'command_execution': {
            'enabled': False,  # Marketing agents typically don't need shell
            'restrictions': ['sandbox_mode']
        }
    },
    
    # Idea/Concept agents - mainly need read and limited write
    'concept_agents': {
        'agents': [
            'idea_generation_agent',
            'idea_refinement_agent',
            'core_concept_agent',
            'elicitation_agent',
            'nlu_processor_agent',
            'generic_purpose_agent'
        ],
        'file_operations': {
            'enabled': True,
            'permissions': {
                'read': True,
                'write': False,
                'create': False,
                'delete': False
            }
        },
        'command_execution': {
            'enabled': False,
            'restrictions': ['sandbox_mode']
        }
    },
    
    # System/Architecture agents - need full access
    'system_agents': {
        'agents': [
            'system_architect_agent'
        ],
        'file_operations': {
            'enabled': True,
            'permissions': {
                'read': True,
                'write': True,
                'create': True,
                'delete': True
            }
        },
        'command_execution': {
            'enabled': True,
            'restrictions': ['sandbox_mode'],
            'allowed_commands': ['*']  # System architects need broad access
        }
    }
}

def get_agent_category(agent_name: str) -> Tuple[str, Dict]:
    """Find which category an agent belongs to"""
    for category, config in AGENT_PERMISSION_MATRIX.items():
        if agent_name in config['agents']:
            return category, config
    return None, None

def update_agent_capabilities(agent_dir: Path, permissions: Dict) -> bool:
    """Update the capabilities.yaml file for an agent"""
    capabilities_file = agent_dir / "capabilities.yaml"
    
    if not capabilities_file.exists():
        print(f"  ⚠️  No capabilities.yaml found for {agent_dir.name}")
        return False
    
    try:
        # Read existing capabilities
        with open(capabilities_file, 'r') as f:
            capabilities = yaml.safe_load(f) or {}
        
        # Update file operations
        if 'file_operations' not in capabilities:
            capabilities['file_operations'] = {}
        capabilities['file_operations'].update(permissions['file_operations'])
        
        # Update command execution
        if 'command_execution' not in capabilities:
            capabilities['command_execution'] = {}
        capabilities['command_execution'].update(permissions['command_execution'])
        
        # Ensure other required fields exist
        if 'collaboration' not in capabilities:
            capabilities['collaboration'] = {
                'agent_communication': True,
                'enabled': True
            }
        
        if 'mcp_tools' not in capabilities:
            capabilities['mcp_tools'] = {
                'enabled': True,
                'tools': []
            }
        
        # Write updated capabilities
        with open(capabilities_file, 'w') as f:
            yaml.dump(capabilities, f, default_flow_style=False, sort_keys=False)
        
        print(f"  ✅ Updated capabilities for {agent_dir.name}")
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
    print("AGENT CAPABILITY FIX SCRIPT")
    print("=" * 60)
    
    # Statistics
    total_agents = 0
    updated_agents = 0
    unknown_agents = []
    
    # Process each agent
    for agent_dir in sorted(base_path.iterdir()):
        if not agent_dir.is_dir():
            continue
        
        agent_name = agent_dir.name
        total_agents += 1
        
        print(f"\n📁 Processing: {agent_name}")
        
        # Find category and permissions
        category, config = get_agent_category(agent_name)
        
        if category:
            print(f"  📋 Category: {category}")
            print(f"  🔐 Permissions: Read={config['file_operations']['permissions']['read']}, "
                  f"Write={config['file_operations']['permissions']['write']}, "
                  f"Create={config['file_operations']['permissions']['create']}, "
                  f"Delete={config['file_operations']['permissions']['delete']}")
            
            if update_agent_capabilities(agent_dir, config):
                updated_agents += 1
        else:
            print(f"  ⚠️  Unknown agent category - skipping")
            unknown_agents.append(agent_name)
    
    # Print summary
    print("\n" + "=" * 60)
    print("SUMMARY")
    print("=" * 60)
    print(f"Total agents processed: {total_agents}")
    print(f"Successfully updated: {updated_agents}")
    print(f"Unknown agents: {len(unknown_agents)}")
    
    if unknown_agents:
        print("\nUnknown agents that need manual review:")
        for agent in unknown_agents:
            print(f"  - {agent}")
    
    print("\n✅ Agent capability fix completed!")
    
    # Create a summary report
    report_file = Path("/home/daihungpham/__projects__/agentic-project/agent_capability_fix_report.md")
    with open(report_file, 'w') as f:
        f.write("# Agent Capability Fix Report\n\n")
        f.write(f"Date: {os.popen('date').read().strip()}\n\n")
        f.write("## Summary\n\n")
        f.write(f"- Total agents: {total_agents}\n")
        f.write(f"- Updated: {updated_agents}\n")
        f.write(f"- Unknown: {len(unknown_agents)}\n\n")
        
        f.write("## Permission Matrix\n\n")
        for category, config in AGENT_PERMISSION_MATRIX.items():
            f.write(f"### {category.replace('_', ' ').title()}\n\n")
            f.write("**Agents:**\n")
            for agent in config['agents']:
                f.write(f"- {agent}\n")
            f.write("\n**File Permissions:**\n")
            perms = config['file_operations']['permissions']
            f.write(f"- Read: {perms['read']}\n")
            f.write(f"- Write: {perms['write']}\n")
            f.write(f"- Create: {perms['create']}\n")
            f.write(f"- Delete: {perms['delete']}\n\n")
        
        if unknown_agents:
            f.write("## Unknown Agents (Need Manual Review)\n\n")
            for agent in unknown_agents:
                f.write(f"- {agent}\n")
    
    print(f"\n📄 Report saved to: {report_file}")

if __name__ == "__main__":
    main()