"""
Tool Configuration Loader for MCP Server

This module provides configuration loading and validation for server tools,
allowing dynamic enabling/disabling of tools based on YAML configuration.
"""

import os
import logging
from pathlib import Path
from typing import Dict, Any, Optional, List, Set
import yaml


logger = logging.getLogger(__name__)


class ToolConfigError(Exception):
    """Raised when there are issues with tool configuration."""
    pass


class ToolConfigLoader:
    """Loads and manages tool configuration from YAML files."""

    def __init__(self, config_path: Optional[str] = None):
        """
        Initialize the tool configuration loader.

        Args:
            config_path: Path to the tool configuration file.
                        If None, uses default path in src/config/tool_config.yaml
        """
        self.config_path = config_path or self._get_default_config_path()
        self.config_data: Dict[str, Any] = {}
        self.environment = self._detect_environment()

    def _get_default_config_path(self) -> str:
        """Get the default configuration file path."""
        # Find the config directory relative to this file
        current_dir = Path(__file__).parent
        config_dir = current_dir.parent.parent / "config"
        return str(config_dir / "tool_config.yaml")

    def _detect_environment(self) -> str:
        """Detect the current environment."""
        env = os.environ.get("ENVIRONMENT", "development")
        production_indicators = ["prod", "production", "live"]

        if any(indicator in env.lower() for indicator in production_indicators):
            return "production"
        return "development"

    def load_config(self) -> Dict[str, Any]:
        """
        Load the tool configuration from YAML file.

        Returns:
            Dict containing the parsed configuration

        Raises:
            ToolConfigError: If configuration cannot be loaded or is invalid
        """
        try:
            config_path = Path(self.config_path)

            if not config_path.exists():
                logger.warning(f"Tool config file not found at {config_path}, using defaults")
                return self._get_default_config()

            with open(config_path, 'r', encoding='utf-8') as file:
                self.config_data = yaml.safe_load(file)

            # Validate configuration
            self._validate_config()

            # Apply environment overrides
            self._apply_environment_overrides()

            logger.info(f"Tool configuration loaded from {config_path}")
            return self.config_data

        except yaml.YAMLError as e:
            raise ToolConfigError(f"Invalid YAML in config file: {e}")
        except Exception as e:
            raise ToolConfigError(f"Failed to load config file: {e}")

    def _get_default_config(self) -> Dict[str, Any]:
        """Get default configuration when file is missing."""
        return {
            "version": "1.0.0",
            "tools": {
                "authentication": {
                    "enabled": True,
                    "tools": {
                        "validate_token": {"enabled": True},
                        "get_rate_limit_status": {"enabled": True},
                        "revoke_token": {"enabled": True},
                        "get_auth_status": {"enabled": True},
                        "generate_token": {"enabled": False}
                    }
                },
                "connection": {
                    "enabled": True,
                    "tools": {
                        "manage_connection": {"enabled": True}
                    }
                }
            },
            "global": {
                "respect_auth_env": True,
                "auth_env_override": True,
                "log_tool_registration": True
            }
        }

    def _validate_config(self) -> None:
        """Validate the loaded configuration structure."""
        if not isinstance(self.config_data, dict):
            raise ToolConfigError("Configuration must be a dictionary")

        # Check version compatibility
        version = self.config_data.get("version", "1.0.0")
        if not self._is_version_compatible(version):
            raise ToolConfigError(f"Unsupported configuration version: {version}")

        # Validate tools section
        tools = self.config_data.get("tools", {})
        if not isinstance(tools, dict):
            raise ToolConfigError("'tools' section must be a dictionary")

        # Validate each tool group
        for group_name, group_config in tools.items():
            self._validate_tool_group(group_name, group_config)

    def _validate_tool_group(self, group_name: str, group_config: Dict[str, Any]) -> None:
        """Validate a tool group configuration."""
        if not isinstance(group_config, dict):
            raise ToolConfigError(f"Tool group '{group_name}' must be a dictionary")

        if "tools" in group_config:
            tools = group_config["tools"]
            if not isinstance(tools, dict):
                raise ToolConfigError(f"Tools in group '{group_name}' must be a dictionary")

    def _is_version_compatible(self, version: str) -> bool:
        """Check if the configuration version is compatible."""
        # For now, support any 1.x.x version
        return version.startswith("1.")

    def _apply_environment_overrides(self) -> None:
        """Apply environment-specific configuration overrides."""
        overrides = self.config_data.get("environment_overrides", {})
        env_overrides = overrides.get(self.environment, {})

        if env_overrides:
            logger.info(f"Applying {self.environment} environment overrides")
            self._merge_config(self.config_data, env_overrides)

    def _merge_config(self, base: Dict[str, Any], override: Dict[str, Any]) -> None:
        """Recursively merge override configuration into base configuration."""
        for key, value in override.items():
            if key in base and isinstance(base[key], dict) and isinstance(value, dict):
                self._merge_config(base[key], value)
            else:
                base[key] = value

    def is_tool_enabled(self, group_name: str, tool_name: str) -> bool:
        """
        Check if a specific tool is enabled.

        Args:
            group_name: Name of the tool group (e.g., 'authentication')
            tool_name: Name of the tool (e.g., 'validate_token')

        Returns:
            True if the tool should be enabled, False otherwise
        """
        # Check AUTH_ENABLED override for authentication tools
        if group_name == "authentication":
            global_config = self.config_data.get("global", {})
            if global_config.get("respect_auth_env", True):
                auth_enabled = os.environ.get("AUTH_ENABLED", "true").lower() == "true"
                if not auth_enabled and global_config.get("auth_env_override", True):
                    logger.info(f"AUTH_ENABLED=false, disabling auth tool: {tool_name}")
                    return False

        # Check group-level enabled flag
        group_config = self.config_data.get("tools", {}).get(group_name, {})
        if not group_config.get("enabled", True):
            logger.info(f"Tool group '{group_name}' is disabled, skipping {tool_name}")
            return False

        # Check tool-level enabled flag
        tool_config = group_config.get("tools", {}).get(tool_name, {})
        tool_enabled = tool_config.get("enabled", True)

        if not tool_enabled:
            logger.info(f"Tool '{tool_name}' in group '{group_name}' is disabled")

        return tool_enabled

    def get_tool_config(self, group_name: str, tool_name: str) -> Dict[str, Any]:
        """
        Get configuration for a specific tool.

        Args:
            group_name: Name of the tool group
            tool_name: Name of the tool

        Returns:
            Dictionary containing tool configuration
        """
        group_config = self.config_data.get("tools", {}).get(group_name, {})
        return group_config.get("tools", {}).get(tool_name, {})

    def get_enabled_tools(self, group_name: str) -> List[str]:
        """
        Get list of enabled tools in a group.

        Args:
            group_name: Name of the tool group

        Returns:
            List of enabled tool names
        """
        group_config = self.config_data.get("tools", {}).get(group_name, {})

        # If group is disabled, return empty list
        if not group_config.get("enabled", True):
            return []

        enabled_tools = []
        tools_config = group_config.get("tools", {})

        for tool_name, tool_config in tools_config.items():
            if self.is_tool_enabled(group_name, tool_name):
                enabled_tools.append(tool_name)

        return enabled_tools

    def validate_dependencies(self, group_name: str, tool_name: str,
                            available_dependencies: Set[str]) -> bool:
        """
        Validate that all dependencies for a tool are available.

        Args:
            group_name: Name of the tool group
            tool_name: Name of the tool
            available_dependencies: Set of available dependency names

        Returns:
            True if all dependencies are satisfied, False otherwise
        """
        tool_config = self.get_tool_config(group_name, tool_name)
        dependencies = tool_config.get("dependencies", [])

        missing_deps = [dep for dep in dependencies if dep not in available_dependencies]

        if missing_deps:
            logger.warning(f"Tool '{tool_name}' missing dependencies: {missing_deps}")

            # Check if we should fail silently
            global_config = self.config_data.get("global", {})
            if global_config.get("fail_silently_on_missing_deps", True):
                return False
            else:
                raise ToolConfigError(
                    f"Tool '{tool_name}' has missing dependencies: {missing_deps}"
                )

        return True

    def should_log_registration(self) -> bool:
        """Check if tool registration should be logged."""
        global_config = self.config_data.get("global", {})
        return global_config.get("log_tool_registration", True)

    def should_log_skipped_tools(self) -> bool:
        """Check if skipped tools should be logged."""
        mounting_config = self.config_data.get("mounting", {})
        return mounting_config.get("log_skipped_tools", True)

    def get_disabled_strategy(self) -> str:
        """Get the strategy for handling disabled tools."""
        mounting_config = self.config_data.get("mounting", {})
        return mounting_config.get("disabled_strategy", "skip")