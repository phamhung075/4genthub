"""Subtask workflow guidance implementation."""

from typing import Any

from ..base import WorkflowGuidanceInterface


class SubtaskWorkflowGuidance(WorkflowGuidanceInterface):
    """Provides comprehensive workflow guidance for subtask management."""

    def enhance_response(
        self, response: dict[str, Any], action: str, context: dict[str, Any]
    ) -> dict[str, Any]:
        """
        Enhance subtask response with comprehensive workflow guidance.

        Args:
            response: Original response from subtask operation
            action: The action that was performed
            context: Context information including task and subtask details

        Returns:
            Enhanced response with workflow_guidance
        """
        if not response.get("success"):
            return response

        # Extract relevant data
        task_id = context.get("task_id")
        subtask_id = context.get("subtask_id")
        subtask = response.get("subtask", {})
        subtasks = response.get("subtasks", [])

        # Determine current state
        if action == "list":
            current_state = self._analyze_subtasks_state(subtasks)
        elif subtask:
            if isinstance(subtask, dict) and "subtask" in subtask:
                current_state = self._analyze_subtask_state(subtask["subtask"])
            else:
                current_state = self._analyze_subtask_state(subtask)
        else:
            current_state = {"phase": "unknown"}

        # Build workflow guidance
        workflow_guidance = {
            "current_state": current_state,
            "rules": self.get_rules(action, response),
            "next_actions": self.suggest_next_actions(action, response, context),
            "hints": self.generate_hints(action, response, context),
            "warnings": self.check_warnings(action, response, context),
            "examples": self.get_examples(action, context),
            "parameter_guidance": self.get_parameter_guidance(action),
        }

        # Add action-specific elements (focused on NEXT actions)
        if action == "create":
            workflow_guidance["tips"] = [
                "🚀 Start working: Update status to 'in_progress' when you begin",
                "📊 Track progress: Use progress_percentage to show completion (0-100)",
                "🚧 Report blockers: Document any issues that prevent progress",
            ]
        elif action == "update":
            workflow_guidance["tips"] = [
                "📊 Use progress_percentage to track completion (0-100)",
                "🚧 Document blockers immediately when encountered",
                "💡 Share insights that might help with other subtasks",
            ]
        elif action == "complete":
            workflow_guidance["completion_checklist"] = [
                "✅ Subtask fully implemented and tested",
                "📝 Completion summary provided",
                "💡 Key insights documented",
                "🔗 Impact on parent task explained",
            ]
        elif action == "list":
            workflow_guidance["overview"] = self._generate_subtasks_overview(
                subtasks or []
            )

        response["workflow_guidance"] = workflow_guidance
        return response

    def analyze_state(
        self, response: dict[str, Any], context: dict[str, Any]
    ) -> dict[str, Any]:
        """Analyze current subtask state for contextual guidance."""
        # This is handled in enhance_response based on action type
        subtask = response.get("subtask", {})
        if isinstance(subtask, dict) and "subtask" in subtask:
            return self._analyze_subtask_state(subtask["subtask"])
        return self._analyze_subtask_state(subtask)

    def _analyze_subtask_state(self, subtask: dict[str, Any]) -> dict[str, Any]:
        """Analyze individual subtask state."""
        status = subtask.get("status", "todo")

        # Determine phase
        if status == "todo":
            phase = "not_started"
        elif status == "in_progress":
            phase = "in_progress"
        elif status == "done":
            phase = "completed"
        else:
            phase = status

        return {
            "phase": phase,
            "status": status,
            "has_assignees": bool(subtask.get("assignees")),
        }

    def _analyze_subtasks_state(self, subtasks: list[dict[str, Any]]) -> dict[str, Any]:
        """Analyze overall subtasks state."""
        total = len(subtasks)
        if total == 0:
            return {"phase": "no_subtasks", "total": 0}

        completed = sum(1 for s in subtasks if s.get("status") == "done")
        in_progress = sum(1 for s in subtasks if s.get("status") == "in_progress")
        todo = sum(1 for s in subtasks if s.get("status") == "todo")

        # Determine overall phase
        if completed == total:
            phase = "all_complete"
        elif in_progress > 0 or completed > 0:
            phase = "in_progress"
        else:
            phase = "not_started"

        return {
            "phase": phase,
            "total": total,
            "completed": completed,
            "in_progress": in_progress,
            "todo": todo,
            "completion_percentage": int((completed / total) * 100) if total > 0 else 0,
        }

    def get_rules(self, action: str, response: dict[str, Any]) -> list[str]:
        """Get contextual rules for the current action."""
        rules = []

        # Universal rules
        rules.append("📝 Keep parent task updated with subtask progress")
        rules.append("🔄 Update subtask status when work begins/ends")

        # Action-specific rules
        if action == "create":
            rules.extend(
                [
                    "🎯 Make subtask titles clear and actionable",
                    "📏 Size subtasks appropriately (2-4 hours)",
                    "🔗 Consider dependencies between subtasks",
                ]
            )
        elif action == "update":
            rules.extend(
                [
                    "📊 Update progress_percentage (0-100)",
                    "🚧 Document blockers immediately",
                    "💡 Share insights for team learning",
                ]
            )
        elif action == "complete":
            rules.extend(
                [
                    "📝 Completion summary is highly recommended",
                    "💡 Document any insights or learnings",
                    "🔗 Explain impact on parent task",
                ]
            )

        return rules

    def suggest_next_actions(
        self, action: str, response: dict[str, Any], context: dict[str, Any]
    ) -> list[dict[str, Any]]:
        """Suggest contextual next actions with examples."""
        actions = []

        task_id = context.get("task_id")
        subtask_id = context.get("subtask_id")
        state = response.get("workflow_guidance", {}).get("current_state", {})

        if action == "list":
            if state.get("todo", 0) > 0:
                actions.append(
                    {
                        "priority": "high",
                        "action": "Start next subtask",
                        "description": "Pick a todo subtask and begin work",
                        "example": f"manage_subtask(action='update', task_id='{task_id}', subtask_id='...', status='in_progress', progress_notes='Starting implementation')",
                    }
                )
            if state.get("phase") == "all_complete":
                actions.append(
                    {
                        "priority": "high",
                        "action": "Complete parent task",
                        "description": "All subtasks done - consider completing the parent",
                        "example": f"manage_task(action='complete', task_id='{task_id}', completion_summary='All subtasks completed successfully')",
                    }
                )

        elif action == "create":
            # For create action, we don't have a subtask_id yet, so use the one from the response
            created_subtask_id = response.get("subtask", {}).get("id", "new-subtask-id")
            actions.append(
                {
                    "priority": "high",
                    "action": "Start the subtask",
                    "description": "Update status when you begin work",
                    "example": f"manage_subtask(action='update', task_id='{task_id}', subtask_id='{created_subtask_id}', progress_percentage=10, progress_notes='Initial setup complete')",
                }
            )

        elif action == "update":
            subtask = response.get("subtask", {})
            # Use the subtask_id from context or from the response
            current_subtask_id = subtask_id or subtask.get("id", "subtask-id")
            if isinstance(subtask, dict) and subtask.get("status") == "in_progress":
                actions.append(
                    {
                        "priority": "medium",
                        "action": "Continue tracking progress",
                        "description": "Update progress_percentage as you work",
                        "example": f"manage_subtask(action='update', task_id='{task_id}', subtask_id='{current_subtask_id}', progress_percentage=75, progress_notes='Almost done, finalizing tests')",
                    }
                )

        return actions

    def generate_hints(
        self, action: str, response: dict[str, Any], context: dict[str, Any]
    ) -> list[str]:
        """Generate contextual hints."""
        hints = []

        state = response.get("workflow_guidance", {}).get("current_state", {})

        # Phase-based hints
        if state.get("phase") == "not_started":
            hints.append("🚀 Ready to start? Update status to 'in_progress' first")
        elif state.get("phase") == "in_progress":
            hints.append("📊 Remember to update progress regularly")
            hints.append("🚧 Report any blockers as soon as you encounter them")
        elif state.get("phase") == "all_complete":
            hints.append(
                "🎉 All subtasks complete! Parent task may be ready for completion"
            )

        # Action-specific hints
        if action == "create":
            hints.append("💡 Keep subtasks focused and measurable")
        elif action == "update" and state.get("status") == "in_progress":
            hints.append("💭 Consider adding insights_found to share learnings")
        elif action == "complete":
            hints.append("📝 Provide a clear completion_summary for context")
        elif action == "list":
            if state.get("todo", 0) > 0:
                hints.append(
                    f"📋 {state.get('todo', 0)} subtask(s) waiting to be started"
                )
            if state.get("in_progress", 0) > 0:
                hints.append(
                    f"🔄 {state.get('in_progress', 0)} subtask(s) currently in progress"
                )

        return hints

    def check_warnings(
        self, action: str, response: dict[str, Any], context: dict[str, Any]
    ) -> list[str]:
        """Check for potential issues and generate warnings."""
        warnings = []

        state = response.get("workflow_guidance", {}).get("current_state", {})

        # Check for subtasks without assignees
        if action == "create" and not state.get("has_assignees"):
            warnings.append("⚠️ No assignee specified - who will work on this?")

        # Check for status inconsistency
        if action == "complete":
            subtask = response.get("subtask", {})
            if isinstance(subtask, dict) and subtask.get("status") != "done":
                warnings.append(
                    "⚠️ Subtask hasn't been started - cannot complete directly"
                )

        # Check for too many in-progress subtasks
        if action == "list" and state.get("in_progress", 0) > 3:
            warnings.append(
                f"⚠️ {state.get('in_progress')} subtasks in progress - consider completing some first"
            )

        return warnings

    def get_examples(self, action: str, context: dict[str, Any]) -> dict[str, Any]:
        """Get relevant examples for the NEXT action after current operation."""
        examples = {}

        task_id = context.get("task_id", "task-id")
        subtask_id = context.get("subtask_id", "subtask-id")

        if action == "create":
            # After creating, show UPDATE examples (what comes next)
            examples["start_work"] = {
                "description": "Start working on the subtask",
                "command": f"manage_subtask(action='update', task_id='{task_id}', subtask_id='{subtask_id}', status='in_progress', progress_notes='Starting implementation')",
            }
            examples["track_progress"] = {
                "description": "Update progress as you work",
                "command": f"manage_subtask(action='update', task_id='{task_id}', subtask_id='{subtask_id}', progress_percentage=25, progress_notes='Completed initial setup')",
            }

        elif action == "update":
            examples["update_progress"] = {
                "description": "Update progress percentage",
                "command": f"manage_subtask(action='update', task_id='{task_id}', subtask_id='{subtask_id}', progress_percentage=50, progress_notes='Halfway done, completed core logic')",
            }
            examples["update_blocked"] = {
                "description": "Report a blocker",
                "command": f"manage_subtask(action='update', task_id='{task_id}', subtask_id='{subtask_id}', blockers='Waiting for API documentation', progress_notes='Cannot proceed without API specs')",
            }

        elif action == "complete":
            examples["complete_basic"] = {
                "description": "Complete with summary",
                "command": f"manage_subtask(action='complete', task_id='{task_id}', subtask_id='{subtask_id}', completion_summary='Successfully implemented authentication with JWT tokens')",
            }
            examples["complete_detailed"] = {
                "description": "Complete with full details",
                "command": f"manage_subtask(action='complete', task_id='{task_id}', subtask_id='{subtask_id}', completion_summary='API endpoints fully tested and documented', impact_on_parent='Core functionality now ready for integration', insights_found=['JWT refresh tokens improve UX', 'Rate limiting prevents abuse'])",
            }

        elif action == "list":
            examples["list_subtasks"] = {
                "description": "List all subtasks",
                "command": f"manage_subtask(action='list', task_id='{task_id}')",
            }

        return examples

    def get_parameter_guidance(self, action: str) -> dict[str, Any]:
        """Get detailed parameter guidance for the NEXT action after current operation."""
        guidance = {"applicable_parameters": [], "parameter_tips": {}}

        # Define parameters for NEXT actions (what user needs to do next)
        next_action_params = {
            "create": [  # After create -> next is UPDATE to start work
                "task_id",
                "subtask_id",
                "status",
                "progress_percentage",
                "progress_notes",
                "blockers",
            ],
            "update": [  # After update -> continue updating or complete
                "task_id",
                "subtask_id",
                "progress_percentage",
                "progress_notes",
                "blockers",
                "insights_found",
                "completion_summary",  # If ready to complete
            ],
            "complete": [  # After complete -> list or create new
                "task_id",  # For listing other subtasks
            ],
            "delete": ["task_id"],  # For listing remaining
            "get": [  # After get -> update
                "task_id",
                "subtask_id",
                "progress_percentage",
                "progress_notes",
            ],
            "list": [  # After list -> start working on subtasks
                "task_id",
                "subtask_id",
                "status",
                "progress_percentage",
                "progress_notes",
            ],
        }

        guidance["applicable_parameters"] = next_action_params.get(action, [])

        # Parameter tips (focused on NEXT actions)
        param_tips = {
            "task_id": {
                "requirement": "REQUIRED for all operations",
                "tip": "Parent task identifier from creation",
            },
            "subtask_id": {
                "requirement": "REQUIRED for update/complete/get/delete",
                "tip": "Use the subtask_id returned from creation",
            },
            "status": {
                "requirement": "Optional - auto-updated by progress_percentage",
                "tip": "Set to 'in_progress' when starting work",
                "examples": ["todo", "in_progress", "done"],
            },
            "progress_percentage": {
                "requirement": "RECOMMENDED for tracking progress",
                "tip": "Use 0-100 range; automatically updates status (0=todo, 1-99=in_progress, 100=done)",
                "when_to_use": "Update regularly as you work",
                "examples": [10, 25, 50, 75, 90, 100],
            },
            "progress_notes": {
                "requirement": "HIGHLY RECOMMENDED",
                "when_to_use": "Every time you update progress or hit blockers",
                "examples": [
                    "Starting implementation",
                    "Completed database schema",
                    "Fixed authentication bug",
                    "Researching third-party integrations",
                ],
                "best_practice": "Be specific about current work and what's done",
            },
            "blockers": {
                "requirement": "Use when blocked",
                "when_to_use": "Immediately when something prevents progress",
                "examples": [
                    "Missing API documentation",
                    "Waiting for design approval",
                    "Dependencies not available",
                ],
                "tip": "Document blockers as soon as encountered",
            },
            "insights_found": {
                "requirement": "Optional but valuable",
                "when_to_use": "When discovering something that could help others",
                "examples": [
                    "Performance bottleneck found in current approach",
                    "Better library available for this use case",
                    "Security vulnerability identified",
                ],
                "best_practice": "Share learnings that impact other subtasks or parent",
            },
            "completion_summary": {
                "requirement": "HIGHLY RECOMMENDED for complete action",
                "tip": "Summarize what was accomplished when completing",
                "when_to_use": "When progress_percentage reaches 100",
                "examples": [
                    "Implemented secure user authentication with JWT",
                    "Completed all CRUD operations for user management",
                ],
            },
        }

        # Only include tips for applicable parameters
        for param in guidance["applicable_parameters"]:
            if param in param_tips:
                guidance["parameter_tips"][param] = param_tips[param]

        return guidance

    def _generate_subtasks_overview(
        self, subtasks: list[dict[str, Any]]
    ) -> dict[str, Any]:
        """Generate overview for subtasks list."""
        total = len(subtasks)

        by_status = {"todo": [], "in_progress": [], "done": []}

        for subtask in subtasks:
            status = subtask.get("status", "todo")
            if status in by_status:
                by_status[status].append(
                    {
                        "id": subtask.get("id"),
                        "title": subtask.get("title"),
                        "assignees": subtask.get("assignees", []),
                    }
                )

        overview = {
            "total_subtasks": total,
            "by_status": by_status,
            "completion_rate": f"{len(by_status['done'])}/{total}"
            if total > 0
            else "0/0",
            "recommendations": [],
        }

        # Add recommendations
        if len(by_status["done"]) == total and total > 0:
            overview["recommendations"].append(
                "All subtasks complete - parent task ready for completion"
            )
        elif len(by_status["in_progress"]) > 3:
            overview["recommendations"].append(
                "Many subtasks in progress - focus on completing some"
            )
        elif len(by_status["todo"]) > 0 and len(by_status["in_progress"]) == 0:
            overview["recommendations"].append("Start work on pending subtasks")

        return overview
