"""Subtask workflow guidance implementation."""

from typing import Dict, Any, List, Optional
from datetime import datetime, timezone

from ..base import WorkflowGuidanceInterface


class SubtaskWorkflowGuidance(WorkflowGuidanceInterface):
    """Provides comprehensive workflow guidance for subtask management."""
    
    def enhance_response(self, response: Dict[str, Any], action: str, context: Dict[str, Any]) -> Dict[str, Any]:
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
            "parameter_guidance": self.get_parameter_guidance(action)
        }
        
        # Add action-specific elements
        if action == "create":
            workflow_guidance["tips"] = [
                "💡 Break down the parent task into clear, actionable subtasks",
                "📏 Each subtask should be small enough to complete in 2-4 hours",
                "🎯 Make subtask titles specific and action-oriented"
            ]
        elif action == "update":
            workflow_guidance["tips"] = [
                "📊 Use progress_percentage to track completion (0-100)",
                "🚧 Document blockers immediately when encountered",
                "💡 Share insights that might help with other subtasks"
            ]
        elif action == "complete":
            workflow_guidance["completion_checklist"] = [
                "✅ Subtask fully implemented and tested",
                "📝 Completion summary provided",
                "💡 Key insights documented",
                "🔗 Impact on parent task explained"
            ]
        elif action == "list":
            workflow_guidance["overview"] = self._generate_subtasks_overview(subtasks or [])
        
        response["workflow_guidance"] = workflow_guidance
        return response
    
    def analyze_state(self, response: Dict[str, Any], context: Dict[str, Any]) -> Dict[str, Any]:
        """Analyze current subtask state for contextual guidance."""
        # This is handled in enhance_response based on action type
        subtask = response.get("subtask", {})
        if isinstance(subtask, dict) and "subtask" in subtask:
            return self._analyze_subtask_state(subtask["subtask"])
        return self._analyze_subtask_state(subtask)
    
    def _analyze_subtask_state(self, subtask: Dict[str, Any]) -> Dict[str, Any]:
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
            "has_assignees": bool(subtask.get("assignees"))
        }
    
    def _analyze_subtasks_state(self, subtasks: List[Dict[str, Any]]) -> Dict[str, Any]:
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
            "completion_percentage": int((completed / total) * 100) if total > 0 else 0
        }
    
    def get_rules(self, action: str, response: Dict[str, Any]) -> List[str]:
        """Get contextual rules for the current action."""
        rules = []
        
        # Universal rules
        rules.append("📝 Keep parent task updated with subtask progress")
        rules.append("🔄 Update subtask status when work begins/ends")
        
        # Action-specific rules
        if action == "create":
            rules.extend([
                "🎯 Make subtask titles clear and actionable",
                "📏 Size subtasks appropriately (2-4 hours)",
                "🔗 Consider dependencies between subtasks"
            ])
        elif action == "update":
            rules.extend([
                "📊 Update progress_percentage (0-100)",
                "🚧 Document blockers immediately",
                "💡 Share insights for team learning"
            ])
        elif action == "complete":
            rules.extend([
                "📝 Completion summary is highly recommended",
                "💡 Document any insights or learnings",
                "🔗 Explain impact on parent task"
            ])
        
        return rules
    
    def suggest_next_actions(self, action: str, response: Dict[str, Any], context: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Suggest contextual next actions with examples."""
        actions = []
        
        task_id = context.get("task_id")
        subtask_id = context.get("subtask_id")
        state = response.get("workflow_guidance", {}).get("current_state", {})
        
        if action == "list":
            if state.get("todo", 0) > 0:
                actions.append({
                    "priority": "high",
                    "action": "Start next subtask",
                    "description": "Pick a todo subtask and begin work",
                    "example": f"manage_subtask(action='update', task_id='{task_id}', subtask_id='...', status='in_progress', progress_notes='Starting implementation')"
                })
            if state.get("phase") == "all_complete":
                actions.append({
                    "priority": "high",
                    "action": "Complete parent task",
                    "description": "All subtasks done - consider completing the parent",
                    "example": f"manage_task(action='complete', task_id='{task_id}', completion_summary='All subtasks completed successfully')"
                })
        
        elif action == "create":
            # For create action, we don't have a subtask_id yet, so use the one from the response
            created_subtask_id = response.get("subtask", {}).get("id", "new-subtask-id")
            actions.append({
                "priority": "high",
                "action": "Start the subtask",
                "description": "Update status when you begin work",
                "example": f"manage_subtask(action='update', task_id='{task_id}', subtask_id='{created_subtask_id}', progress_percentage=10, progress_notes='Initial setup complete')"
            })
        
        elif action == "update":
            subtask = response.get("subtask", {})
            # Use the subtask_id from context or from the response
            current_subtask_id = subtask_id or subtask.get("id", "subtask-id")
            if isinstance(subtask, dict) and subtask.get("status") == "in_progress":
                actions.append({
                    "priority": "medium",
                    "action": "Continue tracking progress",
                    "description": "Update progress_percentage as you work",
                    "example": f"manage_subtask(action='update', task_id='{task_id}', subtask_id='{current_subtask_id}', progress_percentage=75, progress_notes='Almost done, finalizing tests')"
                })
        
        return actions
    
    def generate_hints(self, action: str, response: Dict[str, Any], context: Dict[str, Any]) -> List[str]:
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
            hints.append("🎉 All subtasks complete! Parent task may be ready for completion")
        
        # Action-specific hints
        if action == "create":
            hints.append("💡 Keep subtasks focused and measurable")
        elif action == "update" and state.get("status") == "in_progress":
            hints.append("💭 Consider adding insights_found to share learnings")
        elif action == "complete":
            hints.append("📝 Provide a clear completion_summary for context")
        elif action == "list":
            if state.get("todo", 0) > 0:
                hints.append(f"📋 {state.get('todo', 0)} subtask(s) waiting to be started")
            if state.get("in_progress", 0) > 0:
                hints.append(f"🔄 {state.get('in_progress', 0)} subtask(s) currently in progress")
        
        return hints
    
    def check_warnings(self, action: str, response: Dict[str, Any], context: Dict[str, Any]) -> List[str]:
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
                warnings.append("⚠️ Subtask hasn't been started - cannot complete directly")
        
        # Check for too many in-progress subtasks
        if action == "list" and state.get("in_progress", 0) > 3:
            warnings.append(f"⚠️ {state.get('in_progress')} subtasks in progress - consider completing some first")
        
        return warnings
    
    def get_examples(self, action: str, context: Dict[str, Any]) -> Dict[str, Any]:
        """Get relevant examples for the current action."""
        examples = {}
        
        task_id = context.get("task_id", "task-id")
        subtask_id = context.get("subtask_id", "subtask-id")
        
        if action == "create":
            examples["create_basic"] = {
                "description": "Create a simple subtask",
                "command": f"manage_subtask(action='create', task_id='{task_id}', title='Implement user authentication', description='Add login/logout functionality')"
            }
            examples["create_with_notes"] = {
                "description": "Create with initial progress notes",
                "command": f"manage_subtask(action='create', task_id='{task_id}', title='Design API endpoints', progress_notes='Starting with REST API design patterns')"
            }
        
        elif action == "update":
            examples["update_progress"] = {
                "description": "Update progress percentage",
                "command": f"manage_subtask(action='update', task_id='{task_id}', subtask_id='{subtask_id}', progress_percentage=50, progress_notes='Halfway done, completed core logic')"
            }
            examples["update_blocked"] = {
                "description": "Report a blocker",
                "command": f"manage_subtask(action='update', task_id='{task_id}', subtask_id='{subtask_id}', blockers='Waiting for API documentation', progress_notes='Cannot proceed without API specs')"
            }
        
        elif action == "complete":
            examples["complete_basic"] = {
                "description": "Complete with summary",
                "command": f"manage_subtask(action='complete', task_id='{task_id}', subtask_id='{subtask_id}', completion_summary='Successfully implemented authentication with JWT tokens')"
            }
            examples["complete_detailed"] = {
                "description": "Complete with full details",
                "command": f"manage_subtask(action='complete', task_id='{task_id}', subtask_id='{subtask_id}', completion_summary='API endpoints fully tested and documented', impact_on_parent='Core functionality now ready for integration', insights_found=['JWT refresh tokens improve UX', 'Rate limiting prevents abuse'])"
            }
        
        elif action == "list":
            examples["list_subtasks"] = {
                "description": "List all subtasks",
                "command": f"manage_subtask(action='list', task_id='{task_id}')"
            }
        
        return examples
    
    def get_parameter_guidance(self, action: str) -> Dict[str, Any]:
        """Get detailed parameter guidance for the action."""
        guidance = {
            "applicable_parameters": [],
            "parameter_tips": {}
        }
        
        # Define parameters for each action
        action_params = {
            "create": ["task_id", "title", "description", "priority", "assignees", "progress_notes"],
            "update": ["task_id", "subtask_id", "title", "description", "status", "priority", "assignees", "progress_notes", "progress_percentage", "blockers", "insights_found"],
            "complete": ["task_id", "subtask_id", "completion_summary", "impact_on_parent", "insights_found"],
            "delete": ["task_id", "subtask_id"],
            "get": ["task_id", "subtask_id"],
            "list": ["task_id"]
        }
        
        guidance["applicable_parameters"] = action_params.get(action, [])
        
        # Parameter tips
        param_tips = {
            "title": {
                "requirement": "REQUIRED for create",
                "tip": "Make it specific and action-oriented",
                "examples": ["Implement user login", "Design database schema", "Write unit tests"]
            },
            "description": {
                "requirement": "Optional but recommended",
                "tip": "Provide context and acceptance criteria",
                "examples": ["Implement OAuth2 login with Google provider", "Design normalized schema for user data"]
            },
            "progress_notes": {
                "when_to_use": "Any time you make progress or encounter issues",
                "examples": ["Completed database schema design", "Fixed authentication bug", "Researching third-party integrations"],
                "best_practice": "Be specific about what was done",
                "tip": "Document progress for create/update actions"
            },
            "progress_percentage": {
                "requirement": "Optional (0-100)",
                "tip": "Automatically updates status: 0=todo, 1-99=in_progress, 100=done",
                "when_to_use": "Update action to track completion",
                "examples": [25, 50, 75, 100]
            },
            "blockers": {
                "when_to_use": "When something prevents progress",
                "examples": ["Missing API documentation", "Waiting for design approval", "Dependencies not available"],
                "tip": "Document blockers immediately"
            },
            "completion_summary": {
                "requirement": "HIGHLY RECOMMENDED for complete",
                "tip": "Summarize what was accomplished",
                "examples": ["Implemented secure user authentication with JWT", "Completed all CRUD operations for user management"]
            },
            "impact_on_parent": {
                "requirement": "Optional but valuable",
                "tip": "Explain how this helps complete the parent task",
                "examples": ["Authentication system now ready for frontend integration", "Database layer complete, unblocking API development"]
            },
            "insights_found": {
                "when_to_use": "When you discover something that could help others",
                "examples": ["Performance bottleneck in current approach", "Better library found for this use case"],
                "best_practice": "Share learnings that impact other subtasks or the parent",
                "tip": "List of insights discovered during work"
            }
        }
        
        # Only include tips for applicable parameters
        for param in guidance["applicable_parameters"]:
            if param in param_tips:
                guidance["parameter_tips"][param] = param_tips[param]
        
        return guidance
    
    def _generate_subtasks_overview(self, subtasks: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Generate overview for subtasks list."""
        total = len(subtasks)
        
        by_status = {
            "todo": [],
            "in_progress": [],
            "done": []
        }
        
        for subtask in subtasks:
            status = subtask.get("status", "todo")
            if status in by_status:
                by_status[status].append({
                    "id": subtask.get("id"),
                    "title": subtask.get("title"),
                    "assignees": subtask.get("assignees", [])
                })
        
        overview = {
            "total_subtasks": total,
            "by_status": by_status,
            "completion_rate": f"{len(by_status['done'])}/{total}" if total > 0 else "0/0",
            "recommendations": []
        }
        
        # Add recommendations
        if len(by_status["done"]) == total and total > 0:
            overview["recommendations"].append("All subtasks complete - parent task ready for completion")
        elif len(by_status["in_progress"]) > 3:
            overview["recommendations"].append("Many subtasks in progress - focus on completing some")
        elif len(by_status["todo"]) > 0 and len(by_status["in_progress"]) == 0:
            overview["recommendations"].append("Start work on pending subtasks")
        
        return overview