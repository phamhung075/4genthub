"""Enhanced Task workflow guidance implementation with autonomous AI capabilities."""

from typing import Dict, Any, List
from datetime import datetime, timezone

from ..base import WorkflowGuidanceInterface
from ...workflow_hint_enhancer import WorkflowHintEnhancer


class TaskWorkflowGuidance(WorkflowGuidanceInterface):
    """Provides enhanced workflow guidance for autonomous AI task management."""
    
    def __init__(self):
        """Initialize with enhanced workflow hint enhancer."""
        self.workflow_enhancer = WorkflowHintEnhancer()
    
    def enhance_response(self, response: Dict[str, Any], action: str, context: Dict[str, Any]) -> Dict[str, Any]:
        """
        Enhance response with autonomous AI workflow guidance.
        
        Args:
            response: Original response from task operation
            action: The action that was performed
            context: Context information including task details
            
        Returns:
            Enhanced response with autonomous workflow_guidance and multi-project coordination
        """
        if not response.get("success"):
            # Use enhanced error response handling
            return self.workflow_enhancer._enhance_error_response_v2(response, action, context)
            
        # Use the enhanced workflow hint enhancer for autonomous AI guidance
        # The enhanced system expects request_params instead of context
        request_params = context if isinstance(context, dict) else {}
        enhanced_response = self.workflow_enhancer.enhance_task_response(response, action, request_params)
        
        # Check if enhanced guidance is available; if not, fall back to legacy
        if "workflow_guidance" in enhanced_response and enhanced_response["workflow_guidance"]:
            # Enhanced autonomous guidance is available - merge with legacy features
            workflow_guidance = enhanced_response["workflow_guidance"]
        else:
            # Fall back to legacy workflow guidance
            workflow_guidance = {
                "current_state": self.analyze_state(response, context),
                "rules": self.get_rules(action, response),
                "next_actions": self.suggest_next_actions(action, response, context),
                "hints": self.generate_hints(action, response, context),
                "warnings": self.check_warnings(action, response, context),
                "examples": self.get_examples(action, context),
                "parameter_guidance": self.get_parameter_guidance(action)
            }
            enhanced_response["workflow_guidance"] = workflow_guidance
        
        # Add action-specific enhancements to both enhanced and legacy guidance
        if action == "create":
            if "tips" not in enhanced_response["workflow_guidance"]:
                enhanced_response["workflow_guidance"]["tips"] = [
                    "Break down complex tasks into subtasks for better tracking",
                    "Update progress regularly to maintain context", 
                    "Use descriptive completion summaries for knowledge retention"
                ]
        elif action == "list":
            enhanced_response["workflow_guidance"]["overview"] = self._generate_list_overview(response)
            # Add dependency overview for list actions
            enhanced_response["workflow_guidance"]["dependency_overview"] = self._generate_dependency_overview(response)
        elif action == "complete":
            enhanced_response["workflow_guidance"]["completion_checklist"] = [
                "✅ All acceptance criteria met",
                "✅ Code reviewed and tested",
                "✅ Documentation updated if needed",
                "✅ Completion summary provided",
                "✅ Testing notes documented",
                "✅ Any follow-up tasks created"
            ]
        elif action == "get":
            # Add dependency-specific guidance for get actions
            task = response.get("task", {})
            if task.get("dependency_relationships"):
                enhanced_response["workflow_guidance"]["dependency_guidance"] = self._generate_dependency_guidance(task)
        
        # Add AI reminders for certain actions
        if action in ["create", "get", "next"]:
            enhanced_response["ai_reminders"] = self._generate_ai_reminders(action, enhanced_response, context)
            
        return enhanced_response
    
    def analyze_state(self, response: Dict[str, Any], context: Dict[str, Any]) -> Dict[str, Any]:
        """Analyze current task state for contextual guidance."""
        state = {"phase": "unknown"}
        
        task = response.get("task", {})
        if task:
            status = task.get("status", "todo")
            progress = task.get("overall_progress", 0)
            subtask_count = len(task.get("subtasks", []))
            
            if status == "todo":
                state["phase"] = "not_started"
            elif status == "in_progress":
                if progress < 25:
                    state["phase"] = "early_progress"
                elif progress < 75:
                    state["phase"] = "mid_progress"
                else:
                    state["phase"] = "near_completion"
            elif status == "done":
                state["phase"] = "completed"
            elif status == "blocked":
                state["phase"] = "blocked"
                
            state["status"] = status
            state["progress"] = progress
            state["has_subtasks"] = subtask_count > 0
            state["subtask_count"] = subtask_count
            
        return state
    
    def get_rules(self, action: str, response: Dict[str, Any]) -> List[str]:
        """Get contextual rules for the current action."""
        rules = []
        
        # Universal rules
        rules.append("📝 Always provide context when updating tasks")
        rules.append("🔄 Update task status to reflect actual progress")
        
        # Action-specific rules
        if action == "create":
            rules.extend([
                "🎯 Make task titles specific and actionable",
                "📊 Include estimated effort for better planning",
                "🏷️ Use labels for categorization"
            ])
        elif action == "update":
            rules.extend([
                "💡 Document any blockers or challenges",
                "📈 Update progress percentage if applicable"
            ])
        elif action == "complete":
            rules.extend([
                "✅ Provide comprehensive completion summary",
                "🧪 Document testing performed",
                "📚 Share insights for future reference"
            ])
            
        return rules
    
    def suggest_next_actions(self, action: str, response: Dict[str, Any], context: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Suggest contextual next actions with examples."""
        suggestions = []
        
        task = response.get("task", {})
        task_id = task.get("id") or context.get("task_id")
        task_status = task.get("status", "todo")
        has_context = bool(task.get("context_id"))
        
        # STATE-AWARE SUGGESTIONS based on current task status
        if action == "create" and task_id:
            # CRITICAL: Add context creation as high priority
            if not has_context:
                suggestions.append({
                    "priority": "critical",
                    "action": "Create context",
                    "description": "REQUIRED: Create context before working - task completion will fail without this",
                    "example": {
                        "tool": "manage_context",
                        "params": {
                            "action": "create",
                            "level": "task",
                            "context_id": task_id,
                            "data": {"title": "Task Title", "description": "Task context"}
                        }
                    }
                })
            
            suggestions.append({
                "priority": "high",
                "action": "Start work",
                "description": "Update status to in_progress when you begin",
                "example": {
                    "action": "update",
                    "task_id": task_id,
                    "status": "in_progress",
                    "details": "Starting work on [describe what you're doing]"
                }
            })
            suggestions.append({
                "priority": "medium",
                "action": "Add subtasks",
                "description": "Break down complex work into subtasks",
                "example": {
                    "tool": "manage_subtask",
                    "params": {
                        "action": "create",
                        "task_id": task_id,
                        "title": "Implement core functionality",
                        "description": "Build the main feature component"
                    }
                }
            })
            
        elif task_status == "todo":
            # Task exists but not started
            if not has_context:
                suggestions.append({
                    "priority": "critical",
                    "action": "Create context first",
                    "description": "Context is required for task completion - create it now",
                    "example": {
                        "tool": "manage_context",
                        "params": {
                            "action": "create",
                            "level": "task",
                            "context_id": task_id,
                            "data": {"title": "Task Title", "description": "Task context"}
                        }
                    }
                })
            
            suggestions.append({
                "priority": "high", 
                "action": "Begin task",
                "description": "Start work by updating status",
                "example": {
                    "action": "update",
                    "task_id": task_id,
                    "status": "in_progress",
                    "details": "Starting work on [specific component/feature]"
                }
            })
            
        elif task_status == "in_progress":
            # Task is actively being worked on
            if not has_context:
                suggestions.append({
                    "priority": "critical",
                    "action": "Create context NOW",
                    "description": "URGENT: Context required for completion - create immediately",
                    "example": {
                        "tool": "manage_context",
                        "params": {
                            "action": "create",
                            "level": "task",
                            "context_id": task_id,
                            "data": {"title": "Task Title", "description": "Task context"}
                        }
                    }
                })
            
            # Progress tracking suggestions
            suggestions.append({
                "priority": "high",
                "action": "Track progress",
                "description": "Add progress notes to maintain context",
                "example": {
                    "tool": "manage_context",
                    "params": {
                        "action": "add_progress",
                        "level": "task",
                        "context_id": task_id,
                        "content": "Completed X, working on Y",
                        "agent": "ai_assistant"
                    }
                }
            })
            
            # Completion suggestions if high progress
            if task.get("overall_progress", 0) > 80:
                suggestions.append({
                    "priority": "high",
                    "action": "Complete task",
                    "description": "Task is nearly done - complete with summary",
                    "example": {
                        "action": "complete",
                        "task_id": task_id,
                        "completion_summary": "Successfully implemented [describe achievements]",
                        "testing_notes": "Tested [describe testing approach and results]"
                    }
                })
            else:
                suggestions.append({
                    "priority": "medium",
                    "action": "Update progress",
                    "description": "Document blockers if stuck, or progress if advancing",
                    "example": {
                        "action": "update",
                        "task_id": task_id,
                        "status": "in_progress",
                        "details": "Progress: [describe current work and next steps]"
                    }
                })
                
        elif task_status in ["review", "testing"]:
            # Task is in final stages
            if not has_context:
                suggestions.append({
                    "priority": "critical", 
                    "action": "Create context for completion",
                    "description": "REQUIRED: Context must exist before completing",
                    "example": {
                        "tool": "manage_context",
                        "params": {
                            "action": "create",
                            "level": "task",
                            "context_id": task_id,
                            "data": {"title": "Task Title", "description": "Task context"}
                        }
                    }
                })
            
            suggestions.append({
                "priority": "high",
                "action": "Complete task",
                "description": "Task is ready for completion",
                "example": {
                    "action": "complete",
                    "task_id": task_id,
                    "completion_summary": "Successfully completed [describe what was accomplished]",
                    "testing_notes": "Testing completed: [describe testing approach and results]"
                }
            })
            
        elif task_status == "blocked":
            # Task is blocked - provide recovery guidance
            suggestions.append({
                "priority": "high",
                "action": "Resolve blocker",
                "description": "Document the blocker and create resolution plan",
                "example": {
                    "action": "update", 
                    "task_id": task_id,
                    "details": "Blocked by: [specific issue]. Resolution plan: [steps to unblock]"
                }
            })
            
            suggestions.append({
                "priority": "medium",
                "action": "Create blocker task",
                "description": "Create separate task to resolve the blocking issue",
                "example": {
                    "action": "create",
                    "git_branch_id": "your_branch_id",
                    "title": "Resolve blocker: [issue description]",
                    "description": "Unblock task by addressing [specific blocking issue]"
                }
            })
            
        return suggestions
    
    def generate_hints(self, action: str, response: Dict[str, Any], context: Dict[str, Any]) -> List[str]:
        """Generate contextual hints with error recovery guidance."""
        hints = []
        
        task = response.get("task", {})
        has_context = bool(task.get("context_id"))
        
        # ERROR RECOVERY HINTS
        if not response.get("success"):
            error_msg = response.get("error", "").lower()
            if "validation error" in error_msg:
                hints.append("🔧 VALIDATION ERROR RECOVERY: Use arrays like labels=['tag1','tag2'], not strings")
                hints.append("📝 For progress_percentage, use integers 0-100: progress_percentage=50")
            elif "context must be updated" in error_msg:
                hints.append("🔧 CONTEXT ERROR RECOVERY: Run manage_context(action='create', level='task', context_id='your_task_id', data={'title': 'Task Title'})")
                hints.append("📋 Then update context with manage_context(action='update', level='task', context_id='task_id', data={'status': 'done'})")
            elif "missing required" in error_msg:
                hints.append("🔧 MISSING FIELD RECOVERY: Check the error for required fields and add them")
                hints.append("📚 Use workflow guidance examples for correct parameter format")
        
        # REGULAR CONTEXTUAL HINTS
        if action == "create":
            hints.append("💡 Consider adding subtasks if this work has multiple components")
            hints.append("🎯 Set a realistic estimated_effort to help with planning")
            if not has_context:
                hints.append("⚠️ CRITICAL: Create context immediately after task creation")
            hints.append("🔧 If validation fails: Use arrays for labels=['tag1','tag2'], not strings")
            
        elif action == "list":
            task_count = response.get("count", 0)
            if task_count > 10:
                hints.append("📋 Many tasks found - consider using filters to narrow results")
                hints.append("🔍 Try: status='in_progress' or priority='high' to filter")
            if task_count == 0:
                hints.append("🚀 No tasks found - create one to get started")
                hints.append("💡 Check if you're in the right git branch with git_branch_id parameter")
                
        elif action == "update":
            task_status = task.get("status")
            if task_status == "blocked":
                hints.append("🚧 Task is blocked - document the blocker in details field")
                hints.append("💭 Consider creating a separate task to resolve the blocker")
            elif task_status == "in_progress" and not has_context:
                hints.append("🚨 URGENT: Create context now - completion will fail without it")
            elif task_status == "in_progress":
                hints.append("📈 Track progress with manage_context(action='add_progress', level='task', context_id='task_id', content='Progress update')")
                hints.append("🔄 Update parent task progress syncs automatically from subtasks")
                
        elif action == "complete":
            if not has_context:
                hints.append("🚨 COMPLETION WILL FAIL: Create context first with manage_context")
            hints.append("📝 Detailed completion summaries help with knowledge retention")
            hints.append("🧪 Document testing approach for future reference")
            hints.append("🎯 Include specific achievements and next recommendations")
            
        elif action == "search":
            hints.append("🔍 Use specific keywords for better search results")
            hints.append("💡 Search in title, description, and labels fields")
            
        # Context synchronization hints
        subtask_count = len(task.get("subtasks", []))
        if subtask_count > 0:
            hints.append("🔗 Subtask progress automatically updates parent task statistics")
            
        return hints
    
    def check_warnings(self, action: str, response: Dict[str, Any], context: Dict[str, Any]) -> List[str]:
        """Check for potential issues and generate warnings."""
        warnings = []
        
        task = response.get("task", {})
        
        # CRITICAL: Context requirement warning for task completion
        if task.get("status") in ["in_progress", "review", "testing"] and not task.get("context_id"):
            warnings.append("🚨 CRITICAL: Create context before completing this task!")
            warnings.append("💡 Use: manage_context(action='create', level='task', context_id='{task_id}', data={{'title': 'Task Title'}})".format(task_id=task.get("id", "task-id")))
        
        # Context completion readiness check
        if action in ["update", "complete"] and task.get("status") in ["in_progress", "review"]:
            if not task.get("context_id"):
                warnings.append("⚠️ Task completion will FAIL without context. Create context first!")
        
        # Missing completion summary warning (enhanced with recovery steps)
        if action == "complete" and not context.get("completion_summary"):
            warnings.append("⚠️ No completion summary provided - context will be lost")
            warnings.append("💡 Recovery: Add completion_summary parameter describing what was accomplished")
        
        # Check for stale tasks
        if task.get("status") == "in_progress":
            updated_at = task.get("updated_at")
            if updated_at:
                # Parse timestamp and check if older than 7 days
                try:
                    last_update = datetime.fromisoformat(updated_at.replace('Z', '+00:00'))
                    days_old = (datetime.now(timezone.utc) - last_update).days
                    if days_old > 7:
                        warnings.append(f"⚠️ Task hasn't been updated in {days_old} days")
                        warnings.append("💡 Consider updating progress or changing status to 'blocked'")
                except:
                    pass
        
        # Parameter validation recovery hints
        if action == "create" and response.get("success"):
            warnings.append("💡 TIP: If you get validation errors, use arrays like labels=['tag1','tag2'] not strings")
        
        # Progress synchronization warning  
        if action == "update" and task.get("status") == "in_progress":
            subtask_count = len(task.get("subtasks", []))
            if subtask_count > 0:
                warnings.append("💡 Remember: Subtask progress updates automatically sync to parent task")
        
        # Check for too many in-progress tasks
        if action == "list":
            in_progress = len([t for t in response.get("tasks", []) if t.get("status") == "in_progress"])
            if in_progress > 5:
                warnings.append(f"⚠️ {in_progress} tasks in progress - consider completing some first")
                warnings.append("💡 Use manage_task(action='list', status='in_progress') to review active tasks")
                
        return warnings
    
    def get_examples(self, action: str, context: Dict[str, Any]) -> Dict[str, Any]:
        """Get relevant examples for the current action."""
        examples = {}
        
        task_id = context.get("task_id", "task-id")
        git_branch_id = context.get("git_branch_id", "branch-id")
        
        if action == "create":
            examples["create_basic"] = {
                "description": "Create a simple task",
                "command": f'manage_task(action="create", git_branch_id="{git_branch_id}", title="Implement user authentication", description="Add login and logout functionality")'
            }
            examples["create_detailed"] = {
                "description": "Create task with full details",
                "command": f'manage_task(action="create", git_branch_id="{git_branch_id}", title="Build API endpoints", description="RESTful API for user management", priority="high", estimated_effort="3 days", labels=["backend", "api"])'
            }
            
        elif action == "update":
            examples["update_status"] = {
                "description": "Update task status and add progress notes",
                "command": f'manage_task(action="update", task_id="{task_id}", status="in_progress", details="Completed database schema, working on API endpoints")'
            }
            examples["update_blocked"] = {
                "description": "Mark task as blocked with reason",
                "command": f'manage_task(action="update", task_id="{task_id}", status="blocked", details="Waiting for API credentials from third-party service")'
            }
            
        elif action == "complete":
            examples["complete_basic"] = {
                "description": "Complete task with summary",
                "command": f'manage_task(action="complete", task_id="{task_id}", completion_summary="Implemented full authentication flow with JWT tokens")'
            }
            examples["complete_detailed"] = {
                "description": "Complete with testing notes",
                "command": f'manage_task(action="complete", task_id="{task_id}", completion_summary="Built complete user management API", testing_notes="Added unit tests for all endpoints, integration tests for auth flow, 95% code coverage")'
            }
            
        elif action == "list":
            examples["list_filtered"] = {
                "description": "List tasks with filters",
                "command": f'manage_task(action="list", git_branch_id="{git_branch_id}", status="in_progress", priority="high")'
            }
            examples["list_all"] = {
                "description": "List all tasks in branch",
                "command": f'manage_task(action="list", git_branch_id="{git_branch_id}")'
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
            "create": ["git_branch_id", "title", "description", "priority", "estimated_effort", "labels", "assignees", "due_date"],
            "update": ["task_id", "title", "description", "status", "priority", "details", "estimated_effort", "labels", "assignees", "due_date"],
            "complete": ["task_id", "completion_summary", "testing_notes"],
            "get": ["task_id", "include_context"],
            "list": ["git_branch_id", "status", "priority", "assignees", "labels", "limit"],
            "search": ["query", "git_branch_id", "limit"],
            "next": ["git_branch_id", "include_context"],
            "add_dependency": ["task_id", "dependency_id"],
            "remove_dependency": ["task_id", "dependency_id"]
        }
        
        guidance["applicable_parameters"] = action_params.get(action, [])
        
        # Add parameter-specific tips
        param_tips = {
            "title": {
                "requirement": "REQUIRED for create",
                "tip": "Be specific and action-oriented",
                "examples": ["Implement user authentication", "Fix database connection leak", "Add unit tests for payment module"]
            },
            "description": {
                "requirement": "Optional but recommended",
                "tip": "Include acceptance criteria and technical approach",
                "examples": ["Add JWT-based authentication with refresh tokens", "Implement connection pooling to prevent memory leaks"]
            },
            "status": {
                "requirement": "Optional",
                "tip": "Use to track task progress",
                "values": ["todo", "in_progress", "blocked", "review", "testing", "done", "cancelled"],
                "auto_behavior": "Automatically set to 'todo' on create, 'done' on complete"
            },
            "priority": {
                "requirement": "Optional (default: medium)",
                "tip": "Helps with task prioritization",
                "values": ["low", "medium", "high", "urgent", "critical"]
            },
            "details": {
                "requirement": "Optional",
                "tip": "Use for progress updates and additional context",
                "when_to_use": "When updating task progress or documenting blockers",
                "examples": ["Completed login UI, working on password reset", "Blocked by missing API documentation"]
            },
            "estimated_effort": {
                "requirement": "Optional but valuable",
                "tip": "Helps with sprint planning and workload management",
                "examples": ["2 hours", "3 days", "1 week", "2 sprints"]
            },
            "completion_summary": {
                "requirement": "HIGHLY RECOMMENDED for complete",
                "tip": "Document what was accomplished for future reference",
                "best_practice": "Include key decisions, implementation details, and outcomes",
                "examples": ["Implemented JWT auth with 2FA support, added password reset flow, integrated with existing user service"]
            },
            "testing_notes": {
                "requirement": "Optional but valuable",
                "tip": "Document testing approach and coverage",
                "examples": ["Added unit tests with 90% coverage", "Manual testing completed on staging", "Load tested with 1000 concurrent users"]
            },
            "include_context": {
                "requirement": "Optional (default: false)",
                "tip": "Set to true for detailed task context and AI insights",
                "when_to_use": "When you need vision system insights or detailed context"
            }
        }
        
        # Only include tips for applicable parameters
        for param in guidance["applicable_parameters"]:
            if param in param_tips:
                guidance["parameter_tips"][param] = param_tips[param]
                
        return guidance
    
    def _generate_ai_reminders(self, action: str, response: Dict[str, Any], context: Dict[str, Any]) -> Dict[str, Any]:
        """Generate AI-specific reminders and examples."""
        reminders = {}
        
        task = response.get("task", {})
        task_id = task.get("id") or context.get("task_id")
        
        if action == "create":
            reminders["important"] = "📝 Remember to update task status when you start working!"
            reminders["next_step"] = "Update status to 'in_progress' when beginning work"
            reminders["example"] = {
                "tool": "manage_task",
                "params": {
                    "action": "update",
                    "task_id": task_id,
                    "status": "in_progress",
                    "details": "Starting implementation"
                }
            }
            
        elif action == "get":
            reminders["important"] = "📝 Remember to update progress and context!"
            reminders["update_example"] = {
                "tool": "manage_task",
                "params": {
                    "action": "update",
                    "task_id": task_id,
                    "details": "Describe what you've done",
                    "status": "in_progress"
                }
            }
            reminders["completion_example"] = {
                "tool": "manage_task",
                "params": {
                    "action": "complete",
                    "task_id": task_id,
                    "completion_summary": "Brief summary of what was accomplished",
                    "testing_notes": "Description of tests performed"
                }
            }
            reminders["next_step"] = "Start by updating status to 'in_progress'" if task.get("status") == "todo" else "Continue working and update progress"
            
        return reminders
    
    def _generate_list_overview(self, response: Dict[str, Any]) -> Dict[str, Any]:
        """Generate overview for list action."""
        tasks = response.get("tasks", [])
        total = len(tasks)
        
        by_status = {}
        by_priority = {}
        
        for task in tasks:
            status = task.get("status", "unknown")
            priority = task.get("priority", "medium")
            
            if status not in by_status:
                by_status[status] = []
            by_status[status].append({
                "id": task.get("id"),
                "title": task.get("title"),
                "priority": priority
            })
            
            if priority not in by_priority:
                by_priority[priority] = 0
            by_priority[priority] += 1
            
        overview = {
            "total_tasks": total,
            "by_status": by_status,
            "by_priority": by_priority,
            "recommendations": []
        }
        
        # Add recommendations based on overview
        if by_status.get("blocked", []):
            overview["recommendations"].append("Address blocked tasks to unblock progress")
        if by_status.get("in_progress", []) and len(by_status["in_progress"]) > 3:
            overview["recommendations"].append("Focus on completing in-progress tasks before starting new ones")
        if not by_status.get("in_progress") and by_status.get("todo"):
            overview["recommendations"].append("Start working on pending tasks")
            
        return overview
    
    def _generate_dependency_overview(self, response: Dict[str, Any]) -> Dict[str, Any]:
        """Generate dependency overview for list action"""
        tasks = response.get("tasks", [])
        
        overview = {
            "total_tasks": len(tasks),
            "blocked_tasks": 0,
            "blocking_tasks": 0,
            "ready_tasks": 0,
            "dependency_chains": 0,
            "recommendations": []
        }
        
        for task in tasks:
            dep_summary = task.get("dependency_summary", {})
            if dep_summary.get("is_blocked"):
                overview["blocked_tasks"] += 1
            if dep_summary.get("is_blocking_others"):
                overview["blocking_tasks"] += 1
            if dep_summary.get("can_start"):
                overview["ready_tasks"] += 1
        
        # Add recommendations
        if overview["blocked_tasks"] > 0:
            overview["recommendations"].append(f"🚧 {overview['blocked_tasks']} task(s) are blocked - work on dependencies first")
        
        if overview["blocking_tasks"] > 0:
            overview["recommendations"].append(f"🔓 {overview['blocking_tasks']} task(s) are blocking others - prioritize these")
        
        if overview["ready_tasks"] > 0:
            overview["recommendations"].append(f"✅ {overview['ready_tasks']} task(s) are ready to start")
        
        return overview
    
    def _generate_dependency_guidance(self, task: Dict[str, Any]) -> Dict[str, Any]:
        """Generate dependency-specific guidance for a task"""
        dep_rel = task.get("dependency_relationships", {})
        
        guidance = {
            "dependency_status": "unknown",
            "recommendations": [],
            "dependency_chain_info": [],
            "workflow_actions": []
        }
        
        summary = dep_rel.get("summary", {})
        workflow = dep_rel.get("workflow", {})
        
        # Determine dependency status
        if summary.get("can_start"):
            guidance["dependency_status"] = "ready"
            guidance["recommendations"].append("✅ Task is ready to start - no blocking dependencies")
        elif summary.get("is_blocked"):
            guidance["dependency_status"] = "blocked"
            guidance["recommendations"].append("🚧 Task is blocked by dependencies")
        else:
            guidance["dependency_status"] = "waiting"
            guidance["recommendations"].append("⏳ Task is waiting for dependencies to complete")
        
        # Add workflow actions
        guidance["workflow_actions"] = workflow.get("next_actions", [])
        
        # Add dependency chain information
        for chain in dep_rel.get("dependency_chains", []):
            chain_info = {
                "chain_id": chain["chain_id"],
                "status": chain["chain_status"],
                "progress": f"{chain['completed_tasks']}/{chain['total_tasks']} tasks completed",
                "completion_percentage": chain["completion_percentage"]
            }
            if chain.get("next_task"):
                chain_info["next_task"] = chain["next_task"]["title"]
            guidance["dependency_chain_info"].append(chain_info)
        
        # Add blocking information
        blocking_info = workflow.get("blocking_info", {})
        if blocking_info.get("is_blocked"):
            guidance["blocking_details"] = {
                "blocking_tasks": len(blocking_info.get("blocking_tasks", [])),
                "blocking_chains": len(blocking_info.get("blocking_chains", [])),
                "resolution_suggestions": blocking_info.get("resolution_suggestions", [])
            }
        
        return guidance