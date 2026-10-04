"""
User-Scoped Agent Routes with Authentication

This module provides user-isolated agent management endpoints
using JWT authentication and user-scoped repositories.
Follows the same pattern as project_routes.py
"""

import logging

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
