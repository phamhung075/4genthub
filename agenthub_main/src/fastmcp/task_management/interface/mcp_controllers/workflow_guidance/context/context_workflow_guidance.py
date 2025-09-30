"""Context Management Workflow Guidance

Provides contextual guidance for context management operations to help users
understand next steps, avoid common errors, and follow best practices.
"""

from typing import Any

from ..base import BaseWorkflowGuidance


class ContextWorkflowGuidance(BaseWorkflowGuidance):
    """Workflow guidance for context management operations."""

    def generate_guidance(
        self, action: str, context: dict[str, Any] | None = None
    ) -> dict[str, Any]:
        """Generate workflow guidance for context operations."""

        context = context or {}
        task_id = context.get("task_id", "your-task-id")

        guidance = {
            "current_state": self._determine_state(action, context),
            "rules": self._get_context_rules(),
            "next_actions": self._get_next_actions(action, task_id),
            "hints": self._get_hints(action),
            "warnings": self._get_warnings(action),
            "examples": self._get_examples(action, task_id),
            "parameter_guidance": self._get_parameter_guidance(action),
        }

        return guidance

    def _determine_state(self, action: str, context: dict[str, Any]) -> dict[str, str]:
        """Determine current workflow state."""

        state_map = {
            "create": "creating_context",
            "update": "updating_context",
            "get": "retrieving_context",
            "delete": "removing_context",
            "add_insight": "adding_insight",
            "add_progress": "tracking_progress",
            "list": "browsing_contexts",
        }

        return {"phase": state_map.get(action, "context_operation"), "action": action}

    def _get_context_rules(self) -> list[str]:
        """Get general context management rules."""
        return [
            "📋 Always create context before completing tasks",
            "📝 Use meaningful titles and descriptions",
            "🔄 Update context regularly with progress",
            "🔗 Link context to proper project and branch",
            "💡 Add insights to share knowledge with team",
        ]

    def _get_next_actions(self, action: str, task_id: str) -> list[dict[str, Any]]:
        """Get suggested next actions based on current operation."""

        if action == "create":
            return [
                {
                    "priority": "high",
                    "action": "Add initial progress",
                    "description": "Document your starting point",
                    "example": {
                        "tool": "manage_context",
                        "params": {
                            "action": "add_progress",
                            "task_id": task_id,
                            "content": "Started working on [describe initial work]",
                            "agent": "your_agent_name",
                        },
                    },
                },
                {
                    "priority": "medium",
                    "action": "Update task status",
                    "description": "Mark task as in progress",
                    "example": {
                        "tool": "manage_task",
                        "params": {
                            "action": "update",
                            "task_id": task_id,
                            "status": "in_progress",
                        },
                    },
                },
            ]

        elif action == "update":
            return [
                {
                    "priority": "high",
                    "action": "Continue work",
                    "description": "Proceed with task implementation",
                    "example": {
                        "tool": "manage_context",
                        "params": {
                            "action": "add_progress",
                            "task_id": task_id,
                            "content": "Completed X, working on Y",
                        },
                    },
                }
            ]

        elif action == "add_progress":
            return [
                {
                    "priority": "medium",
                    "action": "Update task details",
                    "description": "Keep task current with latest progress",
                    "example": {
                        "tool": "manage_task",
                        "params": {
                            "action": "update",
                            "task_id": task_id,
                            "details": "Latest progress: [describe current state]",
                        },
                    },
                }
            ]

        else:
            return [
                {
                    "priority": "medium",
                    "action": "Continue context management",
                    "description": "Use context to track task progress",
                    "example": {
                        "tool": "manage_context",
                        "params": {
                            "action": "add_progress",
                            "task_id": task_id,
                            "content": "Describe your progress",
                        },
                    },
                }
            ]

    def _get_hints(self, action: str) -> list[str]:
        """Get helpful hints for the current action."""

        hints_map = {
            "create": [
                "💡 Context is required before completing tasks",
                "🎯 Use descriptive titles for better organization",
                "📁 Group related contexts by project",
            ],
            "update": [
                "📝 Update context regularly to maintain accuracy",
                "🔄 Use data_status to track task progression",
            ],
            "add_progress": [
                "📈 Regular progress updates help team coordination",
                "🎯 Be specific about what was accomplished",
            ],
            "add_insight": [
                "💡 Share important discoveries with insights",
                "🏷️ Use categories to organize insights by topic",
            ],
            "get": [
                "🔍 Use context to understand task history",
                "📊 Check progress timeline for task evolution",
            ],
        }

        return hints_map.get(
            action,
            [
                "📋 Context management helps track task progress",
                "🔗 Keep context synchronized with task status",
            ],
        )

    def _get_warnings(self, action: str) -> list[str]:
        """Get warnings for potential issues."""

        if action == "delete":
            return [
                "⚠️ Deleting context removes all progress history",
                "💾 Consider backing up important insights first",
            ]

        return []

    def _get_examples(self, action: str, task_id: str) -> dict[str, dict[str, str]]:
        """Get example commands for the current action."""

        examples = {
            "create": {
                "basic_create": {
                    "description": "Create context for a task",
                    "command": f"manage_context(action='create', task_id='{task_id}', project_id='your_project')",
                },
                "detailed_create": {
                    "description": "Create context with initial data",
                    "command": f"manage_context(action='create', task_id='{task_id}', data_title='Task Title', data_description='Detailed description')",
                },
            },
            "update": {
                "status_update": {
                    "description": "Update context status",
                    "command": f"manage_context(action='update', task_id='{task_id}', data_status='in_progress')",
                },
                "progress_update": {
                    "description": "Update context with progress",
                    "command": f"manage_context(action='update', task_id='{task_id}', data_description='Updated progress description')",
                },
            },
            "add_progress": {
                "track_progress": {
                    "description": "Add progress note",
                    "command": f"manage_context(action='add_progress', task_id='{task_id}', content='Completed database setup')",
                }
            },
            "add_insight": {
                "share_insight": {
                    "description": "Add insight for team",
                    "command": f"manage_context(action='add_insight', task_id='{task_id}', content='Found better approach using X', category='solution')",
                }
            },
        }

        return examples.get(
            action,
            {
                "general": {
                    "description": "Context management operation",
                    "command": f"manage_context(action='{action}', task_id='{task_id}')",
                }
            },
        )

    def _get_parameter_guidance(self, action: str) -> dict[str, Any]:
        """Get parameter-specific guidance."""

        base_params = ["task_id", "user_id", "project_id", "git_branch_name"]

        action_params = {
            "create": base_params
            + ["data_title", "data_description", "data_status", "data_priority"],
            "update": base_params + ["data_title", "data_description", "data_status"],
            "add_progress": base_params + ["content", "agent"],
            "add_insight": base_params + ["content", "agent", "category", "importance"],
            "get": base_params,
            "delete": base_params,
        }

        return {
            "applicable_parameters": action_params.get(action, base_params),
            "parameter_tips": {
                "task_id": {
                    "requirement": "REQUIRED",
                    "tip": "Must be a valid task UUID",
                    "examples": ["66b7b56abb3b4cccab12cd3c9890d7e7"],
                },
                "content": {
                    "requirement": "REQUIRED for add_progress/add_insight",
                    "tip": "Be specific and descriptive",
                    "examples": [
                        "Completed user authentication module",
                        "Found performance issue in database queries",
                    ],
                },
                "data_status": {
                    "requirement": "Optional",
                    "tip": "Tracks task progression",
                    "values": ["todo", "in_progress", "done", "blocked"],
                },
                "category": {
                    "requirement": "Optional for insights",
                    "tip": "Organizes insights by topic",
                    "examples": ["solution", "blocker", "discovery", "performance"],
                },
            },
        }
