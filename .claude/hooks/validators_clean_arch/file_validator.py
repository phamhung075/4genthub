"""
File validation - Single Responsibility: Validate file operations.
"""
import re
from pathlib import Path
from typing import Dict, Any, List, Optional
from ..core.base import Validator
from ..core.config import get_config


class FileValidator(Validator):
    """Validates file operations according to project rules."""
    
    def __init__(self):
        self.config = get_config()
        self.error_message = ""
    
    def validate(self, data: Dict[str, Any]) -> bool:
        """Validate file operation."""
        tool_name = data.get('tool_name', '')
        tool_input = data.get('tool_input', {})
        
        # Only validate file operations
        if tool_name not in ['Write', 'Edit', 'MultiEdit', 'NotebookEdit']:
            return True
        
        file_path = tool_input.get('file_path', '')
        if not file_path:
            return True
        
        path = Path(file_path).resolve()
        
        # Check various file rules
        if not self._validate_root_file(path):
            return False
        
        if not self._validate_test_file(path):
            return False
        
        if not self._validate_documentation_file(path):
            return False
        
        if not self._validate_protected_file(path):
            return False
        
        return True
    
    def _validate_root_file(self, path: Path) -> bool:
        """Check if file creation in root is allowed."""
        if path.parent != self.config.project_root:
            return True
        
        if path.name not in self.config.allowed_root_files:
            self.error_message = (
                f"❌ FILE CREATION BLOCKED: Cannot create '{path.name}' in project root.\n"
                f"Only these files are allowed in root: {', '.join(self.config.allowed_root_files)}"
            )
            return False
        
        return True
    
    def _validate_test_file(self, path: Path) -> bool:
        """Check if test file is in valid location."""
        path_str = str(path)
        
        # Check if it's a test file
        if not any(pattern in path_str.lower() for pattern in ['test', 'spec', '__test__']):
            return True
        
        # Check if it's in a valid test path
        valid = False
        for test_path in self.config.valid_test_paths:
            if path_str.startswith(str(self.config.project_root / test_path)):
                valid = True
                break
        
        if not valid:
            self.error_message = (
                f"❌ TEST FILE BLOCKED: Test files must be in approved directories.\n"
                f"Valid paths: {', '.join(self.config.valid_test_paths)}"
            )
            return False
        
        return True
    
    def _validate_documentation_file(self, path: Path) -> bool:
        """Check if documentation file is in correct location."""
        if path.suffix != '.md':
            return True
        
        # Allow specific root files
        if path.parent == self.config.project_root and path.name in self.config.allowed_root_files:
            return True
        
        # All other .md files must be in ai_docs
        if not str(path).startswith(str(self.config.project_root / 'ai_docs')):
            self.error_message = (
                f"❌ DOCUMENTATION BLOCKED: All .md files must be in ai_docs/ directory.\n"
                f"Move to: ai_docs/{path.name}"
            )
            return False
        
        return True
    
    def _validate_protected_file(self, path: Path) -> bool:
        """Check if file matches protected patterns."""
        path_str = str(path)
        
        for pattern in self.config.protected_patterns:
            if re.search(pattern, path_str, re.IGNORECASE):
                self.error_message = (
                    f"❌ PROTECTED FILE: Cannot access '{path.name}'.\n"
                    f"This file type is protected for security reasons."
                )
                return False
        
        return True
    
    def get_error_message(self) -> str:
        """Get the validation error message."""
        return self.error_message