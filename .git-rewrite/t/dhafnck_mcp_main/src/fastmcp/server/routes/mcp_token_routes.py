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
from ...auth.interface.supabase_fastapi_auth import get_current_user
from ...auth.domain.entities.user import User
from ...auth.services.mcp_token_service import mcp_token_service

logger = logging.getLogger(__name__)

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
        # Extract the Supabase token from the request
        # Note: This requires the user to be authenticated via Supabase
        
        # For now, we'll generate a token based on the user's authenticated session
        # In a real implementation, you might want to pass the original Supabase token
        
        # Create a mock Supabase token scenario - in reality, you'd extract this
        # from the authentication context or require it in the request
        
        logger.info(f"Generating MCP token for user {current_user.email}")
        
        # For demo purposes, we'll create a simplified token
        # In production, you'd want to use the actual Supabase token
        from ...auth.services.mcp_token_service import MCPToken
        from datetime import datetime, timezone, timedelta
        
        # Generate token using the service
        mcp_token_obj = await mcp_token_service.generate_mcp_token_from_user_id(
            user_id=current_user.id,
            email=current_user.email,
            expires_in_hours=request.expires_in_hours or 24,
            metadata={
                'description': request.description,
                'generated_via': 'api_endpoint',
                'user_agent': 'frontend'
            }
        )
        
        logger.info(f"Generated MCP token for user {current_user.email}")
        
        return TokenResponse(
            success=True,
            token=mcp_token_obj.token,
            expires_at=mcp_token_obj.expires_at.isoformat() if mcp_token_obj.expires_at else None,
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
        success = await mcp_token_service.revoke_user_tokens(current_user.id)
        
        if success:
            logger.info(f"Revoked all MCP tokens for user {current_user.email}")
            return TokenResponse(
                success=True,
                message="All MCP tokens revoked successfully"
            )
        else:
            return TokenResponse(
                success=True,
                message="No MCP tokens found to revoke"
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
        # Get global stats (admin users might see all, regular users see filtered)
        stats = mcp_token_service.get_token_stats()
        
        # For regular users, we might want to filter this to only their tokens
        # For now, return global stats
        
        return TokenStatsResponse(
            success=True,
            stats=stats,
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
        cleaned_count = await mcp_token_service.cleanup_expired_tokens()
        
        logger.info(f"User {current_user.email} triggered token cleanup: {cleaned_count} tokens cleaned")
        
        return {
            "success": True,
            "cleaned_tokens": cleaned_count,
            "message": f"Cleaned up {cleaned_count} expired tokens"
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
        stats = mcp_token_service.get_token_stats()
        
        return {
            "status": "healthy",
            "service": "mcp_token_service",
            "stats": stats,
            "message": "MCP token service is operational"
        }
        
    except Exception as e:
        logger.error(f"MCP token service health check failed: {e}")
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="MCP token service is not healthy"
        )