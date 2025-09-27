"""
API Token Management Routes

This module provides FastAPI endpoints for managing API tokens.
All routes delegate to the TokenAPIController following DDD principles.

NO DIRECT DATABASE ACCESS - All operations go through the controller layer.
"""

from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.responses import JSONResponse
from typing import Optional, List, Dict, Any
from sqlalchemy.orm import Session
from pydantic import BaseModel, Field
from datetime import datetime
import logging

logger = logging.getLogger(__name__)

# Import authentication using unified auth (handles all auth methods properly)
from fastmcp.auth.interface.unified_auth import get_current_user

from fastmcp.auth.domain.entities.user import User
# Use proper DDD database session dependency
from fastmcp.auth.interface.fastapi_auth import get_db

# Import the TokenAPIController for DDD compliance
from fastmcp.task_management.interface.api_controllers.token_api_controller import TokenAPIController

# Initialize token controller for DDD compliance
token_controller = TokenAPIController()

# Pydantic models
class TokenCreateRequest(BaseModel):
    name: str = Field(..., description="Token name")
    scopes: List[str] = Field(default=["read"], description="Token scopes")
    expires_in_days: int = Field(default=30, description="Token expiration in days", ge=1, le=365)
    rate_limit: Optional[int] = Field(default=1000, description="Rate limit per hour")
    metadata: Optional[Dict[str, Any]] = Field(default={}, description="Optional metadata")

class TokenResponse(BaseModel):
    id: str
    name: str
    scopes: List[str]
    created_at: Optional[datetime] = None
    expires_at: Optional[datetime] = None
    last_used_at: Optional[datetime] = None
    usage_count: Optional[int] = 0
    rate_limit: Optional[int] = None
    is_active: bool = True
    token: Optional[str] = None  # Only included during creation
    metadata: Optional[Dict[str, Any]] = {}
    
    class Config:
        from_attributes = True
        json_encoders = {
            datetime: lambda v: v.isoformat() if v else None
        }

class TokenListResponse(BaseModel):
    data: List[TokenResponse]
    total: int

# Create router
router = APIRouter(
    prefix="/api/v2/tokens",
    tags=["tokens"],
    responses={404: {"description": "Not found"}},
)

# Standalone handlers for Starlette integration
async def generate_token_handler(request: TokenCreateRequest, current_user: User, db: Session) -> TokenResponse:
    """Standalone handler for generating tokens (for Starlette integration)"""
    # Delegate to controller following DDD pattern
    result = await token_controller.generate_api_token(
        user_id=current_user.id,
        name=request.name,
        scopes=request.scopes,
        expires_in_days=request.expires_in_days,
        rate_limit=request.rate_limit,
        session=db
    )
    
    if result["success"]:
        return TokenResponse(**result["token_data"])
    else:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=result.get("error", "Failed to generate token")
        )

async def list_tokens_handler(current_user: User, db: Session, skip: int = 0, limit: int = 100) -> TokenListResponse:
    """Standalone handler for listing tokens (for Starlette integration)"""
    # Delegate to controller following DDD pattern
    result = await token_controller.list_user_tokens(
        user_id=current_user.id,
        session=db
    )
    
    if result["success"]:
        # Apply pagination to tokens
        tokens = result["tokens"][skip:skip+limit] if skip or limit != 100 else result["tokens"]
        token_responses = [TokenResponse(**token) for token in tokens]
        return TokenListResponse(data=token_responses, total=result["total"])
    else:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=result.get("error", "Failed to list tokens")
        )

# FastAPI route handlers
@router.post("/", response_model=TokenResponse)
async def create_token(
    request: TokenCreateRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Generate a new API token for the authenticated user"""
    # Delegate to handler which uses controller
    return await generate_token_handler(request, current_user, db)

@router.post("/generate", response_model=TokenResponse)
async def generate_token(
    request: TokenCreateRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Generate a new API token for the authenticated user (frontend compatibility endpoint)"""
    # Delegate to handler which uses controller (same as create_token)
    return await generate_token_handler(request, current_user, db)

@router.get("/", response_model=TokenListResponse)
async def list_tokens(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
    skip: int = 0,
    limit: int = 100
):
    """List all API tokens for the authenticated user"""
    
    # Delegate to controller following DDD pattern
    result = await token_controller.list_user_tokens(
        user_id=current_user.id,
        session=db
    )
    
    if result["success"]:
        # Convert to expected response format
        token_responses = [
            TokenResponse(**token) for token in result["tokens"]
        ]
        return TokenListResponse(data=token_responses, total=result["total"])
    else:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=result.get("error", "Failed to list tokens")
        )

@router.get("/{token_id}", response_model=TokenResponse)
async def get_token_details(
    token_id: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Get details of a specific API token"""
    
    # Delegate to controller following DDD pattern
    result = await token_controller.get_token_details(
        token_id=token_id,
        user_id=current_user.id,
        session=db
    )
    
    if result["success"]:
        return TokenResponse(**result["token_data"])
    else:
        if "not found" in result.get("error", "").lower():
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Token not found"
            )
        else:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=result.get("error", "Failed to get token details")
            )

@router.delete("/{token_id}")
async def delete_token(
    token_id: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Delete an API token"""
    
    # Delegate to controller following DDD pattern
    result = await token_controller.delete_token(
        token_id=token_id,
        user_id=current_user.id,
        session=db
    )
    
    if result["success"]:
        return {"message": result.get("message", "Token deleted successfully")}
    else:
        if "not found" in result.get("error", "").lower():
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Token not found"
            )
        else:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=result.get("error", "Failed to delete token")
            )

@router.patch("/{token_id}/revoke")
async def revoke_token(
    token_id: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Revoke an API token (mark as inactive)"""
    
    # Delegate to controller following DDD pattern
    result = await token_controller.revoke_token(
        token_id=token_id,
        user_id=current_user.id,
        session=db
    )
    
    if result["success"]:
        return {"message": result.get("message", "Token revoked successfully")}
    else:
        if "not found" in result.get("error", "").lower():
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Token not found"
            )
        else:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=result.get("error", "Failed to revoke token")
            )

@router.patch("/{token_id}/reactivate")
async def reactivate_token(
    token_id: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Reactivate a revoked API token"""
    
    # Delegate to controller following DDD pattern
    result = await token_controller.reactivate_token(
        token_id=token_id,
        user_id=current_user.id,
        session=db
    )
    
    if result["success"]:
        return {"message": result.get("message", "Token reactivated successfully")}
    else:
        if "not found" in result.get("error", "").lower():
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Token not found"
            )
        else:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=result.get("error", "Failed to reactivate token")
            )

@router.post("/{token_id}/rotate", response_model=TokenResponse)
async def rotate_token(
    token_id: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Rotate an API token (generate new token, revoke old one)"""
    
    # Delegate to controller following DDD pattern
    result = await token_controller.rotate_token(
        token_id=token_id,
        user_id=current_user.id,
        session=db
    )
    
    if result["success"]:
        return TokenResponse(**result["token_data"])
    else:
        if "not found" in result.get("error", "").lower():
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Token not found"
            )
        else:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=result.get("error", "Failed to rotate token")
            )

# Validation endpoints
@router.post("/validate")
async def validate_token_endpoint(
    token: str,
    db: Session = Depends(get_db)
):
    """Validate a token and return its claims"""
    
    # Delegate to controller following DDD pattern
    result = await token_controller.validate_token(
        token=token,
        session=db
    )
    
    if result["success"]:
        return result["claims"]
    else:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=result.get("error", "Invalid token")
        )

@router.post("/cleanup")
async def cleanup_expired_tokens(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Clean up expired tokens for the current user"""
    
    # Delegate to controller following DDD pattern
    result = await token_controller.cleanup_expired_tokens(
        user_id=current_user.id,
        session=db
    )
    
    if result["success"]:
        return {
            "message": result.get("message", "Cleanup completed"),
            "deleted_count": result.get("deleted_count", 0)
        }
    else:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=result.get("error", "Failed to cleanup tokens")
        )

# Legacy compatibility endpoints (deprecated - use above endpoints instead)
@router.get("/legacy/tokens", deprecated=True)
async def legacy_list_tokens(current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    """Legacy endpoint - use /tokens instead"""
    return await list_tokens(current_user, db)

# Health check endpoint
@router.get("/health")
async def token_service_health():
    """Health check for token service"""
    return {"status": "healthy", "service": "token_management", "ddd_compliant": True}