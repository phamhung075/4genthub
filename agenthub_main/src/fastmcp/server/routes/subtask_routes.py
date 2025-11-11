"""
Subtask Routes - Dedicated subtask management endpoints

This module provides comprehensive subtask management operations
following proper DDD architecture with API controllers.
"""

from __future__ import annotations

import logging
from typing import Any

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from fastmcp.auth.domain.entities.user import User

# Import authentication dependencies
from fastmcp.auth.interface.fastapi_auth import get_current_active_user, get_db

# Import API controller for proper DDD architecture
from fastmcp.task_management.interface.api_controllers.subtask_api_controller import (
    SubtaskAPIController,
)

logger = logging.getLogger(__name__)

# Create router
router = APIRouter(
    prefix="/api/v2/subtasks",
    tags=["User-Scoped Subtasks"],
    dependencies=[Depends(get_current_active_user)],
)

# Initialize API controller
subtask_controller = SubtaskAPIController()


@router.post("")
async def create_subtask(
    task_id: str,
    title: str,
    description: str | None = None,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db),
) -> dict[str, Any]:
    """Create a new subtask"""
    try:
        result = subtask_controller.create_subtask(
            task_id=task_id,
            title=title,
            description=description,
            user_id=current_user.id,
            session=db,
        )

        if not result.success:
            raise HTTPException(
                status_code=400, detail=result.error or "Failed to create subtask"
            )

        return result.model_dump(by_alias=True)

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error creating subtask: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/{subtask_id}")
async def get_subtask(
    subtask_id: str,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db),
) -> dict[str, Any]:
    """Get a specific subtask by ID"""
    try:
        result = subtask_controller.get_subtask(
            subtask_id=subtask_id, user_id=current_user.id, session=db
        )

        if not result.success:
            raise HTTPException(
                status_code=404, detail=result.error or "Subtask not found"
            )

        return result.model_dump(by_alias=True)

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting subtask: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.put("/{subtask_id}")
async def update_subtask(
    subtask_id: str,
    title: str | None = None,
    description: str | None = None,
    status: str | None = None,
    progress_percentage: int | None = None,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db),
) -> dict[str, Any]:
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
            session=db,
        )

        if not result.success:
            raise HTTPException(
                status_code=400, detail=result.error or "Failed to update subtask"
            )

        return result.model_dump(by_alias=True)

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error updating subtask: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.delete("/{subtask_id}")
async def delete_subtask(
    subtask_id: str,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db),
) -> dict[str, Any]:
    """Delete a subtask"""
    try:
        result = subtask_controller.delete_subtask(
            subtask_id=subtask_id, user_id=current_user.id, session=db
        )

        if not result.success:
            raise HTTPException(
                status_code=400, detail=result.error or "Failed to delete subtask"
            )

        return result.model_dump(by_alias=True)

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error deleting subtask: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/task/{task_id}")
async def list_subtasks_for_task(
    task_id: str,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db),
) -> dict[str, Any]:
    """List all subtasks for a specific task"""
    logger.info(f"🔵 [ROUTE] GET /api/v2/subtasks/task/{task_id} - Request received")
    logger.info(
        f"🔵 [ROUTE] User ID: {current_user.id}, User Email: {current_user.email}"
    )

    try:
        logger.info(
            f"🔵 [ROUTE] Calling controller.list_subtasks for task_id={task_id}"
        )
        result = subtask_controller.list_subtasks(
            task_id=task_id, user_id=current_user.id, session=db
        )

        logger.info(
            f"🔵 [ROUTE] Controller returned: success={result.success}, total={result.total}"
        )
        logger.info(
            f"🔵 [ROUTE] Subtasks count: {len(result.subtasks) if result.subtasks else 0}"
        )
        if result.subtasks:
            logger.info(f"🔵 [ROUTE] Subtask IDs: {[st.id for st in result.subtasks]}")

        if not result.success:
            logger.warning(f"🔵 [ROUTE] Controller returned failure: {result.error}")
            raise HTTPException(
                status_code=400, detail=result.error or "Failed to list subtasks"
            )

        # CRITICAL DEBUG: Check data BEFORE and AFTER model_dump
        logger.info(
            f"🐛 [DEBUG] BEFORE model_dump: result.subtasks has {len(result.subtasks)} items"
        )
        logger.info(
            f"🐛 [DEBUG] result.subtasks IDs: {[st.id for st in result.subtasks]}"
        )

        response = result.model_dump(by_alias=True)

        logger.info(
            f"🐛 [DEBUG] AFTER model_dump: response['subtasks'] has {len(response.get('subtasks', []))} items"
        )
        logger.info(
            f"🐛 [DEBUG] response['subtasks'] IDs: {[st.get('id') for st in response.get('subtasks', [])]}"
        )
        logger.info(
            f"🔵 [ROUTE] Returning response with {len(response.get('subtasks', []))} subtasks"
        )
        return response

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"🔴 [ROUTE ERROR] Error listing subtasks for task {task_id}: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/{subtask_id}/complete")
async def complete_subtask(
    subtask_id: str,
    completion_notes: str | None = None,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db),
) -> dict[str, Any]:
    """Mark a subtask as complete"""
    try:
        result = subtask_controller.complete_subtask(
            subtask_id=subtask_id,
            completion_summary=completion_notes,
            user_id=current_user.id,
            session=db,
        )

        if not result.success:
            raise HTTPException(
                status_code=400, detail=result.error or "Failed to complete subtask"
            )

        return result.model_dump(by_alias=True)

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error completing subtask: {e}")
        raise HTTPException(status_code=500, detail=str(e))
