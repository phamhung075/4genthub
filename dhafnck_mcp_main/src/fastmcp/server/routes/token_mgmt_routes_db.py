"""
Token Management API Routes with PostgreSQL Storage

Provides endpoints for creating, listing, and managing API tokens
for MCP authentication. Stores tokens in PostgreSQL database.

Following DDD patterns - routes delegate to controllers, no direct DB access.
"""

from fastapi import APIRouter, Depends, HTTPException, Request
from fastapi.responses import JSONResponse
from typing import List, Dict, Any, Optional
from datetime import datetime, timedelta
import uuid
import secrets
import jwt
import logging
from pydantic import BaseModel
import os
import hashlib
from sqlalchemy.orm import Session

logger = logging.getLogger(__name__)

# Use unified authentication that handles all auth methods
from fastmcp.auth.interface.unified_auth import get_current_user

from fastmcp.auth.domain.entities.user import User

# Import the TokenAPIController for DDD compliance
from fastmcp.task_management.interface.api_controllers.token_api_controller import TokenAPIController

# Import database session dependency - following DDD pattern
from fastmcp.auth.interface.fastapi_auth import get_db

# Get JWT secret from environment - MUST be set for production
JWT_SECRET_KEY = os.getenv("JWT_SECRET_KEY")
if not JWT_SECRET_KEY:
    logger.error("CRITICAL SECURITY WARNING: JWT_SECRET_KEY not set in environment!")
    logger.error("Token generation will not work without JWT_SECRET_KEY!")
    logger.error("Generate a secure secret with: python generate_secure_secrets.py")
    # Will cause token generation to fail
    JWT_SECRET_KEY = None
JWT_ALGORITHM = os.getenv("JWT_ALGORITHM", "HS256")

# Initialize token controller for DDD compliance
token_controller = TokenAPIController()

# Note: Database session is now obtained through DDD-compliant get_db dependency
# No direct database engine or session creation in routes layer

class TokenCreateRequest(BaseModel):
    name: str
    scopes: List[str] = ["read"]
    expires_in_days: int = 30
    rate_limit: Optional[int] = 100
    
class TokenResponse(BaseModel):
    id: str
    name: str
    scopes: List[str]
    created_at: datetime
    expires_at: Optional[datetime] = None
    last_used_at: Optional[datetime] = None
    usage_count: int = 0  # Added to match ORM and frontend
    rate_limit: Optional[int] = None
    is_active: bool
    token: Optional[str] = None  # Only returned when creating
    
    class Config:
        from_attributes = True
        json_encoders = {
            datetime: lambda v: v.isoformat() if v else None
        }

class TokenListResponse(BaseModel):
    data: List[TokenResponse]  # Changed from 'tokens' to 'data' to match frontend
    total: int

# Create router
router = APIRouter(
    prefix="/api/auth/tokens",
    tags=["auth", "tokens"],
    dependencies=[Depends(get_current_user)]
)

def hash_token(token: str) -> str:
    """Hash a token for secure storage"""
    return hashlib.sha256(token.encode()).hexdigest()

@router.post("/generate", response_model=TokenResponse)
async def generate_token(
    request: TokenCreateRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Generate a new API token for the authenticated user.
    Uses controller for DDD compliance.
    """
    try:
        # Delegate to controller
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
            raise HTTPException(status_code=500, detail=result.get("error", "Failed to generate token"))
            
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error generating token: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/", response_model=TokenListResponse)
async def list_tokens(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    List all tokens for the current user.
    Uses controller for DDD compliance.
    """
    try:
        # Delegate to controller
        result = await token_controller.list_user_tokens(
            user_id=current_user.id,
            session=db
        )
        
        if result["success"]:
            return TokenListResponse(
                data=result["tokens"],  # Changed from 'tokens' to 'data' to match frontend
                total=result["total"]
            )
        else:
            raise HTTPException(status_code=500, detail=result.get("error", "Failed to list tokens"))
            
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error listing tokens: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/{token_id}", response_model=TokenResponse)
async def get_token(
    token_id: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Get details of a specific token.
    Uses controller for DDD compliance.
    """
    try:
        # Delegate to controller
        result = await token_controller.get_token_details(
            token_id=token_id,
            user_id=current_user.id,
            session=db
        )
        
        if result["success"]:
            return TokenResponse(**result["token_data"])
        else:
            if "not found" in result.get("error", "").lower():
                raise HTTPException(status_code=404, detail="Token not found")
            else:
                raise HTTPException(status_code=500, detail=result.get("error", "Failed to get token"))
                
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting token {token_id}: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.delete("/{token_id}")
async def delete_token(
    token_id: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Delete a specific token.
    Uses controller for DDD compliance.
    """
    try:
        # Delegate to controller
        result = await token_controller.delete_token(
            token_id=token_id,
            user_id=current_user.id,
            session=db
        )
        
        if result["success"]:
            return {"message": result.get("message", "Token deleted successfully")}
        else:
            if "not found" in result.get("error", "").lower():
                raise HTTPException(status_code=404, detail="Token not found")
            else:
                raise HTTPException(status_code=500, detail=result.get("error", "Failed to delete token"))
                
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error deleting token {token_id}: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/{token_id}/revoke")
async def revoke_token(
    token_id: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Revoke a token (mark as inactive).
    Uses controller for DDD compliance.
    """
    try:
        # Delegate to controller
        result = await token_controller.revoke_token(
            token_id=token_id,
            user_id=current_user.id,
            session=db
        )
        
        if result["success"]:
            return {"message": result.get("message", "Token revoked successfully")}
        else:
            if "not found" in result.get("error", "").lower():
                raise HTTPException(status_code=404, detail="Token not found")
            else:
                raise HTTPException(status_code=500, detail=result.get("error", "Failed to revoke token"))
                
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error revoking token {token_id}: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/{token_id}/reactivate")
async def reactivate_token(
    token_id: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Reactivate a revoked token.
    Uses controller for DDD compliance.
    """
    try:
        # Delegate to controller
        result = await token_controller.reactivate_token(
            token_id=token_id,
            user_id=current_user.id,
            session=db
        )
        
        if result["success"]:
            return {"message": result.get("message", "Token reactivated successfully")}
        else:
            if "not found" in result.get("error", "").lower():
                raise HTTPException(status_code=404, detail="Token not found")
            else:
                raise HTTPException(status_code=500, detail=result.get("error", "Failed to reactivate token"))
                
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error reactivating token {token_id}: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/{token_id}/rotate", response_model=TokenResponse)
async def rotate_token(
    token_id: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Rotate a token (generate new token, revoke old one).
    Uses controller for DDD compliance.
    """
    try:
        # Delegate to controller
        result = await token_controller.rotate_token(
            token_id=token_id,
            user_id=current_user.id,
            session=db
        )
        
        if result["success"]:
            return TokenResponse(**result["token_data"])
        else:
            if "not found" in result.get("error", "").lower():
                raise HTTPException(status_code=404, detail="Token not found")
            else:
                raise HTTPException(status_code=500, detail=result.get("error", "Failed to rotate token"))
                
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error rotating token {token_id}: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# Utility endpoints
@router.get("/validate/{token}", response_model=Dict[str, Any])
async def validate_token(
    token: str,
    db: Session = Depends(get_db)
):
    """
    Validate a token and return its claims.
    Uses controller for DDD compliance.
    """
    try:
        # Delegate to controller
        result = await token_controller.validate_token(
            token=token,
            session=db
        )
        
        if result["success"]:
            return result["claims"]
        else:
            raise HTTPException(status_code=401, detail=result.get("error", "Invalid token"))
            
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error validating token: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/cleanup")
async def cleanup_expired_tokens(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Clean up expired tokens for the current user.
    Uses controller for DDD compliance.
    """
    try:
        # Delegate to controller
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
            raise HTTPException(status_code=500, detail=result.get("error", "Failed to cleanup tokens"))
            
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error cleaning up tokens: {e}")
        raise HTTPException(status_code=500, detail=str(e))