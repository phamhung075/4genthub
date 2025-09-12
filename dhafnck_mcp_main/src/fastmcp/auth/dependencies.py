"""
FastAPI authentication dependencies for token management.
"""

from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from typing import Optional
import jwt
import os
import logging
from datetime import datetime

from fastmcp.auth.domain.entities.user import User

logger = logging.getLogger(__name__)

# Security scheme
security = HTTPBearer()

# JWT configuration - MUST be set in environment variables for production
JWT_SECRET_KEY = os.getenv("JWT_SECRET_KEY")
if not JWT_SECRET_KEY:
    logger.error("CRITICAL SECURITY WARNING: JWT_SECRET_KEY not set in environment!")
    logger.error("Generate a secure secret with: python generate_secure_secrets.py")
    logger.error("This MUST be fixed before deploying to production!")
    # For development only - will fail authentication
    JWT_SECRET_KEY = None
JWT_ALGORITHM = os.getenv("JWT_ALGORITHM", "HS256")


async def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(security)
) -> User:
    """
    Get the current authenticated user from the JWT token.
    
    This dependency extracts and validates the JWT token from the
    Authorization header and returns the authenticated user.
    """
    if not JWT_SECRET_KEY:
        logger.error("JWT_SECRET_KEY not configured - authentication will fail")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Server configuration error: JWT secret not set",
        )
    
    token = credentials.credentials
    
    try:
        # Decode the JWT token
        payload = jwt.decode(token, JWT_SECRET_KEY, algorithms=[JWT_ALGORITHM])
        
        # Extract user information
        user_id = payload.get("sub") or payload.get("user_id")
        email = payload.get("email")
        
        if not user_id:
            logger.error("Token missing user_id/sub claim")
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid authentication credentials",
                headers={"WWW-Authenticate": "Bearer"},
            )
        
        # Check token expiration
        exp = payload.get("exp")
        if exp:
            if datetime.now(timezone.utc).timestamp() > exp:
                logger.error("Token expired")
                raise HTTPException(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    detail="Token expired",
                    headers={"WWW-Authenticate": "Bearer"},
                )
        
        # Create and return User object
        # In a real application, you might fetch additional user details from database
        user = User(
            id=user_id,
            email=email or f"{user_id}@example.com",
            username=payload.get("username") or email or user_id,
            password_hash="authenticated-via-jwt"  # Not used for JWT auth
        )
        
        logger.info(f"Authenticated user: {user.id}")
        return user
        
    except jwt.ExpiredSignatureError:
        logger.error("Token expired")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token expired",
            headers={"WWW-Authenticate": "Bearer"},
        )
    except jwt.InvalidTokenError as e:
        logger.error(f"Invalid token: {e}")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid token",
            headers={"WWW-Authenticate": "Bearer"},
        )
    except HTTPException:
        # Re-raise HTTPExceptions without catching them
        raise
    except Exception as e:
        logger.error(f"Authentication error: {e}")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Could not validate credentials",
            headers={"WWW-Authenticate": "Bearer"},
        )


async def get_optional_current_user(
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(security)
) -> Optional[User]:
    """
    Get the current authenticated user if available, otherwise return None.
    
    This is useful for endpoints that should work with or without authentication.
    """
    if not credentials:
        return None
    
    try:
        return await get_current_user(credentials)
    except HTTPException:
        return None