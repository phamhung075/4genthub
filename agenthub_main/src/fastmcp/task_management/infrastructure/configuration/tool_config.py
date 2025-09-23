from typing import Optional, Dict, Any
import os
import json
import logging

logger = logging.getLogger(__name__)

class ToolConfig:
    """Manages MCP tool configuration and enablement settings"""

    def __init__(self, config_overrides: Optional[Dict[str, Any]] = None):
        self.config = self._load_config(config_overrides)

    def _load_config(self, config_overrides: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """Load configuration from environment variables (.env.dev) or use defaults"""
        # Load enabled tools from environment variables
        enabled_tools = {
            "manage_project": self._get_bool_env("TOOL_MANAGE_PROJECT", True),
            "manage_task": self._get_bool_env("TOOL_MANAGE_TASK", True),
            "manage_subtask": self._get_bool_env("TOOL_MANAGE_SUBTASK", True),
            "manage_agent": self._get_bool_env("TOOL_MANAGE_AGENT", True),
            "call_agent": self._get_bool_env("TOOL_CALL_AGENT", True),
            "manage_document": self._get_bool_env("TOOL_MANAGE_DOCUMENT", True),
            "update_auto_rule": self._get_bool_env("TOOL_UPDATE_AUTO_RULE", True),
            "validate_rules": self._get_bool_env("TOOL_VALIDATE_RULES", True),
            "regenerate_auto_rule": self._get_bool_env("TOOL_REGENERATE_AUTO_RULE", True),
            "validate_tasks_json": self._get_bool_env("TOOL_VALIDATE_TASKS_JSON", True),
            "create_context_file": self._get_bool_env("TOOL_CREATE_CONTEXT_FILE", True),
            "manage_context": self._get_bool_env("TOOL_MANAGE_CONTEXT", True)
        }

        # Load other configuration from environment variables
        config = {
            "enabled_tools": enabled_tools,
            "debug_mode": self._get_bool_env("TOOL_DEBUG_MODE", False),
            "tool_logging": self._get_bool_env("TOOL_LOGGING", False)
        }

        # Legacy support: Check for MCP_TOOL_CONFIG JSON file (with warning)
        config_path = os.environ.get('MCP_TOOL_CONFIG')
        if config_path and os.path.exists(config_path):
            logger.warning(
                f"DEPRECATED: Using JSON config file from MCP_TOOL_CONFIG ({config_path}). "
                f"Please migrate to environment variables in .env.dev for clean configuration."
            )
            try:
                with open(config_path, 'r') as f:
                    json_config = json.load(f)
                    # Merge JSON config into environment-based config (env vars take precedence)
                    for key, value in json_config.items():
                        if key == "enabled_tools" and isinstance(value, dict):
                            # Only use JSON values for tools not explicitly set in environment
                            for tool_name, tool_enabled in value.items():
                                env_var = f"TOOL_{tool_name.upper()}"
                                if env_var not in os.environ:
                                    config["enabled_tools"][tool_name] = tool_enabled
                        elif key not in ["debug_mode", "tool_logging"] or f"TOOL_{key.upper()}" not in os.environ:
                            config[key] = value
            except Exception as e:
                logger.warning(f"Failed to load legacy config from {config_path}: {e}")

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

    def _get_bool_env(self, env_var: str, default: bool) -> bool:
        """Get boolean value from environment variable with proper parsing"""
        value = os.environ.get(env_var)
        if value is None:
            return default
        return value.lower() in ('true', '1', 'yes', 'on')
        
    def is_enabled(self, tool_name: str) -> bool:
        """Check if a specific tool is enabled"""
        return self.config.get("enabled_tools", {}).get(tool_name, True)
    
    def get_enabled_tools(self) -> Dict[str, bool]:
        """Get all enabled tools configuration"""
        return self.config.get("enabled_tools", {})
