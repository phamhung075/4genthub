"""Git Branch Workflow Guidance Implementation

Provides comprehensive guidance for Git Branch Management operations.
"""

from typing import Dict, Any, Optional, List
from ..base import BaseWorkflowGuidance


class GitBranchWorkflowGuidance(BaseWorkflowGuidance):
    """Workflow guidance for Git Branch Management operations."""
    
    def generate_guidance(self, action: str, context: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """Generate comprehensive workflow guidance for git branch operations."""
        
        return {
            "current_state": self._determine_state(action, context),
            "rules": self._get_git_branch_rules(),
            "next_actions": self._get_next_actions(action, context),
            "hints": self._get_hints(action),
            "warnings": self._get_warnings(action),
            "examples": self._get_examples(action, context),
            "parameter_guidance": self._get_parameter_guidance(action)
        }
    
    def _determine_state(self, action: str, context: Optional[Dict[str, Any]] = None) -> Dict[str, str]:
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
            "restore": "branch_restoration"
        }.get(action, "unknown")
        
        return {
            "phase": phase,
            "action": action,
            "context": "git_branch_management"
        }
    
    def _get_git_branch_rules(self) -> List[str]:
        """Get essential rules for git branch management."""
        return [
            "🌿 RULE: Branch names should be descriptive and follow naming conventions (e.g., feature/user-auth, bugfix/login-issue)",
            "📋 RULE: Always assign branches to specific projects - branches cannot exist without a project",
            "🚀 RULE: Active branches should have assigned agents for autonomous work",
            "🔄 RULE: Branch statistics update automatically when tasks are created/completed",
            "⚠️ RULE: Deleting a branch will cascade delete all associated tasks - use archive instead for soft delete",
            "🏷️ RULE: Branch description should clearly state the purpose and scope of work",
            "👥 RULE: Multiple agents can be assigned to a branch for collaboration",
            "📊 RULE: Use get_statistics to monitor branch progress and task completion"
        ]
    
    def _get_next_actions(self, action: str, context: Optional[Dict[str, Any]] = None) -> List[Dict[str, Any]]:
        """Get context-aware next actions with priorities."""
        project_id = context.get("project_id") if context else None
        git_branch_id = context.get("git_branch_id") if context else None
        
        next_actions = []
        
        if action == "create":
            next_actions.extend([
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
                            "agent_id": "agent_id"
                        }
                    }
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
                            "description": "Detailed requirements..."
                        }
                    }
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
                            "git_branch_id": "created_branch_id"
                        }
                    }
                }
            ])
            
        elif action == "list":
            next_actions.extend([
                {
                    "priority": "high",
                    "action": "Select a branch to work on",
                    "description": "Choose a specific branch and get its details",
                    "example": {
                        "tool": "manage_git_branch",
                        "params": {
                            "action": "get",
                            "project_id": project_id or "project_id",
                            "git_branch_id": "selected_branch_id"
                        }
                    }
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
                            "git_branch_description": "Implement new feature X"
                        }
                    }
                }
            ])
            
        elif action == "get":
            next_actions.extend([
                {
                    "priority": "high",
                    "action": "List tasks on this branch",
                    "description": "See all tasks associated with this branch",
                    "example": {
                        "tool": "manage_task",
                        "params": {
                            "action": "list",
                            "git_branch_id": git_branch_id or "branch_id"
                        }
                    }
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
                            "git_branch_id": git_branch_id or "branch_id"
                        }
                    }
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
                            "git_branch_description": "Updated description"
                        }
                    }
                }
            ])
            
        elif action == "assign_agent":
            next_actions.extend([
                {
                    "priority": "high",
                    "action": "Get next task for agent",
                    "description": "Agent should start working on tasks",
                    "example": {
                        "tool": "manage_task",
                        "params": {
                            "action": "next",
                            "git_branch_id": git_branch_id or "branch_id",
                            "include_context": True
                        }
                    }
                },
                {
                    "priority": "medium",
                    "action": "List all agents on branch",
                    "description": "See who else is working on this branch",
                    "example": {
                        "tool": "manage_agent",
                        "params": {
                            "action": "list",
                            "project_id": project_id or "project_id"
                        }
                    }
                }
            ])
            
        elif action == "delete":
            next_actions.extend([
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
                            "git_branch_description": "Next feature to implement"
                        }
                    }
                },
                {
                    "priority": "medium",
                    "action": "List remaining branches",
                    "description": "See what other branches exist",
                    "example": {
                        "tool": "manage_git_branch",
                        "params": {
                            "action": "list",
                            "project_id": project_id or "project_id"
                        }
                    }
                }
            ])
        
        return next_actions
    
    def _get_hints(self, action: str) -> List[str]:
        """Get action-specific hints."""
        hints = {
            "create": [
                "💡 Use descriptive branch names like 'feature/user-authentication' or 'bugfix/login-timeout'",
                "🔍 Include a clear description of what work will be done on this branch",
                "👥 Consider assigning an agent immediately after creation for autonomous work"
            ],
            "list": [
                "📊 Review branch statistics to identify which branches need attention",
                "🎯 Look for branches with incomplete tasks that need work",
                "🔄 Consider archiving old branches instead of deleting them"
            ],
            "get": [
                "📈 Use this to understand the current state and progress of a branch",
                "🔗 Branch ID is required - get it from list action first",
                "📋 Follow up with task list to see detailed work items"
            ],
            "update": [
                "✏️ Update descriptions to reflect current work scope",
                "🏷️ Branch names can be updated if naming conventions change",
                "📝 Keep descriptions current for better team understanding"
            ],
            "delete": [
                "⚠️ WARNING: This will delete ALL tasks on the branch",
                "💾 Consider using 'archive' action instead for soft delete",
                "🔄 Archived branches can be restored later if needed"
            ],
            "assign_agent": [
                "🤖 Agents will autonomously work on tasks in this branch",
                "👥 Multiple agents can collaborate on the same branch",
                "🎯 Assign specialized agents based on the work type"
            ],
            "unassign_agent": [
                "🔄 Agent's work will be preserved when unassigned",
                "📋 Consider reassigning to another agent for continuity",
                "✅ Complete or hand off tasks before unassigning"
            ],
            "get_statistics": [
                "📊 Statistics update automatically as tasks progress",
                "📈 Use this to monitor branch health and progress",
                "🎯 Identify bottlenecks or stalled work"
            ],
            "archive": [
                "💾 Soft delete - branch and tasks are preserved",
                "🔄 Can be restored later with 'restore' action",
                "📦 Good for completed features or abandoned work"
            ],
            "restore": [
                "♻️ Brings back archived branches with all tasks intact",
                "📋 Review branch content before restoring",
                "🔄 Consider if work is still relevant before restoring"
            ]
        }
        return hints.get(action, ["💡 Check action parameter for available operations"])
    
    def _get_warnings(self, action: str) -> List[str]:
        """Get action-specific warnings."""
        warnings = []
        
        if action == "create":
            warnings.append("🚨 Branch name must be unique within the project")
            warnings.append("📋 Always provide a meaningful description for clarity")
            
        elif action == "delete":
            warnings.append("🚨 CRITICAL: This will permanently delete ALL tasks on the branch!")
            warnings.append("⚠️ This action cannot be undone - consider 'archive' instead")
            warnings.append("💡 Use: manage_git_branch(action='archive') for soft delete")
            
        elif action == "update":
            warnings.append("⚠️ Changing branch name may affect external references")
            warnings.append("📋 Ensure updated info doesn't conflict with other branches")
            
        elif action == "assign_agent":
            warnings.append("🤖 Ensure agent exists before assignment")
            warnings.append("📋 Agent will start processing tasks immediately")
            
        elif action == "archive":
            warnings.append("📦 Archived branches won't appear in normal listings")
            warnings.append("🔄 Tasks remain intact but won't be processed")
        
        return warnings
    
    def _get_examples(self, action: str, context: Optional[Dict[str, Any]] = None) -> List[Dict[str, Any]]:
        """Get action-specific examples."""
        examples = []
        
        if action == "create":
            examples.append({
                "description": "Create a feature branch",
                "code": """manage_git_branch(
    action="create",
    project_id="my_project_id",
    git_branch_name="feature/user-authentication",
    git_branch_description="Implement JWT-based authentication with login, logout, and session management"
)"""
            })
            
        elif action == "list":
            examples.append({
                "description": "List all branches in a project",
                "code": """manage_git_branch(
    action="list",
    project_id="my_project_id"
)"""
            })
            
        elif action == "get":
            examples.append({
                "description": "Get branch details",
                "code": """manage_git_branch(
    action="get",
    project_id="my_project_id",
    git_branch_id="branch_uuid"
)"""
            })
            
        elif action == "assign_agent":
            examples.append({
                "description": "Assign an agent to work on a branch",
                "code": """manage_git_branch(
    action="assign_agent",
    project_id="my_project_id",
    git_branch_id="branch_uuid",
    agent_id="agent_uuid"
)"""
            })
            
        elif action == "get_statistics":
            examples.append({
                "description": "Check branch progress",
                "code": """manage_git_branch(
    action="get_statistics",
    project_id="my_project_id",
    git_branch_id="branch_uuid"
)"""
            })
        
        return examples
    
    def _get_parameter_guidance(self, action: str) -> Dict[str, Dict[str, str]]:
        """Get parameter-specific guidance."""
        base_params = {
            "project_id": {
                "requirement": "REQUIRED for all actions",
                "format": "UUID string",
                "tip": "Get from manage_project(action='list') or project context"
            }
        }
        
        action_params = {
            "create": {
                "git_branch_name": {
                    "requirement": "REQUIRED",
                    "format": "String following naming convention",
                    "tip": "Use prefixes like feature/, bugfix/, hotfix/, refactor/"
                },
                "git_branch_description": {
                    "requirement": "OPTIONAL but recommended",
                    "format": "Detailed string",
                    "tip": "Describe the purpose, scope, and goals of this branch"
                }
            },
            "get": {
                "git_branch_id": {
                    "requirement": "REQUIRED",
                    "format": "UUID string",
                    "tip": "Get from list action or previous create response"
                }
            },
            "update": {
                "git_branch_id": {
                    "requirement": "REQUIRED",
                    "format": "UUID string",
                    "tip": "Branch to update"
                },
                "git_branch_name": {
                    "requirement": "OPTIONAL",
                    "format": "String",
                    "tip": "New name if renaming branch"
                },
                "git_branch_description": {
                    "requirement": "OPTIONAL",
                    "format": "String",
                    "tip": "Updated description"
                }
            },
            "delete": {
                "git_branch_id": {
                    "requirement": "REQUIRED",
                    "format": "UUID string",
                    "tip": "⚠️ Will cascade delete all tasks!"
                }
            },
            "assign_agent": {
                "git_branch_id": {
                    "requirement": "REQUIRED (or git_branch_name)",
                    "format": "UUID string",
                    "tip": "Branch to assign agent to"
                },
                "agent_id": {
                    "requirement": "REQUIRED",
                    "format": "UUID string",
                    "tip": "Get from manage_agent(action='list')"
                }
            },
            "get_statistics": {
                "git_branch_id": {
                    "requirement": "REQUIRED",
                    "format": "UUID string",
                    "tip": "Branch to analyze"
                }
            }
        }
        
        params = base_params.copy()
        if action in action_params:
            params.update(action_params[action])
        
        return params