"""
Supabase FastAPI Authentication Integration

This module provides authentication dependencies for FastAPI endpoints
that validate Supabase JWT tokens instead of local JWT tokens.
"""

import logging
from typing import Optional
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from sqlalchemy.orm import Session

from ..infrastructure.supabase_auth import SupabaseAuthService
from ..domain.entities.user import User
from ..infrastructure.repositories.user_repository import UserRepository
from .fastapi_auth import get_db

logger = logging.getLogger(__name__)

# Use HTTPBearer for extracting Bearer tokens
security = HTTPBearer()

# Initialize Supabase auth service lazily
supabase_auth = None

def get_supabase_auth():
    """Get or create Supabase auth service instance."""
    global supabase_auth
    if supabase_auth is None:
        supabase_auth = SupabaseAuthService()
    return supabase_auth


async def get_current_user_supabase(
    credentials: HTTPAuthorizationCredentials = Depends(security),
    db: Session = Depends(get_db)
) -> User:
    """
    Validate Supabase token and return current user
    
    This dependency validates tokens issued by Supabase Auth.
    
    Args:
        credentials: Bearer token extracted by HTTPBearer
        db: Database session
        
    Returns:
        Current user object
        
    Raises:
        HTTPException: 401 if token is invalid or user not found
    """
    if not credentials:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authentication required",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    # Extract the token
    token = credentials.credentials
    
    try:
        # Verify token with Supabase
        result = await get_supabase_auth().verify_token(token)
        
        if not result.success or not result.user:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail=result.error_message or "Invalid or expired token",
                headers={"WWW-Authenticate": "Bearer"},
            )
        
        # Extract user ID from Supabase user data
        supabase_user = result.user
        user_id = supabase_user.id if hasattr(supabase_user, 'id') else supabase_user.get('id')
        
        if not user_id:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid token: missing user ID",
                headers={"WWW-Authenticate": "Bearer"},
            )
        
        # Get or create user in local database
        user_repository = UserRepository(db)
        user = user_repository.find_by_id(user_id)
        
        if not user:
            # Create user from Supabase data if not exists
            email = supabase_user.email if hasattr(supabase_user, 'email') else supabase_user.get('email')
            user_metadata = supabase_user.user_metadata if hasattr(supabase_user, 'user_metadata') else supabase_user.get('user_metadata', {})
            
            from ..domain.entities.user import UserStatus, UserRole
            from ..infrastructure.database.models import User as UserModel
            
            # Create domain user
            domain_user = User(
                id=user_id,
                email=email,
                username=user_metadata.get('username', email.split('@')[0] if email else 'user'),
                full_name=user_metadata.get('full_name', ''),
                password_hash="",  # No password stored for Supabase users
                status=UserStatus.ACTIVE,
                roles=[UserRole.USER],
                email_verified=True  # Supabase users are verified through Supabase
            )
            
            # Convert to database model and save
            db_user = UserModel.from_domain(domain_user)
            db.add(db_user)
            db.commit()
            
            # Convert back to domain entity
            user = db_user.to_domain()
            
            logger.info(f"Created local user from Supabase auth: {user.email}")
        
        return user
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Supabase token validation error: {e}")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authentication failed",
            headers={"WWW-Authenticate": "Bearer"},
        )


# Alias for backward compatibility
get_current_user = get_current_user_supabase