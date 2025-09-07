"""
Auth API Controller

This controller handles authentication operations following DDD architecture.
It centralizes authentication logic that was previously scattered in routes.
"""

import logging
import os
from typing import Optional, Dict, Any
from sqlalchemy.orm import Session

from fastmcp.auth.domain.entities.user import User
from ...application.facades.auth_application_facade import AuthApplicationFacade
# Using facade for proper DDD layering - no direct repository or service access

logger = logging.getLogger(__name__)


class AuthAPIController:
    """
    API Controller for authentication operations.
    
    This controller provides authentication services following DDD principles,
    ensuring proper separation of concerns and delegating to application facade.
    """
    
    def __init__(self):
        """Initialize the auth controller"""
        self._auth_facade = None  # Lazy initialization to avoid circular dependency
    
    def verify_jwt_token(self, token: str, session: Session) -> Optional[User]:
        """
        Verify a JWT token and return the associated user.
        
        This method handles both API tokens and access tokens,
        following DDD by delegating to the application facade.
        
        Args:
            token: JWT token to verify
            session: Database session
            
        Returns:
            User object if token is valid, None otherwise
        """
        try:
            # Initialize facade if not already done (lazy initialization)
            if not self._auth_facade:
                self._auth_facade = AuthApplicationFacade(session)
            
            # Delegate to facade for proper DDD layering
            return self._auth_facade.verify_jwt_token(token)
            
        except Exception as e:
            logger.debug(f"JWT verification failed: {e}")
            return None
    
    async def dual_authenticate(self, token: str, session: Session) -> Optional[User]:
        """
        Perform dual authentication supporting both Supabase and local JWT.
        
        This centralizes the dual authentication logic that was previously in routes,
        following DDD principles by delegating to the application facade.
        
        Args:
            token: Authentication token
            session: Database session
            
        Returns:
            User object if authentication successful, None otherwise
        """
        if not token:
            logger.debug("No authentication token provided")
            return None
        
        # Initialize facade if not already done (lazy initialization)
        if not self._auth_facade:
            self._auth_facade = AuthApplicationFacade(session)
        
        # Delegate to facade for proper DDD layering
        return await self._auth_facade.dual_authenticate(token)
    
    def extract_token_from_headers(self, headers: dict) -> Optional[str]:
        """
        Extract authentication token from request headers.
        
        Note: This is a utility method that doesn't need facade delegation
        as it only deals with header parsing, not domain logic.
        
        Args:
            headers: Request headers dictionary
            
        Returns:
            Token string if found, None otherwise
        """
        auth_header = headers.get('authorization', '')
        
        if auth_header.startswith('Bearer '):
            token = auth_header[7:].strip()
            logger.debug("Found Bearer token in Authorization header")
            return token
        
        # Check X-API-Token header (legacy support)
        api_token = headers.get("x-api-token")
        if api_token:
            return api_token
        
        return None
    
    def extract_token_from_cookies(self, cookies: dict) -> Optional[str]:
        """
        Extract authentication token from cookies.
        
        Note: This is a utility method that doesn't need facade delegation
        as it only deals with cookie parsing, not domain logic.
        
        Args:
            cookies: Request cookies dictionary
            
        Returns:
            Token string if found, None otherwise
        """
        access_token = cookies.get('access_token')
        if access_token:
            logger.debug("Found access_token in cookies")
            return access_token
        
        return None