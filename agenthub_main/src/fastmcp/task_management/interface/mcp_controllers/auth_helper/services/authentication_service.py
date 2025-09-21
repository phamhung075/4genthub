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
        Get authenticated user ID from JWT token or authentication context.

        This function extracts user_id from:
        1. Provided user_id parameter (passed from HTTP server authentication)
        2. Request context middleware (JWT token user_id from DualAuthMiddleware)
        3. Testing mode bypass (if MCP_AUTH_MODE=testing or AUTH_ENABLED=false)

        JWT tokens are the primary source of truth for user authentication.
        Testing mode bypass is available for development and testing only when no JWT user is found.

        Args:
            provided_user_id: User ID from token (provided by HTTP server)
            operation_name: Name of the operation for error messages

        Returns:
            Validated user ID string from JWT token or testing bypass

        Raises:
            UserAuthenticationRequiredError: If no valid authentication is found
        """
        logger.info(f"🔍 JWT authentication check for operation: {operation_name}")

        # Primary: HTTP server should pass authenticated user_id from JWT token
        if provided_user_id:
            logger.info(f"✅ Using JWT user_id from HTTP server: {provided_user_id}")
            return validate_user_id(provided_user_id, operation_name)

        # Secondary: Try to extract from request context middleware (JWT token user_id)
        logger.info("🔑 Extracting user_id from JWT token via request context middleware...")
        user_id = self._get_user_id_from_context()

        if user_id:
            logger.info(f"✅ Found JWT user_id from context: {user_id}")
            return validate_user_id(user_id, operation_name)

        # Testing mode bypass - ONLY when no JWT user is available AND testing mode is enabled
        if not self.auth_enabled or self.auth_mode == "testing":
            logger.warning(f"⚠️ TESTING MODE: No JWT user found, using test user for {operation_name}")
            logger.warning(f"⚠️ Using test user ID: {self.test_user_id}")
            return validate_user_id(self.test_user_id, operation_name)

        # No authentication found - fail with clear error
        logger.error(f"❌ No JWT authentication found for {operation_name}")
        raise UserAuthenticationRequiredError(
            f"{operation_name} requires valid JWT authentication. "
            f"Please ensure you are authenticated and the JWT token is properly configured."
        )
    
    def _get_user_id_from_context(self) -> Optional[str]:
        """
        Get user ID from request context middleware (JWT token user_id from DualAuthMiddleware).

        This method retrieves the user_id that was extracted from the JWT token by
        DualAuthMiddleware and stored in context variables by RequestContextMiddleware.

        Returns:
            User ID string from JWT token or None
        """
        try:
            # Import the context middleware function to get JWT user_id
            from fastmcp.auth.middleware.request_context_middleware import get_current_user_id

            user_id = get_current_user_id()
            if user_id:
                logger.info(f"✅ Found JWT user_id in request context: {user_id}")
                return user_id
            else:
                logger.debug("No JWT user_id found in request context")

        except ImportError:
            logger.debug("Request context middleware not available - cannot get JWT user_id from context")
        except Exception as e:
            logger.debug(f"Could not get JWT user_id from context: {e}")

        return None