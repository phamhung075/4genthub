"""DDD-Compliant Connection Management Tools

This module provides DDD-compliant MCP tools for connection management by:
- Using controllers that delegate to application facades
- Removing business logic from the interface layer
- Following proper dependency direction (Interface → Application → Domain ← Infrastructure)
- Providing clean separation of concerns
- Using external description files for clean documentation separation

This serves as the proper DDD implementation for connection management tools.
"""

import logging
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from fastmcp.server.server import FastMCP

# Interface layer imports (same layer, acceptable)
from .controllers.connection_mcp_controller import ConnectionMCPController

# Application layer imports (proper DDD dependency direction)
from ..application.facades.connection_application_facade import ConnectionApplicationFacade

# Infrastructure layer imports (proper DDD dependency direction)
from ..infrastructure.repositories.in_memory_server_repository import InMemoryServerRepository
from ..infrastructure.repositories.in_memory_connection_repository import InMemoryConnectionRepository
from ..infrastructure.services.mcp_server_health_service import MCPServerHealthService
from ..infrastructure.services.mcp_connection_diagnostics_service import MCPConnectionDiagnosticsService
from ..infrastructure.services.mcp_status_broadcasting_service import MCPStatusBroadcastingService

logger = logging.getLogger(__name__)


class DDDCompliantConnectionTools:
    """
    DDD-compliant MCP tools for connection management.
    
    This class follows proper DDD architecture by:
    - Delegating to application facades instead of containing business logic
    - Using dependency injection for proper layer separation
    - Maintaining clean boundaries between layers
    """
    
    def __init__(self):
        """Initialize DDD-compliant connection tools with proper dependency injection"""
        # Infrastructure layer - Repository implementations
        self._server_repository = InMemoryServerRepository()
        self._connection_repository = InMemoryConnectionRepository()
        
        # Infrastructure layer - Service implementations
        self._health_service = MCPServerHealthService()
        self._diagnostics_service = MCPConnectionDiagnosticsService()
        self._broadcasting_service = MCPStatusBroadcastingService()
        
        # Application layer - Facade
        self._connection_facade = ConnectionApplicationFacade(
            server_repository=self._server_repository,
            connection_repository=self._connection_repository,
            health_service=self._health_service,
            diagnostics_service=self._diagnostics_service,
            broadcasting_service=self._broadcasting_service
        )
        
        # Interface layer - Controller
        self._controller = ConnectionMCPController(self._connection_facade)
        
        logger.info("DDDCompliantConnectionTools initialized with proper DDD architecture")
    
    def register_tools(self, server: 'FastMCP') -> None:
        """Register DDD-compliant connection management tools via controller"""
        
        # Delegate tool registration to the controller
        # This follows the same pattern as task management
        self._controller.register_tools(server)
        
        logger.info("DDD-compliant connection management tools registered successfully")


def register_ddd_connection_tools(server: 'FastMCP') -> None:
    """Register DDD-compliant connection management tools with the FastMCP server"""
    tools = DDDCompliantConnectionTools()
    tools.register_tools(server)
    logger.info("DDD-compliant connection management tools registered") 