"""
Configuration management for hook system.
Single source of truth for all configuration.
"""
import os
from pathlib import Path
from typing import Dict, Any, Optional, List
import json
from dataclasses import dataclass, field


def load_env_claude():
    """Load environment variables from .env.claude file."""
    env_file = Path.cwd() / '.env.claude'
    if env_file.exists():
        try:
            with open(env_file, 'r') as f:
                for line in f:
                    line = line.strip()
                    if line and not line.startswith('#') and '=' in line:
                        key, value = line.split('=', 1)
                        # Only set if not already in environment
                        if key not in os.environ:
                            os.environ[key] = value.strip()
        except Exception:
            pass


# Load .env.claude on module import
load_env_claude()


@dataclass
class Config:
    """Centralized configuration for hook system."""
    
    # Paths
    project_root: Path = field(default_factory=Path.cwd)
    hooks_dir: Path = field(init=False)
    data_dir: Path = field(init=False)
    logs_dir: Path = field(init=False)
    ai_docs_dir: Path = field(init=False)
    
    # Feature flags
    enable_file_protection: bool = True
    enable_mcp_hints: bool = True
    enable_context_injection: bool = True
    enable_documentation_check: bool = True
    enable_session_tracking: bool = True
    enable_logging: bool = True
    
    # File protection settings
    allowed_root_files: List[str] = field(default_factory=list)
    valid_test_paths: List[str] = field(default_factory=list)
    protected_patterns: List[str] = field(default_factory=list)
    
    # MCP settings
    mcp_hint_relevance_minutes: int = 5
    mcp_log_max_entries: int = 100
    
    # Session settings
    session_duration_hours: int = 2
    
    def __post_init__(self):
        """Initialize derived paths and load configurations."""
        self.hooks_dir = self.project_root / '.claude' / 'hooks'
        
        # Use paths from .env.claude
        self.data_dir = self.project_root / os.getenv('AI_DATA', '.claude/data')
        self.logs_dir = self.project_root / os.getenv('LOG_PATH', 'logs/claude')
        self.ai_docs_dir = self.project_root / os.getenv('AI_DOCS', 'ai_docs')
        
        # Ensure directories exist
        self.data_dir.mkdir(parents=True, exist_ok=True)
        self.logs_dir.mkdir(parents=True, exist_ok=True)
        
        # Load configurations
        self._load_allowed_root_files()
        self._load_valid_test_paths()
        self._set_protected_patterns()
    
    def _load_allowed_root_files(self):
        """Load allowed root files from configuration."""
        config_file = self.project_root / '.allowed_root_files'
        
        # Default allowed files
        defaults = [
            'README.md', 'CHANGELOG.md', 'TEST-CHANGELOG.md',
            'CLAUDE.md', 'CLAUDE.local.md', '.gitignore',
            'package.json', 'package-lock.json', 'requirements.txt',
            'pyproject.toml', 'poetry.lock', 'Pipfile', 'Pipfile.lock',
            'docker-compose.yml', 'Dockerfile', '.dockerignore',
            'Makefile', 'setup.py', 'setup.cfg'
        ]
        
        if config_file.exists():
            try:
                with open(config_file, 'r') as f:
                    lines = [line.strip() for line in f if line.strip() and not line.startswith('#')]
                    self.allowed_root_files = lines if lines else defaults
            except Exception:
                self.allowed_root_files = defaults
        else:
            self.allowed_root_files = defaults
    
    def _load_valid_test_paths(self):
        """Load valid test paths from configuration."""
        config_file = self.project_root / '.valid_test_paths'
        
        # Default test paths
        defaults = [
            'dhafnck_mcp_main/src/tests',
            'dhafnck-frontend/src/__tests__',
            'dhafnck-frontend/src/tests',
            'tests'
        ]
        
        if config_file.exists():
            try:
                with open(config_file, 'r') as f:
                    lines = [line.strip() for line in f if line.strip() and not line.startswith('#')]
                    self.valid_test_paths = lines if lines else defaults
            except Exception:
                self.valid_test_paths = defaults
        else:
            self.valid_test_paths = defaults
    
    def _set_protected_patterns(self):
        """Set protected file patterns."""
        self.protected_patterns = [
            r'\.env.*',
            r'.*\.pem$',
            r'.*\.key$',
            r'.*\.cert$',
            r'.*\.crt$',
            r'.*secrets.*',
            r'.*password.*',
            r'.*token.*'
        ]
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert configuration to dictionary."""
        return {
            'project_root': str(self.project_root),
            'hooks_dir': str(self.hooks_dir),
            'data_dir': str(self.data_dir),
            'logs_dir': str(self.logs_dir),
            'ai_docs_dir': str(self.ai_docs_dir),
            'features': {
                'file_protection': self.enable_file_protection,
                'mcp_hints': self.enable_mcp_hints,
                'context_injection': self.enable_context_injection,
                'documentation_check': self.enable_documentation_check,
                'session_tracking': self.enable_session_tracking,
                'logging': self.enable_logging
            },
            'allowed_root_files': self.allowed_root_files,
            'valid_test_paths': self.valid_test_paths
        }


# Singleton instance
_config_instance: Optional[Config] = None


def get_config() -> Config:
    """Get the singleton configuration instance."""
    global _config_instance
    if _config_instance is None:
        _config_instance = Config()
    return _config_instance