"""
User-Scoped Branch Routes with Authentication

This module provides user-isolated branch management endpoints
using JWT authentication and user-scoped repositories.
Follows the same pattern as project_routes.py
"""

from __future__ import annotations

import logging

from fastapi import APIRouter, Depends, Form, HTTPException, status
from pydantic import BaseModel
from sqlalchemy.orm import Session

from ...auth.domain.entities.user import User

# Use unified authentication that switches based on AUTH_PROVIDER
from ...auth.interface.fastapi_auth import get_current_user, get_db
from ...task_management.interface.api_controllers.branch_api_controller import (
    BranchAPIController,
)

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
    db: Session = Depends(get_db),
):
    """
    Create a new branch for a project.

    The branch will be automatically associated with the project and current user,
    ensuring data isolation.
    """
    try:
        # Log the access for audit
        logger.info(
            f"User {current_user.email} creating branch: {git_branch_name} in project {project_id}"
        )

        # Delegate to API controller
        result = await branch_controller.create_branch(
            project_id=project_id,
            name=git_branch_name,
            description=description,
            user_id=current_user.id,
            session=db,
        )

        # ✅ FIX: result is a BranchResponse Pydantic model, not a dict
        if not result.success:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=result.message or "Failed to create branch",
            )

        # Return the Pydantic model directly - FastAPI will serialize it
        return result.model_dump(by_alias=True)

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error creating branch for user {current_user.id}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to create branch",
        )


@router.get("/", response_model=dict)
async def list_branches(
    project_id: str | None = None,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    List all branches accessible to the authenticated user.

    Optionally filter by project_id. Only returns branches that belong to the current user's projects.
    """
    try:
        # Log the access for audit
        logger.info(
            f"User {current_user.email} listing branches"
            + (f" for project {project_id}" if project_id else "")
        )

        # Delegate to API controller
        result = await branch_controller.list_branches(
            project_id=project_id, user_id=current_user.id, session=db
        )

        # ✅ FIX: result is a BranchesResponse Pydantic model, not a dict
        if not result.success:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=result.message or "Failed to list branches",
            )

        # Return the Pydantic model directly - FastAPI will serialize it
        return result.model_dump(by_alias=True)

    except Exception as e:
        logger.error(f"Error listing branches for user {current_user.id}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to list branches",
        )


@router.get("/{branch_id}", response_model=dict)
async def get_branch(
    branch_id: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
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
            branch_id=branch_id, user_id=current_user.id, session=db
        )

        if not result.success:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Branch not found or access denied",
            )

        return result.model_dump(by_alias=True)

    except HTTPException:
        raise
    except Exception as e:
        logger.error(
            f"Error getting branch {branch_id} for user {current_user.id}: {e}"
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to get branch",
        )


@router.put("/{branch_id}", response_model=dict)
async def update_branch(
    branch_id: str,
    name: str | None = None,
    description: str | None = None,
    status: str | None = None,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
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
            session=db,
        )

        if not result.success:
            if result.error and "not found" in result.error.lower():
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail="Branch not found or access denied",
                )
            else:
                raise HTTPException(
                    status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                    detail=result.message or "Failed to update branch",
                )

        return result.model_dump(by_alias=True)

    except HTTPException:
        raise
    except Exception as e:
        logger.error(
            f"Error updating branch {branch_id} for user {current_user.id}: {e}"
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to update branch",
        )


@router.delete("/{branch_id}", response_model=dict)
async def delete_branch(
    branch_id: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
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
            branch_id=branch_id, user_id=current_user.id, session=db
        )

        if not result.success:
            if result.error and "not found" in result.error.lower():
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail="Branch not found or access denied",
                )
            else:
                raise HTTPException(
                    status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                    detail=result.message or "Failed to delete branch",
                )

        # Return the Pydantic model directly - FastAPI will serialize it
        return result.model_dump(by_alias=True)

    except HTTPException:
        raise
    except Exception as e:
        logger.error(
            f"Error deleting branch {branch_id} for user {current_user.id}: {e}"
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to delete branch",
        )


@router.post("/{branch_id}/assign-agent", response_model=dict)
async def assign_agent_to_branch(
    branch_id: str,
    agent_id: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    Assign an AI agent to a branch.

    Only works for branches that belong to the current user's projects.
    """
    try:
        # Log the access for audit
        logger.info(
            f"User {current_user.email} assigning agent {agent_id} to branch: {branch_id}"
        )

        # Delegate to API controller
        result = await branch_controller.assign_agent(
            branch_id=branch_id, agent_id=agent_id, user_id=current_user.id, session=db
        )

        if not result.success:
            if result.error and "not found" in result.error.lower():
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail="Branch not found or access denied",
                )
            else:
                raise HTTPException(
                    status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                    detail=result.message or "Failed to assign agent",
                )

        return result.model_dump(by_alias=True)

    except HTTPException:
        raise
    except Exception as e:
        logger.error(
            f"Error assigning agent to branch {branch_id} for user {current_user.id}: {e}"
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to assign agent",
        )


@router.get("/{branch_id}/task-counts", response_model=dict)
async def get_branch_task_counts(
    branch_id: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    Get task count statistics for a branch.

    Returns counts by status and other metrics. Only works for branches
    that belong to the current user's projects.
    """
    try:
        # Log the access for audit
        logger.info(
            f"User {current_user.email} getting task counts for branch: {branch_id}"
        )

        # Delegate to API controller
        result = await branch_controller.get_branch_task_counts(
            branch_id=branch_id, user_id=current_user.id, session=db
        )

        if not result.success:
            if result.error and "not found" in result.error.lower():
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail="Branch not found or access denied",
                )
            else:
                raise HTTPException(
                    status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                    detail=result.message or "Failed to get task counts",
                )

        # Return the Pydantic model directly - FastAPI will serialize it
        return result.model_dump(by_alias=True)

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting task counts for branch {branch_id}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to get task counts",
        )


@router.post("/project/{project_id}/summaries", response_model=dict)
async def get_project_branches_with_task_counts(
    project_id: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    Get all branches for a project with their task counts.

    This is an optimized endpoint for sidebar performance.
    """
    try:
        # Log the access for audit
        logger.info(
            f"User {current_user.email} loading branch summaries for project: {project_id}"
        )

        # Delegate to API controller - using the optimized method
        result = branch_controller.get_branches_with_task_counts(
            project_id=project_id, user_id=current_user.id, session=db
        )

        if not result.success:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=result.message or "Failed to fetch branch summaries",
            )

        # Return the Pydantic model directly - FastAPI will serialize it
        return result.model_dump(by_alias=True)

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error fetching branch summaries for project {project_id}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to fetch branch summaries",
        )


# Request model for bulk summaries
class BulkSummaryRequest(BaseModel):
    project_ids: list[str] | None = None
    include_archived: bool = False


@router.post("/summaries/bulk", response_model=dict)
async def get_bulk_summaries(
    request: BulkSummaryRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    Get bulk summaries for multiple projects in a single request.

    This endpoint queries the materialized views for optimized performance.
    Returns all branch summaries and project summaries in one response.
    """
    try:
        # Log the access for audit
        project_count = len(request.project_ids) if request.project_ids else "all"
        logger.info(
            f"User {current_user.email} loading bulk summaries for {project_count} projects"
        )

        # Delegate to API controller - using the new bulk method
        result = branch_controller.get_bulk_summaries(
            project_ids=request.project_ids,
            user_id=current_user.id,
            include_archived=request.include_archived,
            session=db,
        )

        # ✅ FIX: result is a BulkSummaryResponse Pydantic model, not a dict
        if not result.success:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=result.message or "Failed to fetch bulk summaries",
            )

        # Return the Pydantic model directly - FastAPI will serialize it
        return result.model_dump(by_alias=True)

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error fetching bulk summaries for user {current_user.id}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to fetch bulk summaries",
        )
