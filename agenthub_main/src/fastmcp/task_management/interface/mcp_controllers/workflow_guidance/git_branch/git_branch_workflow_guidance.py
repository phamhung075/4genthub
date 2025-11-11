"""Git Branch Workflow Guidance Implementation

Provides comprehensive guidance for Git Branch Management operations.
"""

from typing import Any

from ..base import BaseWorkflowGuidance


class GitBranchWorkflowGuidance(BaseWorkflowGuidance):
    """Workflow guidance for Git Branch Management operations."""

    def generate_guidance(
        self, action: str, context: dict[str, Any] | None = None
    ) -> dict[str, Any]:
        """Generate comprehensive workflow guidance for git branch operations."""

        return {
            "current_state": self._determine_state(action, context),
            "rules": self._get_git_branch_rules(),
            "next_actions": self._get_next_actions(action, context),
            "hints": self._get_hints(action),
            "warnings": self._get_warnings(action),
            "examples": self._get_examples(action, context),
            "parameter_guidance": self._get_parameter_guidance(action),
        }

    def _determine_state(
        self, action: str, context: dict[str, Any] | None = None
    ) -> dict[str, str]:
        """Determine the current workflow state."""
        phase = {
            "create": "branch_creation",
            "get": "branch_retrieval",
            "list": "branch_listing",
            "update": "branch_modification",
            "delete": "branch_removal",
            "assign_agent": "agent_assignment",
            "unassign_agent": "agent_removal",
            "get_statistics": "statistics_retrieval",
            "archive": "branch_archival",
            "restore": "branch_restoration",
        }.get(action, "unknown")

        return {"phase": phase, "action": action, "context": "git_branch_management"}

    def _get_git_branch_rules(self) -> list[str]:
        """Get essential rules for git branch management."""
        return [
            "🌿 RULE: Branch names should be descriptive and follow naming conventions (e.g., feature/user-auth, bugfix/login-issue)",
            "📋 RULE: Always assign branches to specific projects - branches cannot exist without a project",
            "🚀 RULE: Active branches should have assigned agents for autonomous work",
            "🔄 RULE: Branch statistics update automatically when tasks are created/completed",
            "⚠️ RULE: Deleting a branch will cascade delete all associated tasks - use archive instead for soft delete",
            "🏷️ RULE: Branch description should clearly state the purpose and scope of work",
            "👥 RULE: Multiple agents can be assigned to a branch for collaboration",
            "📊 RULE: Use get_statistics to monitor branch progress and task completion",
        ]

    def _get_next_actions(
        self, action: str, context: dict[str, Any] | None = None
    ) -> list[dict[str, Any]]:
        """Get context-aware next actions with priorities."""
        project_id = context.get("project_id") if context else None
        git_branch_id = context.get("git_branch_id") if context else None

        next_actions = []

        if action == "create":
            next_actions.extend(
                [
                    {
                        "priority": "high",
                        "action": "Assign an agent to the branch",
                        "description": "Assign specialized AI agent to work on this branch",
                        "example": {
                            "tool": "manage_git_branch",
                            "params": {
                                "action": "assign_agent",
                                "project_id": project_id or "project_id",
                                "git_branch_id": "created_branch_id",
                                "agent_id": "agent_id",
                            },
                        },
                    },
                    {
                        "priority": "high",
                        "action": "Create initial tasks",
                        "description": "Create tasks for the work to be done on this branch",
                        "example": {
                            "tool": "manage_task",
                            "params": {
                                "action": "create",
                                "git_branch_id": "created_branch_id",
                                "title": "Implement feature X",
                                "description": "Detailed requirements...",
                            },
                        },
                    },
                    {
                        "priority": "medium",
                        "action": "Check branch statistics",
                        "description": "Monitor branch progress and task completion",
                        "example": {
                            "tool": "manage_git_branch",
                            "params": {
                                "action": "get_statistics",
                                "project_id": project_id or "project_id",
                                "git_branch_id": "created_branch_id",
                            },
                        },
                    },
                ]
            )

        elif action == "list":
            next_actions.extend(
                [
                    {
                        "priority": "high",
                        "action": "Select a branch to work on",
                        "description": "Choose a specific branch and get its details",
                        "example": {
                            "tool": "manage_git_branch",
                            "params": {
                                "action": "get",
                                "project_id": project_id or "project_id",
                                "git_branch_id": "selected_branch_id",
                            },
                        },
                    },
                    {
                        "priority": "medium",
                        "action": "Create a new branch",
                        "description": "Create a new branch for new work",
                        "example": {
                            "tool": "manage_git_branch",
                            "params": {
                                "action": "create",
                                "project_id": project_id or "project_id",
                                "git_branch_name": "feature/new-feature",
                                "git_branch_description": "Implement new feature X",
                            },
                        },
                    },
                ]
            )

        elif action == "get":
            next_actions.extend(
                [
                    {
                        "priority": "high",
                        "action": "List tasks on this branch",
                        "description": "See all tasks associated with this branch",
                        "example": {
                            "tool": "manage_task",
                            "params": {
                                "action": "list",
                                "git_branch_id": git_branch_id or "branch_id",
                            },
                        },
                    },
                    {
                        "priority": "medium",
                        "action": "Get branch statistics",
                        "description": "Check progress and completion metrics",
                        "example": {
                            "tool": "manage_git_branch",
                            "params": {
                                "action": "get_statistics",
                                "project_id": project_id or "project_id",
                                "git_branch_id": git_branch_id or "branch_id",
                            },
                        },
                    },
                    {
                        "priority": "medium",
                        "action": "Update branch details",
                        "description": "Modify branch name or description",
                        "example": {
                            "tool": "manage_git_branch",
                            "params": {
                                "action": "update",
                                "project_id": project_id or "project_id",
                                "git_branch_id": git_branch_id or "branch_id",
                                "git_branch_description": "Updated description",
                            },
                        },
                    },
                ]
            )

        elif action == "assign_agent":
            next_actions.extend(
                [
                    {
                        "priority": "high",
                        "action": "Get next task for agent",
                        "description": "Agent should start working on tasks",
                        "example": {
                            "tool": "manage_task",
                            "params": {
                                "action": "next",
                                "git_branch_id": git_branch_id or "branch_id",
                                "include_context": True,
                            },
                        },
                    },
                    {
                        "priority": "medium",
                        "action": "List all agents on branch",
                        "description": "See who else is working on this branch",
                        "example": {
                            "tool": "manage_agent",
                            "params": {
                                "action": "list",
                                "project_id": project_id or "project_id",
                            },
                        },
                    },
                ]
            )

        elif action == "delete":
            next_actions.extend(
                [
                    {
                        "priority": "high",
                        "action": "Create a new branch",
                        "description": "Start work on a different feature",
                        "example": {
                            "tool": "manage_git_branch",
                            "params": {
                                "action": "create",
                                "project_id": project_id or "project_id",
                                "git_branch_name": "feature/next-feature",
                                "git_branch_description": "Next feature to implement",
                            },
                        },
                    },
                    {
                        "priority": "medium",
                        "action": "List remaining branches",
                        "description": "See what other branches exist",
                        "example": {
                            "tool": "manage_git_branch",
                            "params": {
                                "action": "list",
                                "project_id": project_id or "project_id",
                            },
                        },
                    },
                ]
            )

        return next_actions

    def _get_hints(self, action: str) -> list[str]:
        """Get action-specific hints."""
        hints = {
            "create": [
                "💡 Use descriptive branch names like 'feature/user-authentication' or 'bugfix/login-timeout'",
                "🔍 Include a clear description of what work will be done on this branch",
                "👥 Consider assigning an agent immediately after creation for autonomous work",
            ],
            "list": [
                "📊 Review branch statistics to identify which branches need attention",
                "🎯 Look for branches with incomplete tasks that need work",
                "🔄 Consider archiving old branches instead of deleting them",
            ],
            "get": [
                "📈 Use this to understand the current state and progress of a branch",
                "🔗 Branch ID is required - get it from list action first",
                "📋 Follow up with task list to see detailed work items",
            ],
            "update": [
                "✏️ Update descriptions to reflect current work scope",
                "🏷️ Branch names can be updated if naming conventions change",
                "📝 Keep descriptions current for better team understanding",
            ],
            "delete": [
                "⚠️ WARNING: This will delete ALL tasks on the branch",
                "💾 Consider using 'archive' action instead for soft delete",
                "🔄 Archived branches can be restored later if needed",
            ],
            "assign_agent": [
                "🤖 Agents will autonomously work on tasks in this branch",
                "👥 Multiple agents can collaborate on the same branch",
                "🎯 Assign specialized agents based on the work type",
            ],
            "unassign_agent": [
                "🔄 Agent's work will be preserved when unassigned",
                "📋 Consider reassigning to another agent for continuity",
                "✅ Complete or hand off tasks before unassigning",
            ],
            "get_statistics": [
                "📊 Statistics update automatically as tasks progress",
                "📈 Use this to monitor branch health and progress",
                "🎯 Identify bottlenecks or stalled work",
            ],
            "archive": [
                "💾 Soft delete - branch and tasks are preserved",
                "🔄 Can be restored later with 'restore' action",
                "📦 Good for completed features or abandoned work",
            ],
            "restore": [
                "♻️ Brings back archived branches with all tasks intact",
                "📋 Review branch content before restoring",
                "🔄 Consider if work is still relevant before restoring",
            ],
        }
        return hints.get(action, ["💡 Check action parameter for available operations"])

    def _get_warnings(self, action: str) -> list[str]:
        """Get action-specific warnings."""
        warnings = []

        if action == "create":
            warnings.append("🚨 Branch name must be unique within the project")
            warnings.append("📋 Always provide a meaningful description for clarity")

        elif action == "delete":
            warnings.append(
                "🚨 CRITICAL: This will permanently delete ALL tasks on the branch!"
            )
            warnings.append(
                "⚠️ This action cannot be undone - consider 'archive' instead"
            )
            warnings.append(
                "💡 Use: manage_git_branch(action='archive') for soft delete"
            )

        elif action == "update":
            warnings.append("⚠️ Changing branch name may affect external references")
            warnings.append(
                "📋 Ensure updated info doesn't conflict with other branches"
            )

        elif action == "assign_agent":
            warnings.append("🤖 Ensure agent exists before assignment")
            warnings.append("📋 Agent will start processing tasks immediately")

        elif action == "archive":
            warnings.append("📦 Archived branches won't appear in normal listings")
            warnings.append("🔄 Tasks remain intact but won't be processed")

        return warnings

    def _get_examples(
        self, action: str, context: dict[str, Any] | None = None
    ) -> list[dict[str, Any]]:
        """Get examples for the NEXT action after current operation."""
        examples = []

        project_id = (
            context.get("project_id", "project_id") if context else "project_id"
        )
        git_branch_id = (
            context.get("git_branch_id", "branch_id") if context else "branch_id"
        )

        if action == "create":
            # After creating, show how to START WORK on the branch (what comes next)
            examples.append(
                {
                    "description": "Assign an agent to work on the branch",
                    "code": f"""manage_git_branch(
    action="assign_agent",
    project_id="{project_id}",
    git_branch_id="{git_branch_id}",
    agent_id="coding-agent"
)""",
                }
            )
            examples.append(
                {
                    "description": "Create first task on the branch",
                    "code": f"""manage_task(
    action="create",
    git_branch_id="{git_branch_id}",
    title="Implement core functionality",
    description="Build the main feature components",
    assignees="coding-agent"
)""",
                }
            )

        elif action == "list":
            examples.append(
                {
                    "description": "List all branches in a project",
                    "code": """manage_git_branch(
    action="list",
    project_id="my_project_id"
)""",
                }
            )

        elif action == "get":
            examples.append(
                {
                    "description": "Get branch details",
                    "code": """manage_git_branch(
    action="get",
    project_id="my_project_id",
    git_branch_id="branch_uuid"
)""",
                }
            )

        elif action == "assign_agent":
            examples.append(
                {
                    "description": "Assign an agent to work on a branch",
                    "code": """manage_git_branch(
    action="assign_agent",
    project_id="my_project_id",
    git_branch_id="branch_uuid",
    agent_id="agent_uuid"
)""",
                }
            )

        elif action == "get_statistics":
            examples.append(
                {
                    "description": "Check branch progress",
                    "code": """manage_git_branch(
    action="get_statistics",
    project_id="my_project_id",
    git_branch_id="branch_uuid"
)""",
                }
            )

        return examples

    def _get_parameter_guidance(self, action: str) -> dict[str, dict[str, str]]:
        """Get parameter-specific guidance for NEXT actions."""
        base_params = {
            "project_id": {
                "requirement": "REQUIRED for all actions",
                "format": "UUID string",
                "tip": "Get from manage_project(action='list') or project context",
            }
        }

        # Define parameters for NEXT actions (what user needs to do next)
        next_action_params = {
            "create": {  # After create -> assign agent or create tasks
                "git_branch_id": {
                    "requirement": "REQUIRED for next actions",
                    "format": "UUID string (returned from creation)",
                    "tip": "Use the git_branch_id from create response",
                },
                "agent_id": {
                    "requirement": "REQUIRED for agent assignment",
                    "format": "Agent identifier string",
                    "tip": "Assign coding-agent, test-orchestrator-agent, or other specialists",
                },
                "title": {
                    "requirement": "REQUIRED for task creation",
                    "format": "String",
                    "tip": "Create initial tasks to define work on this branch",
                },
            },
            "get": {  # After get -> list tasks or update branch
                "git_branch_id": {
                    "requirement": "REQUIRED for task listing",
                    "format": "UUID string",
                    "tip": "List tasks on this branch to see work items",
                },
                "action": {
                    "requirement": "REQUIRED",
                    "format": "String",
                    "tip": "Use 'list' to see tasks, 'get_statistics' to check progress",
                },
            },
            "list": {  # After list -> get specific branch or create new one
                "git_branch_id": {
                    "requirement": "OPTIONAL for filtering",
                    "format": "UUID string",
                    "tip": "Get details of a specific branch",
                },
            },
            "update": {  # After update -> continue working
                "git_branch_id": {
                    "requirement": "REQUIRED",
                    "format": "UUID string",
                    "tip": "Branch was just updated - list tasks to continue work",
                },
            },
            "delete": {  # After delete -> create new branch or list remaining
                "project_id": {
                    "requirement": "REQUIRED",
                    "format": "UUID string",
                    "tip": "List remaining branches or create a new one",
                },
            },
            "assign_agent": {  # After assign_agent -> agent starts working
                "git_branch_id": {
                    "requirement": "REQUIRED",
                    "format": "UUID string",
                    "tip": "Get next task for the assigned agent",
                },
                "include_context": {
                    "requirement": "OPTIONAL",
                    "format": "Boolean",
                    "tip": "Use manage_task(action='next') to get work for agent",
                },
            },
            "get_statistics": {  # After statistics -> continue or complete work
                "git_branch_id": {
                    "requirement": "REQUIRED",
                    "format": "UUID string",
                    "tip": "List tasks to continue work or archive if complete",
                },
            },
        }

        params = base_params.copy()
        if action in next_action_params:
            params.update(next_action_params[action])

        return params
