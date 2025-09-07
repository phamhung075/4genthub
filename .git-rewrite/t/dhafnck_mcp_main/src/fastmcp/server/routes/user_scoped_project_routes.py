"""
User-Scoped Project Routes with Authentication

This module provides user-isolated project management endpoints
using JWT authentication and user-scoped repositories.
"""

import logging
from typing import Optional, Dict, Any
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from ...auth.interface.fastapi_auth import get_db
from ...auth.domain.entities.user import User

# Use Supabase authentication for V2 routes
try:
    from ...auth.interface.supabase_fastapi_auth import get_current_user
except ImportError:
    # Fallback to local JWT if Supabase auth not available
    from ...auth.interface.fastapi_auth import get_current_user
from ...task_management.infrastructure.repositories.orm.project_repository import ORMProjectRepository
from ...task_management.application.services.project_application_service import ProjectApplicationService

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/v2/projects", tags=["User-Scoped Projects"])


@router.post("/", response_model=dict)
async def create_project(
    name: str,
    description: str = "",
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Create a new project for the authenticated user.
    
    The project will be automatically associated with the current user,
    ensuring data isolation.
    """
    try:
        # Create user-scoped repository
        project_repo = ORMProjectRepository(session=db, user_id=current_user.id)
        
        # Create service with user context
        service = ProjectApplicationService(project_repo, user_id=current_user.id)
        
        # Generate project ID
        from uuid import uuid4
        project_id = str(uuid4())
        
        # Log the access for audit
        logger.info(f"User {current_user.email} creating project: {name}")
        
        # Create the project - will automatically be scoped to the user
        result = await service.create_project(project_id, name, description)
        
        return {
            "success": True,
            "project": result,
            "message": f"Project created successfully for user {current_user.email}"
        }
        
    except Exception as e:
        logger.error(f"Error creating project for user {current_user.id}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to create project"
        )


@router.get("/", response_model=dict)
async def list_projects(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    List all projects for the authenticated user.
    
    Only returns projects that belong to the current user.
    """
    try:
        # Create user-scoped repository
        project_repo = ORMProjectRepository(session=db, user_id=current_user.id)
        
        # Create service with user context
        service = ProjectApplicationService(project_repo, user_id=current_user.id)
        
        # Log the access for audit
        logger.info(f"User {current_user.email} listing projects")
        
        # List projects - automatically filtered by user
        result = await service.list_projects()
        
        return {
            "success": True,
            "projects": result.get("projects", []),
            "total": len(result.get("projects", [])),
            "message": f"Projects retrieved for user {current_user.email}"
        }
        
    except Exception as e:
        logger.error(f"Error listing projects for user {current_user.id}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to list projects"
        )


@router.get("/{project_id}", response_model=dict)
async def get_project(
    project_id: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Get a specific project by ID.
    
    Only returns the project if it belongs to the current user.
    """
    try:
        # Create user-scoped repository
        project_repo = ORMProjectRepository(session=db, user_id=current_user.id)
        
        # Create service with user context
        service = ProjectApplicationService(project_repo, user_id=current_user.id)
        
        # Log the access for audit
        logger.info(f"User {current_user.email} accessing project: {project_id}")
        
        # Get the project - will return None if not owned by user
        result = await service.get_project(project_id)
        
        if not result or not result.get("success"):
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Project not found or access denied"
            )
        
        return {
            "success": True,
            "project": result.get("project"),
            "message": f"Project retrieved for user {current_user.email}"
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting project {project_id} for user {current_user.id}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to get project"
        )


@router.put("/{project_id}", response_model=dict)
async def update_project(
    project_id: str,
    name: Optional[str] = None,
    description: Optional[str] = None,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Update a project.
    
    Only allows updating projects that belong to the current user.
    """
    try:
        # Create user-scoped repository
        project_repo = ORMProjectRepository(session=db, user_id=current_user.id)
        
        # Create service with user context
        service = ProjectApplicationService(project_repo, user_id=current_user.id)
        
        # Log the access for audit
        logger.info(f"User {current_user.email} updating project: {project_id}")
        
        # Update the project - will fail if not owned by user
        result = await service.update_project(project_id, name, description)
        
        if not result or not result.get("success"):
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Project not found or access denied"
            )
        
        return {
            "success": True,
            "project": result.get("project"),
            "message": f"Project updated successfully for user {current_user.email}"
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error updating project {project_id} for user {current_user.id}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to update project"
        )


@router.delete("/{project_id}", response_model=dict)
async def delete_project(
    project_id: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Delete a project.
    
    Only allows deleting projects that belong to the current user.
    This will also delete all associated git branches, tasks, and contexts.
    """
    try:
        # Create user-scoped repository
        project_repo = ORMProjectRepository(session=db, user_id=current_user.id)
        
        # First verify the project exists and belongs to the user
        project = await project_repo.find_by_id(project_id)
        if not project:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Project not found or access denied"
            )
        
        # Log the access for audit
        logger.info(f"User {current_user.email} deleting project: {project_id}")
        
        # Delete the project
        result = await project_repo.delete(project)
        
        return {
            "success": True,
            "message": f"Project {project_id} deleted successfully for user {current_user.email}"
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error deleting project {project_id} for user {current_user.id}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to delete project"
        )


@router.post("/{project_id}/health-check", response_model=dict)
async def project_health_check(
    project_id: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Perform a health check on a project.
    
    Only works for projects that belong to the current user.
    """
    try:
        # Create user-scoped repository
        project_repo = ORMProjectRepository(session=db, user_id=current_user.id)
        
        # Create service with user context
        service = ProjectApplicationService(project_repo, user_id=current_user.id)
        
        # Log the access for audit
        logger.info(f"User {current_user.email} checking health of project: {project_id}")
        
        # Perform health check
        result = await service.project_health_check(project_id)
        
        if not result or not result.get("success"):
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Project not found or access denied"
            )
        
        return {
            "success": True,
            "health": result,
            "message": f"Health check completed for user {current_user.email}"
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error checking health of project {project_id} for user {current_user.id}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to perform health check"
        )