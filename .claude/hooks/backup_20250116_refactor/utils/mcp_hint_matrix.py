#!/usr/bin/env python3
"""
MCP Hint Matrix - Comprehensive hint system based on tool/action combinations.

This module provides a matrix-based approach to generating contextual hints
for MCP operations based on the specific tool, action, and parameters.
"""

import json
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, List, Optional, Tuple, Any

class MCPHintMatrix:
    """Matrix-based hint generation for MCP operations."""
    
    def __init__(self):
        """Initialize the hint matrix with comprehensive tool/action mappings."""
        self.workflow_state_file = Path.cwd() / '.claude' / 'hooks' / 'data' / 'workflow_state.json'
        self.workflow_state_file.parent.mkdir(parents=True, exist_ok=True)
        self.load_workflow_state()
        self.init_hint_matrix()
    
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
    
    def init_hint_matrix(self):
        """Initialize the comprehensive hint matrix for all tool/action combinations."""
        self.hint_matrix = {
            # TASK MANAGEMENT MATRIX
            "mcp__dhafnck_mcp_http__manage_task": {
                "create": {
                    "required_fields": ["title", "assignees", "git_branch_id"],
                    "recommended_fields": ["details", "priority", "estimated_effort"],
                    "hints": {
                        "missing_title": "🚨 CRITICAL: 'title' is required - provide clear, specific task title",
                        "missing_assignees": "🚨 CRITICAL: 'assignees' required - use format: '@agent-name' (e.g., '@coding-agent')",
                        "missing_git_branch_id": "🚨 CRITICAL: 'git_branch_id' required - get from git branch creation or list",
                        "missing_details": "📝 STRONG RECOMMENDATION: Add 'details' with full requirements, files, acceptance criteria",
                        "missing_priority": "🎯 TIP: Set 'priority' (low/medium/high/urgent/critical) for proper scheduling",
                        "missing_estimated_effort": "⏱️ TIP: Add 'estimated_effort' (e.g., '2 hours', '3 days') for planning",
                        "complex_task": "🔄 DECOMPOSITION HINT: This looks complex - create subtasks after creation",
                        "parallel_opportunity": "⚡ PARALLEL HINT: Consider creating related tasks for parallel execution"
                    },
                    "workflow_hints": [
                        "After creation, immediately delegate with task_id only",
                        "For complex tasks, create subtasks for granular tracking",
                        "Update task status when starting work (todo → in_progress)"
                    ]
                },
                "update": {
                    "recommended_fields": ["status", "progress_notes", "details"],
                    "hints": {
                        "missing_task_id": "🚨 CRITICAL: 'task_id' required to identify which task to update",
                        "missing_progress": "📊 REMINDER: Include 'progress_notes' or updated 'details' to show progress",
                        "long_time_no_update": "⏰ ATTENTION: Task hasn't been updated in >30 minutes",
                        "status_change": "✅ GOOD: Status change tracked - remember to update regularly",
                        "blocked_status": "⚠️ BLOCKED: Explain blockers in 'details' and consider creating debug task"
                    },
                    "workflow_hints": [
                        "Update at least every 25% progress",
                        "Document blockers immediately when encountered",
                        "Add insights and discoveries as you work"
                    ]
                },
                "complete": {
                    "required_fields": ["task_id"],
                    "recommended_fields": ["completion_summary", "testing_notes"],
                    "hints": {
                        "missing_task_id": "🚨 CRITICAL: 'task_id' required to identify task to complete",
                        "missing_completion_summary": "📝 CRITICAL: Add 'completion_summary' detailing what was accomplished",
                        "missing_testing_notes": "🧪 IMPORTANT: Include 'testing_notes' about verification performed",
                        "quick_completion": "⚡ WARNING: Task completed very quickly - ensure all objectives met",
                        "no_prior_updates": "⚠️ WARNING: Completing without any progress updates - unusual pattern"
                    },
                    "workflow_hints": [
                        "Verify all objectives met before completion",
                        "Update context with learnings before marking complete",
                        "Consider if task needs review before final completion"
                    ]
                },
                "get": {
                    "required_fields": ["task_id"],
                    "hints": {
                        "missing_task_id": "🚨 CRITICAL: 'task_id' required to retrieve task",
                        "include_context": "💡 TIP: Set 'include_context=true' for vision insights"
                    }
                },
                "list": {
                    "optional_fields": ["status", "priority", "git_branch_id"],
                    "hints": {
                        "filter_tip": "🔍 TIP: Use filters (status, priority, git_branch_id) to narrow results",
                        "review_reminder": "📋 REMINDER: Review task list before creating duplicates"
                    }
                },
                "next": {
                    "required_fields": ["git_branch_id"],
                    "hints": {
                        "missing_git_branch_id": "🚨 CRITICAL: 'git_branch_id' required to find next task",
                        "include_context": "💡 TIP: Set 'include_context=true' for AI recommendations"
                    }
                },
                "add_dependency": {
                    "required_fields": ["task_id", "dependency_id"],
                    "hints": {
                        "missing_task_id": "🚨 CRITICAL: 'task_id' required",
                        "missing_dependency_id": "🚨 CRITICAL: 'dependency_id' required - task that must complete first",
                        "circular_warning": "⚠️ CAUTION: Ensure no circular dependencies"
                    }
                },
                "remove_dependency": {
                    "required_fields": ["task_id", "dependency_id"],
                    "hints": {
                        "missing_task_id": "🚨 CRITICAL: 'task_id' required",
                        "missing_dependency_id": "🚨 CRITICAL: 'dependency_id' of dependency to remove"
                    }
                }
            },
            
            # SUBTASK MANAGEMENT MATRIX
            "mcp__dhafnck_mcp_http__manage_subtask": {
                "create": {
                    "required_fields": ["task_id", "title"],
                    "recommended_fields": ["description", "assignees"],
                    "hints": {
                        "missing_task_id": "🚨 CRITICAL: 'task_id' (parent) required",
                        "missing_title": "🚨 CRITICAL: 'title' required for subtask",
                        "assignee_inheritance": "💡 INFO: Subtasks inherit parent's assignees if not specified",
                        "progress_tracking": "📊 TIP: Use 'progress_percentage' for automatic status updates"
                    }
                },
                "update": {
                    "required_fields": ["task_id", "subtask_id"],
                    "recommended_fields": ["progress_percentage", "progress_notes"],
                    "hints": {
                        "missing_ids": "🚨 CRITICAL: Both 'task_id' and 'subtask_id' required",
                        "progress_mapping": "📈 INFO: progress_percentage auto-maps: 0=todo, 1-99=in_progress, 100=done",
                        "blocker_hint": "⚠️ TIP: Use 'blockers' field to document impediments"
                    }
                },
                "complete": {
                    "required_fields": ["task_id", "subtask_id", "completion_summary"],
                    "recommended_fields": ["impact_on_parent", "insights_found"],
                    "hints": {
                        "missing_completion_summary": "🚨 CRITICAL: 'completion_summary' required for subtask completion",
                        "missing_impact": "🔗 IMPORTANT: Describe 'impact_on_parent' for context",
                        "insights_valuable": "💡 EXCELLENT: Share 'insights_found' for team learning"
                    }
                },
                "list": {
                    "required_fields": ["task_id"],
                    "hints": {
                        "parent_progress": "📊 INFO: Shows aggregated progress across all subtasks",
                        "completion_check": "✅ CHECK: Ensure all subtasks complete before parent"
                    }
                }
            },
            
            # CONTEXT MANAGEMENT MATRIX
            "mcp__dhafnck_mcp_http__manage_context": {
                "create": {
                    "required_fields": ["level", "context_id"],
                    "recommended_fields": ["data"],
                    "hints": {
                        "level_explanation": "📚 LEVELS: global(user) → project → branch → task",
                        "inheritance": "🔄 INFO: Child contexts inherit from parents automatically"
                    }
                },
                "update": {
                    "required_fields": ["level", "context_id"],
                    "recommended_fields": ["data", "propagate_changes"],
                    "hints": {
                        "propagation": "📡 TIP: Set 'propagate_changes=true' to cascade updates",
                        "data_format": "📝 FORMAT: 'data' should be JSON string or dict"
                    }
                },
                "resolve": {
                    "required_fields": ["level", "context_id"],
                    "hints": {
                        "include_inherited": "🔍 TIP: Set 'include_inherited=true' for complete chain",
                        "force_refresh": "🔄 TIP: Use 'force_refresh=true' to bypass cache"
                    }
                },
                "add_insight": {
                    "required_fields": ["level", "context_id", "content"],
                    "recommended_fields": ["category", "importance"],
                    "hints": {
                        "categories": "📂 CATEGORIES: technical, business, performance, risk, discovery",
                        "importance_levels": "🎯 IMPORTANCE: low, medium, high, critical"
                    }
                }
            },
            
            # PROJECT MANAGEMENT MATRIX
            "mcp__dhafnck_mcp_http__manage_project": {
                "create": {
                    "required_fields": ["name"],
                    "recommended_fields": ["description"],
                    "hints": {
                        "unique_name": "🔤 IMPORTANT: Project name must be unique",
                        "auto_context": "🔄 INFO: Context automatically initialized on creation"
                    }
                },
                "project_health_check": {
                    "required_fields": ["project_id"],
                    "hints": {
                        "health_metrics": "📊 PROVIDES: Task stats, agent load, blockers, progress",
                        "use_before_work": "🏥 TIP: Run health check before starting major work"
                    }
                }
            },
            
            # GIT BRANCH MANAGEMENT MATRIX
            "mcp__dhafnck_mcp_http__manage_git_branch": {
                "create": {
                    "required_fields": ["project_id", "git_branch_name"],
                    "recommended_fields": ["git_branch_description"],
                    "hints": {
                        "naming_convention": "📝 TIP: Use descriptive names (feature/user-auth, fix/login-bug)",
                        "task_container": "📦 INFO: Branches are containers for related tasks"
                    }
                },
                "assign_agent": {
                    "required_fields": ["project_id", "agent_id"],
                    "hints": {
                        "identification": "🔍 INFO: Use git_branch_name OR git_branch_id",
                        "specialization": "🤖 TIP: Assign agents based on branch type"
                    }
                }
            },
            
            # AGENT MANAGEMENT MATRIX
            "mcp__dhafnck_mcp_http__manage_agent": {
                "register": {
                    "required_fields": ["project_id", "name"],
                    "hints": {
                        "agent_types": "🤖 33 AGENTS: coding, debugging, testing, architecture, etc.",
                        "auto_id": "🔑 INFO: agent_id auto-generated if not provided"
                    }
                }
            },
            
            # AGENT INVOCATION MATRIX
            "mcp__dhafnck_mcp_http__call_agent": {
                "default": {  # No action field for this tool
                    "required_fields": ["name_agent"],
                    "hints": {
                        "first_call": "🚨 CRITICAL: Call this FIRST in any session",
                        "master_orchestrator": "🎯 DEFAULT: Use 'master-orchestrator-agent' for principal sessions",
                        "one_time": "⚠️ IMPORTANT: Call only ONCE per session",
                        "response_usage": "📖 CRITICAL: Read 'system_prompt' from response - it's your instructions"
                    }
                }
            }
        }
    
    def get_hints(self, tool_name: str, tool_input: Dict[str, Any]) -> Optional[str]:
        """
        Generate contextual hints based on tool, action, and parameters.
        
        Args:
            tool_name: The MCP tool being called
            tool_input: Parameters passed to the tool
            
        Returns:
            Optional[str]: Formatted hint message or None
        """
        # Get tool matrix
        if tool_name not in self.hint_matrix:
            return None
        
        tool_matrix = self.hint_matrix[tool_name]
        
        # Get action (default to 'default' for tools without action)
        action = tool_input.get('action', 'default')
        
        # Get action matrix
        if action not in tool_matrix:
            return f"❓ UNKNOWN ACTION: '{action}' is not a valid action for {tool_name}"
        
        action_matrix = tool_matrix[action]
        hints = []
        
        # Track workflow state
        self._update_workflow_state(tool_name, action, tool_input)
        
        # Check required fields
        required = action_matrix.get('required_fields', [])
        for field in required:
            if not tool_input.get(field):
                hint_key = f"missing_{field}"
                if hint_key in action_matrix.get('hints', {}):
                    hints.append(action_matrix['hints'][hint_key])
                else:
                    hints.append(f"🚨 MISSING REQUIRED: '{field}' is required for {action}")
        
        # Check recommended fields
        recommended = action_matrix.get('recommended_fields', [])
        missing_recommended = []
        for field in recommended:
            if not tool_input.get(field):
                hint_key = f"missing_{field}"
                if hint_key in action_matrix.get('hints', {}):
                    hints.append(action_matrix['hints'][hint_key])
                else:
                    missing_recommended.append(field)
        
        if missing_recommended:
            hints.append(f"💡 CONSIDER ADDING: {', '.join(missing_recommended)}")
        
        # Add contextual hints based on workflow state
        context_hints = self._get_contextual_hints(tool_name, action, tool_input)
        hints.extend(context_hints)
        
        # Add workflow hints if applicable
        if 'workflow_hints' in action_matrix and len(hints) < 5:
            hints.append("\n📋 WORKFLOW TIPS:")
            for tip in action_matrix['workflow_hints'][:2]:  # Limit to 2 tips
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
    
    def _get_contextual_hints(self, tool_name: str, action: str, tool_input: Dict) -> List[str]:
        """Generate contextual hints based on workflow state."""
        hints = []
        
        # Task-specific contextual hints
        if 'manage_task' in tool_name:
            task_id = tool_input.get('task_id')
            
            if action == 'create':
                # Check for complex task indicators
                title = tool_input.get('title', '').lower()
                complex_words = ['implement', 'build', 'system', 'integrate', 'refactor', 'optimize']
                if any(word in title for word in complex_words):
                    hints.append("🔄 DECOMPOSITION HINT: This looks complex - plan subtasks after creation")
                
                # Check for parallel opportunities
                if any(word in title for word in ['frontend', 'backend', 'api', 'ui']):
                    hints.append("⚡ PARALLEL HINT: Consider creating parallel tasks for other layers")
            
            elif action == 'update' and task_id:
                # Check time since last update
                if task_id in self.workflow_state:
                    last_update = self.workflow_state[task_id].get('last_update')
                    if last_update:
                        time_diff = datetime.now() - datetime.fromisoformat(last_update)
                        if time_diff > timedelta(minutes=30):
                            hints.append(f"⏰ TIME CHECK: Last updated {int(time_diff.total_seconds()/60)} minutes ago")
            
            elif action == 'complete' and task_id:
                # Check if task was updated
                if task_id in self.workflow_state:
                    if not self.workflow_state[task_id].get('has_updates'):
                        hints.append("⚠️ PATTERN CHECK: Completing without progress updates - unusual")
                    if self.workflow_state[task_id].get('has_subtasks'):
                        hints.append("📋 SUBTASK CHECK: Ensure all subtasks are complete")
        
        return hints
    
    def _get_hint_header(self, tool_name: str, action: str) -> str:
        """Generate appropriate header for hint section."""
        headers = {
            ('manage_task', 'create'): "🎯 TASK CREATION VALIDATION",
            ('manage_task', 'update'): "📊 TASK UPDATE VALIDATION",
            ('manage_task', 'complete'): "✅ TASK COMPLETION CHECKLIST",
            ('manage_task', 'list'): "📋 TASK LIST HINTS",
            ('manage_task', 'next'): "🎯 NEXT TASK HINTS",
            ('manage_subtask', 'create'): "📌 SUBTASK CREATION HINTS",
            ('manage_subtask', 'update'): "📈 SUBTASK UPDATE HINTS",
            ('manage_subtask', 'complete'): "✔️ SUBTASK COMPLETION VALIDATION",
            ('manage_context', 'update'): "🔄 CONTEXT UPDATE HINTS",
            ('manage_context', 'add_insight'): "💡 INSIGHT ADDITION HINTS",
            ('call_agent', 'default'): "🚨 AGENT LOADING CRITICAL REMINDERS"
        }
        
        # Extract base tool name
        base_tool = tool_name.split('__')[-1]
        
        return headers.get((base_tool, action), f"💡 {base_tool.upper()} - {action.upper()} HINTS")


def inject_matrix_hints(tool_name: str, tool_input: Dict) -> Optional[str]:
    """
    Main entry point for matrix-based hint injection.
    
    Args:
        tool_name: Name of the MCP tool being called
        tool_input: Parameters passed to the tool
        
    Returns:
        Optional[str]: Formatted hint message or None
    """
    if not tool_name.startswith('mcp__dhafnck_mcp_http'):
        return None
    
    matrix = MCPHintMatrix()
    return matrix.get_hints(tool_name, tool_input)


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