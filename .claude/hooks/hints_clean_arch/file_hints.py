"""
File hint provider - Single Responsibility: Generate file operation hints.
"""
from pathlib import Path
from typing import Dict, Any, List, Optional
from ..core.base import HintProvider
from ..core.config import get_config


class FileHintProvider(HintProvider):
    """Provides hints for file operations."""
    
    def __init__(self):
        self.config = get_config()
    
    def get_hints(self, data: Dict[str, Any]) -> Optional[List[str]]:
        """Generate hints for file operations."""
        tool_name = data.get('tool_name', '')
        tool_input = data.get('tool_input', {})
        
        hints = []
        
        if tool_name in ['Write', 'Edit', 'MultiEdit']:
            file_path = tool_input.get('file_path', '')
            if file_path:
                path = Path(file_path)
                
                # Hint for test files
                if 'test' in str(path).lower():
                    hints.append("🧪 TEST FILE: Remember to run tests after modifications")
                
                # Hint for configuration files
                if path.suffix in ['.json', '.yml', '.yaml', '.toml']:
                    hints.append("⚙️ CONFIG FILE: Validate syntax after changes")
                
                # Hint for documentation
                if path.suffix == '.md':
                    hints.append("📝 DOCUMENTATION: Keep consistent with code changes")
                
                # Hint for Python files
                if path.suffix == '.py':
                    hints.append("🐍 PYTHON: Follow PEP 8 style guidelines")
                
                # Hint for TypeScript/JavaScript
                if path.suffix in ['.ts', '.tsx', '.js', '.jsx']:
                    hints.append("📦 JS/TS: Check imports and type definitions")
        
        elif tool_name == 'Bash':
            command = tool_input.get('command', '')
            
            # Git operations
            if 'git' in command:
                if 'commit' in command:
                    hints.append("📝 GIT: Use conventional commit format (feat/fix/docs/etc)")
                elif 'push' in command:
                    hints.append("⚠️ GIT: Ensure all tests pass before pushing")
            
            # Package operations
            if any(pkg in command for pkg in ['npm', 'pip', 'poetry']):
                hints.append("📦 PACKAGES: Update lock files after changes")
            
            # Docker operations
            if 'docker' in command:
                hints.append("🐳 DOCKER: Rebuild images after Dockerfile changes")
        
        return hints if hints else None