#!/usr/bin/env python3
"""
MCP Post-Action Hints - Provides reminders AFTER MCP operations are completed.

This module generates contextual reminders based on what was just done,
helping AI agents remember next steps and best practices.

Now uses centralized YAML configuration instead of hardcoded messages.
"""

import json
import sys
from datetime import datetime
from pathlib import Path
from typing import Dict, Optional, Any, List

# Import configuration factory
from .config_factory import get_config_factory

class MCPPostActionHints:
    """Generate post-action reminders for MCP operations using YAML configuration."""

    def __init__(self):
        """Initialize the post-action hint system."""
        self.task_tracking_file = Path.cwd() / '.claude' / 'hooks' / 'data' / 'task_tracking.json'
        self.task_tracking_file.parent.mkdir(parents=True, exist_ok=True)
        self.load_task_tracking()
        self.load_config()

    def load_config(self):
        """Load configuration from YAML file using ConfigFactory."""
        factory = get_config_factory()
        self.config = factory._get_config('mcp_post_action_hints')
        if not self.config:
            # Fallback to empty config
            self.config = {
                'enabled': True,
                'headers': {},
                'task_hints': {},
                'subtask_hints': {},
                'context_hints': {},
                'project_hints': {},
                'branch_hints': {},
                'agent_hints': {},
                'formatting': {'max_hints': 5, 'system_reminder_wrapper': True}
            }

    def load_task_tracking(self):
        """Load task tracking data."""
        if self.task_tracking_file.exists():
            try:
                with open(self.task_tracking_file, 'r') as f:
                    self.task_tracking = json.load(f)
            except:
                self.task_tracking = {}
        else:
            self.task_tracking = {}

    def save_task_tracking(self):
        """Save task tracking data."""
        with open(self.task_tracking_file, 'w') as f:
            json.dump(self.task_tracking, f, indent=2)

    def generate_hints(self, tool_name: str, tool_input: Dict[str, Any], result: Any = None) -> Optional[str]:
        """
        Generate post-action hints based on what was just done.

        Args:
            tool_name: The MCP tool that was just used
            tool_input: Parameters that were passed to the tool
            result: The result returned by the tool (if available)

        Returns:
            Optional[str]: Formatted reminder message or None
        """
        if not self.config.get('enabled', True):
            return None

        hints = []

        # Extract action from tool_input
        action = tool_input.get('action', 'default')

        # Check if operation was successful or failed
        is_success = True
        if result and isinstance(result, dict):
            is_success = result.get('success', True)
            if not is_success:
                # Don't provide hints for failed operations
                return None

        # Only generate hints for successful operations
        if tool_name == "mcp__dhafnck_mcp_http__manage_task":
            hints.extend(self._task_post_hints(action, tool_input, result))
        elif tool_name == "mcp__dhafnck_mcp_http__manage_subtask":
            hints.extend(self._subtask_post_hints(action, tool_input, result))
        elif tool_name == "mcp__dhafnck_mcp_http__manage_context":
            hints.extend(self._context_post_hints(action, tool_input, result))
        elif tool_name == "mcp__dhafnck_mcp_http__manage_project":
            hints.extend(self._project_post_hints(action, tool_input, result))
        elif tool_name == "mcp__dhafnck_mcp_http__manage_git_branch":
            hints.extend(self._branch_post_hints(action, tool_input, result))
        elif tool_name == "mcp__dhafnck_mcp_http__call_agent":
            hints.extend(self._agent_post_hints(tool_input, result))

        # Format and return hints if any
        if hints:
            return self._format_hints(hints, tool_name, action)

        return None

    def _task_post_hints(self, action: str, tool_input: Dict, result: Any) -> List[str]:
        """Generate post-action hints for task operations."""
        hints = []
        task_config = self.config.get('task_hints', {})
        action_config = task_config.get(action, {})

        if action == "create":
            # Track the created task
            if result and isinstance(result, dict):
                task_id = result.get('task', {}).get('id')
                if task_id:
                    self.task_tracking[task_id] = {
                        'created_at': datetime.now().isoformat(),
                        'title': tool_input.get('title'),
                        'has_been_delegated': False,
                        'has_been_updated': False
                    }
                    self.save_task_tracking()

            # Check for missing details
            if not tool_input.get('details'):
                hints.append(action_config.get('missing_details', 'Consider adding task details'))

            # Check for assignees
            if not tool_input.get('assignees'):
                hints.append(action_config.get('no_assignees', 'Add assignees before delegating'))
            else:
                hints.append(action_config.get('has_assignees', 'Ready to delegate to agent'))

            # Check if task seems complex
            title = tool_input.get('title', '').lower()
            complex_keywords = action_config.get('complex_keywords', [])
            if any(word in title for word in complex_keywords):
                hints.append(action_config.get('complex_task', 'Consider creating subtasks'))

        elif action == "update":
            task_id = tool_input.get('task_id')
            if task_id and task_id in self.task_tracking:
                self.task_tracking[task_id]['has_been_updated'] = True
                self.task_tracking[task_id]['last_update'] = datetime.now().isoformat()
                self.save_task_tracking()

            # Check for progress notes
            if not tool_input.get('progress_notes') and not tool_input.get('details'):
                hints.append(action_config.get('no_progress_notes', 'Consider adding progress notes'))

            # Check for blocked status
            if tool_input.get('status') == 'blocked':
                hints.append(action_config.get('blocked_status', 'Consider creating debug task'))

            hints.append(action_config.get('general_reminder', 'Continue updating progress'))

        elif action == "complete":
            task_id = tool_input.get('task_id')
            if task_id and task_id in self.task_tracking:
                if not self.task_tracking[task_id].get('has_been_updated'):
                    hints.append(action_config.get('no_updates_pattern', 'Task completed without updates'))

            # Check for completion summary
            if not tool_input.get('completion_summary'):
                hints.append(action_config.get('missing_completion_summary', 'Add completion summary'))

            # Check for testing notes
            if not tool_input.get('testing_notes'):
                hints.append(action_config.get('missing_testing_notes', 'Add testing notes'))

            hints.append(action_config.get('next_context', 'Update context with learnings'))
            hints.append(action_config.get('continue_work', 'Find next task to work on'))

        elif action in ["get", "list"]:
            hints.append(action_config.get('review_reminder', 'Review task status'))

        elif action == "next":
            hints.append(action_config.get('selected_reminder', 'Update status when starting'))

        return hints

    def _subtask_post_hints(self, action: str, tool_input: Dict, result: Any) -> List[str]:
        """Generate post-action hints for subtask operations."""
        hints = []
        subtask_config = self.config.get('subtask_hints', {})
        action_config = subtask_config.get(action, {})

        if action == "create":
            if not tool_input.get('assignees'):
                hints.append(action_config.get('inherited_assignees', 'Subtask inherited assignees'))
            hints.append(action_config.get('progress_tip', 'Use progress_percentage in updates'))

        elif action == "update":
            progress = tool_input.get('progress_percentage')
            if progress is not None:
                if progress < 100:
                    hint_template = action_config.get('progress_incomplete', '{progress}% complete')
                    hints.append(hint_template.format(progress=progress))
                else:
                    hints.append(action_config.get('progress_complete', 'Ready to complete subtask'))

        elif action == "complete":
            if tool_input.get('insights_found'):
                hints.append(action_config.get('insights_documented', 'Insights documented'))
            hints.append(action_config.get('parent_check', 'Review parent task'))

        return hints

    def _context_post_hints(self, action: str, tool_input: Dict, result: Any) -> List[str]:
        """Generate post-action hints for context operations."""
        hints = []
        context_config = self.config.get('context_hints', {})
        action_config = context_config.get(action, {})

        if action == "update":
            level = tool_input.get('level')
            level_hints = {
                'task': action_config.get('task_level', 'Task context updated'),
                'branch': action_config.get('branch_level', 'Branch context updated'),
                'project': action_config.get('project_level', 'Project context updated')
            }
            if level in level_hints:
                hints.append(level_hints[level])

            if tool_input.get('propagate_changes'):
                hints.append(action_config.get('propagated', 'Changes cascaded'))

        elif action == "add_insight":
            hints.append(action_config.get('insight_added', 'Insight added'))
            hints.append(action_config.get('share_suggestion', 'Consider sharing insights'))

        return hints

    def _project_post_hints(self, action: str, tool_input: Dict, result: Any) -> List[str]:
        """Generate post-action hints for project operations."""
        hints = []
        project_config = self.config.get('project_hints', {})
        action_config = project_config.get(action, {})

        if action == "create":
            hints.append(action_config.get('next_branches', 'Create git branches next'))
            hints.append(action_config.get('setup_tasks', 'Create setup tasks'))

        elif action == "project_health_check":
            hints.append(action_config.get('address_issues', 'Address health issues'))
            hints.append(action_config.get('use_metrics', 'Use health metrics'))

        return hints

    def _branch_post_hints(self, action: str, tool_input: Dict, result: Any) -> List[str]:
        """Generate post-action hints for git branch operations."""
        hints = []
        branch_config = self.config.get('branch_hints', {})
        action_config = branch_config.get(action, {})

        if action == "create":
            hints.append(action_config.get('create_tasks', 'Create tasks for branch'))
            hints.append(action_config.get('assign_agents', 'Assign specialized agents'))

        elif action == "assign_agent":
            hints.append(action_config.get('agent_ready', 'Agent ready for work'))

        return hints

    def _agent_post_hints(self, tool_input: Dict, result: Any) -> List[str]:
        """Generate post-action hints for agent operations."""
        hints = []
        agent_config = self.config.get('agent_hints', {})

        agent_name = tool_input.get('name_agent')
        if agent_name == 'master-orchestrator-agent':
            hints.append(agent_config.get('master_orchestrator', {}).get('coordinator_loaded', 'Orchestrator loaded'))
            hints.append(agent_config.get('master_orchestrator', {}).get('start_work', 'Start coordinating work'))
        else:
            specialized_config = agent_config.get('specialized_agent', {})
            hint_template = specialized_config.get('agent_loaded', '{agent_name} loaded')
            hints.append(hint_template.format(agent_name=agent_name.upper()))

        general_config = agent_config.get('general', {})
        hints.append(general_config.get('one_time_load', 'One-time load complete'))

        return hints

    def _format_hints(self, hints: List[str], tool_name: str, action: str) -> str:
        """Format hints into a system reminder."""
        formatting_config = self.config.get('formatting', {})
        max_hints = formatting_config.get('max_hints', 5)
        use_wrapper = formatting_config.get('system_reminder_wrapper', True)

        # Get header from config
        headers_config = self.config.get('headers', {})
        base_tool = tool_name.split('__')[-1]
        header_key = f"{base_tool}_{action}"
        header = headers_config.get(header_key, f"💡 {action.upper()} COMPLETE - REMINDERS")

        # Build formatted message
        message_parts = [f"{header}:"]

        # Limit hints
        limited_hints = hints[:max_hints]
        for hint in limited_hints:
            message_parts.append(hint)

        message = '\n'.join(message_parts)

        if use_wrapper:
            message = f"<system-reminder>\n{message}\n</system-reminder>"

        return message


def generate_post_action_hints(tool_name: str, tool_input: Dict, result: Any = None) -> Optional[str]:
    """
    Main entry point for post-action hint generation.

    Args:
        tool_name: Name of the MCP tool that was executed
        tool_input: Parameters that were passed to the tool
        result: Result returned by the tool (if available)

    Returns:
        Optional[str]: Formatted reminder message or None
    """
    if not tool_name.startswith('mcp__dhafnck_mcp_http'):
        return None

    hint_generator = MCPPostActionHints()
    return hint_generator.generate_hints(tool_name, tool_input, result)


if __name__ == "__main__":
    # Test the configuration loading
    hint_generator = MCPPostActionHints()
    print("Configuration loaded successfully!")
    print(f"Config enabled: {hint_generator.config.get('enabled')}")
    print(f"Available hint categories: {list(hint_generator.config.keys())}")