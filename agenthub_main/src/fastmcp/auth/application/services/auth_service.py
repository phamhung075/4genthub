"""
Authentication Service - Application Layer

This service orchestrates authentication operations including registration,
login, password management, and token handling.
"""

import logging
from datetime import datetime, timezone
from typing import Optional, Dict, Any, Tuple
from dataclasses import dataclass

from ...domain.entities.user import User, UserStatus
from ...domain.services.password_service import PasswordService
from ...domain.services.jwt_service import JWTService
from ...domain.value_objects.email import Email
from ...domain.value_objects.user_id import UserId

logger = logging.getLogger(__name__)


@dataclass
class LoginResult:
    """Result of a login attempt"""
    success: bool
    user: Optional[User] = None
    access_token: Optional[str] = None
    refresh_token: Optional[str] = None
    error_message: Optional[str] = None
    requires_email_verification: bool = False


@dataclass
class RegistrationResult:
    """Result of a registration attempt"""
    success: bool
    user: Optional[User] = None
    verification_token: Optional[str] = None
    error_message: Optional[str] = None


class AuthService:
    """
    Authentication service for user management
    
    This service handles user registration, login, password management,
    and token operations.
    """
    
    def __init__(self,
                 user_repository,  # Will be implemented next
                 jwt_service: JWTService,
                 password_service: Optional[PasswordService] = None):
        """
        Initialize authentication service
        
        Args:
            user_repository: Repository for user persistence
            jwt_service: Service for JWT operations
            password_service: Service for password operations
        """
        self.user_repository = user_repository
        self.jwt_service = jwt_service
        self.password_service = password_service or PasswordService()
    
    async def register_user(self,
                          email: str,
                          username: str,
                          password: str,
                          full_name: Optional[str] = None) -> RegistrationResult:
        """
        Register a new user
        
        Args:
            email: User's email address
            username: Unique username
            password: Plain text password
            full_name: User's full name (optional)
            
        Returns:
            RegistrationResult with user and verification token
        """
        try:
            # Validate email
            email_obj = Email(email)
            
            # Check if email already exists
            existing_user = await self.user_repository.get_by_email(email)
            if existing_user:
                return RegistrationResult(
                    success=False,
                    error_message="Email already registered"
                )
            
            # Check if username already exists
            existing_user = await self.user_repository.get_by_username(username)
            if existing_user:
                return RegistrationResult(
                    success=False,
                    error_message="Username already taken"
                )
            
            # Check password strength
            strength = self.password_service.check_password_strength(password)
            if strength["strength"] == "weak":
                suggestions = ", ".join(strength["suggestions"])
                return RegistrationResult(
                    success=False,
                    error_message=f"Password too weak. {suggestions}"
                )
            
            # Hash password
            password_hash = self.password_service.hash_password(password)
            
            # Create user entity
            user = User(
                id=str(UserId.generate()),
                email=email,
                username=username,
                password_hash=password_hash,
                full_name=full_name,
                status=UserStatus.PENDING_VERIFICATION,
                email_verified=False
            )
            
            # Save user to repository
            saved_user = await self.user_repository.save(user)
            
            # Generate email verification token
            verification_token = self.jwt_service.create_reset_token(
                saved_user.id,
                saved_user.email
            )
            
            # Log successful registration
            logger.info(f"User registered successfully: {username}")
            
            return RegistrationResult(
                success=True,
                user=saved_user,
                verification_token=verification_token
            )
            
        except Exception as e:
            logger.error(f"Registration failed: {e}")
            return RegistrationResult(
                success=False,
                error_message=f"Registration failed: {str(e)}"
            )
    
    async def login(self,
                   email_or_username: str,
                   password: str,
                   ip_address: Optional[str] = None) -> LoginResult:
        """
        Authenticate user and generate tokens
        
        Args:
            email_or_username: Email or username
            password: Plain text password
            ip_address: Client IP address for audit
            
        Returns:
            LoginResult with tokens if successful
        """
        try:
            # Find user by email or username
            if "@" in email_or_username:
                user = await self.user_repository.get_by_email(email_or_username)
            else:
                user = await self.user_repository.get_by_username(email_or_username)
            
            if not user:
                return LoginResult(
                    success=False,
                    error_message="Invalid credentials"
                )
            
            # Check if account can login
            if not user.can_login():
                if user.is_locked():
                    return LoginResult(
                        success=False,
                        error_message="Account temporarily locked due to failed login attempts"
                    )
                elif user.status == UserStatus.SUSPENDED:
                    return LoginResult(
                        success=False,
                        error_message="Account suspended"
                    )
                else:
                    return LoginResult(
                        success=False,
                        error_message="Account not active"
                    )
            
            # Verify password
            if not self.password_service.verify_password(password, user.password_hash):
                # Record failed attempt
                user.record_failed_login()
                await self.user_repository.save(user)
                
                return LoginResult(
                    success=False,
                    error_message="Invalid credentials"
                )
            
            # Check if email verification required
            if not user.email_verified:
                return LoginResult(
                    success=False,
                    requires_email_verification=True,
                    error_message="Email verification required"
                )
            
            # Check if password needs rehashing
            if self.password_service.needs_rehash(user.password_hash):
                # Rehash with current settings
                user.password_hash = self.password_service.hash_password(password)
            
            # Record successful login
            user.record_successful_login()
            
            # Generate tokens
            access_token = self.jwt_service.create_access_token(
                user_id=user.id,
                email=user.email,
                roles=[r.value if hasattr(r, 'value') else r for r in user.roles]
            )
            
            refresh_token, token_family = self.jwt_service.create_refresh_token(
                user_id=user.id,
                token_family=user.refresh_token_family,
                token_version=user.refresh_token_version
            )
            
            # Update user's refresh token info
            user.refresh_token_family = token_family
            
            # Save updated user
            await self.user_repository.save(user)
            
            # Log successful login
            logger.info(f"User logged in: {user.username}")
            
            return LoginResult(
                success=True,
                user=user,
                access_token=access_token,
                refresh_token=refresh_token
            )
            
        except Exception as e:
            logger.error(f"Login failed: {e}")
            return LoginResult(
                success=False,
                error_message="Login failed"
            )
    
    async def verify_email(self, token: str) -> Tuple[bool, Optional[str]]:
        """
        Verify user's email with token
        
        Args:
            token: Email verification token
            
        Returns:
            Tuple of (success, error_message)
        """
        try:
            # Verify token
            payload = self.jwt_service.verify_reset_token(token)
            if not payload:
                return False, "Invalid or expired verification token"
            
            # Get user
            user_id = payload.get("sub")
            user = await self.user_repository.get_by_id(user_id)
            if not user:
                return False, "User not found"
            
            # Verify email
            user.verify_email()
            
            # Save updated user
            await self.user_repository.save(user)
            
            logger.info(f"Email verified for user: {user.username}")
            return True, None
            
        except Exception as e:
            logger.error(f"Email verification failed: {e}")
            return False, "Email verification failed"
    
    async def request_password_reset(self, email: str) -> Tuple[bool, Optional[str], Optional[str]]:
        """
        Request password reset
        
        Args:
            email: User's email address
            
        Returns:
            Tuple of (success, reset_token, error_message)
        """
        try:
            # Find user
            user = await self.user_repository.get_by_email(email)
            if not user:
                # Don't reveal if email exists
                logger.info(f"Password reset requested for non-existent email: {email}")
                return True, None, None
            
            # Generate reset token
            reset_token = self.password_service.generate_reset_token()
            jwt_token = self.jwt_service.create_reset_token(user.id, user.email)
            
            # Store reset token
            user.initiate_password_reset(reset_token)
            await self.user_repository.save(user)
            
            logger.info(f"Password reset requested for user: {user.username}")
            return True, jwt_token, None
            
        except Exception as e:
            logger.error(f"Password reset request failed: {e}")
            return False, None, "Password reset request failed"
    
    async def reset_password(self, token: str, new_password: str) -> Tuple[bool, Optional[str]]:
        """
        Reset user password with token
        
        Args:
            token: Password reset token
            new_password: New password
            
        Returns:
            Tuple of (success, error_message)
        """
        try:
            # Verify token
            payload = self.jwt_service.verify_reset_token(token)
            if not payload:
                return False, "Invalid or expired reset token"
            
            # Get user
            user_id = payload.get("sub")
            user = await self.user_repository.get_by_id(user_id)
            if not user:
                return False, "User not found"
            
            # Check password strength
            strength = self.password_service.check_password_strength(new_password)
            if strength["strength"] == "weak":
                suggestions = ", ".join(strength["suggestions"])
                return False, f"Password too weak. {suggestions}"
            
            # Hash new password
            password_hash = self.password_service.hash_password(new_password)
            
            # Update password
            user.complete_password_reset(password_hash)
            await self.user_repository.save(user)
            
            logger.info(f"Password reset for user: {user.username}")
            return True, None
            
        except Exception as e:
            logger.error(f"Password reset failed: {e}")
            return False, "Password reset failed"
    
    async def refresh_tokens(self, refresh_token: str) -> Optional[Tuple[str, str]]:
        """
        Refresh access and refresh tokens
        
        Args:
            refresh_token: Valid refresh token
            
        Returns:
            Tuple of (new_access_token, new_refresh_token) if successful
        """
        try:
            # Verify refresh token
            payload = self.jwt_service.verify_refresh_token(refresh_token)
            if not payload:
                return None
            
            # Get user
            user_id = payload.get("sub")
            user = await self.user_repository.get_by_id(user_id)
            if not user:
                return None
            
            # Validate token family and version
            token_family = payload.get("family")
            token_version = payload.get("version", 0)
            
            if (user.refresh_token_family != token_family or 
                user.refresh_token_version > token_version):
                # Token has been rotated or revoked
                logger.warning(f"Invalid refresh token version for user: {user.username}")
                return None
            
            # Generate new tokens
            access_token = self.jwt_service.create_access_token(
                user_id=user.id,
                email=user.email,
                roles=[r.value if hasattr(r, 'value') else r for r in user.roles]
            )
            
            new_refresh_token, _ = self.jwt_service.create_refresh_token(
                user_id=user.id,
                token_family=token_family,
                token_version=user.refresh_token_version + 1
            )
            
            # Update token version
            user.refresh_token_version += 1
            await self.user_repository.save(user)
            
            return access_token, new_refresh_token
            
        except Exception as e:
            logger.error(f"Token refresh failed: {e}")
            return None
    
    async def logout(self, user_id: str, revoke_all_tokens: bool = False) -> bool:
        """
        Logout user and optionally revoke all tokens
        
        Args:
            user_id: User ID to logout
            revoke_all_tokens: Whether to revoke all refresh tokens
            
        Returns:
            True if successful
        """
        try:
            user = await self.user_repository.get_by_id(user_id)
            if not user:
                return False
            
            if revoke_all_tokens:
                # Increment version to invalidate all tokens
                user.refresh_token_version += 1
                await self.user_repository.save(user)
            
            logger.info(f"User logged out: {user.username}")
            return True
            
        except Exception as e:
            logger.error(f"Logout failed: {e}")
            return False
    
    async def get_current_user(self, access_token: str) -> Optional[User]:
        """
        Get current user from access token
        
        Args:
            access_token: Valid access token
            
        Returns:
            User if token is valid
        """
        try:
            # Verify token
            payload = self.jwt_service.verify_access_token(access_token)
            if not payload:
                return None
            
            # Get user
            user_id = payload.get("sub")
            return await self.user_repository.get_by_id(user_id)
            
        except Exception as e:
            logger.error(f"Get current user failed: {e}")
            return None