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

from fastmcp.auth.dependencies import get_current_user
from fastmcp.auth.domain.entities.user import User

logger = logging.getLogger(__name__)

# Get JWT secret from environment - MUST be set for production
JWT_SECRET_KEY = os.getenv("JWT_SECRET_KEY")
if not JWT_SECRET_KEY:
    logger.error("CRITICAL SECURITY WARNING: JWT_SECRET_KEY not set in environment!")
    logger.error("Token generation will not work without JWT_SECRET_KEY!")
    logger.error("Generate a secure secret with: python generate_secure_secrets.py")
    # Will cause token generation to fail
    JWT_SECRET_KEY = None
JWT_ALGORITHM = os.getenv("JWT_ALGORITHM", "HS256")

# In-memory token storage (in production, use database)
# Structure: {token_id: TokenData}
stored_tokens: Dict[str, Dict[str, Any]] = {}

# Map user_id to their tokens
user_tokens: Dict[str, List[str]] = {}


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


router = APIRouter(prefix="/api/v2/tokens", tags=["tokens"])


def generate_jwt_token(user_id: str, scopes: List[str], expires_in_days: int, token_id: str) -> str:
    """Generate a JWT token with specified scopes and expiration."""
    if not JWT_SECRET_KEY:
        raise ValueError("Cannot generate token: JWT_SECRET_KEY not configured")
    
    # Calculate expiration
    exp_timestamp = datetime.utcnow() + timedelta(days=expires_in_days)
    iat_timestamp = datetime.utcnow()
    
    # Create token payload
    payload = {
        "token_id": token_id,
        "user_id": user_id,
        "scopes": scopes,
        "exp": int(exp_timestamp.timestamp()),
        "iat": int(iat_timestamp.timestamp()),
        "type": "api_token"
    }
    
    # Generate token
    token = jwt.encode(payload, JWT_SECRET_KEY, algorithm=JWT_ALGORITHM)
    
    return token


def hash_token(token: str) -> str:
    """Hash a token for secure storage."""
    return hashlib.sha256(token.encode()).hexdigest()


@router.post("", response_model=TokenResponse)
async def generate_token(
    request: GenerateTokenRequest,
    current_user: User = Depends(get_current_user)
) -> TokenResponse:
    """Generate a new API token for the authenticated user."""
    try:
        # Generate unique token ID
        token_id = f"tok_{uuid.uuid4().hex[:16]}"
        
        # Generate the JWT token
        jwt_token = generate_jwt_token(
            user_id=current_user.id,
            scopes=request.scopes,
            expires_in_days=request.expires_in_days,
            token_id=token_id
        )
        
        # Calculate expiration date
        expires_at = datetime.utcnow() + timedelta(days=request.expires_in_days)
        
        # Store token data (store hash of token, not the token itself)
        token_data = {
            "id": token_id,
            "name": request.name,
            "token_hash": hash_token(jwt_token),
            "scopes": request.scopes,
            "created_at": datetime.utcnow().isoformat(),
            "expires_at": expires_at.isoformat(),
            "last_used_at": None,
            "usage_count": 0,
            "rate_limit": request.rate_limit,
            "is_active": True,
            "user_id": current_user.id
        }
        
        # Store token
        stored_tokens[token_id] = token_data
        
        # Track user's tokens
        if current_user.id not in user_tokens:
            user_tokens[current_user.id] = []
        user_tokens[current_user.id].append(token_id)
        
        logger.info(f"Generated token {token_id} for user {current_user.id} with scopes {request.scopes}")
        
        # Return response with actual token (only time we return it)
        return TokenResponse(
            id=token_id,
            name=request.name,
            token=jwt_token,  # Include actual token in response
            scopes=request.scopes,
            created_at=token_data["created_at"],
            expires_at=token_data["expires_at"],
            last_used_at=None,
            usage_count=0,
            rate_limit=request.rate_limit,
            is_active=True,
            user_id=current_user.id
        )
        
    except Exception as e:
        logger.error(f"Error generating token: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("")
async def list_tokens(
    current_user: User = Depends(get_current_user)
) -> Dict[str, Any]:
    """List all tokens for the authenticated user."""
    try:
        # Get user's tokens
        token_ids = user_tokens.get(current_user.id, [])
        
        # Filter and prepare token data (without actual tokens)
        user_token_list = []
        for token_id in token_ids:
            if token_id in stored_tokens:
                token_data = stored_tokens[token_id].copy()
                # Never return the actual token or hash
                token_data.pop("token_hash", None)
                user_token_list.append(token_data)
        
        # Clean up expired tokens
        now = datetime.utcnow()
        active_tokens = []
        for token in user_token_list:
            expires_at = datetime.fromisoformat(token["expires_at"])
            if expires_at > now:
                active_tokens.append(token)
            else:
                # Mark as inactive
                token["is_active"] = False
                active_tokens.append(token)
        
        logger.info(f"Listed {len(active_tokens)} tokens for user {current_user.id}")
        
        return {
            "data": active_tokens,
            "total": len(active_tokens)
        }
        
    except Exception as e:
        logger.error(f"Error listing tokens: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.delete("/{token_id}")
async def revoke_token(
    token_id: str,
    current_user: User = Depends(get_current_user)
) -> Dict[str, str]:
    """Revoke a specific token."""
    try:
        # Check if token exists and belongs to user
        if token_id not in stored_tokens:
            raise HTTPException(status_code=404, detail="Token not found")
        
        token_data = stored_tokens[token_id]
        if token_data["user_id"] != current_user.id:
            raise HTTPException(status_code=403, detail="Not authorized to revoke this token")
        
        # Remove token
        del stored_tokens[token_id]
        
        # Remove from user's token list
        if current_user.id in user_tokens:
            user_tokens[current_user.id] = [
                tid for tid in user_tokens[current_user.id] if tid != token_id
            ]
        
        logger.info(f"Revoked token {token_id} for user {current_user.id}")
        
        return {"message": "Token revoked successfully"}
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error revoking token: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/{token_id}")
async def get_token_details(
    token_id: str,
    current_user: User = Depends(get_current_user)
) -> TokenResponse:
    """Get details of a specific token."""
    try:
        # Check if token exists and belongs to user
        if token_id not in stored_tokens:
            raise HTTPException(status_code=404, detail="Token not found")
        
        token_data = stored_tokens[token_id]
        if token_data["user_id"] != current_user.id:
            raise HTTPException(status_code=403, detail="Not authorized to view this token")
        
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
            user_id=token_data["user_id"]
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
    current_user: User = Depends(get_current_user)
) -> TokenResponse:
    """Update the scopes of a specific token."""
    try:
        # Check if token exists and belongs to user
        if token_id not in stored_tokens:
            raise HTTPException(status_code=404, detail="Token not found")
        
        token_data = stored_tokens[token_id]
        if token_data["user_id"] != current_user.id:
            raise HTTPException(status_code=403, detail="Not authorized to update this token")
        
        # Update scopes
        token_data["scopes"] = request.scopes
        stored_tokens[token_id] = token_data
        
        logger.info(f"Updated scopes for token {token_id} to {request.scopes}")
        
        # Return updated token data
        return TokenResponse(
            id=token_data["id"],
            name=token_data["name"],
            token=None,
            scopes=token_data["scopes"],
            created_at=token_data["created_at"],
            expires_at=token_data["expires_at"],
            last_used_at=token_data.get("last_used_at"),
            usage_count=token_data.get("usage_count", 0),
            rate_limit=token_data.get("rate_limit"),
            is_active=token_data.get("is_active", True),
            user_id=token_data["user_id"]
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error updating token scopes: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/{token_id}/rotate")
async def rotate_token(
    token_id: str,
    current_user: User = Depends(get_current_user)
) -> TokenResponse:
    """Rotate a token (revoke old, generate new with same settings)."""
    try:
        # Check if token exists and belongs to user
        if token_id not in stored_tokens:
            raise HTTPException(status_code=404, detail="Token not found")
        
        old_token_data = stored_tokens[token_id]
        if old_token_data["user_id"] != current_user.id:
            raise HTTPException(status_code=403, detail="Not authorized to rotate this token")
        
        # Generate new token ID
        new_token_id = f"tok_{uuid.uuid4().hex[:16]}"
        
        # Calculate remaining days until expiration
        expires_at = datetime.fromisoformat(old_token_data["expires_at"])
        created_at = datetime.fromisoformat(old_token_data["created_at"])
        original_days = (expires_at - created_at).days
        
        # Generate new JWT token with same settings
        new_jwt_token = generate_jwt_token(
            user_id=current_user.id,
            scopes=old_token_data["scopes"],
            expires_in_days=original_days,
            token_id=new_token_id
        )
        
        # Create new token data
        new_token_data = {
            "id": new_token_id,
            "name": old_token_data["name"] + " (rotated)",
            "token_hash": hash_token(new_jwt_token),
            "scopes": old_token_data["scopes"],
            "created_at": datetime.utcnow().isoformat(),
            "expires_at": (datetime.utcnow() + timedelta(days=original_days)).isoformat(),
            "last_used_at": None,
            "usage_count": 0,
            "rate_limit": old_token_data.get("rate_limit"),
            "is_active": True,
            "user_id": current_user.id
        }
        
        # Remove old token
        del stored_tokens[token_id]
        if current_user.id in user_tokens:
            user_tokens[current_user.id].remove(token_id)
        
        # Store new token
        stored_tokens[new_token_id] = new_token_data
        if current_user.id not in user_tokens:
            user_tokens[current_user.id] = []
        user_tokens[current_user.id].append(new_token_id)
        
        logger.info(f"Rotated token {token_id} to {new_token_id} for user {current_user.id}")
        
        # Return new token
        return TokenResponse(
            id=new_token_id,
            name=new_token_data["name"],
            token=new_jwt_token,  # Include actual token in response
            scopes=new_token_data["scopes"],
            created_at=new_token_data["created_at"],
            expires_at=new_token_data["expires_at"],
            last_used_at=None,
            usage_count=0,
            rate_limit=new_token_data.get("rate_limit"),
            is_active=True,
            user_id=current_user.id
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error rotating token: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/validate")
async def validate_token(request: Request) -> Dict[str, Any]:
    """Validate a token provided in the Authorization header."""
    try:
        # Get token from Authorization header
        auth_header = request.headers.get("Authorization", "")
        if not auth_header.startswith("Bearer "):
            raise HTTPException(status_code=401, detail="Invalid authorization header")
        
        token = auth_header.replace("Bearer ", "")
        
        # Decode and verify token
        try:
            payload = jwt.decode(token, JWT_SECRET_KEY, algorithms=[JWT_ALGORITHM])
        except jwt.ExpiredSignatureError:
            return {"valid": False, "error": "Token expired"}
        except jwt.InvalidTokenError as e:
            return {"valid": False, "error": str(e)}
        
        # Check if token exists in storage
        token_id = payload.get("token_id")
        if token_id and token_id in stored_tokens:
            token_data = stored_tokens[token_id]
            
            # Update usage stats
            token_data["last_used_at"] = datetime.utcnow().isoformat()
            token_data["usage_count"] = token_data.get("usage_count", 0) + 1
            
            return {
                "valid": True,
                "user_id": payload.get("user_id"),
                "scopes": payload.get("scopes", []),
                "token_id": token_id
            }
        
        # Token not found in storage (might be valid JWT but revoked)
        return {"valid": False, "error": "Token not found or revoked"}
        
    except Exception as e:
        logger.error(f"Error validating token: {e}")
        return {"valid": False, "error": str(e)}


@router.get("/{token_id}/usage")
async def get_token_usage_stats(
    token_id: str,
    current_user: User = Depends(get_current_user)
) -> Dict[str, Any]:
    """Get usage statistics for a specific token."""
    try:
        # Check if token exists and belongs to user
        if token_id not in stored_tokens:
            raise HTTPException(status_code=404, detail="Token not found")
        
        token_data = stored_tokens[token_id]
        if token_data["user_id"] != current_user.id:
            raise HTTPException(status_code=403, detail="Not authorized to view this token")
        
        # Calculate stats
        created_at = datetime.fromisoformat(token_data["created_at"])
        expires_at = datetime.fromisoformat(token_data["expires_at"])
        now = datetime.utcnow()
        
        days_active = (now - created_at).days
        days_remaining = max(0, (expires_at - now).days)
        
        return {
            "token_id": token_id,
            "usage_count": token_data.get("usage_count", 0),
            "last_used_at": token_data.get("last_used_at"),
            "days_active": days_active,
            "days_remaining": days_remaining,
            "rate_limit": token_data.get("rate_limit"),
            "is_expired": now > expires_at
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting token usage stats: {e}")
        raise HTTPException(status_code=500, detail=str(e))