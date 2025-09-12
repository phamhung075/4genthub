"""
MCP validation - Single Responsibility: Validate MCP operations.
"""
from typing import Dict, Any, Optional
from ..core.base import Validator


class MCPValidator(Validator):
    """Validates MCP operations for proper usage."""
    
    def __init__(self):
        self.error_message = ""
        self.required_fields = {
            'mcp__dhafnck_mcp_http__manage_task': {
                'create': ['git_branch_id', 'title', 'assignees'],
                'update': ['task_id'],
                'get': ['task_id'],
                'delete': ['task_id'],
                'complete': ['task_id', 'completion_summary'],
                'list': [],
                'search': ['query'],
                'next': ['git_branch_id']
            },
            'mcp__dhafnck_mcp_http__manage_subtask': {
                'create': ['task_id', 'title'],
                'update': ['task_id', 'subtask_id'],
                'delete': ['task_id', 'subtask_id'],
                'get': ['task_id', 'subtask_id'],
                'list': ['task_id'],
                'complete': ['task_id', 'subtask_id', 'completion_summary']
            }
        }
    
    def validate(self, data: Dict[str, Any]) -> bool:
        """Validate MCP operation has required fields."""
        tool_name = data.get('tool_name', '')
        
        if tool_name not in self.required_fields:
            return True
        
        tool_input = data.get('tool_input', {})
        action = tool_input.get('action', 'default')
        
        if action not in self.required_fields[tool_name]:
            return True
        
        required = self.required_fields[tool_name][action]
        missing = []
        
        for field in required:
            if not tool_input.get(field):
                missing.append(field)
        
        if missing:
            self.error_message = (
                f"⚠️ MCP VALIDATION: Missing required fields for {tool_name}:{action}\n"
                f"Required: {', '.join(missing)}\n"
                f"Please provide all required fields."
            )
            return False
        
        return True
    
    def get_error_message(self) -> str:
        """Get the validation error message."""
        return self.error_message