"""
Call Agent MCP Controller

MCP tool for loading and invoking specialized agents using the new
database-backed user agent instance system.
"""

import logging
from typing import Any

from ....task_management.interface.mcp_controllers.auth_helper.services.authentication_service import (
    AuthenticationService,
)
from ...application.facades import AgentManagementFacade
from ...domain.value_objects.user_id import UserId

logger = logging.getLogger(__name__)


def call_agent_mcp_tool(name_agent: str, user_id: str = None) -> dict[str, Any]:
    """
    Load and invoke a specialized agent by name.

    This MCP tool:
    1. Authenticates the user (from JWT token or testing mode)
    2. Gets or creates a user-specific agent instance
    3. Returns the agent configuration for execution
    4. Tracks agent usage

    Args:
        name_agent: Agent slug (e.g., "coding-agent", "master-orchestrator-agent")
        user_id: Optional user ID (extracted from JWT token if not provided)

    Returns:
        Dictionary containing:
        {
            "success": bool,
            "agent": {
                "name": str,
                "slug": str,
                "description": str,
                "system_prompt": str,
                "tools": List[str],
                "capabilities": Dict[str, Any],
                "rules": Optional[List[str]],
                "output_format": Optional[str],
                "category": str,
                "version": str,
                "is_customized": bool,
                "instance_id": str,
                "template_id": str,
                "metadata": Dict[str, Any]
            },
            "source": "agent-management-system"
        }

    Raises:
        UserAuthenticationRequiredError: If authentication fails
        ValueError: If agent template not found
    """
    logger.info(f"🤖 Call Agent MCP Tool: agent={name_agent}")

    try:
        # 1. Authenticate user
        auth_service = AuthenticationService()
        authenticated_user_id = auth_service.get_authenticated_user_id(
            provided_user_id=user_id,
            operation_name="call_agent"
        )
        logger.info(f"✅ Authenticated user: {authenticated_user_id}")

        # 2. Get agent configuration via facade
        facade = AgentManagementFacade()
        user_id_vo = UserId(authenticated_user_id)

        agent_config = facade.get_agent_for_call(
            user_id=user_id_vo,
            agent_slug=name_agent
        )

        logger.info(
            f"✅ Agent loaded: {agent_config['name']} "
            f"(customized={agent_config['is_customized']})"
        )

        # 3. Return formatted response
        return {
            "success": True,
            "agent": agent_config,
            "source": "agent-management-system"
        }

    except ValueError as e:
        logger.error(f"❌ Agent not found: {name_agent} - {e}")
        return {
            "success": False,
            "error": f"Agent not found: {name_agent}",
            "message": str(e)
        }

    except Exception as e:
        logger.error(f"❌ Error loading agent {name_agent}: {e}", exc_info=True)
        return {
            "success": False,
            "error": "Failed to load agent",
            "message": str(e)
        }
