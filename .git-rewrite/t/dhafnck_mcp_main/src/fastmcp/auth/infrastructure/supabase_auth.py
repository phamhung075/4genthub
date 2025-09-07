"""
Supabase Authentication Integration

This module integrates Supabase's built-in authentication system,
providing email verification, password reset, and OAuth capabilities.
"""

import os
import logging
from typing import Optional, Dict, Any
from dataclasses import dataclass
from dotenv import load_dotenv

try:
    from supabase import create_client, Client
    SUPABASE_AVAILABLE = True
except ImportError:
    SUPABASE_AVAILABLE = False
    # Mock classes for when supabase is not available
    class Client:
        pass
    def create_client(*args, **kwargs):
        return None

# Load environment variables
load_dotenv()

logger = logging.getLogger(__name__)


@dataclass
class SupabaseAuthResult:
    """Result from Supabase authentication operations"""
    success: bool
    user: Optional[Dict[str, Any]] = None
    session: Optional[Dict[str, Any]] = None
    error_message: Optional[str] = None
    requires_email_verification: bool = False


class SupabaseAuthService:
    """Service for handling Supabase authentication"""
    
    def __init__(self):
        """Initialize Supabase client with environment credentials"""
        if not SUPABASE_AVAILABLE:
            logger.warning("Supabase package not available - using mock implementation")
            self.client = None
            self.admin_client = None
            return
            
        self.supabase_url = os.getenv("SUPABASE_URL")
        self.supabase_anon_key = os.getenv("SUPABASE_ANON_KEY")
        self.supabase_service_key = os.getenv("SUPABASE_SERVICE_ROLE_KEY")
        
        if not self.supabase_url or not self.supabase_anon_key:
            logger.warning("Missing Supabase credentials in environment - using mock implementation")
            self.client = None
            self.admin_client = None
            return
        
        # Use anon key for client-side operations
        self.client: Client = create_client(self.supabase_url, self.supabase_anon_key)
        
        # Create admin client for server-side operations
        self.admin_client: Client = create_client(self.supabase_url, self.supabase_service_key)
        
        logger.info("Supabase Auth Service initialized")
    
    async def sign_up(self, email: str, password: str, metadata: Optional[Dict] = None) -> SupabaseAuthResult:
        """
        Sign up a new user with Supabase Auth
        
        Args:
            email: User's email address
            password: User's password
            metadata: Optional user metadata (username, full_name, etc.)
            
        Returns:
            SupabaseAuthResult with user and session data
        """
        if not SUPABASE_AVAILABLE or not self.client:
            logger.error("Supabase not available - cannot perform sign up")
            return SupabaseAuthResult(
                success=False,
                error="Supabase authentication not available",
                user=None,
                session=None
            )
        try:
            # Prepare user metadata
            user_metadata = metadata or {}
            
            # Sign up with Supabase Auth
            response = self.client.auth.sign_up({
                "email": email,
                "password": password,
                "options": {
                    "data": user_metadata,
                    "email_redirect_to": f"{os.getenv('FRONTEND_URL', 'http://localhost:3800')}/auth/verify"
                }
            })
            
            if response.user:
                logger.info(f"User signed up successfully: {email}")
                
                # Check if email confirmation is required
                if not response.user.confirmed_at:
                    return SupabaseAuthResult(
                        success=True,
                        user=response.user,
                        session=response.session,
                        requires_email_verification=True,
                        error_message="Please check your email to verify your account"
                    )
                
                return SupabaseAuthResult(
                    success=True,
                    user=response.user,
                    session=response.session
                )
            else:
                return SupabaseAuthResult(
                    success=False,
                    error_message="Failed to create user account"
                )
                
        except Exception as e:
            logger.error(f"Signup error: {e}")
            error_msg = str(e)
            
            # Parse common Supabase error messages
            if "User already registered" in error_msg:
                return SupabaseAuthResult(
                    success=False,
                    error_message="Email already registered"
                )
            elif "Password should be at least" in error_msg:
                return SupabaseAuthResult(
                    success=False,
                    error_message="Password must be at least 6 characters"
                )
            
            return SupabaseAuthResult(
                success=False,
                error_message=error_msg
            )
    
    async def sign_in(self, email: str, password: str) -> SupabaseAuthResult:
        """
        Sign in an existing user
        
        Args:
            email: User's email
            password: User's password
            
        Returns:
            SupabaseAuthResult with session data
        """
        if not SUPABASE_AVAILABLE or not self.client:
            logger.error("Supabase not available - cannot perform sign in")
            return SupabaseAuthResult(
                success=False,
                error="Supabase authentication not available",
                user=None,
                session=None
            )
        try:
            response = self.client.auth.sign_in_with_password({
                "email": email,
                "password": password
            })
            
            if response.user and response.session:
                logger.info(f"User signed in successfully: {email}")
                
                # Check if email is verified
                if not response.user.confirmed_at:
                    return SupabaseAuthResult(
                        success=False,
                        requires_email_verification=True,
                        error_message="Please verify your email before signing in"
                    )
                
                return SupabaseAuthResult(
                    success=True,
                    user=response.user,
                    session=response.session
                )
            else:
                return SupabaseAuthResult(
                    success=False,
                    error_message="Invalid email or password"
                )
                
        except Exception as e:
            logger.error(f"Sign in error: {e}")
            error_msg = str(e)
            
            if "Invalid login credentials" in error_msg:
                return SupabaseAuthResult(
                    success=False,
                    error_message="Invalid email or password"
                )
            elif "Email not confirmed" in error_msg:
                return SupabaseAuthResult(
                    success=False,
                    requires_email_verification=True,
                    error_message="Please verify your email before signing in"
                )
            
            return SupabaseAuthResult(
                success=False,
                error_message=error_msg
            )
    
    async def sign_out(self, access_token: str) -> bool:
        """
        Sign out a user
        
        Args:
            access_token: User's access token
            
        Returns:
            True if successful, False otherwise
        """
        try:
            # Set the session before signing out
            self.client.auth.set_session(access_token, "")
            self.client.auth.sign_out()
            logger.info("User signed out successfully")
            return True
        except Exception as e:
            logger.error(f"Sign out error: {e}")
            return False
    
    async def reset_password_request(self, email: str) -> SupabaseAuthResult:
        """
        Send password reset email
        
        Args:
            email: User's email address
            
        Returns:
            SupabaseAuthResult indicating success
        """
        try:
            response = self.client.auth.reset_password_for_email(
                email,
                {
                    "redirect_to": f"{os.getenv('FRONTEND_URL', 'http://localhost:3800')}/auth/reset-password"
                }
            )
            
            logger.info(f"Password reset email sent to: {email}")
            return SupabaseAuthResult(
                success=True,
                error_message="Password reset email sent. Please check your inbox."
            )
            
        except Exception as e:
            logger.error(f"Password reset error: {e}")
            return SupabaseAuthResult(
                success=False,
                error_message="Failed to send password reset email"
            )
    
    async def update_password(self, access_token: str, new_password: str) -> SupabaseAuthResult:
        """
        Update user's password
        
        Args:
            access_token: User's access token
            new_password: New password
            
        Returns:
            SupabaseAuthResult indicating success
        """
        try:
            # Set the session
            self.client.auth.set_session(access_token, "")
            
            response = self.client.auth.update_user({
                "password": new_password
            })
            
            if response.user:
                logger.info("Password updated successfully")
                return SupabaseAuthResult(
                    success=True,
                    user=response.user
                )
            else:
                return SupabaseAuthResult(
                    success=False,
                    error_message="Failed to update password"
                )
                
        except Exception as e:
            logger.error(f"Password update error: {e}")
            return SupabaseAuthResult(
                success=False,
                error_message=str(e)
            )
    
    async def verify_token(self, access_token: str) -> SupabaseAuthResult:
        """
        Verify and get user from access token
        
        Args:
            access_token: JWT access token
            
        Returns:
            SupabaseAuthResult with user data if valid
        """
        try:
            # The Supabase client's get_user method requires the token to be set as the session first
            # Or we can use the admin client to verify the token
            if hasattr(self, 'admin_client') and self.admin_client:
                # Use admin client to get user by JWT
                response = self.admin_client.auth.get_user(access_token)
            else:
                # Regular client - set session then get user
                # Note: get_user expects just the token, not "Bearer " prefix
                response = self.client.auth.get_user(access_token)
            
            if response and response.user:
                return SupabaseAuthResult(
                    success=True,
                    user=response.user
                )
            else:
                return SupabaseAuthResult(
                    success=False,
                    error_message="Invalid or expired token"
                )
                
        except Exception as e:
            logger.error(f"Token verification error: {e}")
            # Don't decode without verification - this is a security risk!
            # If Supabase can't verify the token, it's invalid
            return SupabaseAuthResult(
                success=False,
                error_message="Invalid or expired token"
            )
    
    async def resend_verification_email(self, email: str) -> SupabaseAuthResult:
        """
        Resend email verification
        
        Args:
            email: User's email address
            
        Returns:
            SupabaseAuthResult indicating success
        """
        try:
            # For Supabase, we need to trigger a new signup to resend the confirmation email
            # This is the standard way to resend verification emails in Supabase
            response = self.client.auth.sign_up({
                "email": email,
                "password": "temporary_resend_" + os.urandom(16).hex(),  # Dummy password for resend
                "options": {
                    "email_redirect_to": f"{os.getenv('FRONTEND_URL', 'http://localhost:3800')}/auth/verify"
                }
            })
            
            # Check if user already exists but not confirmed
            if response.user and response.user.confirmed_at is None:
                logger.info(f"Verification email resent to: {email}")
                return SupabaseAuthResult(
                    success=True,
                    error_message="Verification email sent. Please check your inbox."
                )
            elif response.user and response.user.confirmed_at:
                # User is already confirmed
                return SupabaseAuthResult(
                    success=False,
                    error_message="This email is already verified. Please try logging in."
                )
            else:
                # New user or resend successful
                logger.info(f"Verification email sent to: {email}")
                return SupabaseAuthResult(
                    success=True,
                    error_message="Verification email sent. Please check your inbox."
                )
            
        except Exception as e:
            error_msg = str(e)
            logger.error(f"Resend verification error: {error_msg}")
            
            # Check for specific error cases
            if "already been registered" in error_msg.lower() or "user already registered" in error_msg.lower():
                # User is already registered - this is actually expected for resend
                # Supabase will still send the email for unconfirmed users
                logger.info(f"User already exists, verification email should be sent: {email}")
                return SupabaseAuthResult(
                    success=True,
                    error_message="Verification email sent. Please check your inbox."
                )
            elif "rate limit" in error_msg.lower():
                return SupabaseAuthResult(
                    success=False,
                    error_message="Too many requests. Please wait 60 seconds before trying again."
                )
            else:
                return SupabaseAuthResult(
                    success=False,
                    error_message="Failed to resend verification email. Please try again later."
                )
    
    async def sign_in_with_provider(self, provider: str) -> Dict[str, Any]:
        """
        Get OAuth URL for third-party provider
        
        Args:
            provider: Provider name (google, github, etc.)
            
        Returns:
            Dict with provider URL
        """
        try:
            response = self.client.auth.sign_in_with_oauth({
                "provider": provider,
                "options": {
                    "redirect_to": f"{os.getenv('FRONTEND_URL', 'http://localhost:3800')}/auth/callback"
                }
            })
            
            return {
                "url": response.url,
                "provider": provider
            }
            
        except Exception as e:
            logger.error(f"OAuth provider error: {e}")
            return {
                "error": str(e)
            }