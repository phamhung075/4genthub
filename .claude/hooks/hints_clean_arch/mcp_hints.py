"""
MCP hint provider - Single Responsibility: Generate MCP-related hints.
"""
from typing import Dict, Any, List, Optional
from ..core.base import HintProvider


class MCPHintProvider(HintProvider):
    """Provides hints for MCP operations."""
    
    def __init__(self):
        self.hints_matrix = {
            'mcp__dhafnck_mcp_http__manage_task': {
                'create': [
                    "📋 TASK CREATED - NEXT STEPS:",
                    "✅ NEXT STEP: Delegate to agent using Task tool with task_id only",
                    "💡 SUGGESTION: Create subtasks for better tracking"
                ],
                'update': [
                    "📊 TASK UPDATED - REMINDERS:",
                    "⏰ REMINDER: Continue updating every 25% progress"
                ],
                'complete': [
                    "✅ TASK COMPLETED - FOLLOW-UP:",
                    "💾 NEXT: Update context with learnings from this task",
                    "🎯 CONTINUE: Use 'next' action to find next task to work on"
                ],
                'get': [
                    "💡 GET COMPLETE - REMINDERS:",
                    "📋 REVIEW: Check task status and plan next actions"
                ],
                'list': [
                    "📋 TASK LIST - SUGGESTIONS:",
                    "🔍 REVIEW: Check task priorities and dependencies"
                ]
            },
            'mcp__dhafnck_mcp_http__manage_subtask': {
                'create': [
                    "📝 SUBTASK CREATED:",
                    "💡 TIP: Update progress_percentage as you work"
                ],
                'update': [
                    "📊 SUBTASK PROGRESS:",
                    "⏰ REMINDER: Update parent task when subtask completes"
                ],
                'complete': [
                    "✅ SUBTASK DONE:",
                    "📋 CHECK: Are all subtasks complete? Update parent task"
                ]
            },
            'mcp__dhafnck_mcp_http__call_agent': {
                'default': [
                    "🤖 AGENT LOADED - READY:",
                    "⚠️ REMEMBER: This was a one-time load - don't call again this session"
                ]
            },
            'mcp__dhafnck_mcp_http__manage_context': {
                'update': [
                    "📝 CONTEXT UPDATED:",
                    "💡 TIP: Context changes cascade through hierarchy"
                ],
                'add_insight': [
                    "💡 INSIGHT ADDED:",
                    "📚 SHARE: Insights help future agents learn"
                ]
            }
        }
    
    def get_hints(self, data: Dict[str, Any]) -> Optional[List[str]]:
        """Generate hints based on MCP operation."""
        tool_name = data.get('tool_name', '')
        
        if tool_name not in self.hints_matrix:
            return None
        
        tool_input = data.get('tool_input', {})
        action = tool_input.get('action', 'default')
        
        # Get base hints
        hints = self.hints_matrix.get(tool_name, {}).get(action, [])
        
        # Add context-specific hints
        if tool_name == 'mcp__dhafnck_mcp_http__call_agent':
            agent_name = tool_input.get('name_agent', '').upper()
            if agent_name:
                hints.insert(1, f"🤖 {agent_name} LOADED: Follow agent's specialized workflow")
        
        return hints if hints else None