"""
Auth Application Facade

This facade handles authentication operations following DDD architecture.
It provides a clean interface between the API controllers and the domain/infrastructure layers,
ensuring proper separation of concerns and no direct database access from controllers.
"""

import logging
import os
from typing import Optional
from sqlalchemy.orm import Session

from fastmcp.auth.domain.entities.user import User
from fastmcp.auth.domain.services.jwt_service import JWTService
from fastmcp.auth.application.services.auth_service import AuthService
from fastmcp.auth.infrastructure.repositories.user_repository import UserRepository

logger = logging.getLogger(__name__)


class AuthApplicationFacade:
    """
    Application facade for authentication operations.
    
    This facade orchestrates authentication operations across domain services and repositories,
    ensuring proper DDD layering and no direct database access from upper layers.
    """
    
    def __init__(self, session: Session):
        """
        Initialize the auth facade with required services and repositories.
        
        Args:
            session: Database session for repository creation
        """
        jwt_secret = os.getenv("JWT_SECRET_KEY", "default-secret-key-change-in-production")
        self.jwt_service = JWTService(secret_key=jwt_secret)
        
        # Create repository through proper dependency injection
        user_repository = UserRepository(session)
        
        # Create auth service with injected dependencies
        self.auth_service = AuthService(
            user_repository=user_repository,
            jwt_service=self.jwt_service
        )
    
    def verify_jwt_token(self, token: str) -> Optional[User]:
        """
        Verify a JWT token and return the associated user.
        
        This method handles both API tokens and access tokens,
        following DDD by delegating to domain services.
        
        Args:
            token: JWT token to verify
            
        Returns:
            User object if token is valid, None otherwise
        """
        try:
            # Try API token validation first
            payload = self.jwt_service.verify_token(token, expected_type="api_token")
            
            if not payload:
                # Try access token as fallback
                payload = self.jwt_service.verify_token(token, expected_type="access")
            
            if payload:
                user_id = payload.get('user_id')
                if user_id:
                    # Use auth service to get user (proper DDD delegation)
                    user = self.auth_service.user_repository.find_by_id(user_id)
                    if user:
                        logger.info(f"✅ Authenticated via JWT: {user.email if hasattr(user, 'email') else user_id}")
                        return user
                    else:
                        logger.warning(f"User not found for ID: {user_id}")
            
            return None
            
        except Exception as e:
            logger.debug(f"JWT verification failed: {e}")
            return None
    
    async def dual_authenticate(self, token: str) -> Optional[User]:
        """
        Perform dual authentication supporting both Supabase and local JWT.
        
        This centralizes the dual authentication logic following DDD principles.
        
        Args:
            token: Authentication token
            
        Returns:
            User object if authentication successful, None otherwise
        """
        if not token:
            logger.debug("No authentication token provided")
            return None
        
        # First try Supabase authentication if enabled
        if os.getenv("SUPABASE_ENABLED", "false").lower() == "true":
            try:
                from fastmcp.auth.infrastructure.supabase_client import get_supabase_client
                
                supabase = get_supabase_client()
                if supabase:
                    # Verify the Supabase token
                    user_data = supabase.auth.get_user(token)
                    if user_data and user_data.user:
                        # Find or create user in our database
                        user = self.auth_service.find_or_create_from_supabase(user_data.user)
                        if user:
                            logger.info(f"✅ Authenticated via Supabase: {user.email}")
                            return user
            except Exception as e:
                logger.debug(f"Supabase authentication failed: {e}")
        
        # Fall back to local JWT authentication
        return self.verify_jwt_token(token)
    
    def extract_token_from_headers(self, headers: dict) -> Optional[str]:
        """
        Extract authentication token from request headers.
        
        Args:
            headers: Request headers dictionary
            
        Returns:
            Token string if found, None otherwise
        """
        # Check Authorization header
        auth_header = headers.get("authorization")
        if auth_header and auth_header.startswith("Bearer "):
            return auth_header.replace("Bearer ", "", 1)
        
        # Check X-API-Token header (legacy support)
        api_token = headers.get("x-api-token")
        if api_token:
            return api_token
        
        return None
    
    def extract_token_from_cookies(self, cookies: dict) -> Optional[str]:
        """
        Extract authentication token from cookies.
        
        Args:
            cookies: Request cookies dictionary
            
        Returns:
            Token string if found, None otherwise
        """
        # Check for access token in cookies
        return cookies.get("access_token")