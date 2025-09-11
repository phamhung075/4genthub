#!/usr/bin/env python3
"""
Claude Code Agent Generator

This script generates Claude Code agent files from your dhafnck_mcp_http agent system.
It creates bridge agents that seamlessly integrate your 60+ specialized agents
with Claude Code's agent system.
"""

import json
import os
import sys
import requests
from pathlib import Path
from typing import Dict, List, Any

# Configuration
CLAUDE_AGENTS_DIR = Path.home() / ".claude" / "agents"
DHAFNCK_MCP_URL = "http://localhost:8000"
OUTPUT_DIR = Path("./generated-agents")

# Agent categories and their descriptions
AGENT_CATEGORIES = {
    "orchestrator": "High-level coordination and project management",
    "coding": "Implementation, development, and code-related work", 
    "debugging": "Bug fixes, troubleshooting, and error resolution",
    "testing": "Quality assurance, testing, and validation",
    "design": "UI/UX design, architecture, and system design",
    "security": "Security auditing, penetration testing, and compliance",
    "devops": "Deployment, infrastructure, and operations",
    "documentation": "Technical writing, guides, and documentation",
    "research": "Investigation, analysis, and research tasks",
    "specialized": "Domain-specific and specialized functionality"
}

# MCP tools commonly used with agents
COMMON_MCP_TOOLS = [
    "mcp__dhafnck_mcp_http__call_agent",
    "mcp__dhafnck_mcp_http__manage_task", 
    "mcp__dhafnck_mcp_http__manage_context",
    "mcp__dhafnck_mcp_http__manage_subtask",
    "mcp__dhafnck_mcp_http__manage_project"
]

def get_available_agents() -> List[str]:
    """Get list of available agents from dhafnck_mcp_http system."""
    # This would typically call an API endpoint to get available agents
    # For now, returning the known agents from the documentation
    return [
        "master-orchestrator-agent",
        "coding-agent", 
        "debugger-agent",
        "test-orchestrator-agent",
        "@ui_designer_agent",
        "system-architect-agent",
        "security-auditor-agent",
        "devops-agent",
        "documentation-agent",
        "task-planning-agent",
        "deep-research-agent",
        "@algorithmic_problem_solver_agent",
        "@brainjs_ml_agent",
        "marketing-strategy-orchestrator-agent",
        "compliance-scope-agent",
        "root-cause-analysis-agent",
        "prototyping-agent",
        "performance-load-tester-agent",
        "@ui_designer_expert_shadcn_agent"
        # Add more agents as needed
    ]

def categorize_agent(agent_name: str) -> str:
    """Categorize an agent based on its name."""
    name_lower = agent_name.lower()
    
    if "orchestrator" in name_lower or "uber" in name_lower or "coordinator" in name_lower:
        return "orchestrator"
    elif "coding" in name_lower or "architect" in name_lower or "algorithm" in name_lower:
        return "coding"
    elif "debug" in name_lower or "root_cause" in name_lower:
        return "debugging"
    elif "test" in name_lower or "qa" in name_lower:
        return "testing"
    elif "ui" in name_lower or "design" in name_lower or "ux" in name_lower:
        return "design"
    elif "security" in name_lower or "audit" in name_lower or "compliance" in name_lower:
        return "security"
    elif "devops" in name_lower or "deploy" in name_lower:
        return "devops"
    elif "document" in name_lower or "scribe" in name_lower:
        return "documentation"
    elif "research" in name_lower or "deep" in name_lower:
        return "research"
    else:
        return "specialized"

def generate_agent_description(agent_name: str, category: str) -> str:
    """Generate appropriate description for Claude Code agent."""
    base_descriptions = {
        "orchestrator": f"Advanced project orchestration and coordination. Use for complex multi-phase projects requiring {agent_name} capabilities.",
        "coding": f"Specialized development and implementation work. Ideal for {agent_name} related coding tasks.",
        "debugging": f"Expert debugging and troubleshooting. Activate for issues requiring {agent_name} analysis.",
        "testing": f"Comprehensive testing and quality assurance. Best for {agent_name} testing scenarios.",
        "design": f"Design and architecture expertise. Use for {agent_name} design challenges.",
        "security": f"Security analysis and compliance. Essential for {agent_name} security tasks.",
        "devops": f"Infrastructure and deployment expertise. Use for {agent_name} operations.",
        "documentation": f"Technical writing and documentation. Ideal for {agent_name} documentation needs.",
        "research": f"Research and analysis capabilities. Best for {agent_name} investigation tasks.",
        "specialized": f"Specialized functionality for {agent_name} specific requirements."
    }
    
    return base_descriptions.get(category, f"Specialized agent for {agent_name} tasks.")

def get_relevant_tools(category: str) -> List[str]:
    """Get relevant MCP tools for a category."""
    category_tools = {
        "orchestrator": COMMON_MCP_TOOLS,
        "coding": COMMON_MCP_TOOLS[:4],  # Exclude project management for basic coding
        "debugging": COMMON_MCP_TOOLS[:3], 
        "testing": COMMON_MCP_TOOLS,
        "design": COMMON_MCP_TOOLS[:4],
        "security": COMMON_MCP_TOOLS[:3],
        "devops": COMMON_MCP_TOOLS,
        "documentation": COMMON_MCP_TOOLS[:3],
        "research": COMMON_MCP_TOOLS[:3],
        "specialized": COMMON_MCP_TOOLS[:3]
    }
    
    return category_tools.get(category, COMMON_MCP_TOOLS[:3])

def generate_agent_content(agent_name: str, category: str) -> str:
    """Generate the content for a Claude Code agent."""
    clean_name = agent_name.replace("@", "").replace("_", "-")
    description = generate_agent_description(agent_name, category)
    tools = ", ".join(get_relevant_tools(category))
    
    content = f"""---
name: {clean_name}
description: {description}
tools: {tools}
model: sonnet
---

# {agent_name.replace('@', '').replace('_', ' ').title()} Bridge

I am your bridge to the advanced {agent_name} in your dhafnck_mcp_http system. I provide seamless integration between Claude Code and your sophisticated agent orchestration platform.

## Core Capabilities

This agent specializes in:
- {AGENT_CATEGORIES[category]}
- Integration with your task management system
- Context preservation across sessions
- Multi-agent coordination when needed

## Activation Workflow

When invoked, I will:

1. **Connect to your specialized agent**:
```
mcp__dhafnck_mcp_http__call_agent(name_agent="{agent_name}")
```

2. **Check project context** (if available):
```
mcp__dhafnck_mcp_http__manage_context(
    action="resolve",
    level="branch", 
    context_id=branch_id,
    include_inherited=true
)
```

3. **Create or update tasks** to track work:
```
mcp__dhafnck_mcp_http__manage_task(
    action="create",
    git_branch_id=branch_id,
    title="Work description",
    description="Detailed requirements"
)
```

4. **Execute specialized functionality** through your advanced agent system

5. **Update context** with findings and decisions:
```
mcp__dhafnck_mcp_http__manage_context(
    action="update",
    level="branch",
    context_id=branch_id,
    data={{
        "work_completed": "Description of work done",
        "key_decisions": "Important decisions made", 
        "next_steps": "Recommended follow-up actions"
    }}
)
```

## Integration Benefits

By using me, you get:
- **Direct access** to your advanced {agent_name} capabilities
- **Automatic task tracking** and project integration
- **Context preservation** between Claude Code and your system
- **Seamless workflow** bridging IDE work with orchestration

## Usage Notes

- I maintain compatibility with both Claude Code workflows and your dhafnck_mcp_http system
- All work is properly tracked and documented in your project management system
- Context is preserved and shared across different agents and sessions
- I can coordinate with other bridge agents when complex workflows are needed

This bridge ensures you get the full power of your specialized agent while maintaining natural integration with Claude Code's development environment.
"""
    
    return content

def create_agent_file(agent_name: str, output_dir: Path) -> None:
    """Create a Claude Code agent file for the given agent."""
    category = categorize_agent(agent_name)
    content = generate_agent_content(agent_name, category)
    
    clean_name = agent_name.replace("@", "").replace("_", "-")
    filename = f"{clean_name}.md"
    filepath = output_dir / filename
    
    with open(filepath, 'w', encoding='utf-8') as f:
        f.write(content)
    
    print(f"Generated: {filepath}")

def main():
    """Main function to generate all agent files."""
    print("Claude Code Agent Generator")
    print("=" * 40)
    
    # Create output directories
    OUTPUT_DIR.mkdir(exist_ok=True)
    CLAUDE_AGENTS_DIR.mkdir(parents=True, exist_ok=True)
    
    # Get available agents
    agents = get_available_agents()
    print(f"Found {len(agents)} agents to process")
    
    # Generate agent files
    for agent in agents:
        try:
            create_agent_file(agent, OUTPUT_DIR)
        except Exception as e:
            print(f"Error generating agent {agent}: {e}")
    
    print(f"\\nGenerated {len(agents)} agent files in {OUTPUT_DIR}")
    print(f"\\nTo install agents to Claude Code:")
    print(f"1. Review generated files in {OUTPUT_DIR}")
    print(f"2. Copy desired agents to {CLAUDE_AGENTS_DIR}")
    print(f"3. Restart Claude Code to load new agents")
    
    print(f"\\nExample install commands:")
    print(f"cp {OUTPUT_DIR}/*.md {CLAUDE_AGENTS_DIR}/")

if __name__ == "__main__":
    main()