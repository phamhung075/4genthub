"""
Authentication API Endpoints

This module provides FastAPI endpoints for authentication operations.
"""

import logging
import os
from typing import Optional, Dict, Any
from fastapi import APIRouter, Depends, HTTPException, status, Request, Response
from fastapi.security import OAuth2PasswordRequestForm
from pydantic import BaseModel, EmailStr, Field
from sqlalchemy.orm import Session

from ..application.services.auth_service import AuthService
from ..domain.services.jwt_service import JWTService
from ..domain.entities.user import User
from ..infrastructure.repositories.user_repository import UserRepository
from .fastapi_auth import (
    get_current_user as get_auth_user,
    get_current_active_user,
    require_admin,
    get_optional_user
)

logger = logging.getLogger(__name__)

# Initialize router
router = APIRouter(prefix="/api/auth", tags=["Authentication"])

# Initialize services
JWT_SECRET_KEY = os.getenv("JWT_SECRET_KEY", "your-secret-key-change-in-production")
jwt_service = JWTService(JWT_SECRET_KEY)

# Database configuration - lazy loaded
_db_config = None

def get_db_config():
    """Get database config (lazy loaded)"""
    global _db_config
    if _db_config is None:
        from ...task_management.infrastructure.database.database_config import DatabaseConfig
        _db_config = DatabaseConfig()
    return _db_config


def get_db() -> Session:
    """Get database session"""
    db_config = get_db_config()
    db = db_config.SessionLocal()
    try:
        yield db
    finally:
        db.close()


def get_auth_service(db: Session = Depends(get_db)) -> AuthService:
    """Get authentication service with dependencies"""
    user_repository = UserRepository(db)
    return AuthService(user_repository, jwt_service)


# Request/Response models
class RegisterRequest(BaseModel):
    """User registration request"""
    email: EmailStr
    username: str = Field(..., min_length=3, max_length=50)
    password: str = Field(..., min_length=8, max_length=128)
    full_name: Optional[str] = Field(None, max_length=255)


class LoginRequest(BaseModel):
    """Login request"""
    email_or_username: str
    password: str


class TokenResponse(BaseModel):
    """Token response"""
    access_token: str
    refresh_token: str
    token_type: str = "Bearer"
    expires_in: int = 900  # 15 minutes


class UserResponse(BaseModel):
    """User response (without sensitive data)"""
    id: str
    email: str
    username: str
    full_name: Optional[str]
    email_verified: bool
    roles: list[str]
    created_at: str


class MessageResponse(BaseModel):
    """Simple message response"""
    message: str
    success: bool = True


class PasswordResetRequest(BaseModel):
    """Password reset request"""
    email: EmailStr


class PasswordResetConfirm(BaseModel):
    """Password reset confirmation"""
    token: str
    new_password: str = Field(..., min_length=8, max_length=128)


class RefreshTokenRequest(BaseModel):
    """Refresh token request"""
    refresh_token: str


# Endpoints
@router.post("/register", response_model=MessageResponse)
async def register(
    request: RegisterRequest,
    auth_service: AuthService = Depends(get_auth_service)
):
    """
    Register a new user
    
    Requires:
    - Unique email address
    - Unique username
    - Strong password (min 8 characters)
    """
    try:
        result = await auth_service.register_user(
            email=request.email,
            username=request.username,
            password=request.password,
            full_name=request.full_name
        )
        
        if not result.success:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=result.error_message
            )
        
        # In production, send verification email here
        # For now, just return success
        return MessageResponse(
            message=f"Registration successful. Please check your email to verify your account.",
            success=True
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Registration error: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Registration failed"
        )


@router.post("/login", response_model=TokenResponse)
async def login(
    request: LoginRequest,
    client_request: Request,
    auth_service: AuthService = Depends(get_auth_service)
):
    """
    Login with email/username and password
    
    Returns access and refresh tokens on success.
    """
    try:
        # Get client IP for audit
        client_ip = client_request.client.host if client_request.client else None
        
        result = await auth_service.login(
            email_or_username=request.email_or_username,
            password=request.password,
            ip_address=client_ip
        )
        
        if not result.success:
            if result.requires_email_verification:
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail="Email verification required"
                )
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail=result.error_message or "Invalid credentials"
            )
        
        return TokenResponse(
            access_token=result.access_token,
            refresh_token=result.refresh_token,
            token_type="Bearer",
            expires_in=900
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Login error: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Login failed"
        )


@router.post("/refresh", response_model=TokenResponse)
async def refresh_tokens(
    request: RefreshTokenRequest,
    auth_service: AuthService = Depends(get_auth_service)
):
    """
    Refresh access and refresh tokens
    
    Requires valid refresh token
    """
    try:
        tokens = await auth_service.refresh_tokens(request.refresh_token)
        
        if not tokens:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid or expired refresh token"
            )
        
        access_token, refresh_token = tokens
        
        return TokenResponse(
            access_token=access_token,
            refresh_token=refresh_token,
            token_type="Bearer",
            expires_in=900
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Token refresh error: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Token refresh failed"
        )


@router.get("/me", response_model=UserResponse)
async def get_current_user_endpoint(
    current_user: User = Depends(get_auth_user)
):
    """
    Get current user information
    
    Requires valid access token
    """
    try:
        return UserResponse(
            id=current_user.id,
            email=current_user.email,
            username=current_user.username,
            full_name=current_user.full_name,
            email_verified=current_user.email_verified,
            roles=[r.value if hasattr(r, 'value') else r for r in current_user.roles],
            created_at=current_user.created_at.isoformat() if current_user.created_at else ""
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Get current user error: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to get user information"
        )


@router.post("/logout", response_model=MessageResponse)
async def logout(
    current_user: User = Depends(get_auth_user),
    auth_service: AuthService = Depends(get_auth_service)
):
    """
    Logout user and optionally revoke tokens
    
    Requires valid access token
    """
    try:
        user_id = current_user.id
        success = await auth_service.logout(user_id, revoke_all_tokens=True)
        
        if not success:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Logout failed"
            )
        
        return MessageResponse(
            message="Logged out successfully",
            success=True
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Logout error: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Logout failed"
        )


@router.post("/verify-email/{token}", response_model=MessageResponse)
async def verify_email(
    token: str,
    auth_service: AuthService = Depends(get_auth_service)
):
    """
    Verify email address with token
    
    Token is sent via email after registration
    """
    try:
        success, error_message = await auth_service.verify_email(token)
        
        if not success:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=error_message or "Email verification failed"
            )
        
        return MessageResponse(
            message="Email verified successfully. You can now login.",
            success=True
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Email verification error: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Email verification failed"
        )


@router.post("/password-reset", response_model=MessageResponse)
async def request_password_reset(
    request: PasswordResetRequest,
    auth_service: AuthService = Depends(get_auth_service)
):
    """
    Request password reset
    
    Sends reset token to user's email
    """
    try:
        success, token, error = await auth_service.request_password_reset(request.email)
        
        # Always return success to avoid revealing if email exists
        # In production, send email with token
        return MessageResponse(
            message="If the email exists, a password reset link has been sent.",
            success=True
        )
        
    except Exception as e:
        logger.error(f"Password reset request error: {e}")
        # Still return success to avoid information leakage
        return MessageResponse(
            message="If the email exists, a password reset link has been sent.",
            success=True
        )


@router.post("/password-reset/confirm", response_model=MessageResponse)
async def confirm_password_reset(
    request: PasswordResetConfirm,
    auth_service: AuthService = Depends(get_auth_service)
):
    """
    Confirm password reset with token
    
    Requires valid reset token and new password
    """
    try:
        success, error_message = await auth_service.reset_password(
            token=request.token,
            new_password=request.new_password
        )
        
        if not success:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=error_message or "Password reset failed"
            )
        
        return MessageResponse(
            message="Password reset successfully. You can now login with your new password.",
            success=True
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Password reset confirmation error: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Password reset failed"
        )


@router.get("/health", response_model=MessageResponse)
async def health_check():
    """Health check endpoint"""
    return MessageResponse(
        message="Authentication service is healthy",
        success=True
    )