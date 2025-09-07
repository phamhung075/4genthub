"""
Token Management API Routes

Provides endpoints for creating, listing, and managing API tokens
for MCP authentication.
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
import json
from sqlalchemy.orm import Session

logger = logging.getLogger(__name__)

# Import unified auth that handles all authentication methods properly
from fastmcp.auth.interface.unified_auth import get_current_user
from fastmcp.auth.domain.entities.user import User

# Import database session dependency
from fastmcp.auth.interface.fastapi_auth import get_db

# Import the TokenAPIController for DDD compliance
from fastmcp.task_management.interface.api_controllers.token_api_controller import TokenAPIController

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


class GenerateTokenRequest(BaseModel):
    name: str
    scopes: List[str]
    expires_in_days: int = 30
    rate_limit: Optional[int] = 1000


class UpdateTokenScopesRequest(BaseModel):
    scopes: List[str]


class TokenResponse(BaseModel):
    id: str
    name: str
    token: Optional[str] = None  # Only included when generating
    scopes: List[str]
    created_at: str
    expires_at: str
    last_used_at: Optional[str] = None
    usage_count: int = 0
    rate_limit: Optional[int] = None
    is_active: bool = True
    user_id: str


# Only create router if JWT_SECRET_KEY is configured
if JWT_SECRET_KEY:
    router = APIRouter(prefix="/api/v2/tokens", tags=["tokens"])
else:
    # Create empty router that will have no routes
    router = APIRouter(prefix="/api/v2/tokens", tags=["tokens"])
    logger.warning("Token management routes not available - JWT_SECRET_KEY not configured")


# JWT generation and hashing now delegated to TokenAPIController
# following DDD principles - no business logic in routes


@router.post("", response_model=TokenResponse)
async def generate_token(
    request: GenerateTokenRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
) -> TokenResponse:
    """Generate a new API token for the authenticated user."""
    try:
        # Delegate to controller following DDD pattern
        result = await token_controller.generate_api_token(
            user_id=current_user.id,
            name=request.name,
            scopes=request.scopes,
            expires_in_days=request.expires_in_days,
            rate_limit=request.rate_limit,
            session=db
        )
        
        if not result["success"]:
            raise HTTPException(status_code=500, detail=result.get("error", "Failed to generate token"))
        
        token_data = result["token_data"]
        logger.info(f"Generated token {token_data['id']} for user {current_user.id} with scopes {request.scopes}")
        
        # Return response with actual token (only time we return it)
        return TokenResponse(
            id=token_data["id"],
            name=token_data["name"],
            token=token_data["token"],  # Include actual token in response
            scopes=token_data["scopes"],
            created_at=token_data["created_at"],
            expires_at=token_data["expires_at"],
            last_used_at=None,
            usage_count=0,
            rate_limit=token_data["rate_limit"],
            is_active=token_data["is_active"],
            user_id=current_user.id
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error generating token: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("")
async def list_tokens(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
    skip: int = 0,
    limit: int = 100
) -> Dict[str, Any]:
    """List all tokens for the authenticated user."""
    try:
        # Delegate to controller following DDD pattern
        result = token_controller.list_user_tokens(
            user_id=current_user.id,
            session=db,
            skip=skip,
            limit=limit
        )
        
        if not result["success"]:
            raise HTTPException(status_code=500, detail=result.get("error", "Failed to list tokens"))
        
        logger.info(f"Listed {len(result['tokens'])} tokens for user {current_user.id}")
        
        return {
            "data": result["tokens"],
            "total": result["total"]
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error listing tokens: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.delete("/{token_id}")
async def revoke_token(
    token_id: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
) -> Dict[str, str]:
    """Revoke a specific token."""
    try:
        # Delegate to controller following DDD pattern
        result = token_controller.revoke_token(
            token_id=token_id,
            user_id=current_user.id,
            session=db
        )
        
        if not result["success"]:
            if result.get("error") == "Token not found":
                raise HTTPException(status_code=404, detail="Token not found")
            raise HTTPException(status_code=500, detail=result.get("error", "Failed to revoke token"))
        
        logger.info(f"Revoked token {token_id} for user {current_user.id}")
        
        return {"message": result.get("message", "Token revoked successfully")}
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error revoking token: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/{token_id}")
async def get_token_details(
    token_id: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
) -> TokenResponse:
    """Get details of a specific token."""
    try:
        # Delegate to controller following DDD pattern
        result = token_controller.get_token_details(
            token_id=token_id,
            user_id=current_user.id,
            session=db
        )
        
        if not result["success"]:
            if result.get("error") == "Token not found":
                raise HTTPException(status_code=404, detail="Token not found")
            raise HTTPException(status_code=500, detail=result.get("error", "Failed to get token details"))
        
        token_data = result["token"]
        
        # Prepare response (without token hash)
        return TokenResponse(
            id=token_data["id"],
            name=token_data["name"],
            token=None,  # Never return the actual token
            scopes=token_data["scopes"],
            created_at=token_data["created_at"],
            expires_at=token_data["expires_at"],
            last_used_at=token_data.get("last_used_at"),
            usage_count=token_data.get("usage_count", 0),
            rate_limit=token_data.get("rate_limit"),
            is_active=token_data.get("is_active", True),
            user_id=current_user.id
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting token details: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.patch("/{token_id}/scopes")
async def update_token_scopes(
    token_id: str,
    request: UpdateTokenScopesRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
) -> TokenResponse:
    """Update the scopes of a specific token."""
    try:
        # This functionality should be added to TokenAPIController
        # For now, return not implemented following DDD principles
        raise HTTPException(
            status_code=501,
            detail="Token scope update not yet implemented in controller layer"
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error updating token scopes: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/{token_id}/rotate")
async def rotate_token(
    token_id: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
) -> TokenResponse:
    """Rotate a token (revoke old, generate new with same settings)."""
    try:
        # Delegate to controller following DDD pattern
        result = await token_controller.rotate_token(
            token_id=token_id,
            user_id=current_user.id,
            session=db
        )
        
        if not result["success"]:
            if result.get("error") == "Token not found":
                raise HTTPException(status_code=404, detail="Token not found")
            raise HTTPException(status_code=500, detail=result.get("error", "Failed to rotate token"))
        
        token_data = result["token_data"]
        logger.info(f"Rotated token {token_id} to {token_data['id']} for user {current_user.id}")
        
        # Return new token
        return TokenResponse(
            id=token_data["id"],
            name=token_data["name"],
            token=token_data["token"],  # Include actual token in response
            scopes=token_data["scopes"],
            created_at=token_data["created_at"],
            expires_at=token_data["expires_at"],
            last_used_at=None,
            usage_count=0,
            rate_limit=token_data.get("rate_limit"),
            is_active=True,
            user_id=current_user.id
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error rotating token: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/validate")
async def validate_token(
    request: Request,
    db: Session = Depends(get_db)
) -> Dict[str, Any]:
    """Validate a token provided in the Authorization header."""
    try:
        # Get token from Authorization header
        auth_header = request.headers.get("Authorization", "")
        if not auth_header.startswith("Bearer "):
            raise HTTPException(status_code=401, detail="Invalid authorization header")
        
        token = auth_header.replace("Bearer ", "")
        
        # Delegate to controller following DDD pattern
        result = await token_controller.validate_token(
            token=token,
            session=db
        )
        
        if result["success"]:
            claims = result["claims"]
            return {
                "valid": True,
                "user_id": claims.get("user_id"),
                "scopes": claims.get("scopes", []),
                "token_id": claims.get("token_id")
            }
        else:
            return {"valid": False, "error": result.get("error", "Invalid token")}
        
    except Exception as e:
        logger.error(f"Error validating token: {e}")
        return {"valid": False, "error": str(e)}


@router.get("/{token_id}/usage")
async def get_token_usage_stats(
    token_id: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
) -> Dict[str, Any]:
    """Get usage statistics for a specific token."""
    try:
        # Delegate to controller to get token details
        result = token_controller.get_token_details(
            token_id=token_id,
            user_id=current_user.id,
            session=db
        )
        
        if not result["success"]:
            if result.get("error") == "Token not found":
                raise HTTPException(status_code=404, detail="Token not found")
            raise HTTPException(status_code=500, detail=result.get("error", "Failed to get token stats"))
        
        token_data = result["token"]
        
        # Calculate stats from the retrieved token data
        created_at = datetime.fromisoformat(token_data["created_at"])
        expires_at = datetime.fromisoformat(token_data["expires_at"]) if token_data["expires_at"] else None
        now = datetime.utcnow()
        
        days_active = (now - created_at).days
        days_remaining = max(0, (expires_at - now).days) if expires_at else None
        
        return {
            "token_id": token_id,
            "usage_count": token_data.get("usage_count", 0),
            "last_used_at": token_data.get("last_used_at"),
            "days_active": days_active,
            "days_remaining": days_remaining,
            "rate_limit": token_data.get("rate_limit"),
            "is_expired": now > expires_at if expires_at else False
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting token usage stats: {e}")
        raise HTTPException(status_code=500, detail=str(e))