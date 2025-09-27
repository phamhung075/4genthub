"""
Tool Registry for Conditional MCP Tool Mounting

This module provides a registry system for conditionally mounting MCP tools
based on configuration settings.
"""

import logging
from typing import Dict, Any, Set, Callable, Optional
from fastmcp.server.server import FastMCP
from .tool_config_loader import ToolConfigLoader, ToolConfigError


logger = logging.getLogger(__name__)


class ToolRegistry:
    """Registry for managing conditional tool mounting."""

    def __init__(self, config_loader: Optional[ToolConfigLoader] = None):
        """
        Initialize the tool registry.

        Args:
            config_loader: Tool configuration loader instance.
                          If None, creates a new one.
        """
        self.config_loader = config_loader or ToolConfigLoader()
        self.registered_tools: Dict[str, Dict[str, Callable]] = {}
        self.available_dependencies: Set[str] = set()

    def load_configuration(self) -> None:
        """Load tool configuration from file."""
        try:
            self.config_loader.load_config()
            logger.info("Tool configuration loaded successfully")
        except ToolConfigError as e:
            logger.error(f"Failed to load tool configuration: {e}")
            logger.warning("Falling back to default configuration")

    def register_tool_group(self, group_name: str, tools: Dict[str, Callable]) -> None:
        """
        Register a group of tools.

        Args:
            group_name: Name of the tool group (e.g., 'authentication')
            tools: Dictionary mapping tool names to their implementation functions
        """
        self.registered_tools[group_name] = tools
        logger.debug(f"Registered tool group '{group_name}' with {len(tools)} tools")

    def add_dependency(self, dependency_name: str) -> None:
        """
        Add an available dependency.

        Args:
            dependency_name: Name of the dependency (e.g., 'auth_middleware')
        """
        self.available_dependencies.add(dependency_name)
        logger.debug(f"Added dependency: {dependency_name}")

    def mount_tools_to_server(self, server: FastMCP) -> Dict[str, Any]:
        """
        Mount enabled tools to the FastMCP server.

        Args:
            server: FastMCP server instance

        Returns:
            Dictionary with mounting results and statistics
        """
        mounting_stats = {
            "total_groups": 0,
            "total_tools": 0,
            "mounted_tools": 0,
            "skipped_tools": 0,
            "disabled_tools": 0,
            "dependency_failures": 0,
            "results": {}
        }

        should_log = self.config_loader.should_log_registration()
        should_log_skipped = self.config_loader.should_log_skipped_tools()

        for group_name, tools in self.registered_tools.items():
            mounting_stats["total_groups"] += 1
            group_results = {
                "enabled": [],
                "disabled": [],
                "skipped": [],
                "dependency_failures": []
            }

            for tool_name, tool_func in tools.items():
                mounting_stats["total_tools"] += 1

                try:
                    # Check if tool is enabled
                    if not self.config_loader.is_tool_enabled(group_name, tool_name):
                        mounting_stats["disabled_tools"] += 1
                        group_results["disabled"].append(tool_name)

                        if should_log_skipped:
                            logger.info(f"Tool '{tool_name}' disabled by configuration")
                        continue

                    # Check dependencies
                    if not self.config_loader.validate_dependencies(
                        group_name, tool_name, self.available_dependencies
                    ):
                        mounting_stats["dependency_failures"] += 1
                        group_results["dependency_failures"].append(tool_name)

                        if should_log_skipped:
                            logger.warning(
                                f"Tool '{tool_name}' skipped due to missing dependencies"
                            )
                        continue

                    # Mount the tool
                    self._mount_tool_to_server(server, tool_name, tool_func)
                    mounting_stats["mounted_tools"] += 1
                    group_results["enabled"].append(tool_name)

                    if should_log:
                        logger.info(f"Mounted tool: {tool_name}")

                except Exception as e:
                    mounting_stats["skipped_tools"] += 1
                    group_results["skipped"].append(tool_name)
                    logger.error(f"Failed to mount tool '{tool_name}': {e}")

            mounting_stats["results"][group_name] = group_results

        # Log summary
        self._log_mounting_summary(mounting_stats)

        return mounting_stats

    def _mount_tool_to_server(self, server: FastMCP, tool_name: str, tool_func: Callable) -> None:
        """
        Mount a single tool to the server.

        Args:
            server: FastMCP server instance
            tool_name: Name of the tool
            tool_func: Tool implementation function
        """
        # Get tool configuration for any metadata
        tool_config = self.config_loader.get_tool_config("authentication", tool_name)
        description = tool_config.get("description", f"MCP tool: {tool_name}")

        # Create a wrapper function with the server decorator
        # This mimics how controllers register tools with @mcp.tool()
        decorated_func = server.tool(description=description)(tool_func)

        # The tool is now registered with the server through the decorator
        logger.debug(f"Successfully mounted tool: {tool_name} with description: {description}")

    def _log_mounting_summary(self, stats: Dict[str, Any]) -> None:
        """Log a summary of tool mounting results."""
        logger.info("=== Tool Mounting Summary ===")
        logger.info(f"Total groups processed: {stats['total_groups']}")
        logger.info(f"Total tools found: {stats['total_tools']}")
        logger.info(f"Successfully mounted: {stats['mounted_tools']}")
        logger.info(f"Disabled by config: {stats['disabled_tools']}")
        logger.info(f"Dependency failures: {stats['dependency_failures']}")
        logger.info(f"Other failures: {stats['skipped_tools']}")

        # Log details by group if there were any issues
        for group_name, group_results in stats["results"].items():
            if (group_results["disabled"] or
                group_results["skipped"] or
                group_results["dependency_failures"]):

                logger.info(f"Group '{group_name}':")
                if group_results["enabled"]:
                    logger.info(f"  Enabled: {', '.join(group_results['enabled'])}")
                if group_results["disabled"]:
                    logger.info(f"  Disabled: {', '.join(group_results['disabled'])}")
                if group_results["dependency_failures"]:
                    logger.info(f"  Dep failures: {', '.join(group_results['dependency_failures'])}")
                if group_results["skipped"]:
                    logger.info(f"  Skipped: {', '.join(group_results['skipped'])}")

    def get_enabled_tools_summary(self) -> Dict[str, Any]:
        """
        Get a summary of enabled tools without mounting them.

        Returns:
            Dictionary with enabled tools by group
        """
        summary = {}

        for group_name in self.registered_tools.keys():
            enabled_tools = self.config_loader.get_enabled_tools(group_name)
            summary[group_name] = {
                "enabled_tools": enabled_tools,
                "total_tools": len(self.registered_tools[group_name]),
                "enabled_count": len(enabled_tools)
            }

        return summary

    def is_group_enabled(self, group_name: str) -> bool:
        """
        Check if an entire tool group is enabled.

        Args:
            group_name: Name of the tool group

        Returns:
            True if group has any enabled tools, False otherwise
        """
        enabled_tools = self.config_loader.get_enabled_tools(group_name)
        return len(enabled_tools) > 0

    def get_tool_info(self, group_name: str, tool_name: str) -> Dict[str, Any]:
        """
        Get detailed information about a specific tool.

        Args:
            group_name: Name of the tool group
            tool_name: Name of the tool

        Returns:
            Dictionary with tool information
        """
        tool_config = self.config_loader.get_tool_config(group_name, tool_name)

        return {
            "enabled": self.config_loader.is_tool_enabled(group_name, tool_name),
            "config": tool_config,
            "dependencies": tool_config.get("dependencies", []),
            "description": tool_config.get("description", ""),
            "deprecated": tool_config.get("deprecated", False),
            "deprecation_message": tool_config.get("deprecation_message", "")
        }