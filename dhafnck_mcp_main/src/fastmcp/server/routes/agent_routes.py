"""
User-Scoped Agent Routes with Authentication

This module provides user-isolated agent management endpoints
using JWT authentication and user-scoped repositories.
Follows the same pattern as project_routes.py
"""

import logging
from typing import Optional, Dict, Any, List
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from ...auth.interface.fastapi_auth import get_db
from ...auth.domain.entities.user import User

# Use unified authentication that switches based on AUTH_PROVIDER
from ...auth.interface.fastapi_auth import get_current_user
from ...task_management.interface.api_controllers.agent_api_controller import AgentAPIController

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/v2/agents", tags=["User-Scoped Agents"])

# Initialize the agent API controller
agent_controller = AgentAPIController()


@router.get("/metadata", response_model=dict)
async def get_all_agents_metadata(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
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
            user_id=current_user.id,
            session=db
        )
        
        if not result.get("success"):
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=result.get("message", "Failed to fetch agent metadata")
            )
        
        return {
            "success": True,
            "agents": result.get("agents", []),
            "total": result.get("total", 0),
            "message": f"Agent metadata retrieved for user {current_user.email}"
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error fetching agent metadata: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to fetch agent metadata"
        )


@router.get("/{agent_name}", response_model=dict)
async def get_single_agent_metadata(
    agent_name: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Get metadata for a specific agent by name.
    
    Args:
        agent_name: Name of the agent (e.g., 'coding_agent', 'debugger_agent')
    
    Returns detailed information about the specified agent.
    """
    try:
        # Log the access for audit
        logger.info(f"User {current_user.email} fetching metadata for agent: {agent_name}")
        
        # Delegate to API controller
        result = agent_controller.get_single_agent_metadata(
            agent_name=agent_name,
            user_id=current_user.id,
            session=db
        )
        
        if not result.get("success"):
            if "not found" in result.get("error", "").lower():
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail=f"Agent {agent_name} not found"
                )
            else:
                raise HTTPException(
                    status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                    detail=result.get("message", "Failed to fetch agent metadata")
                )
        
        return {
            "success": True,
            "agent": result.get("agent"),
            "message": f"Agent metadata retrieved for user {current_user.email}"
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error fetching agent {agent_name} metadata: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to fetch agent {agent_name} metadata"
        )


@router.post("/assign", response_model=dict)
async def assign_agent_to_branch(
    branch_id: str,
    agent_id: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Assign an agent to a git branch for automated task execution.
    
    Args:
        branch_id: UUID of the branch
        agent_id: Agent identifier (e.g., '@coding_agent')
    
    The agent will work on tasks within the specified branch.
    """
    try:
        # Log the access for audit
        logger.info(f"User {current_user.email} assigning agent {agent_id} to branch {branch_id}")
        
        # Delegate to API controller
        result = agent_controller.assign_agent(
            branch_id=branch_id,
            agent_id=agent_id,
            user_id=current_user.id,
            session=db
        )
        
        if not result.get("success"):
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=result.get("message", "Failed to assign agent")
            )
        
        return {
            "success": True,
            "assignment": result.get("assignment"),
            "message": f"Agent {agent_id} assigned to branch successfully"
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error assigning agent {agent_id} to branch {branch_id}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to assign agent"
        )


@router.delete("/unassign/{branch_id}", response_model=dict)
async def unassign_agent_from_branch(
    branch_id: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Remove agent assignment from a branch.
    
    Args:
        branch_id: UUID of the branch
    
    Stops the agent from working on tasks in this branch.
    """
    try:
        # Log the access for audit
        logger.info(f"User {current_user.email} unassigning agent from branch {branch_id}")
        
        # Delegate to API controller
        result = agent_controller.unassign_agent(
            branch_id=branch_id,
            user_id=current_user.id,
            session=db
        )
        
        if not result.get("success"):
            if "not found" in result.get("error", "").lower():
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail="Branch not found or no agent assigned"
                )
            else:
                raise HTTPException(
                    status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                    detail=result.get("message", "Failed to unassign agent")
                )
        
        return {
            "success": True,
            "message": f"Agent unassigned from branch {branch_id} successfully"
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error unassigning agent from branch {branch_id}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to unassign agent"
        )


@router.get("/branch/{branch_id}/assignment", response_model=dict)
async def get_branch_agent_assignment(
    branch_id: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Get current agent assignment for a branch.
    
    Args:
        branch_id: UUID of the branch
    
    Returns information about which agent (if any) is assigned to the branch.
    """
    try:
        # Log the access for audit
        logger.info(f"User {current_user.email} checking agent assignment for branch {branch_id}")
        
        # Delegate to API controller
        result = agent_controller.get_branch_assignment(
            branch_id=branch_id,
            user_id=current_user.id,
            session=db
        )
        
        if not result.get("success"):
            if "not found" in result.get("error", "").lower():
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail="Branch not found or access denied"
                )
            else:
                raise HTTPException(
                    status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                    detail=result.get("message", "Failed to get assignment")
                )
        
        return {
            "success": True,
            "assignment": result.get("assignment"),
            "message": f"Agent assignment retrieved for branch {branch_id}"
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting agent assignment for branch {branch_id}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to get agent assignment"
        )


@router.get("/project/{project_id}/assignments", response_model=dict)
async def get_project_agent_assignments(
    project_id: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Get all agent assignments for a project.
    
    Args:
        project_id: UUID of the project
    
    Returns all branches in the project with their assigned agents.
    """
    try:
        # Log the access for audit
        logger.info(f"User {current_user.email} fetching all agent assignments for project {project_id}")
        
        # Delegate to API controller
        result = agent_controller.get_project_assignments(
            project_id=project_id,
            user_id=current_user.id,
            session=db
        )
        
        if not result.get("success"):
            if "not found" in result.get("error", "").lower():
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail="Project not found or access denied"
                )
            else:
                raise HTTPException(
                    status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                    detail=result.get("message", "Failed to get assignments")
                )
        
        return {
            "success": True,
            "assignments": result.get("assignments", []),
            "total": len(result.get("assignments", [])),
            "message": f"Agent assignments retrieved for project {project_id}"
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting agent assignments for project {project_id}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to get agent assignments"
        )


@router.get("/capabilities", response_model=dict)
async def get_agent_capabilities(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Get capabilities summary for all agents.
    
    Returns a structured view of what each agent can do, useful for
    frontend UI to show available actions.
    """
    try:
        # Log the access for audit
        logger.info(f"User {current_user.email} fetching agent capabilities")
        
        # Delegate to API controller
        result = agent_controller.get_all_capabilities(
            user_id=current_user.id,
            session=db
        )
        
        if not result.get("success"):
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=result.get("message", "Failed to fetch capabilities")
            )
        
        return {
            "success": True,
            "capabilities": result.get("capabilities", {}),
            "categories": result.get("categories", []),
            "message": f"Agent capabilities retrieved for user {current_user.email}"
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error fetching agent capabilities: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to fetch agent capabilities"
        )