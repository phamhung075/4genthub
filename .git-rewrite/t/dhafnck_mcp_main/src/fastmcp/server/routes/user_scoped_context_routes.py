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
    from ...auth.interface.supabase_fastapi_auth import get_current_user
except ImportError:
    # Fallback to local JWT if Supabase auth not available
    from ...auth.interface.fastapi_auth import get_current_user
from ...auth.domain.entities.user import User
from ...task_management.application.factories.unified_context_facade_factory import UnifiedContextFacadeFactory

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/v2/contexts", tags=["User-Scoped Contexts"])


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


def get_context_facade(
    user_id: str,
    project_id: Optional[str] = None,
    git_branch_id: Optional[str] = None
):
    """Get a user-scoped context facade"""
    factory = UnifiedContextFacadeFactory.get_instance()
    return factory.create_facade(
        user_id=user_id,
        project_id=project_id,
        git_branch_id=git_branch_id
    )


@router.post("/{level}", response_model=dict)
async def create_context(
    level: str,
    request: ContextCreateRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Create a new context at the specified level for the authenticated user.
    
    The context will be automatically associated with the current user,
    ensuring data isolation.
    """
    try:
        # Override level from URL parameter
        request.level = level
        
        # Get user-scoped facade
        facade = get_context_facade(
            user_id=current_user.id,
            project_id=request.project_id,
            git_branch_id=request.git_branch_id
        )
        
        # Log the access for audit
        logger.info(f"User {current_user.email} creating {level} context: {request.context_id}")
        
        # Create the context - will automatically be scoped to the user
        result = facade.create_context(
            level=request.level,
            context_id=request.context_id,
            data=request.data or {}
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
    
    Returns 404 if the context doesn't exist or doesn't belong to the user.
    """
    try:
        # Get user-scoped facade
        facade = get_context_facade(user_id=current_user.id)
        
        # Get the context - will automatically check user ownership
        result = facade.get_context(
            level=level,
            context_id=context_id,
            include_inherited=include_inherited,
            force_refresh=force_refresh
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
    
    Only allows updating contexts that belong to the current user.
    """
    try:
        # Get user-scoped facade
        facade = get_context_facade(user_id=current_user.id)
        
        # First check if context exists and belongs to user
        existing_result = facade.get_context(level=level, context_id=context_id)
        if not existing_result.get("success"):
            logger.warning(f"User {current_user.email} attempted to update non-existent or unauthorized {level} context {context_id}")
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Context not found"
            )
        
        # Update the context
        result = facade.update_context(
            level=level,
            context_id=context_id,
            data=request.data,
            propagate_changes=request.propagate_changes
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
    
    Only allows deleting contexts that belong to the current user.
    """
    try:
        # Get user-scoped facade
        facade = get_context_facade(user_id=current_user.id)
        
        # First check if context exists and belongs to user
        existing_result = facade.get_context(level=level, context_id=context_id)
        if not existing_result.get("success"):
            logger.warning(f"User {current_user.email} attempted to delete non-existent or unauthorized {level} context {context_id}")
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Context not found"
            )
        
        # Delete the context
        result = facade.delete_context(level=level, context_id=context_id)
        
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
        facade = get_context_facade(user_id=current_user.id)
        
        # Resolve the context - will automatically check user ownership
        result = facade.resolve_context(
            level=level,
            context_id=context_id,
            force_refresh=force_refresh
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
        facade = get_context_facade(user_id=current_user.id)
        
        # First check if context exists and belongs to user
        existing_result = facade.get_context(level=level, context_id=context_id)
        if not existing_result.get("success"):
            logger.warning(f"User {current_user.email} attempted to delegate from non-existent or unauthorized {level} context {context_id}")
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Context not found"
            )
        
        # Delegate the context
        result = facade.delegate_context(
            level=level,
            context_id=context_id,
            delegate_to=request.delegate_to,
            data=request.delegate_data,
            delegation_reason=request.delegation_reason
        )
        
        if result.get("success"):
            logger.info(f"User {current_user.email} delegated {level} context {context_id} to {request.delegate_to}")
            return {
                "success": True,
                "delegation_result": result.get("delegation_result"),
                "message": "Context delegated successfully"
            }
        else:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=result.get("error", "Failed to delegate context")
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
        facade = get_context_facade(user_id=current_user.id)
        
        # First check if context exists and belongs to user
        existing_result = facade.get_context(level=level, context_id=context_id)
        if not existing_result.get("success"):
            logger.warning(f"User {current_user.email} attempted to add insight to non-existent or unauthorized {level} context {context_id}")
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Context not found"
            )
        
        # Add the insight
        result = facade.add_insight(
            level=level,
            context_id=context_id,
            content=request.content,
            category=request.category,
            importance=request.importance,
            agent=request.agent
        )
        
        if result.get("success"):
            logger.info(f"User {current_user.email} added insight to {level} context {context_id}")
            return {
                "success": True,
                "context": result.get("context"),
                "message": "Insight added successfully"
            }
        else:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=result.get("error", "Failed to add insight")
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
        facade = get_context_facade(user_id=current_user.id)
        
        # First check if context exists and belongs to user
        existing_result = facade.get_context(level=level, context_id=context_id)
        if not existing_result.get("success"):
            logger.warning(f"User {current_user.email} attempted to add progress to non-existent or unauthorized {level} context {context_id}")
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Context not found"
            )
        
        # Add the progress
        result = facade.add_progress(
            level=level,
            context_id=context_id,
            content=request.content,
            agent=request.agent
        )
        
        if result.get("success"):
            logger.info(f"User {current_user.email} added progress to {level} context {context_id}")
            return {
                "success": True,
                "context": result.get("context"),
                "message": "Progress added successfully"
            }
        else:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=result.get("error", "Failed to add progress")
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
        
        # Get user-scoped facade
        facade = get_context_facade(user_id=current_user.id)
        
        # List user's contexts only
        result = facade.list_contexts(level=level, filters=parsed_filters)
        
        if result.get("success"):
            contexts = result.get("contexts", [])
            logger.info(f"User {current_user.email} listed {len(contexts)} {level} contexts")
            return {
                "success": True,
                "contexts": contexts,
                "count": len(contexts),
                "level": level,
                "user": current_user.email
            }
        else:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=result.get("error", "Failed to list contexts")
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
        # Get user-scoped facade
        facade = get_context_facade(user_id=current_user.id)
        
        # Get context summary - will automatically check user ownership
        result = facade.get_context_summary(context_id=context_id)
        
        if result.get("success"):
            logger.info(f"User {current_user.email} accessed {level} context summary {context_id}")
            return {
                "success": True,
                "summary": {
                    "has_context": result.get("has_context", False),
                    "context_size": result.get("context_size", 0),
                    "last_updated": result.get("last_updated")
                }
            }
        else:
            # Context summary returns success: False for non-existent contexts
            return {
                "success": True,
                "summary": {
                    "has_context": False,
                    "context_size": 0,
                    "last_updated": None
                }
            }
        
    except Exception as e:
        logger.error(f"Error getting {level} context summary {context_id} for user {current_user.id}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to get context summary"
        )


# Register the router in your main app
# app.include_router(router)