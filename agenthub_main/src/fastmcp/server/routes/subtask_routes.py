"""
Subtask Routes - Dedicated subtask management endpoints

This module provides comprehensive subtask management operations
following proper DDD architecture with API controllers.
"""

from fastapi import APIRouter, HTTPException, Depends, Query
from fastapi.responses import JSONResponse
from typing import Optional, Dict, Any, List
import logging

# Import authentication dependencies
from fastmcp.auth.interface.fastapi_auth import get_current_active_user, get_db
from fastmcp.auth.domain.entities.user import User
from sqlalchemy.orm import Session

# Import API controller for proper DDD architecture
from fastmcp.task_management.interface.api_controllers.subtask_api_controller import SubtaskAPIController

logger = logging.getLogger(__name__)

# Create router
router = APIRouter(
    prefix="/api/v2/subtasks",
    tags=["User-Scoped Subtasks"],
    dependencies=[Depends(get_current_active_user)]
)

# Initialize API controller
subtask_controller = SubtaskAPIController()


@router.post("")
async def create_subtask(
    task_id: str,
    title: str,
    description: Optional[str] = None,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
) -> Dict[str, Any]:
    """Create a new subtask"""
    try:
        result = subtask_controller.create_subtask(
            task_id=task_id,
            title=title,
            description=description,
            user_id=current_user.id,
            session=db
        )
        
        if not result.get("success"):
            raise HTTPException(
                status_code=400,
                detail=result.get("error", "Failed to create subtask")
            )
        
        return result
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error creating subtask: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/{subtask_id}")
async def get_subtask(
    subtask_id: str,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
) -> Dict[str, Any]:
    """Get a specific subtask by ID"""
    try:
        result = subtask_controller.get_subtask(
            subtask_id=subtask_id,
            user_id=current_user.id,
            session=db
        )
        
        if not result.get("success"):
            raise HTTPException(
                status_code=404,
                detail=result.get("error", "Subtask not found")
            )
        
        return result
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting subtask: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.put("/{subtask_id}")
async def update_subtask(
    subtask_id: str,
    title: Optional[str] = None,
    description: Optional[str] = None,
    status: Optional[str] = None,
    progress_percentage: Optional[int] = None,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
) -> Dict[str, Any]:
    """Update a subtask"""
    try:
        # Prepare update data
        update_data = {}
        if title is not None:
            update_data["title"] = title
        if description is not None:
            update_data["description"] = description
        if status is not None:
            update_data["status"] = status
        if progress_percentage is not None:
            update_data["progress_percentage"] = progress_percentage
        
        result = subtask_controller.update_subtask(
            subtask_id=subtask_id,
            update_data=update_data,
            user_id=current_user.id,
            session=db
        )
        
        if not result.get("success"):
            raise HTTPException(
                status_code=400,
                detail=result.get("error", "Failed to update subtask")
            )
        
        return result
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error updating subtask: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.delete("/{subtask_id}")
async def delete_subtask(
    subtask_id: str,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
) -> Dict[str, Any]:
    """Delete a subtask"""
    try:
        result = subtask_controller.delete_subtask(
            subtask_id=subtask_id,
            user_id=current_user.id,
            session=db
        )
        
        if not result.get("success"):
            raise HTTPException(
                status_code=400,
                detail=result.get("error", "Failed to delete subtask")
            )
        
        return result
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error deleting subtask: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/task/{task_id}")
async def list_subtasks_for_task(
    task_id: str,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
) -> Dict[str, Any]:
    """List all subtasks for a specific task"""
    try:
        result = subtask_controller.list_subtasks(
            task_id=task_id,
            user_id=current_user.id,
            session=db
        )
        
        if not result.get("success"):
            raise HTTPException(
                status_code=400,
                detail=result.get("error", "Failed to list subtasks")
            )
        
        return result
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error listing subtasks for task {task_id}: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/{subtask_id}/complete")
async def complete_subtask(
    subtask_id: str,
    completion_notes: Optional[str] = None,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
) -> Dict[str, Any]:
    """Mark a subtask as complete"""
    try:
        result = subtask_controller.complete_subtask(
            subtask_id=subtask_id,
            completion_summary=completion_notes,
            user_id=current_user.id,
            session=db
        )
        
        if not result.get("success"):
            raise HTTPException(
                status_code=400,
                detail=result.get("error", "Failed to complete subtask")
            )
        
        return result
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error completing subtask: {e}")
        raise HTTPException(status_code=500, detail=str(e))