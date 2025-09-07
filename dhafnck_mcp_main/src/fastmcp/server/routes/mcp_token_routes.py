"""
MCP Token Management Routes

API endpoints for generating and managing MCP tokens from the frontend.
These tokens are used by MCP clients to authenticate against the server.
"""

import logging
from typing import Optional
from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel
from sqlalchemy.orm import Session

from ...auth.interface.fastapi_auth import get_db
from ...auth.interface.fastapi_auth import get_current_user
from ...auth.domain.entities.user import User
from ...task_management.interface.api_controllers.token_api_controller import TokenAPIController

logger = logging.getLogger(__name__)

# Initialize token controller (following DDD - no direct service access)
token_controller = TokenAPIController()

router = APIRouter(prefix="/api/v2/mcp-tokens", tags=["MCP Token Management"])


class GenerateTokenRequest(BaseModel):
    """Request model for token generation"""
    expires_in_hours: Optional[int] = 24
    description: Optional[str] = None


class TokenResponse(BaseModel):
    """Response model for token operations"""
    success: bool
    token: Optional[str] = None
    expires_at: Optional[str] = None
    message: str


class TokenStatsResponse(BaseModel):
    """Response model for token statistics"""
    success: bool
    stats: dict
    message: str


@router.post("/generate", response_model=TokenResponse)
async def generate_mcp_token(
    request: GenerateTokenRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Generate a new MCP token for the authenticated user.
    
    This endpoint allows authenticated users to generate MCP tokens
    that can be used for MCP protocol communications.
    """
    try:
        logger.info(f"Generating MCP token for user {current_user.email}")
        
        # Use token controller following DDD pattern
        result = await token_controller.generate_mcp_token_from_user(
            user_id=current_user.id,
            email=current_user.email,
            expires_in_hours=request.expires_in_hours or 24,
            metadata={
                'description': request.description,
                'generated_via': 'api_endpoint',
                'user_agent': 'frontend'
            },
            session=db
        )
        
        if not result.get("success"):
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=result.get("error", "Failed to generate MCP token")
            )
        
        logger.info(f"Generated MCP token for user {current_user.email}")
        
        return TokenResponse(
            success=True,
            token=result.get("token"),
            expires_at=result.get("expires_at"),
            message=f"MCP token generated successfully. Expires in {request.expires_in_hours or 24} hours."
        )
        
    except Exception as e:
        logger.error(f"Error generating MCP token for user {current_user.id}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to generate MCP token"
        )


@router.delete("/revoke", response_model=TokenResponse)
async def revoke_mcp_tokens(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Revoke all MCP tokens for the authenticated user.
    
    This will invalidate all existing MCP tokens for the user,
    requiring them to generate new ones.
    """
    try:
        # Use token controller following DDD pattern
        result = await token_controller.revoke_user_tokens(current_user.id)
        
        if result.get("success"):
            logger.info(f"Revoked all MCP tokens for user {current_user.email}")
            return TokenResponse(
                success=True,
                message=result.get("message", "All MCP tokens revoked successfully")
            )
        else:
            return TokenResponse(
                success=False,
                message=result.get("message", "Failed to revoke tokens")
            )
            
    except Exception as e:
        logger.error(f"Error revoking MCP tokens for user {current_user.id}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to revoke MCP tokens"
        )


@router.get("/stats", response_model=TokenStatsResponse)
async def get_token_stats(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Get statistics about the user's MCP tokens.
    
    Returns information about active and expired tokens.
    """
    try:
        # Use token controller following DDD pattern
        result = token_controller.get_token_stats()
        
        if not result.get("success"):
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=result.get("error", "Failed to get token statistics")
            )
        
        return TokenStatsResponse(
            success=True,
            stats=result.get("stats", {}),
            message="Token statistics retrieved successfully"
        )
        
    except Exception as e:
        logger.error(f"Error getting token stats for user {current_user.id}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to get token statistics"
        )


@router.post("/cleanup", response_model=dict)
async def cleanup_expired_tokens(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Clean up expired MCP tokens.
    
    This endpoint is typically for administrative use but can be
    called by authenticated users to trigger cleanup.
    """
    try:
        # Use token controller following DDD pattern
        result = await token_controller.cleanup_expired_tokens()
        
        if not result.get("success"):
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=result.get("error", "Failed to clean up expired tokens")
            )
        
        cleaned_count = result.get("cleaned_count", 0)
        logger.info(f"User {current_user.email} triggered token cleanup: {cleaned_count} tokens cleaned")
        
        return {
            "success": True,
            "cleaned_tokens": cleaned_count,
            "message": result.get("message", f"Cleaned up {cleaned_count} expired tokens")
        }
        
    except Exception as e:
        logger.error(f"Error cleaning up tokens: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to clean up expired tokens"
        )


# Health check endpoint for MCP token service
@router.get("/health")
async def mcp_token_service_health():
    """
    Health check for MCP token service.
    
    Returns the current status of the token service.
    """
    try:
        # Use token controller following DDD pattern
        result = token_controller.get_token_stats()
        
        if not result.get("success"):
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail="MCP token service is not healthy"
            )
        
        return {
            "status": "healthy",
            "service": "mcp_token_service",
            "stats": result.get("stats", {}),
            "message": "MCP token service is operational"
        }
        
    except Exception as e:
        logger.error(f"MCP token service health check failed: {e}")
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="MCP token service is not healthy"
        )