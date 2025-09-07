from typing import Optional, Dict, Any
import os
import json
import logging

logger = logging.getLogger(__name__)

class ToolConfig:
    """Manages MCP tool configuration and enablement settings"""
    
    DEFAULT_CONFIG = {
        "enabled_tools": {
            "manage_project": True,
            "manage_task": True,
            "manage_subtask": True,
            "manage_agent": True,
            "manage_rule": True,
            "call_agent": True,
            "manage_document": True,
            "update_auto_rule": True,
            "validate_rules": True,
            "regenerate_auto_rule": True,
            "validate_tasks_json": True,
            "create_context_file": True,
            "manage_context": True
        },
        "debug_mode": False,
        "tool_logging": False
    }
    
    def __init__(self, config_overrides: Optional[Dict[str, Any]] = None):
        self.config = self._load_config(config_overrides)
        
    def _load_config(self, config_overrides: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """Load configuration from environment or use defaults"""
        config_path = os.environ.get('MCP_TOOL_CONFIG')
        if config_path and os.path.exists(config_path):
            try:
                with open(config_path, 'r') as f:
                    config = json.load(f)
            except Exception as e:
                logger.warning(f"Failed to load config from {config_path}: {e}")
                config = self.DEFAULT_CONFIG.copy()
        else:
            config = self.DEFAULT_CONFIG.copy()
        
        # Apply overrides if provided
        if config_overrides:
            logger.info(f"Applying configuration overrides: {config_overrides}")
            for key, value in config_overrides.items():
                if key == "enabled_tools" and isinstance(value, dict):
                    # Merge enabled_tools instead of replacing
                    config.setdefault("enabled_tools", {}).update(value)
                else:
                    config[key] = value
        
        return config
        
    def is_enabled(self, tool_name: str) -> bool:
        """Check if a specific tool is enabled"""
        return self.config.get("enabled_tools", {}).get(tool_name, True)
    
    def get_enabled_tools(self) -> Dict[str, bool]:
        """Get all enabled tools configuration"""
        return self.config.get("enabled_tools", {})
