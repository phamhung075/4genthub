"""
User-Scoped Context Routes with Authentication

This module provides v2 API endpoints for context management with proper user isolation
using JWT authentication and user-scoped context facades.
"""

import logging
import json
from typing import Dict, Any, Optional
from fastapi import APIRouter, Depends, HTTPException, status, Request
from pydantic import BaseModel
from sqlalchemy.orm import Session

from ...auth.interface.fastapi_auth import get_db
# Use Supabase authentication for V2 routes
try:
    from ...auth.interface.fastapi_auth import get_current_user
except ImportError:
    # Fallback to local JWT if Supabase auth not available
    from ...auth.interface.fastapi_auth import get_current_user
from ...auth.domain.entities.user import User
from ...task_management.interface.api_controllers.context_api_controller import ContextAPIController

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/v2/contexts", tags=["User-Scoped Contexts"])

# Initialize the context API controller
context_controller = ContextAPIController()


class ContextCreateRequest(BaseModel):
    """Request model for creating contexts"""
    level: str
    context_id: str
    data: Optional[Dict[str, Any]] = None
    project_id: Optional[str] = None
    git_branch_id: Optional[str] = None


class ContextUpdateRequest(BaseModel):
    """Request model for updating contexts"""
    data: Dict[str, Any]
    propagate_changes: bool = True


class ContextDelegateRequest(BaseModel):
    """Request model for delegating contexts"""
    delegate_to: str
    delegate_data: Dict[str, Any]
    delegation_reason: Optional[str] = None


class ContextInsightRequest(BaseModel):
    """Request model for adding insights"""
    content: str
    category: Optional[str] = None
    importance: Optional[str] = None
    agent: Optional[str] = None


class ContextProgressRequest(BaseModel):
    """Request model for adding progress"""
    content: str
    agent: Optional[str] = None


# Context helper functions removed - now using ContextAPIController


@router.post("/{level}", response_model=dict)
async def create_context(
    level: str,
    request: ContextCreateRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Create a new context at the specified level for the authenticated user.
    
    For global context, if context_id is 'me' or not provided, it will use the current user's ID.
    The context will be automatically associated with the current user,
    ensuring data isolation.
    """
    try:
        # Override level from URL parameter
        request.level = level
        
        # For global context, if context_id is 'me' or not provided, use the current user's ID
        if level == 'global' and (request.context_id == 'me' or not request.context_id):
            request.context_id = str(current_user.id)
        
        # Log the access for audit
        logger.info(f"User {current_user.email} creating {level} context: {request.context_id}")
        
        # Delegate to API controller
        result = context_controller.create_context(
            level=request.level,
            context_id=request.context_id,
            data=request.data or {},
            user_id=current_user.id,
            session=db
        )
        
        if result.get("success"):
            return {
                "success": True,
                "context": result.get("context"),
                "message": f"Context created successfully for user {current_user.email}"
            }
        else:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=result.get("error", "Failed to create context")
            )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error creating {level} context for user {current_user.id}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to create context"
        )


@router.get("/{level}/{context_id}", response_model=dict)
async def get_context(
    level: str,
    context_id: str,
    include_inherited: bool = False,
    force_refresh: bool = False,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Get a specific context for the authenticated user.
    
    For global context, context_id is ignored and the current user's ID is used automatically.
    Returns 404 if the context doesn't exist or doesn't belong to the user.
    """
    try:
        # For global context, always use the current user's ID (ignore provided context_id)
        if level == 'global':
            context_id = str(current_user.id)
        
        # Get user-scoped facade
        # Delegate to API controller
        
        # Get the context - will automatically check user ownership
        result = context_controller.get_context(
            level=level,
            context_id=context_id,
            include_inherited=include_inherited,
            user_id=current_user.id,
            session=db
        )
        
        if result.get("success"):
            logger.info(f"User {current_user.email} accessed {level} context {context_id}")
            return {
                "success": True,
                "context": result.get("context")
            }
        else:
            logger.warning(f"User {current_user.email} attempted to access non-existent or unauthorized {level} context {context_id}")
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Context not found"
            )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting {level} context {context_id} for user {current_user.id}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to get context"
        )


@router.put("/{level}/{context_id}", response_model=dict)
async def update_context(
    level: str,
    context_id: str,
    request: ContextUpdateRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Update a context for the authenticated user.
    
    For global context, context_id is ignored and the current user's ID is used automatically.
    Only allows updating contexts that belong to the current user.
    """
    try:
        # For global context, always use the current user's ID (ignore provided context_id)
        if level == 'global':
            context_id = str(current_user.id)
        
        # Get user-scoped facade
        # Delegate to API controller
        
        # First check if context exists and belongs to user
        existing_result = context_controller.get_context(
            level=level,
            context_id=context_id,
            user_id=current_user.id,
            session=db
        )
        if not existing_result.get("success"):
            logger.warning(f"User {current_user.email} attempted to update non-existent or unauthorized {level} context {context_id}")
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Context not found"
            )
        
        # Update the context
        result = context_controller.update_context(
            level=level,
            context_id=context_id,
            data=request.data,
            user_id=current_user.id,
            session=db
        )
        
        if result.get("success"):
            logger.info(f"User {current_user.email} updated {level} context {context_id}")
            return {
                "success": True,
                "context": result.get("context"),
                "message": "Context updated successfully"
            }
        else:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=result.get("error", "Failed to update context")
            )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error updating {level} context {context_id} for user {current_user.id}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to update context"
        )


@router.delete("/{level}/{context_id}", response_model=dict)
async def delete_context(
    level: str,
    context_id: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Delete a context for the authenticated user.
    
    For global context, context_id is ignored and the current user's ID is used automatically.
    Only allows deleting contexts that belong to the current user.
    """
    try:
        # For global context, always use the current user's ID (ignore provided context_id)
        if level == 'global':
            context_id = str(current_user.id)
        
        # Get user-scoped facade
        # Delegate to API controller
        
        # First check if context exists and belongs to user
        existing_result = context_controller.get_context(
            level=level,
            context_id=context_id,
            user_id=current_user.id,
            session=db
        )
        if not existing_result.get("success"):
            logger.warning(f"User {current_user.email} attempted to delete non-existent or unauthorized {level} context {context_id}")
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Context not found"
            )
        
        # Delete the context
        result = context_controller.delete_context(
            level=level,
            context_id=context_id,
            user_id=current_user.id,
            session=db
        )
        
        if result.get("success"):
            logger.info(f"User {current_user.email} deleted {level} context {context_id}")
            return {
                "success": True,
                "message": "Context deleted successfully"
            }
        else:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=result.get("error", "Failed to delete context")
            )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error deleting {level} context {context_id} for user {current_user.id}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to delete context"
        )


@router.get("/{level}/{context_id}/resolve", response_model=dict)
async def resolve_context(
    level: str,
    context_id: str,
    force_refresh: bool = False,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Resolve context with full inheritance chain for the authenticated user.
    
    Returns the context with all inherited data from parent levels.
    """
    try:
        # Get user-scoped facade
        # Delegate to API controller
        
        # Resolve the context - will automatically check user ownership
        result = context_controller.resolve_context(
            level=level,
            context_id=context_id,
            force_refresh=force_refresh,
            user_id=current_user.id,
            session=db
        )
        
        if result.get("success"):
            logger.info(f"User {current_user.email} resolved {level} context {context_id}")
            return {
                "success": True,
                "resolved_context": result.get("resolved_context"),
                "inheritance_chain": result.get("inheritance_chain")
            }
        else:
            logger.warning(f"User {current_user.email} attempted to resolve non-existent or unauthorized {level} context {context_id}")
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Context not found"
            )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error resolving {level} context {context_id} for user {current_user.id}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to resolve context"
        )


@router.post("/{level}/{context_id}/delegate", response_model=dict)
async def delegate_context(
    level: str,
    context_id: str,
    request: ContextDelegateRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Delegate context data to a higher level for the authenticated user.
    
    Only allows delegating from contexts that belong to the current user.
    """
    try:
        # Get user-scoped facade
        # Delegate to API controller
        
        # First check if context exists and belongs to user
        existing_result = context_controller.get_context(
            level=level,
            context_id=context_id,
            user_id=current_user.id,
            session=db
        )
        if not existing_result.get("success"):
            logger.warning(f"User {current_user.email} attempted to delegate from non-existent or unauthorized {level} context {context_id}")
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Context not found"
            )
        
        # Delegation feature not implemented in basic API controller
        # TODO: Implement delegation in ContextAPIController
        raise HTTPException(
            status_code=status.HTTP_501_NOT_IMPLEMENTED,
            detail="Context delegation feature not implemented in API controller"
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error delegating {level} context {context_id} for user {current_user.id}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to delegate context"
        )


@router.post("/{level}/{context_id}/insights", response_model=dict)
async def add_insight(
    level: str,
    context_id: str,
    request: ContextInsightRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Add an insight to context for the authenticated user.
    
    Only allows adding insights to contexts that belong to the current user.
    """
    try:
        # Get user-scoped facade
        # Delegate to API controller
        
        # First check if context exists and belongs to user
        existing_result = context_controller.get_context(
            level=level,
            context_id=context_id,
            user_id=current_user.id,
            session=db
        )
        if not existing_result.get("success"):
            logger.warning(f"User {current_user.email} attempted to add insight to non-existent or unauthorized {level} context {context_id}")
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Context not found"
            )
        
        # Insights feature not implemented in basic API controller
        # TODO: Implement insights in ContextAPIController
        raise HTTPException(
            status_code=status.HTTP_501_NOT_IMPLEMENTED,
            detail="Context insights feature not implemented in API controller"
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error adding insight to {level} context {context_id} for user {current_user.id}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to add insight"
        )


@router.post("/{level}/{context_id}/progress", response_model=dict)
async def add_progress(
    level: str,
    context_id: str,
    request: ContextProgressRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Add progress update to context for the authenticated user.
    
    Only allows adding progress to contexts that belong to the current user.
    """
    try:
        # Get user-scoped facade
        # Delegate to API controller
        
        # First check if context exists and belongs to user
        existing_result = context_controller.get_context(
            level=level,
            context_id=context_id,
            user_id=current_user.id,
            session=db
        )
        if not existing_result.get("success"):
            logger.warning(f"User {current_user.email} attempted to add progress to non-existent or unauthorized {level} context {context_id}")
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Context not found"
            )
        
        # Progress feature not implemented in basic API controller
        # TODO: Implement progress tracking in ContextAPIController
        raise HTTPException(
            status_code=status.HTTP_501_NOT_IMPLEMENTED,
            detail="Context progress feature not implemented in API controller"
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error adding progress to {level} context {context_id} for user {current_user.id}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to add progress"
        )


@router.get("/{level}/list", response_model=dict)
async def list_contexts(
    level: str,
    filters: Optional[str] = None,  # JSON string of filters
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    List all contexts at the specified level for the authenticated user.
    
    Only returns contexts that belong to the current user.
    """
    try:
        # Parse filters if provided
        parsed_filters = {}
        if filters:
            try:
                parsed_filters = json.loads(filters)
            except json.JSONDecodeError as e:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=f"Invalid filters JSON: {e}"
                )
        
        # List contexts feature not implemented in basic API controller
        # TODO: Implement list_contexts in ContextAPIController
        raise HTTPException(
            status_code=status.HTTP_501_NOT_IMPLEMENTED,
            detail="List contexts feature not implemented in API controller"
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error listing {level} contexts for user {current_user.id}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to list contexts"
        )


@router.get("/{level}/{context_id}/summary", response_model=dict)
async def get_context_summary(
    level: str,
    context_id: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Get lightweight context summary for the authenticated user.
    
    Used for performance optimization in lazy loading.
    """
    try:
        # Context summary feature not implemented in basic API controller
        # TODO: Implement get_context_summary in ContextAPIController
        raise HTTPException(
            status_code=status.HTTP_501_NOT_IMPLEMENTED,
            detail="Context summary feature not implemented in API controller"
        )
        
    except Exception as e:
        logger.error(f"Error getting {level} context summary {context_id} for user {current_user.id}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to get context summary"
        )


# Register the router in your main app
# app.include_router(router)