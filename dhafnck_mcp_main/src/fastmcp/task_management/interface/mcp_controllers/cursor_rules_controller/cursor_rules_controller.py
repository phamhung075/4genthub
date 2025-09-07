"""Cursor Rules MCP Controller

This controller handles MCP tool registration for cursor rules management,
following DDD principles by delegating business logic to application services.
"""

import logging
from typing import Dict, Any, Annotated
from pydantic import Field # type: ignore
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from fastmcp.server.server import FastMCP
    from ....application.facades.rule_application_facade import RuleApplicationFacade

from .manage_rule_description import get_manage_rule_description, get_manage_rule_parameters
from .handlers import RuleManagementHandler

logger = logging.getLogger(__name__)


class CursorRulesController:
    """
    MCP Controller for cursor rules management.
    
    Handles only MCP protocol concerns and delegates business operations
    to the RuleApplicationFacade following proper DDD layer separation.
    Documentation is loaded from external files for maintainability.
    """
    
    def __init__(self, rule_facade: "RuleApplicationFacade"):
        """
        Initialize controller with rule application facade.
        
        Args:
            rule_facade: Application facade for rule operations
        """
        self._handler = RuleManagementHandler(rule_facade)
        logger.info("CursorRulesController initialized")
    
    def register_tools(self, mcp: "FastMCP"):
        """Register cursor rules MCP tools with the FastMCP server"""
        # Get centralized parameter definitions
        params = get_manage_rule_parameters()

        @mcp.tool(description=get_manage_rule_description())
        def manage_rule(
            action: Annotated[str, Field(description=params["action"]["description"])],
            target: Annotated[str, Field(description=params["target"]["description"])] = "",
            content: Annotated[str, Field(description=params["content"]["description"])] = ""
        ) -> Dict[str, Any]:
            """Manage rule operations with two-stage validation pattern:
            - Schema level: Only 'action' is required (MCP compatibility)
            - Business logic level: Action-specific validation in handler
            """
            return self._handler.handle_manage_rule(action, target, content)