#!/usr/bin/env python3
# /// script
# requires-python = ">=3.11"
# dependencies = [
#     "python-dotenv",
# ]
# ///

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


def get_git_branch():
    """Get current git branch if in a git repository."""
    try:
        result = subprocess.run(
            ['git', 'rev-parse', '--abbrev-ref', 'HEAD'],
            capture_output=True,
            text=True,
            timeout=2
        )
        if result.returncode == 0:
            return result.stdout.strip()
    except Exception:
        pass
    return None


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
    """Generate a beautiful but simple status line."""
    parts = []
    
    # Model display name - clean and simple
    model_info = input_data.get('model', {})
    model_name = model_info.get('display_name', 'Claude')
    parts.append(f"\033[1;36m◆ {model_name}\033[0m")  # Bold cyan with diamond
    
    # Current directory - just the name
    workspace = input_data.get('workspace', {})
    current_dir = workspace.get('current_dir', '')
    if current_dir:
        dir_name = os.path.basename(current_dir)
        parts.append(f"\033[94m{dir_name}\033[0m")  # Light blue
    
    # Git branch with clean status
    git_branch = get_git_branch()
    if git_branch:
        git_status = get_git_status()
        if git_status:
            # Modified files indicator
            parts.append(f"\033[92m{git_branch}\033[0m \033[93m{git_status}\033[0m")
        else:
            # Clean state
            parts.append(f"\033[92m{git_branch} ✓\033[0m")
    
    # Agent role - Claude IS the master orchestrator
    parts.append("\033[92m🎯 Active: master-orchestrator-agent\033[0m")  # Green text showing active role
    
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