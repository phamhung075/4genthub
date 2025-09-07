"""Call Agent MCP Controller

This controller handles MCP tool registration for agent invocation operations,
following DDD principles by delegating business logic to the application use case.
Documentation is loaded from external files for maintainability.
"""

import logging
from typing import Dict, Any, Annotated
from pydantic import Field  # type: ignore
from typing import TYPE_CHECKING
import os

if TYPE_CHECKING:
    from fastmcp.server.server import FastMCP

from .desc import description_loader

logger = logging.getLogger(__name__)

class CallAgentMCPController:
    """
    MCP Controller for agent invocation operations.
    Handles only MCP protocol concerns and delegates business operations
    to the CallAgentUseCase following proper DDD layer separation.
    """
    def __init__(self, call_agent_use_case):
        """
        Initialize controller with call agent use case.
        Args:
            call_agent_use_case: Application use case for agent operations
        """
        self._call_agent_use_case = call_agent_use_case
        logger.info("CallAgentMCPController initialized")

    def register_tools(self, mcp: "FastMCP"):
        """Register call agent MCP tools with the FastMCP server"""
        # Load documentation for the call_agent tool
        call_agent_desc = description_loader.get_all_descriptions()["agent"]["call_agent"]

        @mcp.tool(name="call_agent", description=call_agent_desc["description"])
        def call_agent(
            name_agent: Annotated[str, Field(description=call_agent_desc["parameters"].get("name_agent", "Name of the agent to call"))]
        ) -> Dict[str, Any]:
            return self.call_agent(name_agent=name_agent)

    def call_agent(self, name_agent: str) -> Dict[str, Any]:
        """
        Unified agent invocation method that handles all agent operations.
        Args:
            name_agent: Name of the agent to call
        Returns:
            Dict containing operation result
        """
        AGENT_DIR = os.path.join(os.path.dirname(__file__), '../../agent-library/agents')
        available_agents = []
        try:
            for entry in os.listdir(os.path.abspath(AGENT_DIR)):
                if entry.endswith('_agent') and os.path.isdir(os.path.join(os.path.abspath(AGENT_DIR), entry)):
                    available_agents.append(entry)
        except Exception:
            pass
        try:
            if not name_agent:
                return {
                    "success": False,
                    "error": "Missing required field: name_agent",
                    "error_code": "MISSING_FIELD",
                    "field": "name_agent",
                    "expected": "A valid agent name string",
                    "hint": "Include 'name_agent' in your request body",
                    "available_agents": available_agents
                }
            return self._call_agent_use_case.execute(name_agent)
        except Exception as e:
            logger.error(f"Call agent error: {e}")
            return {
                "success": False,
                "error": f"Call agent operation failed: {str(e)}",
                "error_code": "INTERNAL_ERROR",
                "details": str(e),
                "available_agents": available_agents
            }