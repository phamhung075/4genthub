import os
from pathlib import Path
import logging
from typing import Optional
# Removed problematic tool_path import, ensure_project_structure

logger = logging.getLogger(__name__)

def find_project_root(start_path=None):
    """Find project root directory by looking for common project markers"""
    if start_path is None:
        start_path = Path.cwd()
    else:
        start_path = Path(start_path)
    
    current = start_path.resolve()
    
    # Look for common project markers
    markers = ['.git', 'pyproject.toml', 'setup.py', 'package.json', 'requirements.txt']
    
    while current != current.parent:  # While not at filesystem root
        for marker in markers:
            if (current / marker).exists():
                return current
        current = current.parent
    
    # If no markers found, return current working directory
    return Path.cwd()

def ensure_project_structure(project_root):
    """Ensure basic project structure exists"""
    cursor_rules_dir = project_root / ".cursor" / "rules"
    cursor_rules_dir.mkdir(parents=True, exist_ok=True)
    return cursor_rules_dir

class PathResolver:
    """Handles dynamic path resolution and directory management for multiple projects"""
    
    def __init__(self):
        # Dynamic project root detection
        self.project_root = find_project_root()
        
        # Ensure project structure exists
        self.cursor_rules_dir = ensure_project_structure(self.project_root)
        
        # Resolve paths dynamically based on current project
        self.brain_dir = self._resolve_path(os.environ.get("BRAIN_DIR_PATH", ".cursor/rules/brain"))
        self.projects_file = self._resolve_path(os.environ.get("PROJECTS_FILE_PATH", str(self.brain_dir / "projects.json")))
        
        # Ensure brain directory exists and create projects file if needed
        self.ensure_brain_dir()
        self._ensure_projects_file()
        
        logger.info(f"PathResolver initialized for project: {self.project_root}")
        logger.info(f"Brain directory: {self.brain_dir}")
        logger.info(f"Projects file: {self.projects_file}")
        
    def _resolve_path(self, path):
        """Resolve path relative to current project root"""
        p = Path(path)
        return p if p.is_absolute() else (self.project_root / p)
        
    def ensure_brain_dir(self):
        """Ensure brain directory exists"""
        os.makedirs(self.brain_dir, exist_ok=True)
    
    def _ensure_projects_file(self):
        """Ensure projects file exists with default content"""
        if not self.projects_file.exists():
            import json
            default_projects = {
                "projects": {},
                "metadata": {
                    "version": "1.0",
                    "created_at": "auto-generated",
                    "description": "Project management configuration"
                }
            }
            
            # Try to create parent directory and file
            try:
                # Ensure parent directory exists
                self.projects_file.parent.mkdir(parents=True, exist_ok=True)
                with open(self.projects_file, 'w') as f:
                    json.dump(default_projects, f, indent=2)
                logger.info(f"Created projects file at: {self.projects_file}")
            except (PermissionError, OSError) as e:
                # Fall back to project-relative path if the environment-specified path isn't writable
                logger.warning(f"Cannot create projects file at {self.projects_file}: {e}")
                fallback_projects_file = self.project_root / ".cursor/rules/brain/projects.json"
                logger.info(f"Falling back to: {fallback_projects_file}")
                
                # Update projects_file to use fallback
                self.projects_file = fallback_projects_file
                
                # Ensure fallback parent directory exists and create file
                self.projects_file.parent.mkdir(parents=True, exist_ok=True)
                with open(self.projects_file, 'w') as f:
                    json.dump(default_projects, f, indent=2)
                logger.info(f"Created fallback projects file at: {self.projects_file}")
        
    def get_tasks_json_path(self, project_id: str = None, git_branch_name: str = "main", user_id: Optional[str] = None) -> Path:
        """
        Get the hierarchical tasks.json path for user/project/tree
        
        Args:
            project_id: Project identifier (required for new structure)
            git_branch_name: Task tree identifier (defaults to "main")
            user_id: User identifier (required for authentication)
            
        Returns:
            Path to tasks.json file in hierarchical structure
        """
        if project_id:
            # New hierarchical structure: .cursor/rules/tasks/{user_id}/{project_id}/{git_branch_name}/tasks.json
            tasks_path = self._resolve_path(f".cursor/rules/tasks/{user_id}/{project_id}/{git_branch_name}/tasks.json")
        else:
            # Legacy fallback for backward compatibility
            tasks_path = self._resolve_path(os.environ.get("TASKS_JSON_PATH", ".cursor/rules/tasks/tasks.json"))
            
        # Ensure the tasks directory exists
        tasks_path.parent.mkdir(parents=True, exist_ok=True)
        return tasks_path
        
    def get_legacy_tasks_json_path(self) -> Path:
        """Get the legacy tasks.json path for migration purposes"""
        tasks_path = self._resolve_path(".cursor/rules/tasks/tasks.json")
        return tasks_path
        
    def get_auto_rule_path(self) -> Path:
        """Get the auto_rule.mdc path for current project"""
        return self._resolve_path(os.environ.get("AUTO_RULE_PATH", ".cursor/rules/auto_rule.mdc"))
        
    def get_rules_directory_from_settings(self) -> Path:
        """Get rules directory using dual-mode configuration with settings fallback"""
        try:
            # First, try using the dual-mode configuration
            from ....dual_mode_config import get_rules_directory, is_http_mode
            import json
            
            rules_dir = get_rules_directory()
            if rules_dir.exists():
                return rules_dir
            
            # Fallback: try to read from settings files (stdio mode only)
            if not is_http_mode():
                # Try 00_RULES/core/settings.json
                settings_path = self.project_root / "00_RULES" / "core" / "settings.json"
                if settings_path.exists():
                    with open(settings_path, 'r', encoding='utf-8') as f:
                        settings = json.load(f)
                        rules_path = settings.get("runtime_constants", {}).get("DOCUMENT_RULES_PATH", "00_RULES")
                        if os.path.isabs(rules_path):
                            return Path(rules_path)
                        return self.project_root / rules_path
                
                # Try .cursor/settings.json
                cursor_settings_path = self.project_root / ".cursor" / "settings.json"
                if cursor_settings_path.exists():
                    with open(cursor_settings_path, 'r', encoding='utf-8') as f:
                        settings = json.load(f)
                        rules_path = settings.get("runtime_constants", {}).get("DOCUMENT_RULES_PATH", "00_RULES")
                        if os.path.isabs(rules_path):
                            return Path(rules_path)
                        return self.project_root / rules_path
                
                # Environment variable override
                if "DOCUMENT_RULES_PATH" in os.environ:
                    rules_path = os.environ["DOCUMENT_RULES_PATH"]
                    if os.path.isabs(rules_path):
                        return Path(rules_path)
                    return self.project_root / rules_path
            
            # Return the dual-mode default even if it doesn't exist yet
            return rules_dir
                
        except Exception as e:
            logger.warning(f"Could not resolve rules directory: {e}")
            # Ultimate fallback using dual-mode config
            from ....dual_mode_config import get_rules_directory
            return get_rules_directory()

    def get_cursor_agent_dir(self) -> Path:
        """Get the agent library directory path"""
        # Check if we have a project-specific agent-library directory
        project_agent_library = self.project_root / "agent-library"
        if project_agent_library.exists():
            return project_agent_library
        
        # Use the AGENT_LIBRARY_DIR_PATH environment variable
        agent_library_path = os.environ.get("AGENT_LIBRARY_DIR_PATH")
        if agent_library_path:
            return Path(agent_library_path)
        
        # Fallback to default agent-library location
        return self._resolve_path("agenthub_main/agent-library")
