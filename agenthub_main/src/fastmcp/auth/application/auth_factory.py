"""
Authentication Factory

Factory pattern for creating authentication providers based on environment configuration.
Supports Supabase, Keycloak, and Local auth providers.
"""

import os
import logging
from abc import ABC, abstractmethod
from typing import Optional, Dict, Any, Tuple
from enum import Enum
from pydantic import BaseModel

logger = logging.getLogger(__name__)


class AuthProvider(Enum):
    """Supported authentication providers"""
    SUPABASE = "supabase"
    KEYCLOAK = "keycloak"
    LOCAL = "local"


class AuthResult(BaseModel):
    """Unified authentication result"""
    success: bool
    error_message: Optional[str] = None
    user: Optional[Dict[str, Any]] = None
    access_token: Optional[str] = None
    refresh_token: Optional[str] = None
    requires_email_verification: bool = False
    expires_in: int = 900  # 15 minutes default


class AuthServiceInterface(ABC):
    """Abstract interface for authentication services"""
    
    @abstractmethod
    async def sign_up(self, email: str, password: str, username: Optional[str] = None, 
                     full_name: Optional[str] = None, **kwargs) -> AuthResult:
        """Register a new user"""
        pass
    
    @abstractmethod
    async def sign_in(self, email: str, password: str) -> AuthResult:
        """Sign in an existing user"""
        pass
    
    @abstractmethod
    async def sign_out(self, access_token: str) -> bool:
        """Sign out a user"""
        pass
    
    @abstractmethod
    async def refresh_token(self, refresh_token: str) -> AuthResult:
        """Refresh access token"""
        pass
    
    @abstractmethod
    async def verify_token(self, access_token: str) -> AuthResult:
        """Verify token and get user info"""
        pass
    
    @abstractmethod
    async def reset_password_request(self, email: str) -> AuthResult:
        """Request password reset"""
        pass
    
    @abstractmethod
    async def reset_password_confirm(self, token: str, new_password: str) -> AuthResult:
        """Confirm password reset"""
        pass


class SupabaseAuthAdapter(AuthServiceInterface):
    """Supabase authentication adapter"""
    
    def __init__(self):
        from ..infrastructure.supabase_auth import SupabaseAuthService
        self.service = SupabaseAuthService()
    
    async def sign_up(self, email: str, password: str, username: Optional[str] = None, 
                     full_name: Optional[str] = None, **kwargs) -> AuthResult:
        """Register with Supabase"""
        try:
            metadata = {}
            if username:
                metadata["username"] = username
            if full_name:
                metadata["full_name"] = full_name
            
            result = await self.service.sign_up(email, password, metadata)
            
            return AuthResult(
                success=result.success,
                error_message=result.error_message,
                user=self._format_user(result.user) if result.user else None,
                access_token=getattr(result.session, 'access_token', None) if result.session else None,
                refresh_token=getattr(result.session, 'refresh_token', None) if result.session else None,
                requires_email_verification=result.requires_email_verification
            )
        except Exception as e:
            logger.error(f"Supabase signup error: {e}")
            return AuthResult(success=False, error_message="Registration failed")
    
    async def sign_in(self, email: str, password: str) -> AuthResult:
        """Sign in with Supabase"""
        try:
            result = await self.service.sign_in(email, password)
            
            return AuthResult(
                success=result.success,
                error_message=result.error_message,
                user=self._format_user(result.user) if result.user else None,
                access_token=getattr(result.session, 'access_token', None) if result.session else None,
                refresh_token=getattr(result.session, 'refresh_token', None) if result.session else None,
                requires_email_verification=result.requires_email_verification
            )
        except Exception as e:
            logger.error(f"Supabase signin error: {e}")
            return AuthResult(success=False, error_message="Sign in failed")
    
    async def sign_out(self, access_token: str) -> bool:
        """Sign out with Supabase"""
        try:
            return await self.service.sign_out(access_token)
        except Exception as e:
            logger.error(f"Supabase signout error: {e}")
            return False
    
    async def refresh_token(self, refresh_token: str) -> AuthResult:
        """Refresh token with Supabase"""
        try:
            # Supabase handles token refresh automatically, but we need to implement manual refresh
            result = await self.service.refresh_session(refresh_token)
            
            return AuthResult(
                success=result.success,
                error_message=result.error_message,
                user=self._format_user(result.user) if result.user else None,
                access_token=getattr(result.session, 'access_token', None) if result.session else None,
                refresh_token=getattr(result.session, 'refresh_token', None) if result.session else None
            )
        except Exception as e:
            logger.error(f"Supabase token refresh error: {e}")
            return AuthResult(success=False, error_message="Token refresh failed")
    
    async def verify_token(self, access_token: str) -> AuthResult:
        """Verify token with Supabase"""
        try:
            result = await self.service.verify_token(access_token)
            
            return AuthResult(
                success=result.success,
                error_message=result.error_message,
                user=self._format_user(result.user) if result.user else None,
                access_token=access_token  # Return the same token
            )
        except Exception as e:
            logger.error(f"Supabase token verification error: {e}")
            return AuthResult(success=False, error_message="Token verification failed")
    
    async def reset_password_request(self, email: str) -> AuthResult:
        """Request password reset with Supabase"""
        try:
            result = await self.service.reset_password_request(email)
            
            return AuthResult(
                success=result.success,
                error_message=result.error_message
            )
        except Exception as e:
            logger.error(f"Supabase password reset request error: {e}")
            return AuthResult(success=False, error_message="Password reset request failed")
    
    async def reset_password_confirm(self, token: str, new_password: str) -> AuthResult:
        """Confirm password reset with Supabase"""
        try:
            result = await self.service.update_password(token, new_password)
            
            return AuthResult(
                success=result.success,
                error_message=result.error_message
            )
        except Exception as e:
            logger.error(f"Supabase password reset confirm error: {e}")
            return AuthResult(success=False, error_message="Password reset failed")
    
    def _format_user(self, user) -> Optional[Dict[str, Any]]:
        """Format Supabase user for unified response"""
        if not user:
            return None
        
        return {
            "id": getattr(user, "id", None),
            "email": getattr(user, "email", None),
            "username": getattr(user, "user_metadata", {}).get("username"),
            "full_name": getattr(user, "user_metadata", {}).get("full_name"),
            "email_verified": getattr(user, "confirmed_at", None) is not None,
            "created_at": str(getattr(user, "created_at", "")),
            "roles": ["user"]  # Default role for Supabase users
        }


class KeycloakAuthAdapter(AuthServiceInterface):
    """Keycloak authentication adapter"""
    
    def __init__(self):
        # Initialize with existing Keycloak authentication implementation
        try:
            from fastmcp.auth.keycloak_auth import KeycloakAuth
            self.keycloak = KeycloakAuth()
            logger.info("Keycloak authentication adapter initialized with KeycloakAuth service")
        except Exception as e:
            logger.error(f"Failed to initialize KeycloakAuth: {e}")
            self.keycloak = None
    
    async def sign_up(self, email: str, password: str, username: Optional[str] = None, 
                     full_name: Optional[str] = None, **kwargs) -> AuthResult:
        """Register with Keycloak"""
        # TODO: Implement Keycloak user creation
        logger.warning("Keycloak signup not implemented yet")
        return AuthResult(success=False, error_message="Keycloak signup not implemented")
    
    async def sign_in(self, email: str, password: str) -> AuthResult:
        """Sign in with Keycloak"""
        if not self.keycloak:
            return AuthResult(success=False, error_message="Keycloak service not available")
        
        try:
            # Use email as username for Keycloak login
            result = await self.keycloak.login(email, password)
            
            if result.success:
                # Convert Keycloak AuthResult to our unified AuthResult
                user_data = None
                if result.user and isinstance(result.user, dict):
                    user_data = {
                        'id': result.user.get('sub') or result.user.get('id', email),
                        'email': result.user.get('email', email), 
                        'username': result.user.get('preferred_username', email.split('@')[0]),
                        'roles': getattr(result, 'roles', None) or ['user']
                    }
                elif result.user:
                    # Handle case where result.user is not a dict
                    user_data = {
                        'id': str(result.user),
                        'email': email,
                        'username': email.split('@')[0], 
                        'roles': getattr(result, 'roles', None) or ['user']
                    }
                
                return AuthResult(
                    success=True,
                    user=user_data,
                    access_token=getattr(result, 'access_token', None),
                    refresh_token=getattr(result, 'refresh_token', None)
                )
            else:
                return AuthResult(success=False, error_message=getattr(result, 'error', None) or "Invalid credentials")
                
        except Exception as e:
            logger.error(f"Keycloak signin error: {e}")
            return AuthResult(success=False, error_message="Authentication failed")
    
    async def sign_out(self, access_token: str) -> bool:
        """Sign out with Keycloak"""
        # TODO: Implement Keycloak logout
        logger.warning("Keycloak signout not implemented yet")
        return False
    
    async def refresh_token(self, refresh_token: str) -> AuthResult:
        """Refresh token with Keycloak"""
        # TODO: Implement Keycloak token refresh
        logger.warning("Keycloak token refresh not implemented yet")
        return AuthResult(success=False, error_message="Keycloak token refresh not implemented")
    
    async def verify_token(self, access_token: str) -> AuthResult:
        """Verify token with Keycloak"""
        # TODO: Implement Keycloak token verification
        logger.warning("Keycloak token verification not implemented yet")
        return AuthResult(success=False, error_message="Keycloak token verification not implemented")
    
    async def reset_password_request(self, email: str) -> AuthResult:
        """Request password reset with Keycloak"""
        # TODO: Implement Keycloak password reset request
        logger.warning("Keycloak password reset not implemented yet")
        return AuthResult(success=False, error_message="Keycloak password reset not implemented")
    
    async def reset_password_confirm(self, token: str, new_password: str) -> AuthResult:
        """Confirm password reset with Keycloak"""
        # TODO: Implement Keycloak password reset confirm
        logger.warning("Keycloak password reset confirm not implemented yet")
        return AuthResult(success=False, error_message="Keycloak password reset confirm not implemented")


class LocalAuthAdapter(AuthServiceInterface):
    """Local authentication adapter (using existing local auth service)"""
    
    def __init__(self):
        # Import local auth service
        from ..application.services.auth_service import AuthService
        from ..domain.services.jwt_service import JWTService
        from ..infrastructure.repositories.user_repository import UserRepository
        
        # Initialize dependencies
        JWT_SECRET_KEY = os.getenv("JWT_SECRET_KEY", "your-secret-key-change-in-production")
        self.jwt_service = JWTService(JWT_SECRET_KEY)
        
        # Get database session
        from ...task_management.infrastructure.database.database_config import DatabaseConfig
        self.db_config = DatabaseConfig()
        
    def _get_auth_service(self):
        """Get auth service with fresh DB session"""
        from ..infrastructure.repositories.user_repository import UserRepository
        from ..application.services.auth_service import AuthService
        
        db = self.db_config.SessionLocal()
        try:
            user_repository = UserRepository(db)
            return AuthService(user_repository, self.jwt_service), db
        except Exception:
            db.close()
            raise
    
    async def sign_up(self, email: str, password: str, username: Optional[str] = None, 
                     full_name: Optional[str] = None, **kwargs) -> AuthResult:
        """Register with local auth"""
        try:
            auth_service, db = self._get_auth_service()
            try:
                result = await auth_service.register_user(email, username or email.split('@')[0], password, full_name)
                
                return AuthResult(
                    success=result.success,
                    error_message=result.error_message,
                    requires_email_verification=True  # Local auth requires email verification
                )
            finally:
                db.close()
        except Exception as e:
            logger.error(f"Local auth signup error: {e}")
            return AuthResult(success=False, error_message="Registration failed")
    
    async def sign_in(self, email: str, password: str) -> AuthResult:
        """Sign in with local auth"""
        try:
            auth_service, db = self._get_auth_service()
            try:
                result = await auth_service.login(email, password)
                
                return AuthResult(
                    success=result.success,
                    error_message=result.error_message,
                    access_token=result.access_token,
                    refresh_token=result.refresh_token,
                    requires_email_verification=result.requires_email_verification,
                    expires_in=900
                )
            finally:
                db.close()
        except Exception as e:
            logger.error(f"Local auth signin error: {e}")
            return AuthResult(success=False, error_message="Sign in failed")
    
    async def sign_out(self, access_token: str) -> bool:
        """Sign out with local auth"""
        try:
            auth_service, db = self._get_auth_service()
            try:
                # Extract user ID from token
                user_id = self.jwt_service.decode_token(access_token).get("sub")
                if user_id:
                    return await auth_service.logout(user_id, revoke_all_tokens=True)
                return False
            finally:
                db.close()
        except Exception as e:
            logger.error(f"Local auth signout error: {e}")
            return False
    
    async def refresh_token(self, refresh_token: str) -> AuthResult:
        """Refresh token with local auth"""
        try:
            auth_service, db = self._get_auth_service()
            try:
                tokens = await auth_service.refresh_tokens(refresh_token)
                if tokens:
                    access_token, new_refresh_token = tokens
                    return AuthResult(
                        success=True,
                        access_token=access_token,
                        refresh_token=new_refresh_token,
                        expires_in=900
                    )
                return AuthResult(success=False, error_message="Token refresh failed")
            finally:
                db.close()
        except Exception as e:
            logger.error(f"Local auth token refresh error: {e}")
            return AuthResult(success=False, error_message="Token refresh failed")
    
    async def verify_token(self, access_token: str) -> AuthResult:
        """Verify token with local auth"""
        try:
            payload = self.jwt_service.decode_token(access_token)
            if payload:
                return AuthResult(
                    success=True,
                    user={
                        "id": payload.get("sub"),
                        "email": payload.get("email"),
                        "username": payload.get("username"),
                        "roles": payload.get("roles", ["user"])
                    },
                    access_token=access_token
                )
            return AuthResult(success=False, error_message="Invalid token")
        except Exception as e:
            logger.error(f"Local auth token verification error: {e}")
            return AuthResult(success=False, error_message="Token verification failed")
    
    async def reset_password_request(self, email: str) -> AuthResult:
        """Request password reset with local auth"""
        try:
            auth_service, db = self._get_auth_service()
            try:
                success, token, error = await auth_service.request_password_reset(email)
                return AuthResult(
                    success=success,
                    error_message=error
                )
            finally:
                db.close()
        except Exception as e:
            logger.error(f"Local auth password reset request error: {e}")
            return AuthResult(success=False, error_message="Password reset request failed")
    
    async def reset_password_confirm(self, token: str, new_password: str) -> AuthResult:
        """Confirm password reset with local auth"""
        try:
            auth_service, db = self._get_auth_service()
            try:
                success, error_message = await auth_service.reset_password(token, new_password)
                return AuthResult(
                    success=success,
                    error_message=error_message
                )
            finally:
                db.close()
        except Exception as e:
            logger.error(f"Local auth password reset confirm error: {e}")
            return AuthResult(success=False, error_message="Password reset failed")


class AuthFactory:
    """Factory for creating authentication providers"""
    
    _instances: Dict[AuthProvider, AuthServiceInterface] = {}
    
    @classmethod
    def create_auth_service(cls, provider: Optional[AuthProvider] = None) -> AuthServiceInterface:
        """
        Create authentication service based on provider or environment configuration
        
        Args:
            provider: Specific provider to use (overrides environment)
            
        Returns:
            AuthServiceInterface implementation
        """
        if provider is None:
            # Get from environment
            provider_str = os.getenv("AUTH_PROVIDER", "local").lower()
            try:
                provider = AuthProvider(provider_str)
            except ValueError:
                logger.warning(f"Unknown AUTH_PROVIDER '{provider_str}', defaulting to local")
                provider = AuthProvider.LOCAL
        
        # Use singleton pattern for each provider
        if provider not in cls._instances:
            if provider == AuthProvider.SUPABASE:
                cls._instances[provider] = SupabaseAuthAdapter()
            elif provider == AuthProvider.KEYCLOAK:
                cls._instances[provider] = KeycloakAuthAdapter()
            else:  # LOCAL
                cls._instances[provider] = LocalAuthAdapter()
        
        return cls._instances[provider]
    
    @classmethod
    def get_current_provider(cls) -> AuthProvider:
        """Get the currently configured auth provider"""
        provider_str = os.getenv("AUTH_PROVIDER", "local").lower()
        try:
            return AuthProvider(provider_str)
        except ValueError:
            return AuthProvider.LOCAL
    
    @classmethod
    def is_provider_available(cls, provider: AuthProvider) -> bool:
        """Check if a provider is properly configured"""
        if provider == AuthProvider.SUPABASE:
            return bool(os.getenv("SUPABASE_URL") and os.getenv("SUPABASE_ANON_KEY"))
        elif provider == AuthProvider.KEYCLOAK:
            return bool(os.getenv("KEYCLOAK_URL") and 
                       os.getenv("KEYCLOAK_CLIENT_ID") and 
                       os.getenv("KEYCLOAK_CLIENT_SECRET"))
        else:  # LOCAL
            return bool(os.getenv("JWT_SECRET_KEY"))