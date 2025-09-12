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

# Import agent context manager
try:
    from utils.agent_context_manager import switch_to_agent
    AGENT_CONTEXT_ENABLED = True
except ImportError:
    switch_to_agent = None
    AGENT_CONTEXT_ENABLED = False

# Import agent state manager for dynamic status line agent tracking
try:
    from utils.agent_state_manager import update_agent_state_from_call_agent
    AGENT_STATE_TRACKING_ENABLED = True
except ImportError:
    update_agent_state_from_call_agent = None
    AGENT_STATE_TRACKING_ENABLED = False

# Import MCP hint matrix for post-action reminders
try:
    from utils.mcp_post_action_hints import generate_post_action_hints
    MCP_POST_HINTS_ENABLED = True
except ImportError:
    generate_post_action_hints = None
    MCP_POST_HINTS_ENABLED = False

# Import hint bridge to store hints for next tool use
try:
    from utils.hint_bridge import store_hint
    HINT_BRIDGE_ENABLED = True
except ImportError:
    store_hint = None
    HINT_BRIDGE_ENABLED = False

# Import display formatter for Claude interface
try:
    from utils.post_action_display import format_for_claude_display
    DISPLAY_FORMATTER_ENABLED = True
except ImportError:
    format_for_claude_display = None
    DISPLAY_FORMATTER_ENABLED = False

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
        tool_result = input_data.get('tool_result', None)  # Get result if available
        
        # MCP POST-ACTION HINTS: Provide reminders after MCP operations
        if MCP_POST_HINTS_ENABLED and generate_post_action_hints and tool_name.startswith('mcp__dhafnck_mcp_http'):
            try:
                # Get action for logging
                action = tool_input.get('action', 'default')
                
                # Generate post-action hints based on what was just done
                post_hints = generate_post_action_hints(tool_name, tool_input, tool_result)
                if post_hints:
                    # Store hints for display on next tool use (since post output might not be visible)
                    if HINT_BRIDGE_ENABLED and store_hint:
                        store_hint(post_hints, tool_name, action)
                    
                    # Try formatted output for Claude interface
                    if DISPLAY_FORMATTER_ENABLED and format_for_claude_display:
                        formatted_hints = format_for_claude_display(post_hints, tool_name, action)
                        print(formatted_hints, flush=True)
                    else:
                        # Fallback to plain output
                        print(post_hints, flush=True)
                    
                    # Log detailed hint information
                    log_dir = get_ai_data_path()
                    hints_log_path = log_dir / 'mcp_post_hints_detailed.json'
                    
                    # Load existing log or create new
                    if hints_log_path.exists():
                        try:
                            with open(hints_log_path, 'r') as f:
                                hint_log = json.load(f)
                        except:
                            hint_log = []
                    else:
                        hint_log = []
                    
                    # Extract hint content for logging
                    hint_content = post_hints
                    if '<system-reminder>' in hint_content:
                        hint_content = hint_content.replace('<system-reminder>', '').replace('</system-reminder>', '').strip()
                    
                    # Add detailed log entry
                    log_entry = {
                        'timestamp': datetime.now().isoformat(),
                        'tool_name': tool_name,
                        'action': action,
                        'tool_input_summary': {
                            'task_id': tool_input.get('task_id'),
                            'title': tool_input.get('title'),
                            'status': tool_input.get('status'),
                            'completion_summary': tool_input.get('completion_summary')[:100] if tool_input.get('completion_summary') else None
                        },
                        'hint_generated': hint_content,
                        'hint_stored': HINT_BRIDGE_ENABLED and store_hint is not None,
                        'hint_displayed': DISPLAY_FORMATTER_ENABLED and format_for_claude_display is not None
                    }
                    hint_log.append(log_entry)
                    
                    # Keep only last 100 entries
                    if len(hint_log) > 100:
                        hint_log = hint_log[-100:]
                    
                    # Save detailed log
                    with open(hints_log_path, 'w') as f:
                        json.dump(hint_log, f, indent=2)
                    
                    # Also update simple log for quick reference
                    simple_log_path = log_dir / 'mcp_post_hints.log'
                    with open(simple_log_path, 'a') as f:
                        f.write(f"{datetime.now().isoformat()} - {tool_name}:{action} - Hint: {hint_content[:100]}...\n")
            except Exception as e:
                # Log error but don't block
                log_dir = get_ai_data_path()
                error_log_path = log_dir / 'mcp_post_hint_errors.log'
                with open(error_log_path, 'a') as f:
                    f.write(f"{datetime.now().isoformat()} - Error generating post hints: {e}\n")
        
        # AGENT CONTEXT SWITCHING: Detect call_agent tool and provide runtime context switch
        if tool_name == 'mcp__dhafnck_mcp_http__call_agent':
            agent_name = tool_input.get('name_agent', '')
            
            # AGENT STATE TRACKING: Update agent state for status line display
            if AGENT_STATE_TRACKING_ENABLED and agent_name:
                try:
                    # Get session_id from context (this might come from various places)
                    session_id = input_data.get('session_id', '')
                    if session_id:
                        update_agent_state_from_call_agent(session_id, tool_input)
                except Exception as e:
                    # Log error but don't block
                    log_dir = get_ai_data_path()
                    error_log_path = log_dir / 'agent_state_errors.log'
                    with open(error_log_path, 'a') as f:
                        f.write(f"{datetime.now().isoformat()} - Agent state update error: {e}\n")
            
            # AGENT CONTEXT SWITCHING: Provide runtime context switch instructions  
            if AGENT_CONTEXT_ENABLED and agent_name and agent_name != 'master-orchestrator-agent':
                try:
                    # Provide runtime context switch instructions
                    context_instructions = switch_to_agent(agent_name)
                    print(f"\n<system-reminder>\n{context_instructions}\n</system-reminder>\n", file=sys.stderr)
                except Exception as e:
                    print(f"Warning: Agent context switch failed: {e}", file=sys.stderr)
        
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