"""
Call Agent MCP Controller Wrapper

Provides a controller class that follows the existing DDD pattern for MCP tool registration.
"""

import logging
from typing import TYPE_CHECKING, Any

from .call_agent import call_agent_mcp_tool

if TYPE_CHECKING:
    from ....server.server import FastMCP

logger = logging.getLogger(__name__)


class CallAgentMCPController:
    """
    MCP Controller for call_agent tool.

    This controller follows the existing DDD pattern by providing a
    register_tools() method for consistent tool registration.
    """

    def __init__(self):
        """Initialize the controller."""
        logger.info("CallAgentMCPController initialized (agent_management module)")

    def register_tools(self, mcp: "FastMCP") -> None:
        """
        Register call_agent tool with the MCP server.

        Args:
            mcp: FastMCP server instance
        """
        logger.info(
            "Registering call_agent tool (new agent_management implementation)..."
        )

        # Register the tool with description
        @mcp.tool(
            description=(
                "Load and invoke a specialized agent by name using the database-backed "
                "user agent instance system. Returns agent configuration including "
                "system_prompt, tools, and capabilities."
            )
        )
        def call_agent(name_agent: str, user_id: str = None) -> dict[str, Any]:
            """
            Load and invoke a specialized agent.

            Args:
                name_agent: Agent slug (e.g., "coding-agent", "master-orchestrator-agent")
                user_id: Optional user ID (extracted from JWT token if not provided)

            Returns:
                Agent configuration with system_prompt, tools, and capabilities
            """
            return call_agent_mcp_tool(name_agent=name_agent, user_id=user_id)

        logger.info("call_agent tool registered successfully")
