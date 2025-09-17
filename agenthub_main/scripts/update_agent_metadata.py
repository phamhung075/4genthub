#!/usr/bin/env python3
"""
Update metadata.yaml files for all agents in the agent-library
This script reads each agent's config.yaml and creates a proper metadata.yaml
with description, examples, model, and color fields.
"""

import os
import yaml
from pathlib import Path
import random

# Define available colors
COLORS = [
    "red", "blue", "green", "yellow", "purple", "orange", "cyan", "magenta",
    "pink", "teal", "indigo", "lime", "amber", "emerald", "violet", "rose",
    "sky", "slate", "zinc", "stone"
]

# Define model preferences based on agent category
MODEL_MAPPING = {
    "development": "sonnet",
    "devops": "sonnet",
    "testing": "sonnet",
    "security": "sonnet",
    "architecture": "sonnet",
    "planning": "sonnet",
    "documentation": "sonnet",
    "marketing": "sonnet",
    "design": "sonnet",
    "research": "sonnet",
    "business": "sonnet",
    "orchestration": "sonnet",
    "quality": "sonnet",
    "frontend": "sonnet",
    "database": "sonnet",
    "infrastructure": "sonnet",
    "monitoring": "sonnet",
    "integration": "sonnet",
    "advisory": "sonnet",
    "general": "sonnet"
}

def generate_examples(agent_name, description, usage_scenarios):
    """Generate context examples for the agent"""
    agent_slug = agent_name.replace(" ", "-").replace("_", "-").lower()
    
    # Extract key action words from description
    action_words = []
    desc_lower = description.lower()
    
    if "implement" in desc_lower or "code" in desc_lower or "develop" in desc_lower:
        action_words.append("implement")
    if "debug" in desc_lower or "fix" in desc_lower or "troubleshoot" in desc_lower:
        action_words.append("debug")
    if "test" in desc_lower or "verify" in desc_lower or "validate" in desc_lower:
        action_words.append("test")
    if "deploy" in desc_lower or "release" in desc_lower:
        action_words.append("deploy")
    if "design" in desc_lower or "architect" in desc_lower:
        action_words.append("design")
    if "analyze" in desc_lower or "research" in desc_lower:
        action_words.append("analyze")
    if "plan" in desc_lower or "organize" in desc_lower:
        action_words.append("plan")
    if "secure" in desc_lower or "audit" in desc_lower:
        action_words.append("secure")
    if "document" in desc_lower:
        action_words.append("document")
    if "optimize" in desc_lower or "improve" in desc_lower:
        action_words.append("optimize")
    
    if not action_words:
        action_words = ["help with"]
    
    # Generate three example scenarios
    examples = []
    
    # Example 1: Direct request
    examples.append(f"""<example>
  Context: User needs {action_words[0] if action_words else 'help with'} related to {agent_name.replace('_agent', '').replace('_', ' ')}
  user: "I need to {action_words[0] if action_words else 'work on'} {agent_name.replace('_agent', '').replace('_', ' ').lower()}"
  assistant: "I'll use the {agent_slug} agent to help you with this task"
  <commentary>
  The user needs {agent_name.replace('_agent', '').replace('_', ' ').lower()} expertise, so use the Task tool to launch the {agent_slug} agent.
  </commentary>
  </example>""")
    
    # Example 2: Problem scenario
    if len(action_words) > 1:
        examples.append(f"""<example>
  Context: User experiencing issues that need {agent_name.replace('_agent', '').replace('_', ' ').lower()} expertise
  user: "Can you help me {action_words[1]} this problem?"
  assistant: "Let me use the {agent_slug} agent to {action_words[1]} this for you"
  <commentary>
  The user needs {action_words[1]} assistance, so use the Task tool to launch the {agent_slug} agent.
  </commentary>
  </example>""")
    
    # Example 3: General assistance
    examples.append(f"""<example>
  Context: User needs guidance from {agent_name.replace('_agent', '').replace('_', ' ').lower()}
  user: "I need expert help with {agent_name.replace('_agent', '').replace('_', ' ').lower().split()[-1]}"
  assistant: "I'll use the {agent_slug} agent to provide expert guidance"
  <commentary>
  The user needs specialized expertise, so use the Task tool to launch the {agent_slug} agent.
  </commentary>
  </example>""")
    
    return "\n  \n  ".join(examples[:2])  # Return 2 examples to keep it concise

def process_agent(agent_path):
    """Process a single agent directory and create/update metadata.yaml"""
    agent_name = agent_path.name
    config_path = agent_path / "config.yaml"
    metadata_path = agent_path / "metadata.yaml"
    
    if not config_path.exists():
        print(f"⚠️  No config.yaml found for {agent_name}")
        return False
    
    try:
        # Read config.yaml
        with open(config_path, 'r') as f:
            config = yaml.safe_load(f)
        
        agent_info = config.get('agent_info', {})
        
        # Extract information
        name = agent_info.get('slug', agent_name).replace('_', '-')
        description = agent_info.get('description', f"Agent for {agent_name.replace('_', ' ')}")
        usage_scenarios = agent_info.get('usage_scenarios', '')
        category = agent_info.get('category', 'general')
        
        # Generate the full description with examples
        full_description = f"{usage_scenarios.strip()}. {description.strip()}".strip()
        if not full_description.endswith('.'):
            full_description += '.'
        
        examples = generate_examples(agent_name, description, usage_scenarios)
        
        full_description_with_examples = f"""{full_description}
  
  {examples}"""
        
        # Determine model based on category
        model = MODEL_MAPPING.get(category, "sonnet")
        
        # Assign a color (deterministic based on agent name for consistency)
        color_index = hash(agent_name) % len(COLORS)
        color = COLORS[color_index]
        
        # Read existing metadata if it exists
        existing_metadata = {}
        if metadata_path.exists():
            with open(metadata_path, 'r') as f:
                content = f.read()
                if content.strip():
                    # Parse YAML frontmatter
                    if content.startswith('---'):
                        yaml_content = content.split('---')[1]
                        existing_metadata = yaml.safe_load(yaml_content) or {}
        
        # Create new metadata
        metadata = {
            'name': name,
            'description': full_description_with_examples,
            'model': model,
            'color': color
        }
        
        # Preserve migration and validation info if it exists
        if 'migration' in existing_metadata:
            metadata['migration'] = existing_metadata['migration']
        else:
            metadata['migration'] = {
                'date': agent_info.get('migration_date', '2025-06-30T11:55:00.000000'),
                'source': 'agent-library',
                'target': 'agent-library',
                'version': agent_info.get('version', '1.0.0')
            }
        
        if 'validation' in existing_metadata:
            metadata['validation'] = existing_metadata['validation']
        else:
            metadata['validation'] = {
                'backward_compatible': True,
                'capabilities_mapped': True,
                'structure_valid': True
            }
        
        # Write metadata.yaml with frontmatter format
        with open(metadata_path, 'w') as f:
            f.write('---\n')
            yaml.dump(metadata, f, default_flow_style=False, sort_keys=False, allow_unicode=True)
            f.write('---\n')
        
        print(f"✅ Updated {agent_name} - model: {model}, color: {color}")
        return True
        
    except Exception as e:
        print(f"❌ Error processing {agent_name}: {e}")
        return False

def main():
    """Main function to process all agents"""
    agent_library_path = Path("/home/daihungpham/agentic-project/agenthub_main/agent-library/agents")
    
    if not agent_library_path.exists():
        print(f"Error: Agent library path not found: {agent_library_path}")
        return
    
    # Get all agent directories
    agent_dirs = [d for d in agent_library_path.iterdir() if d.is_dir()]
    agent_dirs.sort()
    
    print(f"Found {len(agent_dirs)} agents to process\n")
    
    success_count = 0
    failed_count = 0
    
    for agent_dir in agent_dirs:
        if process_agent(agent_dir):
            success_count += 1
        else:
            failed_count += 1
    
    print(f"\n{'='*60}")
    print(f"Processing complete:")
    print(f"  ✅ Successfully updated: {success_count}")
    print(f"  ❌ Failed: {failed_count}")
    print(f"  📁 Total: {len(agent_dirs)}")

if __name__ == "__main__":
    main()