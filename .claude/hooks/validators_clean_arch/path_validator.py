"""
Path validation - Single Responsibility: Validate directory operations.
"""
from pathlib import Path
from typing import Dict, Any
from ..core.base import Validator
from ..core.config import get_config


class PathValidator(Validator):
    """Validates directory/path operations."""
    
    def __init__(self):
        self.config = get_config()
        self.error_message = ""
    
    def validate(self, data: Dict[str, Any]) -> bool:
        """Validate path operation."""
        tool_name = data.get('tool_name', '')
        tool_input = data.get('tool_input', {})
        
        # Check Bash mkdir commands
        if tool_name == 'Bash':
            command = tool_input.get('command', '')
            if 'mkdir' in command:
                return self._validate_mkdir(command)
        
        return True
    
    def _validate_mkdir(self, command: str) -> bool:
        """Validate mkdir commands."""
        # Extract path from mkdir command
        import re
        match = re.search(r'mkdir\s+(?:-[pm]\s+)?([^\s;|&]+)', command)
        if not match:
            return True
        
        path_str = match.group(1).strip('"\'')
        path = Path(path_str)
        
        # Check if trying to create in root
        if path.parent == Path('.') or path.parent == self.config.project_root:
            self.error_message = (
                f"❌ DIRECTORY CREATION BLOCKED: Cannot create '{path.name}' in project root.\n"
                f"All necessary folders should already exist."
            )
            return False
        
        # Check kebab-case for ai_docs subdirectories
        if 'ai_docs' in str(path):
            if not self._is_kebab_case(path.name) and path.name not in ['_absolute_docs', '_obsolete_docs']:
                self.error_message = (
                    f"❌ INVALID FOLDER NAME: '{path.name}' must use kebab-case.\n"
                    f"Example: 'api-integration' not 'API_Integration'"
                )
                return False
        
        return True
    
    def _is_kebab_case(self, name: str) -> bool:
        """Check if name follows kebab-case convention."""
        import re
        return bool(re.match(r'^[a-z][a-z0-9-]*$', name))
    
    def get_error_message(self) -> str:
        """Get the validation error message."""
        return self.error_message