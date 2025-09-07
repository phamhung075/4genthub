"""DDD-Compliant Cursor Rules Tools

This is the refactored version of cursor_rules_tools.py that follows DDD principles
by properly separating concerns and delegating to application facades.
"""

from .controllers.cursor_rules_controller import CursorRulesController
from ..application.facades.rule_application_facade import RuleApplicationFacade
from ..infrastructure.utilities.path_resolver import PathResolver

# DDD-compliant module-level wrappers for dual-mode and project root logic
from ...dual_mode_config import get_rules_directory as _get_rules_directory, is_http_mode as _is_http_mode
# Local path resolution implementation
def _find_project_root(start_path=None):
    """Find project root by looking for dhafnck_mcp_main directory"""
    current_path = Path(start_path).resolve() if start_path else Path(__file__).resolve()
    
    # Walk up the directory tree looking for dhafnck_mcp_main
    while current_path.parent != current_path:
        if (current_path / "dhafnck_mcp_main").exists():
            return current_path
        current_path = current_path.parent
    
    # If not found, use current working directory as fallback
    cwd = Path.cwd()
    if (cwd / "dhafnck_mcp_main").exists():
        return cwd
        
    # Last resort - use the directory containing dhafnck_mcp_main
    current_path = Path(__file__).resolve()
    while current_path.parent != current_path:
        if current_path.name == "dhafnck_mcp_main":
            return current_path.parent
        current_path = current_path.parent
    
    # Absolute fallback
    # Use environment variable or default data path
    data_path = os.environ.get('DHAFNCK_DATA_PATH', '/data')
    # If running in development, try to find project root
    if not os.path.exists(data_path):
        # Try current working directory
        cwd = Path.cwd()
        if (cwd / "dhafnck_mcp_main").exists():
            return cwd
        # Try parent directories
        current = Path(__file__).resolve()
        while current.parent != current:
            if (current / "dhafnck_mcp_main").exists():
                return current
            current = current.parent
        # Fall back to temp directory for safety
        return Path("/tmp/dhafnck_project")
    return Path(data_path)


class CursorRulesToolsDDD:
    """
    DDD-compliant wrapper for cursor rules management.
    
    This class demonstrates proper DDD architecture by:
    - Using controllers that delegate to application facades
    - Separating infrastructure concerns (PathResolver)
    - Following proper dependency injection patterns
    """
    
    def __init__(self, path_resolver=None):
        """Initialize DDD-compliant cursor rules tools"""
        # Allow dependency injection for testability and DDD compliance
        self._path_resolver = path_resolver or PathResolver()
        
        # Application layer
        self._rule_facade = RuleApplicationFacade(path_resolver=self._path_resolver)
        
        # Interface layer
        self._controller = CursorRulesController(self._rule_facade)
    
    def register_tools(self, mcp):
        """Register cursor rules tools with the MCP server"""
        self._controller.register_tools(mcp)
    
    @property
    def project_root(self):
        """Access to project root via path resolver"""
        return self._path_resolver.project_root

    def _get_rules_directory_from_settings(self):
        """
        DDD-compliant method to get the rules directory using dual-mode configuration with settings/environment fallback.
        Returns the first existing Path found from get_rules_directory, env, or settings files (relative to project root).
        If none exist, returns the non-existent path from get_rules_directory as a Path object (if not None/falsey).
        Only returns None if all options are None/falsey.
        """
        import os
        import json
        from pathlib import Path
        # 1. Try the (possibly patched) module-level get_rules_directory
        rules_dir = get_rules_directory()
        rules_dir_path = Path(rules_dir) if rules_dir else None
        if rules_dir_path and rules_dir_path.exists():
            return rules_dir_path

        # 2. Fallback: Check DOCUMENT_RULES_PATH in environment
        env_path = os.environ.get("DOCUMENT_RULES_PATH")
        env_path_obj = Path(env_path) if env_path else None
        if env_path_obj and env_path_obj.exists():
            return env_path_obj

        # 3. Fallback: Check runtime_constants.DOCUMENT_RULES_PATH in settings files relative to project root
        project_root = _find_project_root() or Path('.')
        settings_files = [
            project_root / "00_RULES" / "core" / "settings.json",
            project_root / ".cursor" / "settings.json",
        ]
        for settings_file in settings_files:
            if settings_file.exists():
                try:
                    with open(settings_file, "r") as f:
                        data = json.load(f)
                    doc_rules_path = (
                        data.get("runtime_constants", {})
                        .get("DOCUMENT_RULES_PATH")
                    )
                    doc_rules_path_obj = Path(doc_rules_path) if doc_rules_path else None
                    if doc_rules_path_obj and doc_rules_path_obj.exists():
                        return doc_rules_path_obj
                except Exception:
                    continue

        # 4. If no fallback exists, return the non-existent path from get_rules_directory (if not None/falsey)
        if rules_dir_path:
            return rules_dir_path
        return None

def get_rules_directory():
    """DDD-compliant wrapper for rules directory resolution."""
    return _get_rules_directory()

def is_http_mode():
    """DDD-compliant wrapper for HTTP mode detection."""
    return _is_http_mode()

def find_project_root(start_path=None):
    """DDD-compliant wrapper for project root finding."""
    return _find_project_root(start_path)