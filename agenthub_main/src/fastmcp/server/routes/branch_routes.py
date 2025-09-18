"""
User-Scoped Branch Routes with Authentication

This module provides user-isolated branch management endpoints
using JWT authentication and user-scoped repositories.
Follows the same pattern as project_routes.py
"""

import logging
from typing import Optional, Dict, Any, List
from fastapi import APIRouter, Depends, HTTPException, status, Form
from sqlalchemy.orm import Session
from pydantic import BaseModel

from ...auth.interface.fastapi_auth import get_db
from ...auth.domain.entities.user import User

# Use unified authentication that switches based on AUTH_PROVIDER
from ...auth.interface.fastapi_auth import get_current_user
from ...task_management.interface.api_controllers.branch_api_controller import BranchAPIController

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/v2/branches", tags=["User-Scoped Branches"])

# Initialize the branch API controller
branch_controller = BranchAPIController()


@router.post("/", response_model=dict)
async def create_branch(
    project_id: str = Form(...),
    git_branch_name: str = Form(...),
    description: str = Form(""),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Create a new branch for a project.
    
    The branch will be automatically associated with the project and current user,
    ensuring data isolation.
    """
    try:
        # Log the access for audit
        logger.info(f"User {current_user.email} creating branch: {git_branch_name} in project {project_id}")

        # Delegate to API controller
        result = await branch_controller.create_branch(
            project_id=project_id,
            name=git_branch_name,
            description=description,
            user_id=current_user.id,
            session=db
        )
        
        if not result.get("success"):
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=result.get("message", "Failed to create branch")
            )
        
        return {
            "success": True,
            "branch": result.get("branch"),
            "message": f"Branch created successfully for user {current_user.email}"
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error creating branch for user {current_user.id}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to create branch"
        )


@router.get("/", response_model=dict)
async def list_branches(
    project_id: Optional[str] = None,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    List all branches accessible to the authenticated user.
    
    Optionally filter by project_id. Only returns branches that belong to the current user's projects.
    """
    try:
        # Log the access for audit
        logger.info(f"User {current_user.email} listing branches" + (f" for project {project_id}" if project_id else ""))
        
        # Delegate to API controller
        result = await branch_controller.list_branches(
            project_id=project_id,
            user_id=current_user.id,
            session=db
        )
        
        if not result.get("success"):
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=result.get("message", "Failed to list branches")
            )
        
        return {
            "success": True,
            "branches": result.get("branches", []),
            "total": len(result.get("branches", [])),
            "message": f"Branches retrieved for user {current_user.email}"
        }
        
    except Exception as e:
        logger.error(f"Error listing branches for user {current_user.id}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to list branches"
        )


@router.get("/{branch_id}", response_model=dict)
async def get_branch(
    branch_id: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Get a specific branch by ID.
    
    Only returns the branch if it belongs to the current user's projects.
    """
    try:
        # Log the access for audit
        logger.info(f"User {current_user.email} accessing branch: {branch_id}")
        
        # Delegate to API controller
        result = await branch_controller.get_branch(
            branch_id=branch_id,
            user_id=current_user.id,
            session=db
        )
        
        if not result.get("success"):
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Branch not found or access denied"
            )
        
        return {
            "success": True,
            "branch": result.get("branch"),
            "message": f"Branch retrieved for user {current_user.email}"
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting branch {branch_id} for user {current_user.id}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to get branch"
        )


@router.put("/{branch_id}", response_model=dict)
async def update_branch(
    branch_id: str,
    name: Optional[str] = None,
    description: Optional[str] = None,
    status: Optional[str] = None,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Update a branch.
    
    Only allows updating branches that belong to the current user's projects.
    """
    try:
        # Log the access for audit
        logger.info(f"User {current_user.email} updating branch: {branch_id}")
        
        # Delegate to API controller
        result = await branch_controller.update_branch(
            branch_id=branch_id,
            name=name,
            description=description,
            status=status,
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
                    detail=result.get("message", "Failed to update branch")
                )
        
        return {
            "success": True,
            "branch": result.get("branch"),
            "message": f"Branch updated successfully for user {current_user.email}"
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error updating branch {branch_id} for user {current_user.id}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to update branch"
        )


@router.delete("/{branch_id}", response_model=dict)
async def delete_branch(
    branch_id: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Delete a branch.
    
    Only allows deleting branches that belong to the current user's projects.
    This will also delete all associated tasks and contexts.
    """
    try:
        # Log the access for audit
        logger.info(f"User {current_user.email} deleting branch: {branch_id}")
        
        # Delegate to API controller
        result = await branch_controller.delete_branch(
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
                    detail=result.get("message", "Failed to delete branch")
                )
        
        return {
            "success": True,
            "message": f"Branch {branch_id} deleted successfully for user {current_user.email}"
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error deleting branch {branch_id} for user {current_user.id}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to delete branch"
        )


@router.post("/{branch_id}/assign-agent", response_model=dict)
async def assign_agent_to_branch(
    branch_id: str,
    agent_id: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Assign an AI agent to a branch.
    
    Only works for branches that belong to the current user's projects.
    """
    try:
        # Log the access for audit
        logger.info(f"User {current_user.email} assigning agent {agent_id} to branch: {branch_id}")
        
        # Delegate to API controller
        result = await branch_controller.assign_agent(
            branch_id=branch_id,
            agent_id=agent_id,
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
                    detail=result.get("message", "Failed to assign agent")
                )
        
        return {
            "success": True,
            "assignment": result.get("assignment"),
            "message": f"Agent assigned successfully for user {current_user.email}"
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error assigning agent to branch {branch_id} for user {current_user.id}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to assign agent"
        )


@router.get("/{branch_id}/task-counts", response_model=dict)
async def get_branch_task_counts(
    branch_id: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Get task count statistics for a branch.
    
    Returns counts by status and other metrics. Only works for branches
    that belong to the current user's projects.
    """
    try:
        # Log the access for audit
        logger.info(f"User {current_user.email} getting task counts for branch: {branch_id}")
        
        # Delegate to API controller
        result = await branch_controller.get_branch_task_counts(
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
                    detail=result.get("message", "Failed to get task counts")
                )
        
        return {
            "success": True,
            "task_counts": result.get("task_counts"),
            "message": f"Task counts retrieved for user {current_user.email}"
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting task counts for branch {branch_id}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to get task counts"
        )


@router.post("/project/{project_id}/summaries", response_model=dict)
async def get_project_branches_with_task_counts(
    project_id: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Get all branches for a project with their task counts.
    
    This is an optimized endpoint for sidebar performance.
    """
    try:
        # Log the access for audit
        logger.info(f"User {current_user.email} loading branch summaries for project: {project_id}")
        
        # Delegate to API controller - using the optimized method
        result = branch_controller.get_branches_with_task_counts(
            project_id=project_id,
            user_id=current_user.id,
            session=db
        )
        
        if not result.get("success"):
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=result.get("message", "Failed to fetch branch summaries")
            )
        
        return {
            "success": True,
            "branches": result.get("branches", []),
            "project_summary": result.get("project_summary", {}),
            "total_branches": result.get("total_branches", 0),
            "message": f"Branch summaries retrieved for user {current_user.email}"
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error fetching branch summaries for project {project_id}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to fetch branch summaries"
        )