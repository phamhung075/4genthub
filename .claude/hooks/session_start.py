#!/usr/bin/env python3
# /// script
# requires-python = ">=3.11"
# dependencies = [
#     "python-dotenv",
#     "requests",
# ]
# ///

import argparse
import json
import os
import sys
import subprocess
from pathlib import Path
from datetime import datetime
from typing import Optional, Dict, List, Any
import logging

try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass  # dotenv is optional

# Import the AI_DATA path loader and utilities
sys.path.insert(0, str(Path(__file__).parent))
from utils.env_loader import get_ai_data_path
from utils.mcp_client import get_default_client, ResilientMCPClient
from utils.cache_manager import get_session_cache

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def log_session_start(input_data):
    """Log session start event to AI_DATA directory."""
    # Get AI_DATA path from environment
    log_dir = get_ai_data_path()
    log_file = log_dir / 'session_start.json'
    
    # Read existing log data or initialize empty list
    if log_file.exists():
        with open(log_file, 'r') as f:
            try:
                log_data = json.load(f)
            except (json.JSONDecodeError, ValueError):
                log_data = []
    else:
        log_data = []
    
    # Append the entire input data
    log_data.append(input_data)
    
    # Write back to file with formatting
    with open(log_file, 'w') as f:
        json.dump(log_data, f, indent=2)


def get_git_status():
    """Get current git status information."""
    try:
        # Get current branch
        branch_result = subprocess.run(
            ['git', 'rev-parse', '--abbrev-ref', 'HEAD'],
            capture_output=True,
            text=True,
            timeout=5
        )
        current_branch = branch_result.stdout.strip() if branch_result.returncode == 0 else "unknown"
        
        # Get uncommitted changes count
        status_result = subprocess.run(
            ['git', 'status', '--porcelain'],
            capture_output=True,
            text=True,
            timeout=5
        )
        if status_result.returncode == 0:
            changes = status_result.stdout.strip().split('\n') if status_result.stdout.strip() else []
            uncommitted_count = len(changes)
        else:
            uncommitted_count = 0
        
        return current_branch, uncommitted_count
    except Exception:
        return None, None


def get_recent_issues():
    """Get recent GitHub issues if gh CLI is available."""
    try:
        # Check if gh is available
        gh_check = subprocess.run(['which', 'gh'], capture_output=True)
        if gh_check.returncode != 0:
            return None
        
        # Get recent open issues
        result = subprocess.run(
            ['gh', 'issue', 'list', '--limit', '5', '--state', 'open'],
            capture_output=True,
            text=True,
            timeout=10
        )
        if result.returncode == 0 and result.stdout.strip():
            return result.stdout.strip()
    except Exception:
        pass
    return None


def query_mcp_pending_tasks() -> Optional[List[Dict]]:
    """Query MCP server for pending tasks with fallback strategies."""
    cache = get_session_cache()
    
    # Strategy 1: Try cached data first for quick response
    cached_tasks = cache.get_pending_tasks()
    if cached_tasks:
        logger.debug("Using cached pending tasks")
        return cached_tasks
    
    # Strategy 2: Query live MCP server
    try:
        client = get_default_client()
        tasks = client.query_pending_tasks(limit=5)
        
        if tasks:
            # Cache successful result
            cache.cache_pending_tasks(tasks)
            logger.info(f"Retrieved {len(tasks)} pending tasks from MCP")
            return tasks
            
    except Exception as e:
        logger.warning(f"Failed to query pending tasks: {e}")
    
    # Strategy 3: Return None if all strategies fail
    logger.warning("No pending tasks available (server unavailable, no cache)")
    return None


def query_mcp_next_task(git_branch_id: Optional[str] = None) -> Optional[Dict]:
    """Query MCP server for next recommended task."""
    if not git_branch_id:
        logger.warning("No git branch ID provided for next task query")
        return None
    
    cache = get_session_cache()
    
    # Try cached data first
    cached_task = cache.get_next_task(git_branch_id)
    if cached_task:
        logger.debug("Using cached next task")
        return cached_task
    
    # Query live MCP server
    try:
        client = get_default_client()
        task = client.get_next_recommended_task(git_branch_id)
        
        if task:
            # Cache successful result
            cache.cache_next_task(git_branch_id, task)
            logger.info(f"Retrieved next task: {task.get('title', 'Unknown')}")
            return task
            
    except Exception as e:
        logger.warning(f"Failed to query next task: {e}")
    
    return None


def get_git_branch_context() -> Optional[Dict]:
    """Get git branch context including branch ID if available."""
    cache = get_session_cache()
    
    # Try cached git status first
    cached_git = cache.get_git_status()
    if cached_git:
        return cached_git
    
    try:
        # Get current branch
        branch_result = subprocess.run(
            ['git', 'rev-parse', '--abbrev-ref', 'HEAD'],
            capture_output=True,
            text=True,
            timeout=5
        )
        current_branch = branch_result.stdout.strip() if branch_result.returncode == 0 else "unknown"
        
        # Get uncommitted changes count
        status_result = subprocess.run(
            ['git', 'status', '--porcelain'],
            capture_output=True,
            text=True,
            timeout=5
        )
        if status_result.returncode == 0:
            changes = status_result.stdout.strip().split('\n') if status_result.stdout.strip() else []
            uncommitted_count = len(changes)
        else:
            uncommitted_count = 0
        
        # Get recent commits
        log_result = subprocess.run(
            ['git', 'log', '--oneline', '-5'],
            capture_output=True,
            text=True,
            timeout=5
        )
        recent_commits = log_result.stdout.strip() if log_result.returncode == 0 else ""
        
        git_context = {
            "branch": current_branch,
            "uncommitted_changes": uncommitted_count,
            "recent_commits": recent_commits.split('\n') if recent_commits else [],
            "git_branch_id": None  # Will be populated by MCP query if available
        }
        
        # Cache the result
        cache.cache_git_status(git_context)
        return git_context
        
    except Exception as e:
        logger.warning(f"Failed to get git context: {e}")
        return None


def format_mcp_context(tasks: Optional[List[Dict]], next_task: Optional[Dict], git_context: Optional[Dict]) -> str:
    """Format MCP context data for injection into Claude session."""
    context_parts = []
    
    # Add task context
    if tasks:
        context_parts.append("📋 **Current Pending Tasks:**")
        for i, task in enumerate(tasks[:3], 1):  # Limit to top 3 tasks
            title = task.get("title", "Unknown Task")
            status = task.get("status", "unknown")
            priority = task.get("priority", "medium")
            task_id = task.get("id", "")
            
            # Format with status and priority indicators
            status_emoji = {"todo": "⚪", "in_progress": "🔵", "blocked": "🔴"}.get(status, "⚫")
            priority_emoji = {"critical": "🚨", "high": "🔴", "medium": "🟡", "low": "🟢"}.get(priority, "⚫")
            
            context_parts.append(f"{i}. {status_emoji} {priority_emoji} {title}")
            if task_id:
                context_parts.append(f"   Task ID: {task_id}")
        context_parts.append("")
    
    # Add next recommended task
    if next_task:
        context_parts.append("🎯 **Next Recommended Task:**")
        title = next_task.get("title", "Unknown Task")
        description = next_task.get("description", "")
        task_id = next_task.get("id", "")
        
        context_parts.append(f"• {title}")
        if description:
            # Limit description to first 200 chars
            desc_preview = description[:200] + "..." if len(description) > 200 else description
            context_parts.append(f"  Description: {desc_preview}")
        if task_id:
            context_parts.append(f"  Task ID: {task_id}")
        context_parts.append("")
    
    # Add git context
    if git_context:
        context_parts.append("🌿 **Git Status:**")
        branch = git_context.get("branch", "unknown")
        changes = git_context.get("uncommitted_changes", 0)
        commits = git_context.get("recent_commits", [])
        
        context_parts.append(f"• Branch: {branch}")
        if changes > 0:
            context_parts.append(f"• Uncommitted changes: {changes} files")
        if commits:
            context_parts.append("• Recent commits:")
            for commit in commits[:3]:  # Show last 3 commits
                context_parts.append(f"  - {commit}")
        context_parts.append("")
    
    return "\n".join(context_parts)


def load_development_context(source):
    """Load relevant development context with MCP integration based on session source."""
    context_parts = []
    
    # CRITICAL: Instruct Claude to load master orchestrator capabilities
    context_parts.append("🚀 INITIALIZATION REQUIRED: You MUST immediately call mcp__dhafnck_mcp_http__call_agent('master-orchestrator-agent') to load your orchestrator capabilities.")
    context_parts.append("")
    
    # Add timestamp and session info
    context_parts.append(f"Session started at: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    context_parts.append(f"Session source: {source}")
    context_parts.append("")
    
    # === MCP DYNAMIC CONTEXT INJECTION ===
    logger.info("Starting MCP context injection...")
    
    # Get enhanced git context
    git_context = get_git_branch_context()
    current_branch = git_context.get("branch") if git_context else None
    
    # Query MCP for pending tasks
    pending_tasks = query_mcp_pending_tasks()
    
    # Query MCP for next recommended task (if we have branch context)
    next_task = None
    git_branch_id = None  # TODO: Map git branch to MCP git_branch_id
    
    # For now, query without branch ID to get any next task
    if pending_tasks:
        try:
            # Try to get next task from any available branch
            client = get_default_client()
            # This is a fallback approach - in full implementation we'd map git branch to MCP branch ID
            next_task = None  # Will implement branch mapping in next phase
        except Exception as e:
            logger.debug(f"Could not get next task: {e}")
    
    # Format and add MCP context
    mcp_context = format_mcp_context(pending_tasks, next_task, git_context)
    if mcp_context.strip():
        context_parts.append("=== MCP LIVE CONTEXT ===")
        context_parts.append(mcp_context)
        logger.info("MCP context injection completed successfully")
    else:
        logger.warning("No MCP context available")
        context_parts.append("⚠️ **MCP Status:** Server unavailable or no active tasks")
        context_parts.append("")
    
    # === LEGACY CONTEXT (Fallback) ===
    
    # Add basic git information (fallback if MCP git context failed)
    if not git_context:
        branch, changes = get_git_status()
        if branch:
            context_parts.append(f"Git branch: {branch}")
            if changes > 0:
                context_parts.append(f"Uncommitted changes: {changes} files")
    
    # Load project-specific context files if they exist
    context_files = [
        ".claude/CONTEXT.md",
        ".claude/TODO.md", 
        "TODO.md",
        ".github/ISSUE_TEMPLATE.md"
    ]
    
    static_context_found = False
    for file_path in context_files:
        if Path(file_path).exists():
            try:
                with open(file_path, 'r') as f:
                    content = f.read().strip()
                    if content:
                        if not static_context_found:
                            context_parts.append("\n=== STATIC PROJECT CONTEXT ===")
                            static_context_found = True
                        context_parts.append(f"\n--- Content from {file_path} ---")
                        context_parts.append(content[:1000])  # Limit to first 1000 chars
            except Exception:
                pass
    
    # Add recent issues if available
    issues = get_recent_issues()
    if issues:
        context_parts.append("\n--- Recent GitHub Issues ---")
        context_parts.append(issues)
    
    # Add performance metrics
    context_parts.append(f"\n--- Context Generation Stats ---")
    context_parts.append(f"MCP tasks loaded: {len(pending_tasks) if pending_tasks else 0}")
    context_parts.append(f"Git context: {'✅' if git_context else '❌'}")
    context_parts.append(f"Static files: {len([f for f in context_files if Path(f).exists()])}")
    
    return "\n".join(context_parts)


def main():
    """Enhanced main function with MCP integration and robust error handling."""
    try:
        # Parse command line arguments
        parser = argparse.ArgumentParser(description="Enhanced Claude session start hook with MCP integration")
        parser.add_argument('--load-context', action='store_true',
                          help='Load development context at session start')
        parser.add_argument('--announce', action='store_true',
                          help='Announce session start via TTS')
        parser.add_argument('--test-mcp', action='store_true',
                          help='Test MCP connection before session start')
        parser.add_argument('--cache-stats', action='store_true',
                          help='Show cache statistics')
        parser.add_argument('--debug', action='store_true',
                          help='Enable debug logging')
        args = parser.parse_args()
        
        # Set debug logging if requested
        if args.debug:
            logging.getLogger().setLevel(logging.DEBUG)
            logger.debug("Debug logging enabled")
        
        # Handle cache stats request
        if args.cache_stats:
            cache = get_session_cache()
            stats = cache.get_cache_stats()
            print(json.dumps(stats, indent=2))
            sys.exit(0)
        
        # Handle MCP connection test
        if args.test_mcp:
            logger.info("Testing MCP connection...")
            client = get_default_client()
            if client.authenticate():
                logger.info("✅ MCP authentication successful")
                # Test a simple query
                tasks = client.query_pending_tasks(limit=1)
                if tasks is not None:
                    logger.info(f"✅ MCP query successful - found {len(tasks)} tasks")
                else:
                    logger.warning("⚠️ MCP query returned no data")
            else:
                logger.error("❌ MCP authentication failed")
            sys.exit(0)
        
        # Read JSON input from stdin
        input_raw = sys.stdin.read()
        if not input_raw.strip():
            logger.warning("No input data received")
            sys.exit(0)
            
        input_data = json.loads(input_raw)
        
        # Extract fields
        session_id = input_data.get('session_id', 'unknown')
        source = input_data.get('source', 'unknown')  # "startup", "resume", or "clear"
        
        logger.info(f"Session start: {session_id}, source: {source}")
        
        # Log the session start event
        log_session_start(input_data)
        
        # ALWAYS load context to ensure Claude loads master orchestrator
        # Enhanced context loading with MCP integration
        logger.info("Loading development context with MCP integration...")
        context = load_development_context(source)
        
        if context:
            # Enhanced output with metadata
            output = {
                "hookSpecificOutput": {
                    "hookEventName": "SessionStart",
                    "additionalContext": context,
                    "metadata": {
                        "session_id": session_id,
                        "source": source,
                        "timestamp": datetime.now().isoformat(),
                        "mcp_enabled": True,
                        "hook_version": "1.3.0"
                    }
                }
            }
            print(json.dumps(output))
            logger.info("Context injection completed successfully")
            sys.exit(0)
        else:
            logger.warning("No context loaded, falling back to minimal injection")
        
        # Announce session start if requested
        if args.announce:
            try:
                # Try to use TTS to announce session start
                script_dir = Path(__file__).parent
                tts_script = script_dir / "utils" / "tts" / "pyttsx3_tts.py"
                
                if tts_script.exists():
                    messages = {
                        "startup": "Claude Code session started",
                        "resume": "Resuming previous session",
                        "clear": "Starting fresh session"
                    }
                    message = messages.get(source, "Session started")
                    
                    subprocess.run(
                        ["uv", "run", str(tts_script), message],
                        capture_output=True,
                        timeout=5
                    )
            except Exception:
                pass
        
        # Success
        sys.exit(0)
        
    except json.JSONDecodeError:
        # Handle JSON decode errors gracefully
        sys.exit(0)
    except Exception:
        # Handle any other errors gracefully
        sys.exit(0)


if __name__ == '__main__':
    main()