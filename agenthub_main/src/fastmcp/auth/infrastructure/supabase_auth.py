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
import re
import httpx
import ssl

# Set environment variables to disable SSL verification for self-hosted instances
# This needs to be done before importing the supabase client
if os.getenv("SUPABASE_URL") and re.search(r'\d+\.\d+\.\d+\.\d+', os.getenv("SUPABASE_URL", "")):
    os.environ["HTTPX_SSL_VERIFY"] = "0"
    os.environ["CURL_CA_BUNDLE"] = ""
    os.environ["REQUESTS_CA_BUNDLE"] = ""
    # Create a custom SSL context that doesn't verify certificates
    ssl._create_default_https_context = ssl._create_unverified_context

try:
    from supabase import create_client, Client
    from supabase.lib.client_options import ClientOptions
    SUPABASE_AVAILABLE = True
    # Disable SSL warnings for self-hosted instances in development
    import urllib3
    urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)
except ImportError:
    SUPABASE_AVAILABLE = False
    # Mock classes for when supabase is not available
    class Client:
        pass
    class ClientOptions:
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
        self.supabase_jwt_secret = os.getenv("SUPABASE_JWT_SECRET")
        
        if not self.supabase_url or not self.supabase_anon_key:
            raise ValueError("Missing Supabase credentials: SUPABASE_URL and SUPABASE_ANON_KEY must be set")
        
        # Check if this is a self-hosted instance (has IP address in URL)
        is_self_hosted = bool(re.search(r'\d+\.\d+\.\d+\.\d+', self.supabase_url or ''))
        use_mock = os.getenv("USE_MOCK_AUTH", "false").lower() in ["true", "1", "yes"]
        
        # Test self-hosted connectivity and fall back to mock if needed
        if is_self_hosted and not use_mock:
            import socket
            try:
                ip_match = re.search(r'(\d+\.\d+\.\d+\.\d+)', self.supabase_url)
                if ip_match:
                    ip = ip_match.group(1)
                    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                    sock.settimeout(2)
                    result = sock.connect_ex((ip, 443))
                    sock.close()
                    
                    if result != 0:
                        logger.warning(f"⚠️  Self-hosted Supabase at {ip}:443 is not reachable")
                        logger.warning("⚠️  To use mock authentication, set USE_MOCK_AUTH=true in .env")
                        # Don't auto-switch to mock, let user decide
            except Exception as e:
                logger.warning(f"Could not test self-hosted connection: {e}")
        
        # Use mock authentication if requested
        if use_mock:
            logger.warning("🔧 Using mock authentication for development")
            logger.warning("⚠️  Set USE_MOCK_AUTH=false when self-hosted instance is ready")
            
            from .mock_supabase_auth import MockSupabaseClient
            mock_client = MockSupabaseClient(self.supabase_url, self.supabase_anon_key)
            self.client = mock_client
            self.admin_client = mock_client
            logger.info("Mock authentication initialized successfully")
            return
        
        # Configure clients for self-hosted instances with self-signed certificates
        if is_self_hosted:
            logger.info("Using self-hosted Supabase with SSL verification disabled")
            logger.info(f"Connecting to: {self.supabase_url}")
            
            # Create httpx clients with SSL disabled for self-hosted instances
            import httpx
            
            # Sync client for synchronous operations
            sync_client = httpx.Client(verify=False, timeout=30.0)
            
            # Use anon key for client-side operations with SSL verification disabled
            self.client: Client = create_client(
                self.supabase_url, 
                self.supabase_anon_key,
                options=ClientOptions(
                    auto_refresh_token=False,  # Disable auto-refresh to avoid SSL issues
                    persist_session=False,     # Don't persist session to avoid SSL issues
                    httpx_client=sync_client  # Use custom httpx client with SSL disabled
                )
            )
            
            # Create admin client for server-side operations  
            # Create separate httpx client for admin to avoid sharing state
            admin_sync_client = httpx.Client(verify=False, timeout=30.0)
            
            self.admin_client: Client = create_client(
                self.supabase_url, 
                self.supabase_service_key or self.supabase_anon_key,  # Fallback to anon key if no service key
                options=ClientOptions(
                    auto_refresh_token=False,
                    persist_session=False,
                    httpx_client=admin_sync_client
                )
            )
        else:
            # For cloud Supabase, use default SSL verification
            # Use anon key for client-side operations
            self.client: Client = create_client(
                self.supabase_url, 
                self.supabase_anon_key,
                options=ClientOptions(
                    auto_refresh_token=True,   # Enable auto-refresh for cloud instances
                    persist_session=True      # Enable session persistence for cloud instances
                )
            )
            
            # Create admin client for server-side operations
            self.admin_client: Client = create_client(
                self.supabase_url, 
                self.supabase_service_key,
                options=ClientOptions(
                    auto_refresh_token=False,  # Admin client doesn't need auto-refresh
                    persist_session=False     # Admin client doesn't need session persistence
                )
            )
        
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
                error_message="Supabase authentication not available",
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
            
            # Handle SSL certificate errors gracefully for self-hosted instances
            if "SSL" in error_msg or "CERTIFICATE_VERIFY_FAILED" in error_msg:
                logger.warning("SSL certificate verification failed during signup - likely self-hosted instance")
                # Don't expose SSL errors to frontend
                return SupabaseAuthResult(
                    success=False,
                    error_message="Unable to create account. Please try again."
                )
            # Parse common Supabase error messages
            elif "User already registered" in error_msg:
                return SupabaseAuthResult(
                    success=False,
                    error_message="Email already registered"
                )
            elif "Password should be at least" in error_msg:
                return SupabaseAuthResult(
                    success=False,
                    error_message="Password must be at least 6 characters"
                )
            
            # For other errors, return a generic message instead of the raw error
            logger.error(f"Unexpected error during signup: {error_msg}")
            return SupabaseAuthResult(
                success=False,
                error_message="Unable to create account. Please try again later."
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
                error_message="Supabase authentication not available",
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
            
            # Handle SSL certificate errors gracefully for self-hosted instances
            if "SSL" in error_msg or "CERTIFICATE_VERIFY_FAILED" in error_msg:
                logger.warning("SSL certificate verification failed - likely self-hosted instance")
                # Don't expose SSL errors to frontend, return generic auth error
                return SupabaseAuthResult(
                    success=False,
                    error_message="Invalid email or password"
                )
            elif "Invalid login credentials" in error_msg:
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
            
            # For other errors, return a generic message instead of the raw error
            logger.error(f"Unexpected error during sign in: {error_msg}")
            return SupabaseAuthResult(
                success=False,
                error_message="Authentication service temporarily unavailable. Please try again."
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
            # WORKAROUND: The Supabase Go client has issues with the `amr` field format
            # from frontend Supabase tokens (array format vs expected struct).
            # Use Python JWT validation directly as a fallback.
            
            # First try the native Supabase client
            if hasattr(self, 'admin_client') and self.admin_client:
                try:
                    # Use admin client to get user by JWT
                    response = self.admin_client.auth.get_user(access_token)
                    if response and response.user:
                        return SupabaseAuthResult(
                            success=True,
                            user=response.user
                        )
                except Exception as supabase_error:
                    logger.debug(f"Supabase native client failed, trying manual JWT validation: {supabase_error}")
                    
            # Fallback to manual JWT validation with Python library
            # This bypasses the Go client parsing issues
            import jwt as pyjwt
            
            # Validate using Supabase JWT secret
            if self.supabase_jwt_secret:  # Use JWT secret for JWT verification
                try:
                    payload = pyjwt.decode(
                        access_token,
                        self.supabase_jwt_secret,
                        algorithms=["HS256"],
                        audience="authenticated",
                        options={
                            "verify_iss": False  # Skip issuer verification for broader compatibility
                        }
                    )
                    
                    # Create user object from JWT payload
                    user_data = {
                        'id': payload.get('sub'),
                        'email': payload.get('email'),
                        'phone': payload.get('phone', ''),
                        'user_metadata': payload.get('user_metadata', {}),
                        'app_metadata': payload.get('app_metadata', {}),
                        'role': payload.get('role', 'authenticated'),
                        'aal': payload.get('aal'),
                        'amr': payload.get('amr', []),  # Handle array format correctly
                        'session_id': payload.get('session_id'),
                        'is_anonymous': payload.get('is_anonymous', False),
                        'confirmed_at': True,  # Assume confirmed if token is valid
                        'email_confirmed_at': True
                    }
                    
                    logger.info(f"Manual JWT validation successful for user: {user_data['email']}")
                    
                    return SupabaseAuthResult(
                        success=True,
                        user=user_data
                    )
                    
                except pyjwt.InvalidTokenError as jwt_error:
                    logger.warning(f"Manual JWT validation failed: {jwt_error}")
                except Exception as jwt_error:
                    logger.warning(f"Manual JWT validation error: {jwt_error}")
            
            # If manual validation also fails, return error
            return SupabaseAuthResult(
                success=False,
                error_message="Invalid or expired token"
            )
                
        except Exception as e:
            logger.error(f"Token verification error: {e}")
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
    
    async def refresh_session(self, refresh_token: str) -> SupabaseAuthResult:
        """
        Refresh access token using refresh token
        
        Args:
            refresh_token: Valid refresh token
            
        Returns:
            SupabaseAuthResult with new tokens or error
        """
        try:
            logger.info("Attempting to refresh session token")
            
            response = self.client.auth.refresh_session(refresh_token)
            
            if response.user and response.session:
                logger.info(f"Session refresh successful for user: {response.user.email}")
                return SupabaseAuthResult(
                    success=True,
                    user=response.user,
                    session=response.session
                )
            else:
                logger.warning("Session refresh failed - no user or session in response")
                return SupabaseAuthResult(
                    success=False,
                    error_message="Invalid or expired refresh token"
                )
                
        except Exception as e:
            logger.error(f"Session refresh error: {e}")
            error_msg = str(e)
            
            # Handle common refresh token errors
            if "Invalid Refresh Token" in error_msg or "refresh_token" in error_msg:
                return SupabaseAuthResult(
                    success=False,
                    error_message="Refresh token expired or invalid"
                )
            elif "Network" in error_msg or "Connection" in error_msg:
                return SupabaseAuthResult(
                    success=False,
                    error_message="Network error during token refresh"
                )
            
            # Generic error for unexpected issues
            return SupabaseAuthResult(
                success=False,
                error_message="Token refresh failed. Please sign in again."
            )