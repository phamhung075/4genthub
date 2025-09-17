"""Main Authentication Service

This service handles user authentication by extracting user_id from Keycloak JWT tokens.
Keycloak is the single source of truth for user authentication.
"""

import os
import logging
from typing import Optional

from .....domain.constants import validate_user_id
from .....domain.exceptions.authentication_exceptions import UserAuthenticationRequiredError
from .token_extraction_service import TokenExtractionService

logger = logging.getLogger(__name__)


class AuthenticationService:
    """Main authentication service for MCP controllers - Keycloak-only authentication"""
    
    def __init__(self):
        self.token_service = TokenExtractionService()
        # Check for testing mode
        self.auth_enabled = os.getenv("AUTH_ENABLED", "true").lower() in ["true", "1", "yes"]
        self.auth_mode = os.getenv("MCP_AUTH_MODE", "production").lower()
        self.test_user_id = os.getenv("TEST_USER_ID", "test-user-001")
    
    def get_authenticated_user_id(
        self, 
        provided_user_id: Optional[str] = None, 
        operation_name: str = "Operation"
    ) -> str:
        """
        Get authenticated user ID from Keycloak authentication.
        
        This function extracts user_id from:
        1. Testing mode bypass (if MCP_AUTH_MODE=testing or AUTH_ENABLED=false)
        2. Provided user_id parameter (passed from HTTP server Keycloak authentication)
        3. Request context middleware (fallback)
        
        Keycloak is the single source of truth for user authentication in production.
        Testing mode bypass is available for development and testing only.
        
        Args:
            provided_user_id: User ID from Keycloak token (provided by HTTP server)
            operation_name: Name of the operation for error messages
            
        Returns:
            Validated user ID string from Keycloak or testing bypass
            
        Raises:
            UserAuthenticationRequiredError: If no valid authentication is found
        """
        # Testing mode bypass - ONLY for development/testing
        if not self.auth_enabled or self.auth_mode == "testing":
            logger.warning(f"⚠️ TESTING MODE: Authentication bypassed for {operation_name}")
            logger.warning(f"⚠️ Using test user ID: {self.test_user_id}")
            return validate_user_id(self.test_user_id, operation_name)
        
        logger.info(f"🔍 Keycloak authentication check for operation: {operation_name}")
        
        # Primary: HTTP server should pass authenticated user_id from Keycloak
        if provided_user_id:
            logger.info(f"✅ Using Keycloak user_id from HTTP server: {provided_user_id}")
            return validate_user_id(provided_user_id, operation_name)
        
        # Fallback: Try to extract from request context middleware
        logger.info("🔑 Extracting user_id from request context middleware...")
        user_id = self._get_user_id_from_context()
        
        if user_id:
            logger.info(f"✅ Found Keycloak user_id from context: {user_id}")
            return validate_user_id(user_id, operation_name)
        
        # No authentication found - fail with clear error
        logger.error(f"❌ No Keycloak authentication found for {operation_name}")
        raise UserAuthenticationRequiredError(
            f"{operation_name} requires valid Keycloak authentication. "
            f"Please ensure you are authenticated with Keycloak and the HTTP server is properly configured."
        )
    
    def _get_user_id_from_context(self) -> Optional[str]:
        """
        Get user ID from request context middleware (fallback method).
        
        Note: With HTTP server Keycloak auth, this should rarely be needed.
        
        Returns:
            User ID string or None
        """
        try:
            # Try to import the context middleware (may not exist)
            from fastmcp.auth.middleware.request_context_middleware import get_current_user_id
            
            user_id = get_current_user_id()
            if user_id:
                logger.info(f"✅ Found user_id in request context: {user_id}")
                return user_id
            else:
                logger.debug("No user_id found in request context")
                
        except ImportError:
            logger.debug("Request context middleware not available (using HTTP server auth)")
        except Exception as e:
            logger.debug(f"Could not get user_id from context: {e}")
        
        return None