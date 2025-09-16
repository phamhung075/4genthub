"""
User-Scoped Project Routes with Authentication

This module provides user-isolated project management endpoints
using JWT authentication and user-scoped repositories.
"""

import logging
from typing import Optional, Dict, Any
from fastapi import APIRouter, Depends, HTTPException, status, Form
from sqlalchemy.orm import Session

from ...auth.interface.fastapi_auth import get_db
from ...auth.domain.entities.user import User

# Use unified authentication that switches based on AUTH_PROVIDER
from ...auth.interface.fastapi_auth import get_current_user
from ...task_management.interface.api_controllers.project_api_controller import ProjectAPIController
from ...task_management.application.dtos.project.create_project_request import CreateProjectRequest
from ...task_management.application.dtos.project.update_project_request import UpdateProjectRequest

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/v2/projects", tags=["User-Scoped Projects"])

# Initialize the project API controller
project_controller = ProjectAPIController()


@router.post("/", response_model=dict)
async def create_project(
    name: str = Form(...),
    description: str = Form(""),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Create a new project for the authenticated user.
    
    The project will be automatically associated with the current user,
    ensuring data isolation.
    """
    try:
        # Log the access for audit
        logger.info(f"User {current_user.email} creating project: {name}")
        
        # Create request DTO
        request = CreateProjectRequest(name=name, description=description)
        
        # Delegate to API controller
        result = await project_controller.create_project(request, current_user.id, db)
        
        if not result.get("success"):
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=result.get("message", "Failed to create project")
            )
        
        return {
            "success": True,
            "project": result.get("project"),
            "message": f"Project created successfully for user {current_user.email}"
        }
        
    except HTTPException:
        raise
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
        # Log the access for audit
        logger.info(f"User {current_user.email} listing projects")
        
        # Delegate to API controller
        result = await project_controller.list_projects(current_user.id, db)
        
        if not result.get("success"):
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=result.get("message", "Failed to list projects")
            )
        
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
        # Log the access for audit
        logger.info(f"User {current_user.email} accessing project: {project_id}")
        
        # Delegate to API controller
        result = await project_controller.get_project(project_id, current_user.id, db)
        
        if not result.get("success"):
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
    name: Optional[str] = Form(None),
    description: Optional[str] = Form(None),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Update a project.
    
    Only allows updating projects that belong to the current user.
    """
    try:
        # Log the access for audit
        logger.info(f"User {current_user.email} updating project: {project_id}")
        
        # Create request DTO
        update_request = UpdateProjectRequest(name=name, description=description)
        
        # Delegate to API controller
        result = await project_controller.update_project(project_id, update_request, current_user.id, db)
        
        if not result.get("success"):
            if "not found" in result.get("error", "").lower():
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail="Project not found or access denied"
                )
            else:
                raise HTTPException(
                    status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                    detail=result.get("message", "Failed to update project")
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
        # Log the access for audit
        logger.info(f"User {current_user.email} deleting project: {project_id}")
        
        # Delegate to API controller
        result = await project_controller.delete_project(project_id, current_user.id, db)
        
        if not result.get("success"):
            if "not found" in result.get("error", "").lower():
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail="Project not found or access denied"
                )
            else:
                # Return the detailed error message from the error field, not the generic message
                error_detail = result.get("error", result.get("message", "Failed to delete project"))
                raise HTTPException(
                    status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                    detail=error_detail
                )
        
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
        # Log the access for audit
        logger.info(f"User {current_user.email} checking health of project: {project_id}")
        
        # Delegate to API controller
        result = await project_controller.get_project_health(project_id, current_user.id, db)
        
        if not result.get("success"):
            if "not found" in result.get("error", "").lower():
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail="Project not found or access denied"
                )
            else:
                raise HTTPException(
                    status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                    detail=result.get("message", "Failed to check project health")
                )
        
        return {
            "success": True,
            "health": result.get("health"),
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