"""
Enhanced Authentication API Endpoints with Email Integration

This module provides FastAPI endpoints that combine Supabase Auth with custom
SMTP email functionality for complete authentication workflows.
"""

import logging
from typing import Optional, Dict, Any
from fastapi import APIRouter, HTTPException, Depends, Header, Body, Request
from pydantic import BaseModel, EmailStr, Field
from datetime import datetime

from ..infrastructure.enhanced_auth_service import EnhancedAuthService, get_enhanced_auth_service

logger = logging.getLogger(__name__)

# Create router
router = APIRouter(prefix="/auth/enhanced", tags=["Enhanced Authentication"])


# Request/Response Models
class EnhancedSignUpRequest(BaseModel):
    """Enhanced sign up request model"""
    email: EmailStr
    password: str = Field(..., min_length=6)
    username: Optional[str] = None
    full_name: Optional[str] = None
    send_custom_email: bool = True


class PasswordResetRequest(BaseModel):
    """Password reset request model"""
    email: EmailStr
    send_custom_email: bool = True


class VerifyEmailRequest(BaseModel):
    """Email verification request model"""
    token: str = Field(..., min_length=10)
    email: EmailStr


class ResetPasswordRequest(BaseModel):
    """Reset password with token request model"""
    token: str = Field(..., min_length=10)
    email: EmailStr
    new_password: str = Field(..., min_length=6)


class ResendVerificationRequest(BaseModel):
    """Resend verification email request"""
    email: EmailStr


class EnhancedAuthResponse(BaseModel):
    """Enhanced auth response with email status"""
    success: bool
    message: str
    user: Optional[Dict[str, Any]] = None
    access_token: Optional[str] = None
    refresh_token: Optional[str] = None
    requires_email_verification: bool = False
    email_sent: bool = False
    email_error: Optional[str] = None
    token_data: Optional[Dict[str, Any]] = None


def get_client_info(request: Request) -> Dict[str, str]:
    """Extract client information from request"""
    return {
        "ip_address": request.client.host if request.client else "unknown",
        "user_agent": request.headers.get("user-agent", "unknown")
    }


# API Endpoints
@router.post("/signup", response_model=EnhancedAuthResponse)
async def enhanced_sign_up(
    request: EnhancedSignUpRequest,
    http_request: Request,
    auth_service: EnhancedAuthService = Depends(get_enhanced_auth_service)
):
    """
    Sign up a new user with enhanced email verification.
    Combines Supabase auth with custom SMTP emails.
    """
    try:
        # Prepare metadata
        metadata = {}
        if request.username:
            metadata["username"] = request.username
        if request.full_name:
            metadata["full_name"] = request.full_name
        
        # Add client info to metadata
        client_info = get_client_info(http_request)
        metadata.update(client_info)
        
        # Register with enhanced service
        result = await auth_service.register_user(
            email=request.email,
            password=request.password,
            metadata=metadata,
            send_custom_email=request.send_custom_email
        )
        
        if not result.success:
            raise HTTPException(status_code=400, detail=result.error_message)
        
        return EnhancedAuthResponse(
            success=result.success,
            message=result.error_message or "Registration successful",
            user=result.user,
            access_token=result.session.get("access_token") if result.session else None,
            refresh_token=result.session.get("refresh_token") if result.session else None,
            requires_email_verification=result.requires_email_verification,
            email_sent=result.email_sent,
            email_error=result.email_error,
            token_data=result.token_data
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Enhanced signup error: {e}")
        raise HTTPException(status_code=500, detail="Internal server error during signup")


@router.post("/password-reset", response_model=EnhancedAuthResponse)
async def enhanced_password_reset(
    request: PasswordResetRequest,
    auth_service: EnhancedAuthService = Depends(get_enhanced_auth_service)
):
    """
    Request password reset with enhanced email functionality.
    Sends both Supabase and custom SMTP emails.
    """
    try:
        result = await auth_service.request_password_reset(
            email=request.email,
            send_custom_email=request.send_custom_email
        )
        
        return EnhancedAuthResponse(
            success=result.success,
            message=result.error_message or "Password reset email sent",
            email_sent=result.email_sent,
            email_error=result.email_error,
            token_data=result.token_data
        )
        
    except Exception as e:
        logger.error(f"Enhanced password reset error: {e}")
        raise HTTPException(status_code=500, detail="Internal server error during password reset")


@router.post("/verify-email", response_model=EnhancedAuthResponse)
async def verify_email_token(
    request: VerifyEmailRequest,
    auth_service: EnhancedAuthService = Depends(get_enhanced_auth_service)
):
    """
    Verify email using custom token.
    Sends welcome email upon successful verification.
    """
    try:
        result = await auth_service.verify_email_token(
            token=request.token,
            email=request.email
        )
        
        if not result.success:
            raise HTTPException(status_code=400, detail=result.error_message)
        
        return EnhancedAuthResponse(
            success=result.success,
            message=result.error_message or "Email verified successfully",
            email_sent=result.email_sent,
            email_error=result.email_error
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Email verification error: {e}")
        raise HTTPException(status_code=500, detail="Internal server error during email verification")


@router.post("/reset-password", response_model=EnhancedAuthResponse)
async def reset_password_with_token(
    request: ResetPasswordRequest,
    http_request: Request,
    auth_service: EnhancedAuthService = Depends(get_enhanced_auth_service)
):
    """
    Reset password using custom token.
    Sends confirmation email after successful reset.
    """
    try:
        client_info = get_client_info(http_request)
        
        result = await auth_service.reset_password_with_token(
            token=request.token,
            email=request.email,
            new_password=request.new_password,
            ip_address=client_info.get("ip_address"),
            user_agent=client_info.get("user_agent")
        )
        
        if not result.success:
            raise HTTPException(status_code=400, detail=result.error_message)
        
        return EnhancedAuthResponse(
            success=result.success,
            message=result.error_message or "Password reset successfully",
            email_sent=result.email_sent,
            email_error=result.email_error
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Password reset with token error: {e}")
        raise HTTPException(status_code=500, detail="Internal server error during password reset")


@router.post("/resend-verification", response_model=EnhancedAuthResponse)
async def resend_verification_email(
    request: ResendVerificationRequest,
    auth_service: EnhancedAuthService = Depends(get_enhanced_auth_service)
):
    """
    Resend email verification with custom token.
    Generates new token and sends custom SMTP email.
    """
    try:
        result = await auth_service.resend_verification_email(
            email=request.email
        )
        
        if not result.success:
            raise HTTPException(status_code=400, detail=result.error_message)
        
        return EnhancedAuthResponse(
            success=result.success,
            message=result.error_message or "Verification email sent",
            email_sent=result.email_sent,
            email_error=result.email_error,
            token_data=result.token_data
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Resend verification error: {e}")
        raise HTTPException(status_code=500, detail="Internal server error during resend verification")


# Admin/Utility Endpoints
@router.post("/cleanup-tokens")
async def cleanup_expired_tokens(
    older_than_days: int = 7,
    auth_service: EnhancedAuthService = Depends(get_enhanced_auth_service)
):
    """
    Clean up expired email tokens (admin endpoint).
    Removes tokens older than specified days.
    """
    try:
        result = await auth_service.cleanup_expired_tokens(older_than_days)
        
        if not result["success"]:
            raise HTTPException(status_code=500, detail=result["error_message"])
        
        return result
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Token cleanup error: {e}")
        raise HTTPException(status_code=500, detail="Internal server error during token cleanup")


@router.get("/email-stats")
async def get_email_statistics(
    auth_service: EnhancedAuthService = Depends(get_enhanced_auth_service)
):
    """
    Get email token usage statistics (admin endpoint).
    Returns token counts and usage metrics.
    """
    try:
        result = await auth_service.get_email_stats()
        
        if not result["success"]:
            raise HTTPException(status_code=500, detail=result["error_message"])
        
        return result
        
    except Exception as e:
        logger.error(f"Email stats error: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")


@router.get("/test-email")
async def test_email_service(
    auth_service: EnhancedAuthService = Depends(get_enhanced_auth_service)
):
    """
    Test SMTP email service connection (admin endpoint).
    Verifies SMTP configuration and connectivity.
    """
    try:
        result = await auth_service.test_email_service()
        
        return {
            "success": result["success"],
            "message": result["message"],
            "error": result.get("error_message"),
            "timestamp": datetime.now(timezone.utc).isoformat()
        }
        
    except Exception as e:
        logger.error(f"Email service test error: {e}")
        return {
            "success": False,
            "message": "Email service test failed",
            "error": str(e),
            "timestamp": datetime.now(timezone.utc).isoformat()
        }


# Health check endpoint
@router.get("/health")
async def health_check(
    auth_service: EnhancedAuthService = Depends(get_enhanced_auth_service)
):
    """Check enhanced auth service health"""
    try:
        # Test email service connection
        email_result = await auth_service.test_email_service()
        
        # Get basic stats
        stats_result = await auth_service.get_email_stats()
        
        return {
            "status": "healthy" if email_result["success"] else "degraded",
            "services": {
                "supabase_auth": {
                    "status": "configured" if auth_service.supabase.supabase_url else "not_configured"
                },
                "smtp_email": {
                    "status": "healthy" if email_result["success"] else "unhealthy",
                    "error": email_result.get("error_message")
                },
                "token_repository": {
                    "status": "healthy" if stats_result["success"] else "unhealthy",
                    "stats": stats_result.get("stats", {})
                }
            },
            "timestamp": datetime.now(timezone.utc).isoformat()
        }
        
    except Exception as e:
        logger.error(f"Health check error: {e}")
        return {
            "status": "unhealthy",
            "error": str(e),
            "timestamp": datetime.now(timezone.utc).isoformat()
        }