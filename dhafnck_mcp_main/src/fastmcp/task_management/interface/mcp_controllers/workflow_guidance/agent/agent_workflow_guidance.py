"""Agent Workflow Guidance Implementation

Provides comprehensive guidance for Agent Management operations.
"""

from typing import Dict, Any, Optional, List
from ..base import BaseWorkflowGuidance


class AgentWorkflowGuidance(BaseWorkflowGuidance):
    """Workflow guidance for Agent Management operations."""
    
    def generate_guidance(self, action: str, context: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """Generate comprehensive workflow guidance for agent operations."""
        
        return {
            "current_state": self._determine_state(action, context),
            "rules": self._get_agent_rules(),
            "next_actions": self._get_next_actions(action, context),
            "hints": self._get_hints(action),
            "warnings": self._get_warnings(action),
            "examples": self._get_examples(action, context),
            "parameter_guidance": self._get_parameter_guidance(action)
        }
    
    def _determine_state(self, action: str, context: Optional[Dict[str, Any]] = None) -> Dict[str, str]:
        """Determine the current workflow state."""
        phase = {
            "register": "agent_registration",
            "assign": "agent_assignment",
            "get": "agent_retrieval",
            "list": "agent_listing",
            "update": "agent_modification",
            "unassign": "agent_removal",
            "unregister": "agent_deregistration",
            "rebalance": "agent_rebalancing"
        }.get(action, "unknown")
        
        return {
            "phase": phase,
            "action": action,
            "context": "agent_management"
        }
    
    def _get_agent_rules(self) -> List[str]:
        """Get essential rules for agent management."""
        return [
            "🤖 RULE: Each agent must have a unique identifier within a project",
            "📋 RULE: Agents must be registered before they can be assigned to branches",
            "🌿 RULE: Agents can be assigned to multiple branches for parallel work",
            "🔄 RULE: Agent workload is tracked across all assigned branches",
            "👥 RULE: Multiple agents can collaborate on the same branch",
            "🎯 RULE: Agents should have specialized roles (e.g., @frontend_agent, @testing_agent)",
            "⚖️ RULE: Use rebalance to distribute work evenly among agents",
            "🏷️ RULE: Agent names should reflect their specialization or role"
        ]
    
    def _get_next_actions(self, action: str, context: Optional[Dict[str, Any]] = None) -> List[Dict[str, Any]]:
        """Get context-aware next actions with priorities."""
        project_id = context.get("project_id") if context else None
        agent_id = context.get("agent_id") if context else None
        
        next_actions = []
        
        if action == "register":
            next_actions.extend([
                {
                    "priority": "high",
                    "action": "Assign agent to a branch",
                    "description": "Put the agent to work on a specific branch",
                    "example": {
                        "tool": "manage_git_branch",
                        "params": {
                            "action": "assign_agent",
                            "project_id": project_id or "project_id",
                            "git_branch_id": "branch_id",
                            "agent_id": "registered_agent_id"
                        }
                    }
                },
                {
                    "priority": "medium",
                    "action": "List available branches",
                    "description": "See which branches need agents",
                    "example": {
                        "tool": "manage_git_branch",
                        "params": {
                            "action": "list",
                            "project_id": project_id or "project_id"
                        }
                    }
                },
                {
                    "priority": "low",
                    "action": "Update agent details",
                    "description": "Modify agent name or capabilities",
                    "example": {
                        "tool": "manage_agent",
                        "params": {
                            "action": "update",
                            "project_id": project_id or "project_id",
                            "agent_id": "registered_agent_id",
                            "name": "specialized-agent-v2"
                        }
                    }
                }
            ])
            
        elif action == "list":
            next_actions.extend([
                {
                    "priority": "high",
                    "action": "Get specific agent details",
                    "description": "View detailed information about an agent",
                    "example": {
                        "tool": "manage_agent",
                        "params": {
                            "action": "get",
                            "project_id": project_id or "project_id",
                            "agent_id": "selected_agent_id"
                        }
                    }
                },
                {
                    "priority": "medium",
                    "action": "Register a new agent",
                    "description": "Add a new specialized agent to the project",
                    "example": {
                        "tool": "manage_agent",
                        "params": {
                            "action": "register",
                            "project_id": project_id or "project_id",
                            "name": "new-specialist-agent",
                            "call_agent": "@specialist_agent"
                        }
                    }
                },
                {
                    "priority": "medium",
                    "action": "Rebalance workload",
                    "description": "Redistribute work among agents",
                    "example": {
                        "tool": "manage_agent",
                        "params": {
                            "action": "rebalance",
                            "project_id": project_id or "project_id"
                        }
                    }
                }
            ])
            
        elif action == "assign":
            next_actions.extend([
                {
                    "priority": "high",
                    "action": "Have agent get next task",
                    "description": "Agent should start working on tasks",
                    "example": {
                        "tool": "manage_task",
                        "params": {
                            "action": "next",
                            "git_branch_id": "assigned_branch_id",
                            "include_context": True
                        }
                    }
                },
                {
                    "priority": "medium",
                    "action": "Check agent workload",
                    "description": "See all branches this agent is working on",
                    "example": {
                        "tool": "manage_agent",
                        "params": {
                            "action": "get",
                            "project_id": project_id or "project_id",
                            "agent_id": agent_id or "agent_id"
                        }
                    }
                }
            ])
            
        elif action == "unassign":
            next_actions.extend([
                {
                    "priority": "high",
                    "action": "Reassign to another agent",
                    "description": "Assign a different agent to continue the work",
                    "example": {
                        "tool": "manage_git_branch",
                        "params": {
                            "action": "assign_agent",
                            "project_id": project_id or "project_id",
                            "git_branch_id": "branch_id",
                            "agent_id": "replacement_agent_id"
                        }
                    }
                },
                {
                    "priority": "medium",
                    "action": "Check branch status",
                    "description": "Review work status on the branch",
                    "example": {
                        "tool": "manage_git_branch",
                        "params": {
                            "action": "get_statistics",
                            "project_id": project_id or "project_id",
                            "git_branch_id": "branch_id"
                        }
                    }
                }
            ])
            
        elif action == "rebalance":
            next_actions.extend([
                {
                    "priority": "high",
                    "action": "Review agent assignments",
                    "description": "Check the new workload distribution",
                    "example": {
                        "tool": "manage_agent",
                        "params": {
                            "action": "list",
                            "project_id": project_id or "project_id"
                        }
                    }
                },
                {
                    "priority": "medium",
                    "action": "Monitor agent progress",
                    "description": "Track how agents handle their new workload",
                    "example": {
                        "tool": "manage_task",
                        "params": {
                            "action": "list",
                            "status": "in_progress"
                        }
                    }
                }
            ])
        
        return next_actions
    
    def _get_hints(self, action: str) -> List[str]:
        """Get action-specific hints."""
        hints = {
            "register": [
                "💡 Use descriptive agent names that indicate their specialization",
                "🔍 The call_agent parameter should match the agent's @handle format",
                "🤖 Consider creating agents for specific roles: frontend, backend, testing, docs"
            ],
            "list": [
                "📊 Review agent workload to identify who might need help",
                "🎯 Look for agents with fewer assignments for new work",
                "⚖️ Consider rebalancing if workload is uneven"
            ],
            "get": [
                "📈 Check agent's current branch assignments and workload",
                "🔗 Agent details show all active assignments",
                "📋 Use this to understand an agent's specialization"
            ],
            "assign": [
                "🌿 Agents can work on multiple branches simultaneously",
                "🤝 Multiple agents can collaborate on the same branch",
                "🎯 Match agent specialization to branch requirements"
            ],
            "update": [
                "✏️ Update agent names to reflect evolved capabilities",
                "🏷️ Keep agent metadata current for better organization",
                "📝 Document agent capabilities in the name or metadata"
            ],
            "unassign": [
                "🔄 Agent's completed work remains on the branch",
                "📋 Consider documenting handoff in task context",
                "✅ Ensure critical tasks are completed or handed off"
            ],
            "unregister": [
                "⚠️ Unassign agent from all branches first",
                "📦 Agent's work history is preserved in tasks",
                "🔄 Can re-register the agent later if needed"
            ],
            "rebalance": [
                "⚖️ Automatically redistributes work based on capacity",
                "📊 Considers task priorities and agent specializations",
                "🔄 Run periodically for optimal performance"
            ]
        }
        return hints.get(action, ["💡 Check action parameter for available operations"])
    
    def _get_warnings(self, action: str) -> List[str]:
        """Get action-specific warnings."""
        warnings = []
        
        if action == "register":
            warnings.append("🚨 Agent ID must be unique within the project")
            warnings.append("📋 Agent name should clearly indicate its purpose")
            
        elif action == "assign":
            warnings.append("⚠️ Ensure agent exists before assignment")
            warnings.append("🔄 Agent will start processing tasks immediately")
            
        elif action == "unassign":
            warnings.append("📋 In-progress work should be completed or reassigned")
            warnings.append("⚠️ Agent will stop processing new tasks on this branch")
            
        elif action == "unregister":
            warnings.append("🚨 Agent must be unassigned from all branches first")
            warnings.append("⚠️ This removes the agent from the project completely")
            
        elif action == "rebalance":
            warnings.append("🔄 This may reassign tasks between agents")
            warnings.append("📋 In-progress tasks are not affected")
        
        return warnings
    
    def _get_examples(self, action: str, context: Optional[Dict[str, Any]] = None) -> List[Dict[str, Any]]:
        """Get action-specific examples."""
        examples = []
        
        if action == "register":
            examples.append({
                "description": "Register a frontend specialist agent",
                "code": """manage_agent(
    action="register",
    project_id="my_project_id",
    name="frontend-react-specialist",
    call_agent="@react_expert"
)"""
            })
            
        elif action == "list":
            examples.append({
                "description": "List all agents in a project",
                "code": """manage_agent(
    action="list",
    project_id="my_project_id"
)"""
            })
            
        elif action == "assign":
            examples.append({
                "description": "Assign agent to a branch",
                "code": """manage_agent(
    action="assign",
    project_id="my_project_id",
    agent_id="agent_uuid",
    git_branch_id="branch_uuid"
)"""
            })
            
        elif action == "get":
            examples.append({
                "description": "Get agent details and workload",
                "code": """manage_agent(
    action="get",
    project_id="my_project_id",
    agent_id="agent_uuid"
)"""
            })
            
        elif action == "rebalance":
            examples.append({
                "description": "Rebalance workload across agents",
                "code": """manage_agent(
    action="rebalance",
    project_id="my_project_id"
)"""
            })
        
        return examples
    
    def _get_parameter_guidance(self, action: str) -> Dict[str, Dict[str, str]]:
        """Get parameter-specific guidance."""
        base_params = {
            "project_id": {
                "requirement": "OPTIONAL (default: 'default_project')",
                "format": "String identifier",
                "tip": "Project to manage agents in"
            }
        }
        
        action_params = {
            "register": {
                "name": {
                    "requirement": "REQUIRED",
                    "format": "Descriptive string",
                    "tip": "Use format: role-specialization (e.g., 'frontend-vue-specialist')"
                },
                "agent_id": {
                    "requirement": "OPTIONAL (auto-generated if blank)",
                    "format": "UUID string",
                    "tip": "Leave blank for auto-generation"
                },
                "call_agent": {
                    "requirement": "OPTIONAL",
                    "format": "String with @ prefix",
                    "tip": "Agent handle for invocation (e.g., '@frontend_agent')"
                }
            },
            "get": {
                "agent_id": {
                    "requirement": "REQUIRED",
                    "format": "UUID string",
                    "tip": "Get from list action or registration response"
                }
            },
            "update": {
                "agent_id": {
                    "requirement": "REQUIRED",
                    "format": "UUID string",
                    "tip": "Agent to update"
                },
                "name": {
                    "requirement": "OPTIONAL",
                    "format": "String",
                    "tip": "New name for the agent"
                },
                "call_agent": {
                    "requirement": "OPTIONAL",
                    "format": "String",
                    "tip": "Updated invocation handle"
                }
            },
            "assign": {
                "agent_id": {
                    "requirement": "REQUIRED",
                    "format": "UUID string",
                    "tip": "Agent to assign"
                },
                "git_branch_id": {
                    "requirement": "REQUIRED",
                    "format": "UUID string",
                    "tip": "Branch where agent will work"
                }
            },
            "unassign": {
                "agent_id": {
                    "requirement": "REQUIRED",
                    "format": "UUID string",
                    "tip": "Agent to remove from branch"
                },
                "git_branch_id": {
                    "requirement": "REQUIRED",
                    "format": "UUID string",
                    "tip": "Branch to remove agent from"
                }
            },
            "unregister": {
                "agent_id": {
                    "requirement": "REQUIRED",
                    "format": "UUID string",
                    "tip": "⚠️ Must be unassigned from all branches first"
                }
            }
        }
        
        params = base_params.copy()
        if action in action_params:
            params.update(action_params[action])
        
        return params