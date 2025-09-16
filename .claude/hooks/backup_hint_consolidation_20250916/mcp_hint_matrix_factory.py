#!/usr/bin/env python3
"""
MCP Hint Matrix Factory - Loads hint configuration from YAML files.

This module provides a factory pattern for loading and managing hint
configurations for MCP operations from YAML configuration files.
"""

import json
import yaml
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, List, Optional, Tuple, Any


class HintConfigLoader:
    """Loads hint configurations from YAML files."""

    def __init__(self, config_dir: Optional[Path] = None):
        """Initialize the configuration loader."""
        if config_dir is None:
            config_dir = Path(__file__).parent.parent / 'config'
        self.config_dir = config_dir
        self._cache = {}

    def load_config(self, config_name: str) -> Optional[Dict]:
        """Load a specific configuration file."""
        if config_name in self._cache:
            return self._cache[config_name]

        config_path = self.config_dir / f"{config_name}.yaml"
        if not config_path.exists():
            return None

        try:
            with open(config_path, 'r') as f:
                config = yaml.safe_load(f)
                self._cache[config_name] = config
                return config
        except Exception:
            return None

    def get_hint_matrix_config(self) -> Optional[Dict]:
        """Load the main hint matrix configuration."""
        return self.load_config('mcp_hint_matrix_config')


class MCPHintMatrixFactory:
    """Factory for creating hint matrix with configuration from YAML."""

    def __init__(self, config_loader: Optional[HintConfigLoader] = None):
        """Initialize the factory with a configuration loader."""
        self.config_loader = config_loader or HintConfigLoader()
        self.workflow_state_file = Path.cwd() / '.claude' / 'hooks' / 'data' / 'workflow_state.json'
        self.workflow_state_file.parent.mkdir(parents=True, exist_ok=True)
        self.load_workflow_state()
        self.load_configuration()

    def load_workflow_state(self):
        """Load workflow state to track task progression."""
        if self.workflow_state_file.exists():
            try:
                with open(self.workflow_state_file, 'r') as f:
                    self.workflow_state = json.load(f)
            except:
                self.workflow_state = {}
        else:
            self.workflow_state = {}

    def save_workflow_state(self):
        """Save workflow state to file."""
        with open(self.workflow_state_file, 'w') as f:
            json.dump(self.workflow_state, f, indent=2)

    def load_configuration(self):
        """Load hint configuration from YAML."""
        config = self.config_loader.get_hint_matrix_config()
        if config:
            self.enabled = config.get('enabled', True)
            self.version = config.get('version', '1.0')
            # Remove the top-level tools and get their configurations directly
            self.tool_configs = {}
            for key, value in config.items():
                if key not in ['version', 'enabled', 'hint_headers', 'complex_task_indicators', 'parallel_indicators']:
                    self.tool_configs[key] = value
            self.hint_headers = config.get('hint_headers', {})
            self.complex_task_indicators = config.get('complex_task_indicators', [])
            self.parallel_indicators = config.get('parallel_indicators', [])
        else:
            # Fallback to empty configuration
            self.enabled = False
            self.tool_configs = {}
            self.hint_headers = {}
            self.complex_task_indicators = []
            self.parallel_indicators = []

    def get_hints(self, tool_name: str, tool_input: Dict[str, Any]) -> Optional[str]:
        """
        Generate contextual hints based on tool, action, and parameters.

        Args:
            tool_name: The MCP tool being called
            tool_input: Parameters passed to the tool

        Returns:
            Optional[str]: Formatted hint message or None
        """
        if not self.enabled:
            return None

        # Get tool configuration
        if tool_name not in self.tool_configs:
            return None

        tool_config = self.tool_configs[tool_name]

        # Get action (default to 'default' for tools without action)
        action = tool_input.get('action', 'default')

        # Get action configuration
        if action not in tool_config:
            return f"❓ UNKNOWN ACTION: '{action}' is not a valid action for {tool_name}"

        action_config = tool_config[action]
        hints = []

        # Track workflow state
        self._update_workflow_state(tool_name, action, tool_input)

        # Check required fields
        required = action_config.get('required_fields', [])
        field_hints = action_config.get('field_hints', {})

        for field in required:
            if not tool_input.get(field):
                hint_key = f"missing_{field}"
                if hint_key in field_hints:
                    hints.append(field_hints[hint_key])
                else:
                    hints.append(f"🚨 MISSING REQUIRED: '{field}' is required for {action}")

        # Check recommended fields
        recommended = action_config.get('recommended_fields', [])
        missing_recommended = []
        for field in recommended:
            if not tool_input.get(field):
                hint_key = f"missing_{field}"
                if hint_key in field_hints:
                    hints.append(field_hints[hint_key])
                else:
                    missing_recommended.append(field)

        if missing_recommended:
            hints.append(f"💡 CONSIDER ADDING: {', '.join(missing_recommended)}")

        # Add contextual hints based on workflow state
        context_hints = self._get_contextual_hints(tool_name, action, tool_input, action_config)
        hints.extend(context_hints)

        # Add workflow hints if applicable
        workflow_hints = action_config.get('workflow_hints', [])
        if workflow_hints and len(hints) < 5:
            hints.append("\n📋 WORKFLOW TIPS:")
            for tip in workflow_hints[:2]:  # Limit to 2 tips
                hints.append(f"  • {tip}")

        # Format and return hints
        if hints:
            header = self._get_hint_header(tool_name, action)
            return f"<system-reminder>\n{header}\n" + "\n".join(hints) + "\n</system-reminder>"

        return None

    def _update_workflow_state(self, tool_name: str, action: str, tool_input: Dict):
        """Update workflow state based on current operation."""
        timestamp = datetime.now().isoformat()

        # Track task operations
        if 'manage_task' in tool_name:
            task_id = tool_input.get('task_id')
            if action == 'create':
                # Store temporary reference until we get real task_id
                temp_id = f"temp_{timestamp}"
                self.workflow_state[temp_id] = {
                    'title': tool_input.get('title'),
                    'status': 'created',
                    'created_at': timestamp,
                    'last_update': None,
                    'has_updates': False,
                    'has_subtasks': False
                }
            elif task_id:
                if task_id not in self.workflow_state:
                    self.workflow_state[task_id] = {}

                if action == 'update':
                    self.workflow_state[task_id]['last_update'] = timestamp
                    self.workflow_state[task_id]['has_updates'] = True
                elif action == 'complete':
                    self.workflow_state[task_id]['completed_at'] = timestamp
                    self.workflow_state[task_id]['status'] = 'completed'

        # Track subtask operations
        elif 'manage_subtask' in tool_name:
            parent_id = tool_input.get('task_id')
            if parent_id and parent_id in self.workflow_state:
                self.workflow_state[parent_id]['has_subtasks'] = True

        self.save_workflow_state()

    def _get_contextual_hints(self, tool_name: str, action: str, tool_input: Dict, action_config: Dict) -> List[str]:
        """Generate contextual hints based on workflow state and configuration."""
        hints = []
        contextual_hints = action_config.get('contextual_hints', {})

        # Task-specific contextual hints
        if 'manage_task' in tool_name:
            task_id = tool_input.get('task_id')

            if action == 'create':
                # Check for complex task indicators
                title = tool_input.get('title', '').lower()
                if any(word in title for word in self.complex_task_indicators):
                    if 'complex_task' in contextual_hints:
                        hints.append(contextual_hints['complex_task'])

                # Check for parallel opportunities
                if any(word in title for word in self.parallel_indicators):
                    if 'parallel_opportunity' in contextual_hints:
                        hints.append(contextual_hints['parallel_opportunity'])

            elif action == 'update' and task_id:
                # Check time since last update
                if task_id in self.workflow_state:
                    last_update = self.workflow_state[task_id].get('last_update')
                    if last_update:
                        time_diff = datetime.now() - datetime.fromisoformat(last_update)
                        if time_diff > timedelta(minutes=30):
                            if 'long_time_no_update' in action_config.get('field_hints', {}):
                                hints.append(action_config['field_hints']['long_time_no_update'])

            elif action == 'complete' and task_id:
                # Check if task was updated
                if task_id in self.workflow_state:
                    if not self.workflow_state[task_id].get('has_updates'):
                        if 'no_prior_updates' in action_config.get('field_hints', {}):
                            hints.append(action_config['field_hints']['no_prior_updates'])
                    if self.workflow_state[task_id].get('has_subtasks'):
                        hints.append("📋 SUBTASK CHECK: Ensure all subtasks are complete")

        return hints

    def _get_hint_header(self, tool_name: str, action: str) -> str:
        """Generate appropriate header for hint section from configuration."""
        # Extract base tool name
        base_tool = tool_name.split('__')[-1]

        # Look for configured header
        if base_tool in self.hint_headers:
            if action in self.hint_headers[base_tool]:
                return self.hint_headers[base_tool][action]

        # Fallback to generic header
        return f"💡 {base_tool.upper()} - {action.upper()} HINTS"

    def get_post_action_hints(self, tool_name: str, tool_input: Dict, tool_result: Any) -> Optional[str]:
        """
        Generate post-action hints based on tool result.

        This is a placeholder for post-action hint generation.
        Can be extended to provide context-aware hints after tool execution.
        """
        # This would load from a post-action hints configuration
        # For now, return None as this is handled separately
        return None


def inject_matrix_hints(tool_name: str, tool_input: Dict) -> Optional[str]:
    """
    Main entry point for matrix-based hint injection using factory pattern.

    Args:
        tool_name: Name of the MCP tool being called
        tool_input: Parameters passed to the tool

    Returns:
        Optional[str]: Formatted hint message or None
    """
    if not tool_name.startswith('mcp__dhafnck_mcp_http'):
        return None

    factory = MCPHintMatrixFactory()
    return factory.get_hints(tool_name, tool_input)


# For backward compatibility, also expose the factory class
MCPHintMatrix = MCPHintMatrixFactory


if __name__ == "__main__":
    # Test cases
    test_cases = [
        {
            "tool_name": "mcp__dhafnck_mcp_http__manage_task",
            "tool_input": {
                "action": "create",
                "title": "Implement full authentication system"
                # Missing: assignees, git_branch_id, details
            }
        },
        {
            "tool_name": "mcp__dhafnck_mcp_http__manage_task",
            "tool_input": {
                "action": "update",
                "task_id": "task_123",
                "status": "in_progress"
                # Missing: progress_notes
            }
        },
        {
            "tool_name": "mcp__dhafnck_mcp_http__manage_task",
            "tool_input": {
                "action": "complete",
                "task_id": "task_123"
                # Missing: completion_summary, testing_notes
            }
        },
        {
            "tool_name": "mcp__dhafnck_mcp_http__manage_subtask",
            "tool_input": {
                "action": "create",
                "task_id": "parent_123",
                "title": "Design database schema"
            }
        },
        {
            "tool_name": "mcp__dhafnck_mcp_http__call_agent",
            "tool_input": {}  # Missing name_agent
        }
    ]

    for test in test_cases:
        print(f"\nTesting: {test['tool_name']} - {test['tool_input'].get('action', 'default')}")
        print("-" * 60)
        hint = inject_matrix_hints(test['tool_name'], test['tool_input'])
        if hint:
            print(hint)
        else:
            print("No hints generated")