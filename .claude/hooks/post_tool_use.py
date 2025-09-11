#!/usr/bin/env python3
# /// script
# requires-python = ">=3.8"
# ///

"""
Post-tool use hook for automatic documentation tracking and index updates.

This hook runs after tool execution and:
1. Updates ai_docs/index.json when files are added/modified/deleted
2. Tracks documentation requirements for modified files
3. Moves obsolete documentation when source files are deleted
"""

import json
import os
import sys
from pathlib import Path
from datetime import datetime

# Import utilities
sys.path.insert(0, str(Path(__file__).parent))
from utils.env_loader import get_ai_data_path
from utils.docs_indexer import update_index, check_documentation_requirement, move_to_obsolete

# Import the new context update system
try:
    from utils.context_updater import update_context_sync
    CONTEXT_UPDATES_ENABLED = True
except ImportError:
    update_context_sync = None
    CONTEXT_UPDATES_ENABLED = False

def get_modified_file(tool_name, tool_input):
    """Extract the file path that was modified by the tool."""
    if tool_name == 'Write' or tool_name == 'Edit' or tool_name == 'MultiEdit':
        return tool_input.get('file_path')
    elif tool_name == 'NotebookEdit':
        return tool_input.get('notebook_path')
    elif tool_name == 'Bash':
        # Check for file operations in bash commands
        command = tool_input.get('command', '')
        if 'mv ' in command or 'rm ' in command or 'touch ' in command:
            # Simple extraction - this could be enhanced
            parts = command.split()
            for i, part in enumerate(parts):
                if part in ['mv', 'rm', 'touch'] and i + 1 < len(parts):
                    return parts[i + 1]
    return None

def main():
    try:
        # Read JSON input from stdin
        input_data = json.load(sys.stdin)
        
        tool_name = input_data.get('tool_name', '')
        tool_input = input_data.get('tool_input', {})
        
        # Get paths
        log_dir = get_ai_data_path()
        ai_docs_path = Path.cwd() / 'ai_docs'
        
        # Original logging
        log_path = log_dir / 'post_tool_use.json'
        if log_path.exists():
            with open(log_path, 'r') as f:
                try:
                    log_data = json.load(f)
                except (json.JSONDecodeError, ValueError):
                    log_data = []
        else:
            log_data = []
        log_data.append(input_data)
        with open(log_path, 'w') as f:
            json.dump(log_data, f, indent=2)
        
        # Check if ai_docs was modified
        modified_file = get_modified_file(tool_name, tool_input)
        
        if modified_file:
            modified_path = Path(modified_file)
            
            # If file is in ai_docs, update index
            if 'ai_docs' in modified_path.parts:
                try:
                    update_index(ai_docs_path)
                except:
                    pass  # Don't block on index update errors
            
            # Check documentation requirement for code files
            elif modified_path.suffix in ['.py', '.js', '.ts', '.sh', '.sql', '.jsx', '.tsx']:
                try:
                    has_doc, doc_path, needs_update = check_documentation_requirement(
                        modified_path, ai_docs_path
                    )
                    
                    # Emit warning if documentation is missing or outdated
                    if not has_doc or needs_update:
                        action = "create" if not has_doc else "update"
                        print(f"📝 Documentation needed: Please {action} {doc_path}", file=sys.stderr)
                        print(f"   for file: {modified_path}", file=sys.stderr)
                except:
                    pass  # Don't block on documentation check errors
        
        # CONTEXT UPDATES: Update MCP context based on tool execution
        if CONTEXT_UPDATES_ENABLED and update_context_sync:
            try:
                # Attempt context updates with error handling
                context_update_success = update_context_sync(tool_name, tool_input)
                
                if context_update_success:
                    # Log successful context update
                    log_dir = get_ai_data_path()
                    context_update_log_path = log_dir / 'context_updates.json'
                    
                    context_update_entry = {
                        'timestamp': datetime.now().isoformat(),
                        'tool_name': tool_name,
                        'update_successful': True,
                        'modified_file': modified_file
                    }
                    
                    # Append to context update log
                    if context_update_log_path.exists():
                        with open(context_update_log_path, 'r') as f:
                            try:
                                context_update_data = json.load(f)
                            except (json.JSONDecodeError, ValueError):
                                context_update_data = []
                    else:
                        context_update_data = []
                    
                    context_update_data.append(context_update_entry)
                    
                    # Keep only last 100 entries to prevent log bloat
                    if len(context_update_data) > 100:
                        context_update_data = context_update_data[-100:]
                    
                    with open(context_update_log_path, 'w') as f:
                        json.dump(context_update_data, f, indent=2)
                        
            except Exception as e:
                # Context update failure should not block hook execution
                # Log the error but continue normally
                error_msg = f"Context update failed: {str(e)}"
                print(f"WARNING: {error_msg}", file=sys.stderr)
                
                # Log the error
                log_dir = get_ai_data_path()
                error_log_path = log_dir / 'context_update_errors.json'
                
                error_entry = {
                    'timestamp': datetime.now().isoformat(),
                    'tool_name': tool_name,
                    'error': str(e),
                    'update_successful': False,
                    'modified_file': modified_file
                }
                
                if error_log_path.exists():
                    with open(error_log_path, 'r') as f:
                        try:
                            error_log_data = json.load(f)
                        except (json.JSONDecodeError, ValueError):
                            error_log_data = []
                else:
                    error_log_data = []
                
                error_log_data.append(error_entry)
                
                # Keep only last 50 error entries
                if len(error_log_data) > 50:
                    error_log_data = error_log_data[-50:]
                
                with open(error_log_path, 'w') as f:
                    json.dump(error_log_data, f, indent=2)
        
        sys.exit(0)
        
    except json.JSONDecodeError:
        # Handle JSON decode errors gracefully
        sys.exit(0)
    except Exception:
        # Exit cleanly on any other error
        sys.exit(0)

if __name__ == '__main__':
    main()