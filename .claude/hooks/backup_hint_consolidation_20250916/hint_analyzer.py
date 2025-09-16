#!/usr/bin/env python3
"""
Hint Analyzer for Tool Usage
Analyzes tool usage patterns and provides contextual hints to AI agents
"""

import yaml
import json
from pathlib import Path
from typing import Dict, Any, List, Optional
from datetime import datetime
import re

# Import task tracker for context
try:
    from .task_tracker import get_task_tracker
except ImportError:
    get_task_tracker = None

# Import session tracker
try:
    from .session_tracker import is_file_in_session
except ImportError:
    is_file_in_session = None

# Import agent state manager
try:
    from .agent_state_manager import get_current_agent
except ImportError:
    get_current_agent = None


class HintAnalyzer:
    """Analyzes tool usage and provides contextual hints."""

    def __init__(self, session_id: str = None):
        """Initialize hint analyzer with session context."""
        self.session_id = session_id
        self.config_dir = Path(__file__).parent.parent / "config"
        self.pre_hints_file = self.config_dir / "__hint_message__pre_tool_use.yaml"
        self.post_hints_file = self.config_dir / "__hint_message__post_tool_use.yaml"
        self.config_file = self.config_dir / "__hint_message__config.yaml"

        # Load configurations
        self.pre_hints = self._load_config(self.pre_hints_file)
        self.post_hints = self._load_config(self.post_hints_file)
        self.config = self._load_config(self.config_file)

        # Track tool usage history for pattern detection
        self.tool_history = []

        # Tool call counter for task status display
        self.tool_call_count = 0

    def _load_config(self, file_path: Path) -> Dict[str, Any]:
        """Load YAML configuration file."""
        if not file_path.exists():
            return {"enabled": False}

        try:
            with open(file_path, 'r') as f:
                return yaml.safe_load(f) or {"enabled": False}
        except Exception as e:
            print(f"Error loading {file_path}: {e}")
            return {"enabled": False}

    def analyze_pre_tool(self, tool_name: str, parameters: Dict[str, Any]) -> List[str]:
        """Analyze tool usage before execution and return relevant hints."""
        if not self.pre_hints.get("enabled", False):
            return []

        hints = []

        # Increment tool call counter
        self.tool_call_count += 1

        # Check if we should display task status
        if self.config.get("enabled", False):
            task_status_hints = self._check_task_status_display()
            if task_status_hints:
                hints.extend(task_status_hints)

        # Check global hints
        hints.extend(self._check_global_hints(tool_name, parameters))

        # Check tool-specific hints
        hints.extend(self._check_tool_hints(tool_name, parameters, self.pre_hints))

        # Check workflow hints
        hints.extend(self._check_workflow_hints(tool_name, parameters))

        # Check context rules
        hints.extend(self._check_context_rules(tool_name, parameters))

        return hints

    def analyze_post_tool(self, tool_name: str, parameters: Dict[str, Any],
                         result: Any) -> List[str]:
        """Analyze tool execution result and provide follow-up hints."""
        if not self.post_hints.get("enabled", False):
            return []

        hints = []

        # Record tool in history
        self.tool_history.append({
            "tool": tool_name,
            "parameters": parameters,
            "timestamp": datetime.now().isoformat()
        })

        # Check tool-specific post hints
        hints.extend(self._check_tool_hints(tool_name, parameters, self.post_hints, result))

        # Check workflow completion
        hints.extend(self._check_workflow_completion())

        # Check success patterns
        hints.extend(self._check_success_patterns())

        return hints

    def _check_task_status_display(self) -> List[str]:
        """Check if task status should be displayed based on configuration."""
        hints = []

        # Get task tracking configuration
        task_config = self.config.get("task_tracking", {})
        if not task_config.get("enabled", True):
            return hints

        # Get display interval
        display_config = self.config.get("display", {})
        interval = display_config.get("task_status_interval", 5)

        # Check if it's time to display task status
        if self.tool_call_count % interval == 0:
            if get_task_tracker:
                try:
                    tracker = get_task_tracker(self.session_id)
                    summary = tracker.get_task_summary()

                    # Format task status message
                    summary_format = task_config.get("summary_format", "")
                    if summary_format:
                        status_msg = summary_format.format(
                            call_count=self.tool_call_count,
                            total_tasks=summary['total'],
                            in_progress=summary['status_counts'].get('in_progress', 0),
                            pending=summary['status_counts'].get('pending', 0),
                            blocked=summary['status_counts'].get('blocked', 0),
                            current_task=summary['current_task']['title'] if summary['current_task'] else "None"
                        )
                        hints.append(status_msg)

                    # Check for warnings
                    warnings = task_config.get("warnings", {})

                    # No tasks warning
                    if summary['total'] == 0 and display_config.get("show_no_task_warning", True):
                        current_agent = get_current_agent(self.session_id) if get_current_agent else None
                        if current_agent == "master-orchestrator-agent":
                            hints.append(warnings.get("no_tasks", ""))

                    # Blocked tasks warning
                    if summary['has_blocked']:
                        blocked_count = summary['status_counts'].get('blocked', 0)
                        if blocked_count > 0:
                            blocked_msg = warnings.get("blocked_tasks", "")
                            if blocked_msg:
                                hints.append(blocked_msg.format(count=blocked_count))

                except Exception:
                    pass  # Don't fail on task status display

        return hints

    def _check_global_hints(self, tool_name: str, parameters: Dict[str, Any]) -> List[str]:
        """Check global hints that apply to all tools."""
        hints = []
        global_hints = self.pre_hints.get("global_hints", {})

        for hint_name, hint_config in global_hints.items():
            if self._evaluate_condition(hint_config.get("condition", ""), tool_name, parameters):
                hints.append(hint_config.get("message", ""))

        return hints

    def _check_tool_hints(self, tool_name: str, parameters: Dict[str, Any],
                         config: Dict, result: Any = None) -> List[str]:
        """Check tool-specific hints."""
        hints = []
        tool_hints = config.get("tool_hints", {}).get(tool_name, {})

        # Check default hint
        if "default" in tool_hints:
            hints.append(tool_hints["default"].get("message", ""))

        # Check action-specific hints (for MCP tasks)
        action = parameters.get("action", "")
        if action and action in tool_hints:
            hint_data = tool_hints[action]
            if isinstance(hint_data, dict):
                if result and "success" in hint_data:
                    hints.append(hint_data["success"].get("message", ""))
                elif "message" in hint_data:
                    hints.append(hint_data["message"])

        # Check pattern-based hints
        patterns = tool_hints.get("patterns", [])
        for pattern_config in patterns:
            if self._match_pattern(pattern_config.get("pattern", ""), tool_name, parameters):
                hints.append(pattern_config.get("message", ""))

        return hints

    def _check_workflow_hints(self, tool_name: str, parameters: Dict[str, Any]) -> List[str]:
        """Check workflow-specific hints."""
        hints = []
        workflow_hints = self.pre_hints.get("workflow_hints", {})

        for workflow_name, workflow_config in workflow_hints.items():
            triggers = workflow_config.get("triggers", [])
            for trigger in triggers:
                if self._match_trigger(trigger, tool_name, parameters):
                    hints.append(workflow_config.get("message", ""))
                    break

        return hints

    def _check_context_rules(self, tool_name: str, parameters: Dict[str, Any]) -> List[str]:
        """Check context-specific rules based on current agent."""
        hints = []

        # Get current agent
        current_agent = get_current_agent(self.session_id) if get_current_agent else None
        if not current_agent:
            return hints

        context_rules = self.pre_hints.get("context_rules", [])
        for rule in context_rules:
            if current_agent in rule.get("applies_to", []):
                for check in rule.get("checks", []):
                    hint = self._perform_check(check, tool_name, parameters)
                    if hint:
                        hints.append(hint)

        return hints

    def _check_workflow_completion(self) -> List[str]:
        """Check if a workflow was completed successfully."""
        hints = []

        if len(self.tool_history) < 2:
            return hints

        completion_hints = self.post_hints.get("workflow_completion", {})

        # Check recent tool sequence
        recent_tools = [h["tool"] for h in self.tool_history[-3:]]

        for workflow_name, workflow_config in completion_hints.items():
            condition = workflow_config.get("condition", "")
            if self._evaluate_workflow_condition(condition, recent_tools):
                hints.append(workflow_config.get("message", ""))

        return hints

    def _check_success_patterns(self) -> List[str]:
        """Check if tool usage matches success patterns."""
        hints = []

        if len(self.tool_history) < 2:
            return hints

        success_patterns = self.post_hints.get("success_patterns", {})

        for pattern_name, pattern_config in success_patterns.items():
            sequence = pattern_config.get("sequence", [])
            if self._match_sequence(sequence):
                hints.append(pattern_config.get("message", ""))

        return hints

    def _evaluate_condition(self, condition: str, tool_name: str, parameters: Dict[str, Any]) -> bool:
        """Evaluate a condition string."""
        if not condition:
            return False

        # Special condition checks
        if condition == "no_active_tasks_and_master_orchestrator":
            if get_task_tracker and get_current_agent:
                tracker = get_task_tracker(self.session_id)
                summary = tracker.get_task_summary()
                current_agent = get_current_agent(self.session_id)
                return summary['total'] == 0 and current_agent == "master-orchestrator-agent"

        elif condition == "modifying_important_file":
            file_path = parameters.get("file_path", "")
            if file_path:
                doc_path = Path("ai_docs/_absolute_docs") / Path(file_path).relative_to("/")
                return doc_path.with_suffix(".md").exists()

        return False

    def _match_pattern(self, pattern: str, tool_name: str, parameters: Dict[str, Any]) -> bool:
        """Match a pattern against tool usage."""
        if pattern == "no_task_id_in_prompt":
            return tool_name == "Task" and "task_id" not in parameters.get("prompt", "")

        elif pattern == "passing_full_context":
            return tool_name == "Task" and len(parameters.get("prompt", "")) > 500

        elif pattern == "root_directory":
            file_path = parameters.get("file_path", "")
            return file_path and "/" not in file_path.strip("/")

        elif pattern == "test_file":
            file_path = parameters.get("file_path", "")
            return any(x in file_path.lower() for x in ["test", "spec", "__test__"])

        elif pattern == "documentation":
            file_path = parameters.get("file_path", "")
            return file_path.endswith(".md")

        elif pattern == "not_read_yet":
            if is_file_in_session:
                file_path = parameters.get("file_path", "")
                return not is_file_in_session(file_path, self.session_id)

        elif pattern == "rm_command":
            command = parameters.get("command", "")
            return "rm " in command or "rm -" in command

        elif pattern == "find_command":
            command = parameters.get("command", "")
            return command.startswith("find ")

        elif pattern == "cat_command":
            command = parameters.get("command", "")
            return command.startswith("cat ")

        return False

    def _match_trigger(self, trigger: str, tool_name: str, parameters: Dict[str, Any]) -> bool:
        """Match a workflow trigger."""
        if trigger == "Task tool with no prior manage_task":
            if tool_name == "Task" and len(self.tool_history) > 0:
                # Check if manage_task was called recently
                recent = self.tool_history[-5:] if len(self.tool_history) >= 5 else self.tool_history
                has_manage_task = any("manage_task" in h["tool"] for h in recent)
                return not has_manage_task

        elif trigger == "Edit/Write without Read":
            if tool_name in ["Edit", "Write", "MultiEdit"]:
                file_path = parameters.get("file_path", "")
                # Check if file was read in recent history
                for h in self.tool_history[-10:]:
                    if h["tool"] == "Read" and h["parameters"].get("file_path") == file_path:
                        return False
                return True

        elif trigger == "Creating test files":
            return tool_name == "Write" and self._match_pattern("test_file", tool_name, parameters)

        return False

    def _perform_check(self, check: str, tool_name: str, parameters: Dict[str, Any]) -> Optional[str]:
        """Perform a specific check and return hint if needed."""
        if check == "no_tasks_before_delegation":
            if tool_name == "Task" and get_task_tracker:
                tracker = get_task_tracker(self.session_id)
                if tracker.get_task_summary()['total'] == 0:
                    return "WARNING: No MCP tasks exist! Create task before delegating."

        elif check == "task_id_in_delegation":
            if tool_name == "Task" and "task_id" not in parameters.get("prompt", ""):
                return "WARNING: Missing task_id in delegation prompt!"

        return None

    def _evaluate_workflow_condition(self, condition: str, recent_tools: List[str]) -> bool:
        """Evaluate workflow completion condition."""
        if condition == "task_created_and_delegated":
            return "mcp__dhafnck_mcp_http__manage_task" in recent_tools and "Task" in recent_tools

        elif condition == "file_read_and_edited":
            return "Read" in recent_tools and "Edit" in recent_tools

        elif condition == "test_file_created":
            for h in self.tool_history[-3:]:
                if h["tool"] == "Write" and self._match_pattern("test_file", h["tool"], h["parameters"]):
                    return True

        return False

    def _match_sequence(self, sequence: List[Dict]) -> bool:
        """Check if recent tool history matches a sequence."""
        if len(self.tool_history) < len(sequence):
            return False

        recent = self.tool_history[-len(sequence):]

        for i, step in enumerate(sequence):
            tool_match = recent[i]["tool"] == step.get("tool", "")

            # Check additional conditions
            if "action" in step:
                action_match = recent[i]["parameters"].get("action") == step["action"]
                if not action_match:
                    return False

            if "path_contains" in step:
                path = recent[i]["parameters"].get("file_path", "")
                if step["path_contains"] not in path:
                    return False

            if "command_contains" in step:
                command = recent[i]["parameters"].get("command", "")
                if step["command_contains"] not in command:
                    return False

            if not tool_match:
                return False

        return True

    def format_hints(self, hints: List[str], severity: str = "medium") -> str:
        """Format hints for display with appropriate styling."""
        if not hints:
            return ""

        severity_config = self.pre_hints.get("severity_levels", {}).get(severity, {})
        prefix = severity_config.get("prefix", "INFO:")

        formatted = []
        for hint in hints:
            if hint:
                # Clean up extra whitespace
                hint = " ".join(hint.split())
                formatted.append(f"{prefix} {hint}")

        return "\n".join(formatted)


# Singleton instance
_analyzer_instance = None

def get_hint_analyzer(session_id: str = None) -> HintAnalyzer:
    """Get or create hint analyzer instance."""
    global _analyzer_instance
    if _analyzer_instance is None or (session_id and _analyzer_instance.session_id != session_id):
        _analyzer_instance = HintAnalyzer(session_id)
    return _analyzer_instance


def analyze_and_hint(tool_name: str, parameters: Dict[str, Any],
                    session_id: str = None, phase: str = "pre") -> str:
    """Convenience function to analyze tool usage and return formatted hints."""
    analyzer = get_hint_analyzer(session_id)

    if phase == "pre":
        hints = analyzer.analyze_pre_tool(tool_name, parameters)
    else:
        hints = analyzer.analyze_post_tool(tool_name, parameters, None)

    return analyzer.format_hints(hints)