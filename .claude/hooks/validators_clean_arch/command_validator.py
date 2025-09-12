"""
Command validation - Single Responsibility: Validate dangerous commands.
"""
import re
from typing import Dict, Any, List
from ..core.base import Validator


class CommandValidator(Validator):
    """Validates commands for dangerous operations."""
    
    def __init__(self):
        self.error_message = ""
        self.dangerous_patterns = [
            (r'rm\s+-rf\s+/', "Removing root directories"),
            (r'rm\s+-rf\s+\*', "Removing all files"),
            (r'chmod\s+777', "Setting overly permissive permissions"),
            (r'curl.*\|\s*sh', "Executing remote scripts"),
            (r'wget.*\|\s*sh', "Executing remote scripts"),
            (r'>\s*/dev/sd[a-z]', "Writing directly to disk"),
            (r'dd\s+if=/dev/zero\s+of=/dev/', "Overwriting disk data"),
            (r':(){ :|:& };:', "Fork bomb"),
            (r'mv\s+/\s+', "Moving root directory"),
            (r'>\s*\.bashrc', "Overwriting shell configuration"),
            (r'>\s*\.zshrc', "Overwriting shell configuration")
        ]
    
    def validate(self, data: Dict[str, Any]) -> bool:
        """Validate command for dangerous operations."""
        tool_name = data.get('tool_name', '')
        
        if tool_name != 'Bash':
            return True
        
        tool_input = data.get('tool_input', {})
        command = tool_input.get('command', '')
        
        for pattern, description in self.dangerous_patterns:
            if re.search(pattern, command, re.IGNORECASE):
                self.error_message = (
                    f"❌ DANGEROUS COMMAND BLOCKED: {description}\n"
                    f"Command: {command}\n"
                    f"This operation could damage the system."
                )
                return False
        
        return True
    
    def get_error_message(self) -> str:
        """Get the validation error message."""
        return self.error_message