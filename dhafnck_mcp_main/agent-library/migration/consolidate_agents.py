#!/usr/bin/env python3
"""
Agent Consolidation Migration Script
Consolidates redundant agents into optimized structure (42 → 30 agents)
"""

import os
import shutil
import yaml
import json
from pathlib import Path
from datetime import datetime
from typing import Dict, List, Optional

class AgentConsolidator:
    """Handles consolidation of redundant agents"""
    
    def __init__(self, agent_library_path: str):
        self.agent_library_path = Path(agent_library_path)
        self.agents_path = self.agent_library_path / "agents"
        self.deprecated_path = self.agent_library_path / "deprecated"
        self.backup_path = self.agent_library_path / "backup"
        
        # Define consolidation mappings
        self.consolidation_map = {
            # Documentation consolidation
            "tech_spec_agent": "documentation_agent",
            "prd_architect_agent": "documentation_agent",
            
            # Research consolidation
            "mcp_researcher_agent": "deep_research_agent",
            
            # Creative consolidation (creates new agent)
            "idea_generation_agent": "creative_ideation_agent",
            "idea_refinement_agent": "creative_ideation_agent",
            
            # Marketing consolidation
            "seo_sem_agent": "marketing_strategy_orchestrator_agent",
            "growth_hacking_idea_agent": "marketing_strategy_orchestrator_agent",
            "content_strategy_agent": "marketing_strategy_orchestrator_agent",
            
            # DevOps consolidation
            "swarm_scaler_agent": "devops_agent",
            "adaptive_deployment_strategist_agent": "devops_agent",
            "mcp_configuration_agent": "devops_agent",
            
            # Debug consolidation
            "remediation_agent": "debugger_agent",
        }
        
        # Define renaming map
        self.rename_map = {
            "master_orchestrator_agent": "master_orchestrator_agent",
            "brainjs_ml_agent": "ml_specialist_agent",
            "ui_designer_expert_shadcn_agent": "ui_specialist_agent",
        }
        
        self.migration_log = []
    
    def backup_agents(self):
        """Create backup of all agents before migration"""
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        backup_dir = self.backup_path / f"backup_{timestamp}"
        
        print(f"Creating backup at {backup_dir}")
        shutil.copytree(self.agents_path, backup_dir)
        self.migration_log.append(f"Backup created: {backup_dir}")
        return backup_dir
    
    def merge_capabilities(self, source_agent: str, target_agent: str):
        """Merge capabilities from source agent into target agent"""
        source_path = self.agents_path / source_agent / "capabilities.yaml"
        target_path = self.agents_path / target_agent / "capabilities.yaml"
        
        if not source_path.exists():
            print(f"Warning: {source_path} not found")
            return
        
        with open(source_path, 'r') as f:
            source_caps = yaml.safe_load(f)
        
        with open(target_path, 'r') as f:
            target_caps = yaml.safe_load(f)
        
        # Merge MCP tools
        if 'mcp_tools' in source_caps and 'mcp_tools' in target_caps:
            source_tools = source_caps['mcp_tools'].get('tools', [])
            target_tools = target_caps['mcp_tools'].get('tools', [])
            
            # Combine and deduplicate
            combined_tools = list(set(target_tools + source_tools))
            target_caps['mcp_tools']['tools'] = combined_tools
        
        # Write back merged capabilities
        with open(target_path, 'w') as f:
            yaml.dump(target_caps, f, default_flow_style=False)
        
        self.migration_log.append(f"Merged capabilities: {source_agent} → {target_agent}")
    
    def create_creative_ideation_agent(self):
        """Create new creative_ideation_agent from idea agents"""
        creative_path = self.agents_path / "creative_ideation_agent"
        
        if creative_path.exists():
            print("creative_ideation_agent already exists")
            return
        
        # Copy from idea_generation_agent as base
        source_path = self.agents_path / "idea_generation_agent"
        if source_path.exists():
            shutil.copytree(source_path, creative_path)
            
            # Update config
            config_path = creative_path / "config.yaml"
            with open(config_path, 'r') as f:
                config = yaml.safe_load(f)
            
            config['agent_info']['name'] = "💡 Creative Ideation Agent"
            config['agent_info']['slug'] = "creative-ideation-agent"
            config['agent_info']['description'] = (
                "This autonomous agent handles the complete creative ideation lifecycle, "
                "from generating innovative ideas to refining and iterating them into "
                "actionable concepts. It combines brainstorming, refinement, and validation "
                "into a unified creative process."
            )
            config['agent_info']['version'] = "2.0.0"
            config['agent_info']['modes'] = ['generate', 'refine', 'iterate', 'validate']
            
            with open(config_path, 'w') as f:
                yaml.dump(config, f, default_flow_style=False)
            
            # Merge capabilities from idea_refinement_agent
            self.merge_capabilities("idea_refinement_agent", "creative_ideation_agent")
            
            self.migration_log.append("Created creative_ideation_agent")
    
    def rename_agent(self, old_name: str, new_name: str):
        """Rename an agent directory and update its configuration"""
        old_path = self.agents_path / old_name
        new_path = self.agents_path / new_name
        
        if not old_path.exists():
            print(f"Warning: {old_path} not found")
            return
        
        if new_path.exists():
            print(f"Warning: {new_path} already exists")
            return
        
        # Rename directory
        shutil.move(str(old_path), str(new_path))
        
        # Update config
        config_path = new_path / "config.yaml"
        with open(config_path, 'r') as f:
            config = yaml.safe_load(f)
        
        # Update slug
        config['agent_info']['slug'] = new_name.replace('_', '-')
        
        # Update name for specific agents
        if new_name == "master_orchestrator_agent":
            config['agent_info']['name'] = "🎯 Master Orchestrator Agent"
        elif new_name == "ml_specialist_agent":
            config['agent_info']['name'] = "🤖 ML Specialist Agent"
        elif new_name == "ui_specialist_agent":
            config['agent_info']['name'] = "🎨 UI Specialist Agent"
        
        with open(config_path, 'w') as f:
            yaml.dump(config, f, default_flow_style=False)
        
        self.migration_log.append(f"Renamed: {old_name} → {new_name}")
    
    def deprecate_agent(self, agent_name: str):
        """Move agent to deprecated folder"""
        source_path = self.agents_path / agent_name
        
        if not source_path.exists():
            print(f"Warning: {source_path} not found")
            return
        
        # Create deprecated folder if it doesn't exist
        self.deprecated_path.mkdir(exist_ok=True)
        
        target_path = self.deprecated_path / agent_name
        shutil.move(str(source_path), str(target_path))
        
        # Add deprecation notice
        notice_path = target_path / "DEPRECATED.md"
        with open(notice_path, 'w') as f:
            f.write(f"# DEPRECATED AGENT: {agent_name}\n\n")
            f.write(f"**Deprecation Date**: {datetime.now().isoformat()}\n\n")
            
            if agent_name in self.consolidation_map:
                f.write(f"**Replaced By**: {self.consolidation_map[agent_name]}\n\n")
            
            f.write("This agent has been deprecated as part of the agent optimization initiative.\n")
            f.write("Its functionality has been consolidated into other agents.\n")
        
        self.migration_log.append(f"Deprecated: {agent_name}")
    
    def update_call_agent_mappings(self):
        """Update call_agent.py with new mappings"""
        call_agent_path = Path("dhafnck_mcp_main/src/fastmcp/task_management/application/use_cases/call_agent.py")
        
        if not call_agent_path.exists():
            print(f"Warning: {call_agent_path} not found")
            return
        
        # Create mapping code
        mapping_code = """
# Agent name mappings for backward compatibility
DEPRECATED_AGENT_MAPPINGS = {
"""
        for old, new in {**self.consolidation_map, **self.rename_map}.items():
            mapping_code += f'    "{old}": "{new}",\n'
        mapping_code += "}\n"
        
        # Write mapping to separate file
        mapping_path = call_agent_path.parent / "agent_mappings.py"
        with open(mapping_path, 'w') as f:
            f.write(mapping_code)
        
        self.migration_log.append(f"Created agent mappings: {mapping_path}")
    
    def run_migration(self):
        """Execute the complete migration"""
        print("Starting Agent Consolidation Migration")
        print("=" * 60)
        
        # Step 1: Backup
        self.backup_agents()
        
        # Step 2: Create new agents
        print("\nCreating new consolidated agents...")
        self.create_creative_ideation_agent()
        
        # Step 3: Merge capabilities
        print("\nMerging agent capabilities...")
        for source, target in self.consolidation_map.items():
            if source not in ["idea_generation_agent", "idea_refinement_agent"]:
                self.merge_capabilities(source, target)
        
        # Step 4: Rename agents
        print("\nRenaming agents...")
        for old_name, new_name in self.rename_map.items():
            self.rename_agent(old_name, new_name)
        
        # Step 5: Deprecate old agents
        print("\nDeprecating redundant agents...")
        for agent in self.consolidation_map.keys():
            self.deprecate_agent(agent)
        
        # Step 6: Update mappings
        print("\nUpdating code mappings...")
        self.update_call_agent_mappings()
        
        # Step 7: Write migration log
        log_path = self.agent_library_path / "migration" / f"migration_log_{datetime.now().strftime('%Y%m%d_%H%M%S')}.txt"
        log_path.parent.mkdir(exist_ok=True)
        
        with open(log_path, 'w') as f:
            f.write("Agent Consolidation Migration Log\n")
            f.write("=" * 60 + "\n")
            f.write(f"Date: {datetime.now().isoformat()}\n\n")
            for entry in self.migration_log:
                f.write(f"- {entry}\n")
        
        print(f"\nMigration complete! Log saved to: {log_path}")
        print(f"Total actions: {len(self.migration_log)}")
        
        # Summary
        print("\nSummary:")
        print(f"- Agents consolidated: {len(self.consolidation_map)}")
        print(f"- Agents renamed: {len(self.rename_map)}")
        print(f"- New agents created: 1 (creative_ideation_agent)")
        print(f"- Final agent count: ~30 (from 42)")
    
    def rollback(self, backup_path: str):
        """Rollback to a previous backup"""
        backup_dir = Path(backup_path)
        
        if not backup_dir.exists():
            print(f"Error: Backup {backup_dir} not found")
            return
        
        # Remove current agents
        shutil.rmtree(self.agents_path)
        
        # Restore from backup
        shutil.copytree(backup_dir, self.agents_path)
        
        print(f"Rolled back to: {backup_dir}")


def main():
    """Main execution"""
    import argparse
    
    parser = argparse.ArgumentParser(description="Agent Consolidation Migration")
    parser.add_argument("--path", default="dhafnck_mcp_main/agent-library", 
                       help="Path to agent library")
    parser.add_argument("--rollback", help="Rollback to specific backup")
    parser.add_argument("--dry-run", action="store_true", 
                       help="Show what would be done without executing")
    
    args = parser.parse_args()
    
    consolidator = AgentConsolidator(args.path)
    
    if args.rollback:
        consolidator.rollback(args.rollback)
    elif args.dry_run:
        print("DRY RUN - No changes will be made")
        print("\nPlanned consolidations:")
        for source, target in consolidator.consolidation_map.items():
            print(f"  {source} → {target}")
        print("\nPlanned renames:")
        for old, new in consolidator.rename_map.items():
            print(f"  {old} → {new}")
    else:
        consolidator.run_migration()


if __name__ == "__main__":
    main()