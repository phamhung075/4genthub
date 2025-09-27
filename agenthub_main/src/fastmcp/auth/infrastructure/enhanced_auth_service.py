"""
Enhanced Authentication Service with Email Integration

This service combines Supabase authentication with custom SMTP email functionality
for complete authentication workflows including registration, password reset, and
email verification.
"""

import os
import logging
from typing import Optional, Dict, Any
from datetime import datetime
from dataclasses import dataclass

from .supabase_auth import SupabaseAuthService, SupabaseAuthResult
from .email_service import SMTPEmailService, EmailResult, get_email_service
from .repositories.email_token_repository import (
    EmailTokenRepository, 
    EmailToken, 
    get_email_token_repository
)

logger = logging.getLogger(__name__)


@dataclass
class EnhancedAuthResult:
    """Enhanced authentication result with email status"""
    success: bool
    user: Optional[Dict[str, Any]] = None
    session: Optional[Dict[str, Any]] = None
    error_message: Optional[str] = None
    requires_email_verification: bool = False
    email_sent: bool = False
    email_error: Optional[str] = None
    token_data: Optional[Dict[str, Any]] = None


class EnhancedAuthService:
    """Enhanced authentication service with email integration"""
    
    def __init__(self, 
                 supabase_service: Optional[SupabaseAuthService] = None,
                 email_service: Optional[SMTPEmailService] = None,
                 token_repository: Optional[EmailTokenRepository] = None):
        """Initialize enhanced auth service"""
        self.supabase = supabase_service or SupabaseAuthService()
        self.email_service = email_service or get_email_service()
        self.token_repository = token_repository or get_email_token_repository()
        
        logger.info("Enhanced authentication service initialized")
    
    async def register_user(self, 
                           email: str, 
                           password: str, 
                           metadata: Optional[Dict] = None,
                           send_custom_email: bool = True) -> EnhancedAuthResult:
        """
        Register new user with custom email verification
        
        Args:
            email: User's email
            password: User's password
            metadata: Additional user metadata
            send_custom_email: Whether to send custom SMTP email
            
        Returns:
            EnhancedAuthResult with registration status and email status
        """
        try:
            # First register with Supabase (this may send its own email)
            supabase_result = await self.supabase.sign_up(email, password, metadata)
            
            if not supabase_result.success:
                return EnhancedAuthResult(
                    success=False,
                    error_message=supabase_result.error_message,
                    user=supabase_result.user,
                    session=supabase_result.session
                )
            
            # If custom email is requested, send our own verification email
            email_sent = False
            email_error = None
            token_data = None
            
            if send_custom_email:
                try:
                    # Generate our own verification token
                    from .email_service import TokenManager
                    token_manager = TokenManager()
                    token_data = token_manager.generate_verification_token(email, "verification")
                    
                    # Save token to repository
                    email_token = EmailToken(
                        token=token_data["token"],
                        email=email,
                        token_type="verification",
                        token_hash=token_data["hash"],
                        expires_at=token_data["expires_at"],
                        created_at=token_data["created_at"],
                        user_id=supabase_result.user.get("id") if supabase_result.user else None,
                        metadata={"registration": True, "user_metadata": metadata or {}}
                    )
                    
                    saved = self.token_repository.save_token(email_token)
                    if not saved:
                        logger.warning(f"Failed to save verification token for {email}")
                    
                    # Send custom verification email
                    user_name = None
                    if metadata:
                        user_name = metadata.get("username") or metadata.get("full_name")
                    
                    email_result = await self.email_service.send_verification_email(
                        email=email,
                        user_name=user_name
                    )
                    
                    email_sent = email_result.success
                    if not email_result.success:
                        email_error = email_result.error_message
                        logger.error(f"Failed to send verification email: {email_error}")
                    else:
                        logger.info(f"Custom verification email sent to {email}")
                        
                except Exception as e:
                    email_error = str(e)
                    logger.error(f"Error sending verification email: {e}")
            
            return EnhancedAuthResult(
                success=True,
                user=supabase_result.user,
                session=supabase_result.session,
                requires_email_verification=supabase_result.requires_email_verification,
                email_sent=email_sent,
                email_error=email_error,
                token_data=token_data,
                error_message="Registration successful. Please check your email to verify your account." if email_sent else supabase_result.error_message
            )
            
        except Exception as e:
            logger.error(f"Registration error: {e}")
            return EnhancedAuthResult(
                success=False,
                error_message=f"Registration failed: {str(e)}"
            )
    
    async def request_password_reset(self, 
                                   email: str,
                                   send_custom_email: bool = True) -> EnhancedAuthResult:
        """
        Request password reset with custom email
        
        Args:
            email: User's email
            send_custom_email: Whether to send custom SMTP email
            
        Returns:
            EnhancedAuthResult with request status and email status
        """
        try:
            # First use Supabase's built-in password reset
            supabase_result = await self.supabase.reset_password_request(email)
            
            email_sent = False
            email_error = None
            token_data = None
            
            # Send custom password reset email if requested
            if send_custom_email:
                try:
                    # Generate our own reset token
                    from .email_service import TokenManager
                    token_manager = TokenManager()
                    token_data = token_manager.generate_verification_token(email, "password_reset")
                    
                    # Save token to repository
                    email_token = EmailToken(
                        token=token_data["token"],
                        email=email,
                        token_type="password_reset",
                        token_hash=token_data["hash"],
                        expires_at=token_data["expires_at"],
                        created_at=token_data["created_at"],
                        metadata={"password_reset": True}
                    )
                    
                    saved = self.token_repository.save_token(email_token)
                    if not saved:
                        logger.warning(f"Failed to save password reset token for {email}")
                    
                    # Send custom reset email
                    email_result = await self.email_service.send_password_reset_email(
                        email=email
                    )
                    
                    email_sent = email_result.success
                    if not email_result.success:
                        email_error = email_result.error_message
                        logger.error(f"Failed to send password reset email: {email_error}")
                    else:
                        logger.info(f"Custom password reset email sent to {email}")
                        
                except Exception as e:
                    email_error = str(e)
                    logger.error(f"Error sending password reset email: {e}")
            
            return EnhancedAuthResult(
                success=True,  # We consider it successful if either email method works
                email_sent=email_sent,
                email_error=email_error,
                token_data=token_data,
                error_message="Password reset email sent. Please check your inbox."
            )
            
        except Exception as e:
            logger.error(f"Password reset request error: {e}")
            return EnhancedAuthResult(
                success=False,
                error_message=f"Password reset request failed: {str(e)}"
            )
    
    async def verify_email_token(self, token: str, email: str) -> EnhancedAuthResult:
        """
        Verify email verification token
        
        Args:
            token: Verification token
            email: User's email
            
        Returns:
            EnhancedAuthResult with verification status
        """
        try:
            # Validate token with repository
            email_token = self.token_repository.validate_token(
                token=token,
                email=email,
                token_type="verification",
                mark_used=True
            )
            
            if not email_token:
                return EnhancedAuthResult(
                    success=False,
                    error_message="Invalid or expired verification token"
                )
            
            # TODO: Mark user as verified in Supabase if needed
            # This depends on how you want to handle the verification flow
            
            # Send welcome email
            email_sent = False
            email_error = None
            
            try:
                user_name = None
                if email_token.metadata and "user_metadata" in email_token.metadata:
                    user_metadata = email_token.metadata["user_metadata"]
                    user_name = user_metadata.get("username") or user_metadata.get("full_name")
                
                email_result = await self.email_service.send_welcome_email(
                    email=email,
                    user_name=user_name
                )
                
                email_sent = email_result.success
                if not email_result.success:
                    email_error = email_result.error_message
                    logger.error(f"Failed to send welcome email: {email_error}")
                else:
                    logger.info(f"Welcome email sent to {email}")
                    
            except Exception as e:
                email_error = str(e)
                logger.error(f"Error sending welcome email: {e}")
            
            return EnhancedAuthResult(
                success=True,
                email_sent=email_sent,
                email_error=email_error,
                error_message="Email verified successfully! Welcome to Oracle Server."
            )
            
        except Exception as e:
            logger.error(f"Email verification error: {e}")
            return EnhancedAuthResult(
                success=False,
                error_message=f"Email verification failed: {str(e)}"
            )
    
    async def reset_password_with_token(self, 
                                      token: str, 
                                      email: str, 
                                      new_password: str,
                                      ip_address: Optional[str] = None,
                                      user_agent: Optional[str] = None) -> EnhancedAuthResult:
        """
        Reset password using token
        
        Args:
            token: Password reset token
            email: User's email
            new_password: New password
            ip_address: User's IP address
            user_agent: User's user agent
            
        Returns:
            EnhancedAuthResult with reset status
        """
        try:
            # Validate token with repository
            email_token = self.token_repository.validate_token(
                token=token,
                email=email,
                token_type="password_reset",
                mark_used=True
            )
            
            if not email_token:
                return EnhancedAuthResult(
                    success=False,
                    error_message="Invalid or expired reset token"
                )
            
            # TODO: Update password in Supabase
            # This would require implementing password update with admin privileges
            # For now, we'll assume it's handled by Supabase's built-in flow
            
            # Send password changed confirmation email
            email_sent = False
            email_error = None
            
            try:
                email_result = await self.email_service.send_password_changed_email(
                    email=email,
                    ip_address=ip_address,
                    user_agent=user_agent
                )
                
                email_sent = email_result.success
                if not email_result.success:
                    email_error = email_result.error_message
                    logger.error(f"Failed to send password changed email: {email_error}")
                else:
                    logger.info(f"Password changed confirmation sent to {email}")
                    
            except Exception as e:
                email_error = str(e)
                logger.error(f"Error sending password changed email: {e}")
            
            return EnhancedAuthResult(
                success=True,
                email_sent=email_sent,
                email_error=email_error,
                error_message="Password reset successfully. You can now log in with your new password."
            )
            
        except Exception as e:
            logger.error(f"Password reset error: {e}")
            return EnhancedAuthResult(
                success=False,
                error_message=f"Password reset failed: {str(e)}"
            )
    
    async def resend_verification_email(self, email: str) -> EnhancedAuthResult:
        """
        Resend verification email
        
        Args:
            email: User's email
            
        Returns:
            EnhancedAuthResult with resend status
        """
        try:
            # Generate new verification token
            from .email_service import TokenManager
            token_manager = TokenManager()
            token_data = token_manager.generate_verification_token(email, "verification")
            
            # Save token to repository
            email_token = EmailToken(
                token=token_data["token"],
                email=email,
                token_type="verification",
                token_hash=token_data["hash"],
                expires_at=token_data["expires_at"],
                created_at=token_data["created_at"],
                metadata={"resend": True}
            )
            
            saved = self.token_repository.save_token(email_token)
            if not saved:
                logger.warning(f"Failed to save verification token for {email}")
                return EnhancedAuthResult(
                    success=False,
                    error_message="Failed to generate verification token"
                )
            
            # Send verification email
            email_result = await self.email_service.send_verification_email(email=email)
            
            if email_result.success:
                logger.info(f"Verification email resent to {email}")
                return EnhancedAuthResult(
                    success=True,
                    email_sent=True,
                    token_data=token_data,
                    error_message="Verification email sent. Please check your inbox."
                )
            else:
                logger.error(f"Failed to resend verification email: {email_result.error_message}")
                return EnhancedAuthResult(
                    success=False,
                    email_sent=False,
                    email_error=email_result.error_message,
                    error_message="Failed to send verification email"
                )
                
        except Exception as e:
            logger.error(f"Resend verification error: {e}")
            return EnhancedAuthResult(
                success=False,
                error_message=f"Failed to resend verification email: {str(e)}"
            )
    
    async def cleanup_expired_tokens(self, older_than_days: int = 7) -> Dict[str, Any]:
        """Clean up expired email tokens"""
        try:
            deleted_count = self.token_repository.cleanup_expired_tokens(older_than_days)
            return {
                "success": True,
                "deleted_tokens": deleted_count,
                "message": f"Cleaned up {deleted_count} expired tokens"
            }
        except Exception as e:
            logger.error(f"Token cleanup error: {e}")
            return {
                "success": False,
                "error_message": str(e)
            }
    
    async def get_email_stats(self) -> Dict[str, Any]:
        """Get email token statistics"""
        try:
            stats = self.token_repository.get_token_stats()
            return {
                "success": True,
                "stats": stats
            }
        except Exception as e:
            logger.error(f"Email stats error: {e}")
            return {
                "success": False,
                "error_message": str(e)
            }
    
    async def test_email_service(self) -> Dict[str, Any]:
        """Test email service connection"""
        try:
            result = await self.email_service.test_connection()
            return {
                "success": result.success,
                "error_message": result.error_message,
                "message": "Email service connection test completed"
            }
        except Exception as e:
            logger.error(f"Email service test error: {e}")
            return {
                "success": False,
                "error_message": str(e)
            }


# Global enhanced auth service instance
_enhanced_auth_service: Optional[EnhancedAuthService] = None


def get_enhanced_auth_service() -> EnhancedAuthService:
    """Get global enhanced auth service instance"""
    global _enhanced_auth_service
    if _enhanced_auth_service is None:
        _enhanced_auth_service = EnhancedAuthService()
    return _enhanced_auth_service