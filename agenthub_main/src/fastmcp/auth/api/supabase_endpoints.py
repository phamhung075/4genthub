"""
Supabase Authentication API Endpoints

This module provides FastAPI endpoints that integrate with Supabase Auth
for user registration, login, password reset, and email verification.
"""

import logging
from typing import Optional, Dict, Any
from fastapi import APIRouter, HTTPException, Depends, Header, Body
from pydantic import BaseModel, EmailStr, Field

from ..infrastructure.supabase_auth import SupabaseAuthService, SupabaseAuthResult

logger = logging.getLogger(__name__)

# Create router
router = APIRouter(prefix="/auth/supabase", tags=["Supabase Authentication"])

# Initialize Supabase service
supabase_service = SupabaseAuthService()


# Request/Response Models
class SignUpRequest(BaseModel):
    """Sign up request model"""
    email: EmailStr
    password: str = Field(..., min_length=6)
    username: Optional[str] = None
    full_name: Optional[str] = None


class SignInRequest(BaseModel):
    """Sign in request model"""
    email: EmailStr
    password: str


class PasswordResetRequest(BaseModel):
    """Password reset request model"""
    email: EmailStr


class UpdatePasswordRequest(BaseModel):
    """Update password request model"""
    new_password: str = Field(..., min_length=6)


class ResendVerificationRequest(BaseModel):
    """Resend verification email request"""
    email: EmailStr


class AuthResponse(BaseModel):
    """Standard auth response"""
    success: bool
    message: str
    user: Optional[Dict[str, Any]] = None
    access_token: Optional[str] = None
    refresh_token: Optional[str] = None
    requires_email_verification: bool = False


# Helper functions
def get_bearer_token(authorization: Optional[str] = Header(None)) -> str:
    """Extract bearer token from authorization header"""
    if not authorization:
        raise HTTPException(status_code=401, detail="Authorization header missing")
    
    parts = authorization.split()
    if len(parts) != 2 or parts[0].lower() != "bearer":
        raise HTTPException(status_code=401, detail="Invalid authorization header format")
    
    return parts[1]


def format_auth_response(result: SupabaseAuthResult) -> AuthResponse:
    """Format Supabase result into API response"""
    response = AuthResponse(
        success=result.success,
        message=result.error_message or "Operation successful",
        requires_email_verification=result.requires_email_verification
    )
    
    if result.user:
        # Extract user info safely
        response.user = {
            "id": getattr(result.user, "id", None),
            "email": getattr(result.user, "email", None),
            "email_confirmed": getattr(result.user, "confirmed_at", None) is not None,
            "created_at": str(getattr(result.user, "created_at", "")),
            "user_metadata": getattr(result.user, "user_metadata", {})
        }
    
    if result.session:
        # Extract session tokens
        response.access_token = getattr(result.session, "access_token", None)
        response.refresh_token = getattr(result.session, "refresh_token", None)
    
    return response


# API Endpoints
@router.post("/signup", response_model=AuthResponse)
async def sign_up(request: SignUpRequest):
    """
    Sign up a new user with Supabase Auth.
    Automatically sends verification email.
    """
    try:
        # Prepare metadata
        metadata = {}
        if request.username:
            metadata["username"] = request.username
        if request.full_name:
            metadata["full_name"] = request.full_name
        
        # Sign up with Supabase
        result = await supabase_service.sign_up(
            email=request.email,
            password=request.password,
            metadata=metadata
        )
        
        if not result.success:
            raise HTTPException(status_code=400, detail=result.error_message)
        
        return format_auth_response(result)
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Signup error: {e}")
        raise HTTPException(status_code=500, detail="Internal server error during signup")


@router.post("/signin", response_model=AuthResponse)
async def sign_in(request: SignInRequest):
    """
    Sign in an existing user.
    Returns access and refresh tokens on success.
    """
    try:
        result = await supabase_service.sign_in(
            email=request.email,
            password=request.password
        )
        
        if not result.success:
            if result.requires_email_verification:
                raise HTTPException(
                    status_code=403,
                    detail="Please verify your email before signing in"
                )
            raise HTTPException(status_code=401, detail=result.error_message)
        
        return format_auth_response(result)
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Signin error: {e}")
        raise HTTPException(status_code=500, detail="Internal server error during signin")


@router.post("/signout")
async def sign_out(token: str = Depends(get_bearer_token)):
    """
    Sign out the current user.
    Invalidates the access token.
    """
    try:
        success = await supabase_service.sign_out(access_token=token)
        
        if not success:
            raise HTTPException(status_code=400, detail="Failed to sign out")
        
        return {"success": True, "message": "Signed out successfully"}
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Signout error: {e}")
        raise HTTPException(status_code=500, detail="Internal server error during signout")


@router.post("/password-reset", response_model=AuthResponse)
async def request_password_reset(request: PasswordResetRequest):
    """
    Request a password reset email.
    Sends reset link to user's email.
    """
    try:
        result = await supabase_service.reset_password_request(email=request.email)
        
        if not result.success:
            raise HTTPException(status_code=400, detail=result.error_message)
        
        return format_auth_response(result)
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Password reset request error: {e}")
        raise HTTPException(status_code=500, detail="Internal server error during password reset")


@router.post("/update-password", response_model=AuthResponse)
async def update_password(
    request: UpdatePasswordRequest,
    token: str = Depends(get_bearer_token)
):
    """
    Update user's password.
    Requires valid access token.
    """
    try:
        result = await supabase_service.update_password(
            access_token=token,
            new_password=request.new_password
        )
        
        if not result.success:
            raise HTTPException(status_code=400, detail=result.error_message)
        
        return format_auth_response(result)
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Password update error: {e}")
        raise HTTPException(status_code=500, detail="Internal server error during password update")


@router.get("/verify-token", response_model=AuthResponse)
async def verify_token(token: str = Depends(get_bearer_token)):
    """
    Verify an access token and get user info.
    Used for checking authentication status.
    """
    try:
        result = await supabase_service.verify_token(access_token=token)
        
        if not result.success:
            raise HTTPException(status_code=401, detail=result.error_message)
        
        return format_auth_response(result)
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Token verification error: {e}")
        raise HTTPException(status_code=500, detail="Internal server error during token verification")


@router.post("/resend-verification", response_model=AuthResponse)
async def resend_verification_email(request: ResendVerificationRequest):
    """
    Resend email verification link.
    For users who didn't receive or lost the original email.
    """
    try:
        result = await supabase_service.resend_verification_email(email=request.email)
        
        if not result.success:
            raise HTTPException(status_code=400, detail=result.error_message)
        
        return format_auth_response(result)
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Resend verification error: {e}")
        raise HTTPException(status_code=500, detail="Internal server error during resend verification")


@router.get("/oauth/{provider}")
async def get_oauth_url(provider: str):
    """
    Get OAuth URL for third-party provider.
    Supports: google, github, gitlab, bitbucket, etc.
    """
    try:
        result = await supabase_service.sign_in_with_provider(provider=provider)
        
        if "error" in result:
            raise HTTPException(status_code=400, detail=result["error"])
        
        return {
            "success": True,
            "url": result["url"],
            "provider": result["provider"]
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"OAuth URL generation error: {e}")
        raise HTTPException(status_code=500, detail="Internal server error during OAuth URL generation")


@router.get("/me", response_model=AuthResponse)
async def get_current_user(token: str = Depends(get_bearer_token)):
    """
    Get current authenticated user info.
    Requires valid access token.
    """
    try:
        result = await supabase_service.verify_token(access_token=token)
        
        if not result.success:
            raise HTTPException(status_code=401, detail="Not authenticated")
        
        return format_auth_response(result)
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Get current user error: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")


# Health check endpoint
@router.get("/health")
async def health_check():
    """Check if Supabase Auth service is configured"""
    try:
        # Just check if service is initialized
        if supabase_service.supabase_url and supabase_service.supabase_anon_key:
            return {
                "status": "healthy",
                "service": "Supabase Auth",
                "configured": True
            }
        else:
            return {
                "status": "unhealthy",
                "service": "Supabase Auth",
                "configured": False,
                "error": "Missing configuration"
            }
    except Exception as e:
        return {
            "status": "unhealthy",
            "service": "Supabase Auth",
            "error": str(e)
        }