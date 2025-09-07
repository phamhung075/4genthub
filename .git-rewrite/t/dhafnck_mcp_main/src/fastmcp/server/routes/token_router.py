"""
Token Management Router - API Token CRUD operations for MCP authentication
"""
from datetime import datetime, timedelta
from typing import List, Optional, Dict, Any
from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session
from sqlalchemy import Column, String, DateTime, Boolean, Integer, JSON, ForeignKey
from sqlalchemy.orm import declarative_base
import secrets
import hashlib
import jwt
from typing import Annotated

from fastmcp.auth.interface.fastapi_auth import get_current_user, get_db
from fastmcp.auth.domain.entities.user import User
from fastmcp.auth.mcp_integration.jwt_auth_backend import JWTAuthBackend
from fastmcp.task_management.infrastructure.database.models import APIToken

# Pydantic models for API
class TokenGenerateRequest(BaseModel):
    name: str = Field(..., min_length=1, max_length=100)
    scopes: List[str] = Field(default_factory=list)
    expires_in_days: int = Field(default=30, ge=1, le=365)
    rate_limit: Optional[int] = Field(default=1000, ge=1, le=10000)
    metadata: Optional[Dict[str, Any]] = Field(default_factory=dict)

class TokenResponse(BaseModel):
    id: str
    name: str
    token: Optional[str] = None  # Only included when generating
    scopes: List[str]
    created_at: datetime
    expires_at: datetime
    last_used_at: Optional[datetime]
    usage_count: int
    rate_limit: int
    is_active: bool
    metadata: Dict[str, Any]

class TokenListResponse(BaseModel):
    data: List[TokenResponse]
    total: int

class TokenUpdateRequest(BaseModel):
    name: Optional[str] = None
    scopes: Optional[List[str]] = None
    rate_limit: Optional[int] = None
    is_active: Optional[bool] = None

class TokenValidateResponse(BaseModel):
    valid: bool
    user_id: Optional[str] = None
    scopes: Optional[List[str]] = None
    expires_at: Optional[datetime] = None

# Router setup
router = APIRouter(prefix="/api/v2/tokens", tags=["Token Management"])
security = HTTPBearer()

# ===== STANDALONE HANDLER FUNCTIONS FOR STARLETTE INTEGRATION =====

async def generate_token_handler(request: TokenGenerateRequest, current_user: User, db: Session) -> TokenResponse:
    """Standalone handler for generating tokens (for Starlette integration)"""
    # Generate token
    raw_token = generate_secure_token()
    token_hash = hash_token(raw_token)
    
    # Calculate expiration
    expires_at = datetime.utcnow() + timedelta(days=request.expires_in_days)
    
    # Create token ID
    token_id = f"tok_{secrets.token_hex(8)}"
    
    # Create database record
    db_token = APIToken(
        id=token_id,
        user_id=current_user.id,
        name=request.name,
        token_hash=token_hash,
        scopes=request.scopes,
        expires_at=expires_at,
        rate_limit=request.rate_limit or 1000,
        token_metadata=request.metadata or {}
    )
    
    db.add(db_token)
    db.commit()
    db.refresh(db_token)
    
    # Create JWT for the token
    jwt_token = create_jwt_for_token(
        token_id=token_id,
        user_id=current_user.id,
        scopes=request.scopes,
        expires_at=expires_at
    )
    
    # Return response with the actual token (only shown once)
    return TokenResponse(
        id=db_token.id,
        name=db_token.name,
        token=jwt_token,  # Include the JWT token
        scopes=db_token.scopes,
        created_at=db_token.created_at,
        expires_at=db_token.expires_at,
        last_used_at=db_token.last_used_at,
        usage_count=db_token.usage_count,
        rate_limit=db_token.rate_limit,
        is_active=db_token.is_active,
        metadata=db_token.token_metadata if isinstance(db_token.token_metadata, dict) else {}
    )

async def list_tokens_handler(current_user: User, db: Session, skip: int = 0, limit: int = 100) -> TokenListResponse:
    """Standalone handler for listing tokens (for Starlette integration)"""
    # Query tokens for the user
    query = db.query(APIToken).filter(
        APIToken.user_id == current_user.id
    ).order_by(APIToken.created_at.desc())
    
    total = query.count()
    tokens = query.offset(skip).limit(limit).all()
    
    # Convert to response format (without exposing actual tokens)
    token_responses = [
        TokenResponse(
            id=token.id,
            name=token.name,
            scopes=token.scopes,
            created_at=token.created_at,
            expires_at=token.expires_at,
            last_used_at=token.last_used_at,
            usage_count=token.usage_count,
            rate_limit=token.rate_limit,
            is_active=token.is_active,
            metadata=token.token_metadata if isinstance(token.token_metadata, dict) else {}
        )
        for token in tokens
    ]
    
    return TokenListResponse(data=token_responses, total=total)

async def get_token_details_handler(token_id: str, current_user: User, db: Session) -> TokenResponse:
    """Standalone handler for getting token details (for Starlette integration)"""
    # Query for the token
    token = db.query(APIToken).filter(
        APIToken.id == token_id,
        APIToken.user_id == current_user.id
    ).first()
    
    if not token:
        raise HTTPException(status_code=404, detail="Token not found")
    
    return TokenResponse(
        id=token.id,
        name=token.name,
        scopes=token.scopes,
        created_at=token.created_at,
        expires_at=token.expires_at,
        last_used_at=token.last_used_at,
        usage_count=token.usage_count,
        rate_limit=token.rate_limit,
        is_active=token.is_active,
        metadata=token.token_metadata if isinstance(token.token_metadata, dict) else {}
    )

async def revoke_token_handler(token_id: str, current_user: User, db: Session) -> dict:
    """Standalone handler for revoking tokens (for Starlette integration)"""
    # Query for the token
    token = db.query(APIToken).filter(
        APIToken.id == token_id,
        APIToken.user_id == current_user.id
    ).first()
    
    if not token:
        raise HTTPException(status_code=404, detail="Token not found")
    
    # Mark as inactive
    token.is_active = False
    db.commit()
    
    return {"message": "Token revoked successfully"}

async def update_token_handler(token_id: str, request: TokenUpdateRequest, current_user: User, db: Session) -> TokenResponse:
    """Standalone handler for updating tokens (for Starlette integration)"""
    # Query for the token
    token = db.query(APIToken).filter(
        APIToken.id == token_id,
        APIToken.user_id == current_user.id
    ).first()
    
    if not token:
        raise HTTPException(status_code=404, detail="Token not found")
    
    # Update fields
    if request.name is not None:
        token.name = request.name
    if request.scopes is not None:
        token.scopes = request.scopes
    if request.rate_limit is not None:
        token.rate_limit = request.rate_limit
    if request.is_active is not None:
        token.is_active = request.is_active
    
    db.commit()
    db.refresh(token)
    
    return TokenResponse(
        id=token.id,
        name=token.name,
        scopes=token.scopes,
        created_at=token.created_at,
        expires_at=token.expires_at,
        last_used_at=token.last_used_at,
        usage_count=token.usage_count,
        rate_limit=token.rate_limit,
        is_active=token.is_active,
        metadata=token.token_metadata
    )

async def rotate_token_handler(token_id: str, current_user: User, db: Session) -> TokenResponse:
    """Standalone handler for rotating tokens (for Starlette integration)"""
    # Query for the token
    old_token = db.query(APIToken).filter(
        APIToken.id == token_id,
        APIToken.user_id == current_user.id
    ).first()
    
    if not old_token:
        raise HTTPException(status_code=404, detail="Token not found")
    
    # Generate new token
    raw_token = generate_secure_token()
    token_hash = hash_token(raw_token)
    
    # Create new token ID
    new_token_id = f"tok_{secrets.token_hex(8)}"
    
    # Update the existing token with new credentials
    old_token.id = new_token_id
    old_token.token_hash = token_hash
    
    db.commit()
    db.refresh(old_token)
    
    # Create JWT for the new token
    jwt_token = create_jwt_for_token(
        token_id=new_token_id,
        user_id=current_user.id,
        scopes=old_token.scopes,
        expires_at=old_token.expires_at
    )
    
    return TokenResponse(
        id=old_token.id,
        name=old_token.name,
        token=jwt_token,  # Include the new JWT token
        scopes=old_token.scopes,
        created_at=old_token.created_at,
        expires_at=old_token.expires_at,
        last_used_at=old_token.last_used_at,
        usage_count=old_token.usage_count,
        rate_limit=old_token.rate_limit,
        is_active=old_token.is_active,
        metadata=old_token.token_metadata
    )

async def validate_token_handler(token: str) -> TokenValidateResponse:
    """Standalone handler for validating tokens (for Starlette integration)"""
    try:
        jwt_backend = get_jwt_backend()
        payload = jwt.decode(token, jwt_backend.secret_key, algorithms=[jwt_backend.algorithm])
        
        return TokenValidateResponse(
            valid=True,
            user_id=payload.get("user_id"),
            scopes=payload.get("scopes", []),
            expires_at=datetime.fromtimestamp(payload.get("exp", 0))
        )
    except jwt.ExpiredSignatureError:
        return TokenValidateResponse(valid=False)
    except jwt.InvalidTokenError:
        return TokenValidateResponse(valid=False)

async def get_token_usage_stats_handler(token_id: str, current_user: User, db: Session) -> dict:
    """Standalone handler for getting token usage stats (for Starlette integration)"""
    # Query for the token
    token = db.query(APIToken).filter(
        APIToken.id == token_id,
        APIToken.user_id == current_user.id
    ).first()
    
    if not token:
        raise HTTPException(status_code=404, detail="Token not found")
    
    return {
        "token_id": token.id,
        "usage_count": token.usage_count,
        "last_used_at": token.last_used_at,
        "rate_limit": token.rate_limit,
        "is_active": token.is_active
    }

# JWT backend for user authentication (lazy initialization)
_jwt_backend = None

def get_jwt_backend():
    global _jwt_backend
    if _jwt_backend is None:
        _jwt_backend = JWTAuthBackend()
    return _jwt_backend

def generate_secure_token() -> str:
    """Generate a cryptographically secure token"""
    return secrets.token_urlsafe(32)

def hash_token(token: str) -> str:
    """Hash a token for storage"""
    return hashlib.sha256(token.encode()).hexdigest()

def create_jwt_for_token(token_id: str, user_id: str, scopes: List[str], expires_at: datetime) -> str:
    """Create a JWT that encapsulates the API token"""
    jwt_backend = get_jwt_backend()
    payload = {
        "token_id": token_id,
        "user_id": user_id,
        "scopes": scopes,
        "exp": expires_at,
        "iat": datetime.utcnow(),
        "type": "api_token"
    }
    return jwt.encode(payload, jwt_backend.secret_key, algorithm=jwt_backend.algorithm)

@router.post("/", response_model=TokenResponse)
async def generate_token(
    request: TokenGenerateRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Generate a new API token for the authenticated user"""
    
    # Generate token
    raw_token = generate_secure_token()
    token_hash = hash_token(raw_token)
    
    # Calculate expiration
    expires_at = datetime.utcnow() + timedelta(days=request.expires_in_days)
    
    # Create token ID
    token_id = f"tok_{secrets.token_hex(8)}"
    
    # Create database record
    db_token = APIToken(
        id=token_id,
        user_id=current_user.id,
        name=request.name,
        token_hash=token_hash,
        scopes=request.scopes,
        expires_at=expires_at,
        rate_limit=request.rate_limit or 1000,
        token_metadata=request.metadata or {}
    )
    
    db.add(db_token)
    db.commit()
    db.refresh(db_token)
    
    # Create JWT for the token
    jwt_token = create_jwt_for_token(
        token_id=token_id,
        user_id=current_user.id,
        scopes=request.scopes,
        expires_at=expires_at
    )
    
    # Return response with the actual token (only shown once)
    return TokenResponse(
        id=db_token.id,
        name=db_token.name,
        token=jwt_token,  # Include the JWT token
        scopes=db_token.scopes,
        created_at=db_token.created_at,
        expires_at=db_token.expires_at,
        last_used_at=db_token.last_used_at,
        usage_count=db_token.usage_count,
        rate_limit=db_token.rate_limit,
        is_active=db_token.is_active,
        metadata=db_token.token_metadata if isinstance(db_token.token_metadata, dict) else {}
    )

@router.get("/", response_model=TokenListResponse)
async def list_tokens(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
    skip: int = 0,
    limit: int = 100
):
    """List all API tokens for the authenticated user"""
    
    # Query tokens for the user
    query = db.query(APIToken).filter(
        APIToken.user_id == current_user.id
    ).order_by(APIToken.created_at.desc())
    
    total = query.count()
    tokens = query.offset(skip).limit(limit).all()
    
    # Convert to response format (without exposing actual tokens)
    token_responses = [
        TokenResponse(
            id=token.id,
            name=token.name,
            scopes=token.scopes,
            created_at=token.created_at,
            expires_at=token.expires_at,
            last_used_at=token.last_used_at,
            usage_count=token.usage_count,
            rate_limit=token.rate_limit,
            is_active=token.is_active,
            metadata=token.token_metadata if isinstance(token.token_metadata, dict) else {}
        )
        for token in tokens
    ]
    
    return TokenListResponse(data=token_responses, total=total)

@router.get("/{token_id}", response_model=TokenResponse)
async def get_token_details(
    token_id: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Get details of a specific API token"""
    
    token = db.query(APIToken).filter(
        APIToken.id == token_id,
        APIToken.user_id == current_user.id
    ).first()
    
    if not token:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Token not found"
        )
    
    return TokenResponse(
        id=token.id,
        name=token.name,
        scopes=token.scopes,
        created_at=token.created_at,
        expires_at=token.expires_at,
        last_used_at=token.last_used_at,
        usage_count=token.usage_count,
        rate_limit=token.rate_limit,
        is_active=token.is_active,
        metadata=token.token_metadata if isinstance(token.token_metadata, dict) else {}
    )

@router.delete("/{token_id}")
async def revoke_token(
    token_id: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Revoke (delete) an API token"""
    
    token = db.query(APIToken).filter(
        APIToken.id == token_id,
        APIToken.user_id == current_user.id
    ).first()
    
    if not token:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Token not found"
        )
    
    # Delete the token
    db.delete(token)
    db.commit()
    
    return {"message": "Token revoked successfully"}

@router.patch("/{token_id}", response_model=TokenResponse)
async def update_token(
    token_id: str,
    request: TokenUpdateRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Update an API token's properties"""
    
    token = db.query(APIToken).filter(
        APIToken.id == token_id,
        APIToken.user_id == current_user.id
    ).first()
    
    if not token:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Token not found"
        )
    
    # Update fields if provided
    if request.name is not None:
        token.name = request.name
    if request.scopes is not None:
        token.scopes = request.scopes
    if request.rate_limit is not None:
        token.rate_limit = request.rate_limit
    if request.is_active is not None:
        token.is_active = request.is_active
    
    db.commit()
    db.refresh(token)
    
    return TokenResponse(
        id=token.id,
        name=token.name,
        scopes=token.scopes,
        created_at=token.created_at,
        expires_at=token.expires_at,
        last_used_at=token.last_used_at,
        usage_count=token.usage_count,
        rate_limit=token.rate_limit,
        is_active=token.is_active,
        metadata=token.token_metadata if isinstance(token.token_metadata, dict) else {}
    )

@router.post("/{token_id}/rotate", response_model=TokenResponse)
async def rotate_token(
    token_id: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Rotate an API token (generate new token, keep same settings)"""
    
    old_token = db.query(APIToken).filter(
        APIToken.id == token_id,
        APIToken.user_id == current_user.id
    ).first()
    
    if not old_token:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Token not found"
        )
    
    # Generate new token
    raw_token = generate_secure_token()
    token_hash = hash_token(raw_token)
    
    # Create new token with same settings
    new_token_id = f"tok_{secrets.token_hex(8)}"
    new_expires_at = datetime.utcnow() + timedelta(days=30)  # Reset expiration
    
    new_token = APIToken(
        id=new_token_id,
        user_id=current_user.id,
        name=f"{old_token.name} (rotated)",
        token_hash=token_hash,
        scopes=old_token.scopes,
        expires_at=new_expires_at,
        rate_limit=old_token.rate_limit,
        token_metadata={**old_token.token_metadata, "rotated_from": old_token.id}
    )
    
    # Delete old token and add new one
    db.delete(old_token)
    db.add(new_token)
    db.commit()
    db.refresh(new_token)
    
    # Create JWT for the new token
    jwt_token = create_jwt_for_token(
        token_id=new_token_id,
        user_id=current_user.id,
        scopes=new_token.scopes,
        expires_at=new_expires_at
    )
    
    return TokenResponse(
        id=new_token.id,
        name=new_token.name,
        token=jwt_token,  # Include the new JWT token
        scopes=new_token.scopes,
        created_at=new_token.created_at,
        expires_at=new_token.expires_at,
        last_used_at=new_token.last_used_at,
        usage_count=new_token.usage_count,
        rate_limit=new_token.rate_limit,
        is_active=new_token.is_active,
        metadata=new_token.token_metadata if isinstance(new_token.token_metadata, dict) else {}
    )

@router.post("/validate", response_model=TokenValidateResponse)
async def validate_token(
    credentials: HTTPAuthorizationCredentials = Depends(security),
    db: Session = Depends(get_db)
):
    """Validate an API token"""
    
    token = credentials.credentials
    
    try:
        # Decode the JWT token
        jwt_backend = get_jwt_backend()
        payload = jwt.decode(
            token,
            jwt_backend.secret_key,
            algorithms=[jwt_backend.algorithm]
        )
        
        # Check if it's an API token
        if payload.get("type") != "api_token":
            return TokenValidateResponse(valid=False)
        
        token_id = payload.get("token_id")
        user_id = payload.get("user_id")
        scopes = payload.get("scopes", [])
        
        # Verify token exists and is active in database
        db_token = db.query(APIToken).filter(
            APIToken.id == token_id,
            APIToken.is_active == True
        ).first()
        
        if not db_token:
            return TokenValidateResponse(valid=False)
        
        # Update usage stats
        db_token.last_used_at = datetime.utcnow()
        db_token.usage_count += 1
        db.commit()
        
        return TokenValidateResponse(
            valid=True,
            user_id=user_id,
            scopes=scopes,
            expires_at=db_token.expires_at
        )
        
    except jwt.ExpiredSignatureError:
        return TokenValidateResponse(valid=False)
    except jwt.InvalidTokenError:
        return TokenValidateResponse(valid=False)
    except Exception:
        return TokenValidateResponse(valid=False)

@router.get("/{token_id}/usage")
async def get_token_usage_stats(
    token_id: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Get usage statistics for a token"""
    
    token = db.query(APIToken).filter(
        APIToken.id == token_id,
        APIToken.user_id == current_user.id
    ).first()
    
    if not token:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Token not found"
        )
    
    # Calculate stats
    now = datetime.utcnow()
    time_since_creation = (now - token.created_at).total_seconds() / 3600  # hours
    avg_requests_per_hour = token.usage_count / max(time_since_creation, 1)
    
    return {
        "token_id": token.id,
        "total_requests": token.usage_count,
        "last_used_at": token.last_used_at,
        "created_at": token.created_at,
        "expires_at": token.expires_at,
        "is_expired": now > token.expires_at,
        "is_active": token.is_active,
        "rate_limit": token.rate_limit,
        "avg_requests_per_hour": round(avg_requests_per_hour, 2),
        "time_until_expiry": (token.expires_at - now).total_seconds() if now < token.expires_at else 0
    }