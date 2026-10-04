"""
User-Scoped Agent Routes with Authentication

This module provides user-isolated agent management endpoints
using JWT authentication and user-scoped repositories.
Follows the same pattern as project_routes.py
"""

import logging
from typing import Any

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from ...auth.domain.entities.user import User

# Use unified authentication that switches based on AUTH_PROVIDER
from ...auth.interface.fastapi_auth import get_current_user, get_db
from ...task_management.interface.api_controllers.agent_api_controller import (
    AgentAPIController,
)

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/v2/agents", tags=["User-Scoped Agents"])

# Initialize the agent API controller
agent_controller = AgentAPIController()


@router.get("/metadata", response_model=dict)
async def get_all_agents_metadata(
    current_user: User = Depends(get_current_user), db: Session = Depends(get_db)
):
    """
    Get metadata for all available agents.

    Returns comprehensive information about each agent including capabilities,
    description, and supported operations.
    """
    try:
        # Log the access for audit
        logger.info(f"User {current_user.email} fetching all agents metadata")

        # Delegate to API controller
        result = agent_controller.get_agent_metadata(
            user_id=current_user.id, session=db
        )

        if not result.get("success"):
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=result.get("message") or "Failed to fetch agent metadata",
            )

        return result

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error fetching agent metadata: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to fetch agent metadata",
        )


@router.post("/call", response_model=dict)
async def call_agent(
    request: dict[str, Any],
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    Call an agent to get its information and capabilities.

    Uses the new user-agent-instance system with AgentManagementFacade.
    Gets or creates a user-specific instance and returns full agent configuration.

    Args:
        request: Dict with 'agent_name' and optional 'params'

    Returns:
        Agent configuration with system_prompt, tools, capabilities, rules
    """
    try:
        agent_name = request.get("agent_name")
        request.get("params", {})

        if not agent_name:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST, detail="agent_name is required"
            )

        # Import the new agent management system
        from ...agent_management.application.facades.agent_management_facade import (
            AgentManagementFacade,
        )
        from ...agent_management.domain.value_objects.user_id import UserId
        from ...agent_management.infrastructure.repositories.orm.agent_template_repository import (
            ORMAgentTemplateRepository,
        )
        from ...agent_management.infrastructure.repositories.orm.user_agent_instance_repository import (
            ORMUserAgentInstanceRepository,
        )

        # Log the access for audit
        logger.info(f"User {current_user.email} calling agent: {agent_name}")

        # Initialize facade with database session
        template_repo = ORMAgentTemplateRepository()
        instance_repo = ORMUserAgentInstanceRepository()
        template_repo._session = db
        instance_repo._session = db

        facade = AgentManagementFacade(
            template_repository=template_repo, instance_repository=instance_repo
        )

        # Get agent configuration using the new system
        user_id_vo = UserId(current_user.id)
        agent_config = facade.get_agent_for_call(
            user_id=user_id_vo, agent_slug=agent_name
        )

        logger.info(
            f"Agent {agent_name} loaded successfully for user {current_user.email}"
        )

        return {
            "success": True,
            "agent": agent_config,
            "source": "agent-management-system",
            "called_by": current_user.email,
        }

    except HTTPException:
        raise
    except ValueError:
        # Template not found or invalid agent name
        logger.error(f"Agent not found: {agent_name}")
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Agent not found: {agent_name}",
        )
    except Exception as e:
        logger.error(f"Error calling agent {agent_name}: {e}", exc_info=True)
        import traceback

        return {
            "success": False,
            "message": "Failed to call agent",
            "error": str(e),
            "traceback": traceback.format_exc(),
        }
