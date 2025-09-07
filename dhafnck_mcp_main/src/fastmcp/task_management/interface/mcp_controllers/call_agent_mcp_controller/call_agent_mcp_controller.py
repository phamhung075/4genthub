"""Call Agent MCP Controller

This controller handles MCP tool registration for agent invocation operations,
following DDD principles by delegating business logic to the application use case.
Documentation is loaded from external files for maintainability.
"""

import logging
from typing import Dict, Any, Annotated
from pydantic import Field  # type: ignore
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from fastmcp.server.server import FastMCP

from .call_agent_description import get_call_agent_description, get_call_agent_parameters
from .handlers import AgentInvocationHandler
from .services import AgentDiscoveryService

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
        self._handler = AgentInvocationHandler(call_agent_use_case)
        self._discovery_service = AgentDiscoveryService()
        logger.info("CallAgentMCPController initialized")

    def register_tools(self, mcp: "FastMCP"):
        """Register call agent MCP tools with the FastMCP server"""
        
        # Get centralized parameter definitions
        params = get_call_agent_parameters()

        @mcp.tool(description=get_call_agent_description())
        def call_agent(
            name_agent: Annotated[str, Field(description=params["name_agent"]["description"])]
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
        # Discover available agents for error reporting
        available_agents = self._discovery_service.get_available_agents()
        
        # Delegate to handler
        return self._handler.invoke_agent(name_agent, available_agents)