#!/usr/bin/env python3
"""
Comprehensive script to update all agent names to kebab-case format across the entire codebase.
This will update Python files, YAML files, Markdown files, and any other text files.
"""

import os
import re
from pathlib import Path
from typing import Set, Dict, List, Tuple

# Define base paths
PROJECT_ROOT = Path("/home/daihungpham/__projects__/agentic-project")

# Define agent name mappings (old -> new)
AGENT_NAME_MAPPINGS = {
    # With @ prefix
    "@coding_agent": "coding-agent",
    "@debugger_agent": "debugger-agent",
    "@code_reviewer_agent": "code-reviewer-agent",
    "@prototyping_agent": "prototyping-agent",
    "@test_orchestrator_agent": "test-orchestrator-agent",
    "@uat_coordinator_agent": "uat-coordinator-agent",
    "@performance_load_tester_agent": "performance-load-tester-agent",
    "@system_architect_agent": "system-architect-agent",
    "@design_system_agent": "design-system-agent",
    "@ui_specialist_agent": "ui-specialist-agent",
    "@core_concept_agent": "core-concept-agent",
    "@devops_agent": "devops-agent",
    "@documentation_agent": "documentation-agent",
    "@project_initiator_agent": "project-initiator-agent",
    "@task_planning_agent": "task-planning-agent",
    "@elicitation_agent": "elicitation-agent",
    "@security_auditor_agent": "security-auditor-agent",
    "@compliance_scope_agent": "compliance-scope-agent",
    "@ethical_review_agent": "ethical-review-agent",
    "@efficiency_optimization_agent": "efficiency-optimization-agent",
    "@health_monitor_agent": "health-monitor-agent",
    "@marketing_strategy_orchestrator_agent": "marketing-strategy-orchestrator-agent",
    "@community_strategy_agent": "community-strategy-agent",
    "@branding_agent": "branding-agent",
    "@deep_research_agent": "deep-research-agent",
    "@llm_ai_agents_research": "llm-ai-agents-research",
    "@root_cause_analysis_agent": "root-cause-analysis-agent",
    "@technology_advisor_agent": "technology-advisor-agent",
    "@ml_specialist_agent": "ml-specialist-agent",
    "@creative_ideation_agent": "creative-ideation-agent",
    "@analytics_setup_agent": "analytics-setup-agent",
    
    # Without @ prefix  
    "coding_agent": "coding-agent",
    "debugger_agent": "debugger-agent",
    "code_reviewer_agent": "code-reviewer-agent",
    "prototyping_agent": "prototyping-agent",
    "test_orchestrator_agent": "test-orchestrator-agent",
    "uat_coordinator_agent": "uat-coordinator-agent",
    "performance_load_tester_agent": "performance-load-tester-agent",
    "system_architect_agent": "system-architect-agent",
    "design_system_agent": "design-system-agent",
    "ui_specialist_agent": "ui-specialist-agent",
    "core_concept_agent": "core-concept-agent",
    "devops_agent": "devops-agent",
    "documentation_agent": "documentation-agent",
    "project_initiator_agent": "project-initiator-agent",
    "task_planning_agent": "task-planning-agent",
    "master_orchestrator_agent": "master-orchestrator-agent",
    "elicitation_agent": "elicitation-agent",
    "security_auditor_agent": "security-auditor-agent",
    "compliance_scope_agent": "compliance-scope-agent",
    "ethical_review_agent": "ethical-review-agent",
    "efficiency_optimization_agent": "efficiency-optimization-agent",
    "health_monitor_agent": "health-monitor-agent",
    "marketing_strategy_orchestrator_agent": "marketing-strategy-orchestrator-agent",
    "community_strategy_agent": "community-strategy-agent",
    "branding_agent": "branding-agent",
    "deep_research_agent": "deep-research-agent",
    "llm_ai_agents_research": "llm-ai-agents-research",
    "root_cause_analysis_agent": "root-cause-analysis-agent",
    "technology_advisor_agent": "technology-advisor-agent",
    "ml_specialist_agent": "ml-specialist-agent",
    "creative_ideation_agent": "creative-ideation-agent",
    "analytics_setup_agent": "analytics-setup-agent",
}

# Directories to process
DIRECTORIES_TO_PROCESS = [
    "dhafnck_mcp_main/src",
    "dhafnck_mcp_main/scripts",
    "dhafnck_mcp_main/agent-library",
    ".claude",
    "ai_docs",
    "dhafnck-frontend/src",
]

# File extensions to process
FILE_EXTENSIONS = {".py", ".yaml", ".yml", ".md", ".json", ".ts", ".tsx", ".js", ".jsx"}

def should_process_file(file_path: Path) -> bool:
    """Determine if a file should be processed."""
    # Skip if not a file
    if not file_path.is_file():
        return False
    
    # Skip hidden files
    if file_path.name.startswith('.'):
        return False
    
    # Check extension
    return file_path.suffix.lower() in FILE_EXTENSIONS

def update_file_content(file_path: Path, mappings: Dict[str, str]) -> bool:
    """Update agent names in a file."""
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            content = f.read()
    except Exception as e:
        print(f"Error reading {file_path}: {e}")
        return False
    
    original_content = content
    
    # Sort mappings by length (longest first) to avoid partial replacements
    sorted_mappings = sorted(mappings.items(), key=lambda x: len(x[0]), reverse=True)
    
    for old_name, new_name in sorted_mappings:
        # Use word boundary for non-@ prefixed names
        if not old_name.startswith('@'):
            # Match whole words only
            pattern = r'\b' + re.escape(old_name) + r'\b'
            content = re.sub(pattern, new_name, content)
        else:
            # Direct replacement for @ prefixed names
            content = content.replace(old_name, new_name)
    
    # Save if changed
    if content != original_content:
        try:
            with open(file_path, 'w', encoding='utf-8') as f:
                f.write(content)
            return True
        except Exception as e:
            print(f"Error writing {file_path}: {e}")
            return False
    
    return False

def process_directory(directory: Path, mappings: Dict[str, str]) -> Tuple[int, List[Path]]:
    """Process all files in a directory recursively."""
    updated_count = 0
    updated_files = []
    
    for file_path in directory.rglob('*'):
        if should_process_file(file_path):
            if update_file_content(file_path, mappings):
                updated_count += 1
                updated_files.append(file_path)
                rel_path = file_path.relative_to(PROJECT_ROOT)
                print(f"Updated: {rel_path}")
    
    return updated_count, updated_files

def main():
    """Main execution function."""
    print("=" * 80)
    print("COMPREHENSIVE AGENT NAME UPDATE TO KEBAB-CASE FORMAT")
    print("=" * 80)
    
    total_updated = 0
    all_updated_files = []
    
    for dir_name in DIRECTORIES_TO_PROCESS:
        dir_path = PROJECT_ROOT / dir_name
        if not dir_path.exists():
            print(f"Skipping non-existent directory: {dir_name}")
            continue
        
        print(f"\nProcessing: {dir_name}")
        print("-" * 40)
        
        count, files = process_directory(dir_path, AGENT_NAME_MAPPINGS)
        total_updated += count
        all_updated_files.extend(files)
    
    print("\n" + "=" * 80)
    print(f"SUMMARY: Updated {total_updated} files")
    print("=" * 80)
    
    if all_updated_files:
        print("\nUpdated files:")
        for file_path in sorted(all_updated_files):
            rel_path = file_path.relative_to(PROJECT_ROOT)
            print(f"  - {rel_path}")
    
    print("\n✅ Agent name standardization complete!")
    print("All agent names have been converted to kebab-case format.")

if __name__ == "__main__":
    main()