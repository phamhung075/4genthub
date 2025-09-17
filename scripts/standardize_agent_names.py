#!/usr/bin/env python3
"""
Script to standardize all agent names to kebab-case format.
This will rename files in .claude/agents and folders in 4genthub_main/agent-library/agents
"""

import os
import re
import shutil
from pathlib import Path

# Define base paths
PROJECT_ROOT = Path("/home/daihungpham/__projects__/agentic-project")
CLAUDE_AGENTS_DIR = PROJECT_ROOT / ".claude/agents"
AGENT_LIBRARY_DIR = PROJECT_ROOT / "4genthub_main/agent-library/agents"

def to_kebab_case(name):
    """Convert any agent name format to kebab-case."""
    # Remove @ prefix if present
    name = name.lstrip('@')
    
    # Replace underscores with hyphens
    name = name.replace('_', '-')
    
    # Ensure it ends with -agent if not already
    if not name.endswith('-agent'):
        name = name + '-agent' if '-agent' not in name else name
    
    return name.lower()

def rename_claude_agent_files():
    """Rename all files in .claude/agents to kebab-case."""
    print("\n=== Renaming .claude/agents files ===")
    
    for file_path in CLAUDE_AGENTS_DIR.glob("*.md"):
        old_name = file_path.stem
        new_name = to_kebab_case(old_name) + ".md"
        new_path = CLAUDE_AGENTS_DIR / new_name
        
        if file_path.name != new_name:
            print(f"Renaming: {file_path.name} -> {new_name}")
            file_path.rename(new_path)
        else:
            print(f"Already correct: {file_path.name}")

def update_claude_agent_content():
    """Update content in .claude/agents files to use kebab-case references."""
    print("\n=== Updating .claude/agents file content ===")
    
    for file_path in CLAUDE_AGENTS_DIR.glob("*.md"):
        with open(file_path, 'r') as f:
            content = f.read()
        
        original_content = content
        
        # Replace @agent_name patterns with kebab-case
        content = re.sub(r'@(\w+_\w+(?:_\w+)*)', lambda m: '@' + to_kebab_case(m.group(1)), content)
        
        # Replace agent_name patterns (without @) with kebab-case
        content = re.sub(r'\b(\w+_\w+(?:_\w+)*agent)\b', lambda m: to_kebab_case(m.group(1)), content)
        
        if content != original_content:
            print(f"Updating content in: {file_path.name}")
            with open(file_path, 'w') as f:
                f.write(content)
        else:
            print(f"No changes needed in: {file_path.name}")

def rename_agent_library_folders():
    """Rename all folders in 4genthub_main/agent-library/agents to kebab-case."""
    print("\n=== Renaming agent-library folders ===")
    
    # Get all directories except hidden ones
    folders = [d for d in AGENT_LIBRARY_DIR.iterdir() 
               if d.is_dir() and not d.name.startswith('.')]
    
    for folder_path in folders:
        old_name = folder_path.name
        new_name = to_kebab_case(old_name)
        new_path = AGENT_LIBRARY_DIR / new_name
        
        if folder_path.name != new_name:
            print(f"Renaming: {folder_path.name} -> {new_name}")
            folder_path.rename(new_path)
        else:
            print(f"Already correct: {folder_path.name}")

def update_yaml_files():
    """Update all YAML files in agent-library to use kebab-case."""
    print("\n=== Updating YAML files in agent-library ===")
    
    for yaml_file in AGENT_LIBRARY_DIR.rglob("*.yaml"):
        with open(yaml_file, 'r') as f:
            content = f.read()
        
        original_content = content
        
        # Update agent names in YAML content
        content = re.sub(r'agent_name:\s*"?([^"\n]+)"?', 
                        lambda m: f'agent_name: "{to_kebab_case(m.group(1))}"', 
                        content)
        
        # Update @agent references
        content = re.sub(r'@(\w+_\w+(?:_\w+)*)', 
                        lambda m: '@' + to_kebab_case(m.group(1)), 
                        content)
        
        # Update plain agent references
        content = re.sub(r'\b(\w+_\w+(?:_\w+)*agent)\b', 
                        lambda m: to_kebab_case(m.group(1)), 
                        content)
        
        if content != original_content:
            print(f"Updating: {yaml_file.relative_to(PROJECT_ROOT)}")
            with open(yaml_file, 'w') as f:
                f.write(content)

def main():
    """Main execution function."""
    print("Starting agent name standardization to kebab-case format...")
    
    # Step 1: Rename .claude/agents files
    rename_claude_agent_files()
    
    # Step 2: Update content in .claude/agents files
    update_claude_agent_content()
    
    # Step 3: Rename agent-library folders
    rename_agent_library_folders()
    
    # Step 4: Update YAML files
    update_yaml_files()
    
    print("\n=== Standardization complete! ===")
    print("All agent names have been converted to kebab-case format.")

if __name__ == "__main__":
    main()