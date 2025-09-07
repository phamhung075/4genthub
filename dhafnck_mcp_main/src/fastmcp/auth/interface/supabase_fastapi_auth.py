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
from fastapi import Request

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


async def get_current_user_from_middleware(
    request: Request,
    db: Session = Depends(get_db)
) -> User:
    """
    Get current user from middleware authentication context.
    
    This dependency uses the user authentication processed by DualAuthMiddleware
    instead of re-validating tokens.
    
    Args:
        request: FastAPI request object
        db: Database session
        
    Returns:
        Current user object
        
    Raises:
        HTTPException: 401 if not authenticated
    """
    # Check if middleware has processed authentication
    if not hasattr(request.state, 'user_id') or not request.state.user_id:
        logger.warning("No authentication found in request state - middleware may not be working")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authentication required - no user context found",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    user_id = request.state.user_id
    logger.debug(f"Retrieved user_id from middleware: {user_id}")
    
    # Get user from database
    try:
        user_repository = UserRepository(db)
        user = user_repository.find_by_id(user_id)
        
        if not user:
            # If user doesn't exist in local DB, create from auth info
            auth_info = getattr(request.state, 'auth_info', {})
            email = auth_info.get('email') if isinstance(auth_info, dict) else None
            
            if email:
                logger.info(f"Creating new user record for authenticated user: {user_id}")
                
                from ..domain.entities.user import UserStatus, UserRole
                
                # Create domain user  
                domain_user = User(
                    id=user_id,
                    email=email,
                    username=email.split('@')[0],  # Use email prefix as username
                    password_hash="",  # Empty for JWT-authenticated users
                    status=UserStatus.ACTIVE,
                    roles=[UserRole.USER]  # Fixed: roles is a list, not singular role
                )
                
                # Save to database
                user = await user_repository.save(domain_user)
                logger.info(f"Created new user: {user.id}")
            else:
                raise HTTPException(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    detail="User not found in database and no email available for creation",
                    headers={"WWW-Authenticate": "Bearer"},
                )
        
        return user
        
    except Exception as e:
        logger.error(f"Error retrieving user {user_id} from database: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Internal server error while retrieving user"
        )


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


# Use middleware-based authentication for better compatibility
get_current_user = get_current_user_from_middleware