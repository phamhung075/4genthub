#!/usr/bin/env python3
# /// script
# requires-python = ">=3.11"
# dependencies = [
#     "python-dotenv",
# ]
# ///

"""
Status Line Generator with Project and Branch Context

This script generates a status line with project name and git branch information,
along with other context like the active agent and AI data paths.

Configuration Options (Environment Variables):
- STATUS_SHOW_PROJECT=true/false    : Show/hide project name (default: true)
- STATUS_SHOW_BRANCH=true/false     : Show/hide git branch (default: true)
- STATUS_SHORT_PROJECT_NAME=true/false : Truncate long project names (default: false)

Example Output:
◆ Claude • 📁 project-name • 🌿 main ±5 • 🎯 Active: coding-agent • 📊 data 📚 ai_docs

Features:
- Project name extraction from git remote origin URL with fallback to directory name
- Enhanced git branch display with color coding by branch type:
  * main/master: Bold green
  * develop/*: Yellow
  * feature/*: Blue
  * hotfix/*: Red
  * detached HEAD: Magenta
- Git status indicators (±N for modified files)
- Detached HEAD state handling
- Configurable display options via environment variables
- Timeout protection on git commands (2 seconds)
- Graceful error handling and fallbacks
"""

import json
import os
import sys
import subprocess
from pathlib import Path
from datetime import datetime

try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass  # dotenv is optional

# Import the path loader utilities
sys.path.insert(0, str(Path(__file__).parent.parent / "hooks"))
from utils.env_loader import get_ai_data_path, get_ai_docs_path
from utils.agent_state_manager import get_current_agent, get_agent_role_from_session


def log_status_line(input_data, status_line_output):
    """Log status line event to AI_DATA directory."""
    # Get AI_DATA path from environment
    log_dir = get_ai_data_path()
    log_file = log_dir / 'status_line.json'
    
    # Read existing log data or initialize empty list
    if log_file.exists():
        with open(log_file, 'r') as f:
            try:
                log_data = json.load(f)
            except (json.JSONDecodeError, ValueError):
                log_data = []
    else:
        log_data = []
    
    # Create log entry with input data and generated output
    log_entry = {
        "timestamp": datetime.now().isoformat(),
        "input_data": input_data,
        "status_line_output": status_line_output
    }
    
    # Append the log entry
    log_data.append(log_entry)
    
    # Write back to file with formatting
    with open(log_file, 'w') as f:
        json.dump(log_data, f, indent=2)


def get_project_name():
    """Get project name from git remote origin or directory name."""
    try:
        # Try git remote origin URL first
        result = subprocess.run(
            ['git', 'remote', 'get-url', 'origin'],
            capture_output=True,
            text=True,
            timeout=2
        )
        if result.returncode == 0:
            url = result.stdout.strip()
            if url:
                # Extract project name from URL (handle both SSH and HTTPS)
                # Examples: git@github.com:user/repo.git -> repo
                #          https://github.com/user/repo.git -> repo
                project_name = Path(url).stem.replace('.git', '')
                if project_name and project_name != 'origin':
                    return project_name

        # Fallback to current directory name
        return Path.cwd().name
    except Exception:
        # Final fallback to current directory name
        return Path.cwd().name


def get_git_branch():
    """Get current git branch if in a git repository."""
    try:
        result = subprocess.run(
            ['git', 'branch', '--show-current'],
            capture_output=True,
            text=True,
            timeout=2
        )
        if result.returncode == 0:
            branch = result.stdout.strip()
            if branch:
                return branch
            else:
                # Handle detached HEAD state
                result = subprocess.run(
                    ['git', 'rev-parse', '--short', 'HEAD'],
                    capture_output=True,
                    text=True,
                    timeout=2
                )
                if result.returncode == 0:
                    return f"detached:{result.stdout.strip()}"
        return "no-git"
    except Exception:
        return "no-git"


def get_git_status():
    """Get git status indicators."""
    try:
        # Check if there are uncommitted changes
        result = subprocess.run(
            ['git', 'status', '--porcelain'],
            capture_output=True,
            text=True,
            timeout=2
        )
        if result.returncode == 0:
            changes = result.stdout.strip()
            if changes:
                lines = changes.split('\n')
                return f"±{len(lines)}"
    except Exception:
        pass
    return ""


def generate_status_line(input_data):
    """Generate a beautiful but simple status line with project and branch context."""
    parts = []

    # Configuration options from environment variables
    show_project = os.getenv('STATUS_SHOW_PROJECT', 'true').lower() in ('true', '1', 'yes', 'on')
    show_branch = os.getenv('STATUS_SHOW_BRANCH', 'true').lower() in ('true', '1', 'yes', 'on')
    short_project_name = os.getenv('STATUS_SHORT_PROJECT_NAME', 'false').lower() in ('true', '1', 'yes', 'on')

    # Model display name - clean and simple
    model_info = input_data.get('model', {})
    model_name = model_info.get('display_name', 'Claude')
    parts.append(f"\033[1;36m◆ {model_name}\033[0m")  # Bold cyan with diamond

    # Project name - prominent display as requested
    if show_project:
        project_name = get_project_name()
        if project_name:
            # Option to show short project name (just the name without path info)
            if short_project_name and len(project_name) > 20:
                project_name = project_name[:17] + "..."
            parts.append(f"\033[1;94m📁 {project_name}\033[0m")  # Bold blue with folder icon

    # Git branch with enhanced display and status
    if show_branch:
        git_branch = get_git_branch()
        if git_branch and git_branch != "no-git":
            git_status = get_git_status()

            # Color code branches by type
            branch_color = "\033[92m"  # Default green
            if git_branch == "main" or git_branch == "master":
                branch_color = "\033[1;92m"  # Bold green for main branches
            elif git_branch.startswith("develop"):
                branch_color = "\033[93m"  # Yellow for develop
            elif git_branch.startswith("feature/"):
                branch_color = "\033[94m"  # Blue for features
            elif git_branch.startswith("hotfix/"):
                branch_color = "\033[91m"  # Red for hotfixes
            elif git_branch.startswith("detached:"):
                branch_color = "\033[95m"  # Magenta for detached HEAD

            if git_status:
                # Modified files indicator
                parts.append(f"{branch_color}🌿 {git_branch}\033[0m \033[93m{git_status}\033[0m")
            else:
                # Clean state
                parts.append(f"{branch_color}🌿 {git_branch} ✓\033[0m")

    # Agent role - Dynamic based on session state
    session_id = input_data.get('session_id', '')
    current_agent = get_current_agent(session_id) if session_id else 'master-orchestrator-agent'

    # Dynamic agent role display that changes based on session state
    agent_role = get_agent_role_from_session(session_id) if session_id else 'Assistant'
    if agent_role and agent_role != 'Assistant':
        # Show dynamic agent role format: [Agent] [Role]
        parts.append(f"\033[94m[Agent] [{agent_role}]\033[0m")  # Blue text for agent role

    # Active agent display
    parts.append(f"\033[92m🎯 Active: {current_agent}\033[0m")  # Green text showing active role

    # Task tracking moved to hint system - displays every 5 tool calls
    # See .claude/hooks/config/__hint_message__config.yaml for configuration

    # Paths - always show for AI memory
    try:
        ai_data = get_ai_data_path()
        ai_docs = get_ai_docs_path()

        # Always show paths to help AI remember where things are
        paths = []
        if ai_data:
            paths.append(f"📊 {ai_data.name}")
        if ai_docs:
            paths.append(f"📚 {ai_docs.name}")

        if paths:
            parts.append(f"\033[95m{' '.join(paths)}\033[0m")
    except Exception:
        pass

    return " • ".join(parts)  # Use bullet separator for cleaner look


def main():
    try:
        # Read JSON input from stdin
        input_data = json.loads(sys.stdin.read())
        
        # Generate status line
        status_line = generate_status_line(input_data)
        
        # Log the status line event
        log_status_line(input_data, status_line)
        
        # Output the status line (first line of stdout becomes the status line)
        print(status_line)
        
        # Success
        sys.exit(0)
        
    except json.JSONDecodeError:
        # Handle JSON decode errors gracefully - output basic status
        print("\033[31m[Claude] 📁 Unknown\033[0m")
        sys.exit(0)
    except Exception:
        # Handle any other errors gracefully - output basic status
        print("\033[31m[Claude] 📁 Error\033[0m")
        sys.exit(0)


if __name__ == '__main__':
    main()