"""
Token Extraction Service

Service for extracting user_id from JWT tokens issued by Keycloak.
This service handles the extraction of user information from bearer tokens
in the Authorization header.
"""

import logging
from typing import Optional, Dict, Any
import jwt
from jwt.exceptions import (
    ExpiredSignatureError,
    InvalidTokenError,
    DecodeError
)

logger = logging.getLogger(__name__)


class TokenExtractionService:
    """Service for extracting user information from JWT tokens"""
    
    def __init__(self):
        """Initialize the token extraction service"""
        self.logger = logging.getLogger(f"{__name__}.{self.__class__.__name__}")
    
    def extract_user_id_from_token(
        self, 
        token: str, 
        verify_exp: bool = True,
        verify_signature: bool = False
    ) -> Optional[str]:
        """
        Extract user_id from a JWT token.
        
        In production, tokens are verified by Keycloak middleware.
        This method extracts the user_id from an already validated token.
        
        Args:
            token: JWT token string
            verify_exp: Whether to verify token expiration (default: True)
            verify_signature: Whether to verify signature (default: False, as Keycloak middleware handles this)
            
        Returns:
            User ID from token or None if extraction fails
        """
        if not token:
            self.logger.warning("No token provided for extraction")
            return None
        
        try:
            # Decode token without verification (verification is done by Keycloak middleware)
            decode_options = {
                "verify_signature": verify_signature,
                "verify_exp": verify_exp,
                "verify_aud": False,
                "verify_iss": False
            }
            
            decoded_token = jwt.decode(
                token,
                options=decode_options,
                algorithms=["HS256", "RS256"]  # Support both symmetric and asymmetric
            )
            
            # Extract user_id from 'sub' claim (standard JWT subject claim)
            user_id = decoded_token.get('sub')
            
            if user_id:
                self.logger.info(f"Successfully extracted user_id from token: {user_id[:8]}...")
                
                # Log additional user info for debugging (if available)
                if self.logger.isEnabledFor(logging.DEBUG):
                    email = decoded_token.get('email', 'N/A')
                    username = decoded_token.get('preferred_username', 'N/A')
                    self.logger.debug(f"Token user info - Email: {email}, Username: {username}")
            else:
                self.logger.warning("Token does not contain 'sub' claim for user_id")
            
            return user_id
            
        except ExpiredSignatureError:
            self.logger.error("Token has expired")
            return None
        except (InvalidTokenError, DecodeError) as e:
            self.logger.error(f"Invalid token: {str(e)}")
            return None
        except Exception as e:
            self.logger.error(f"Unexpected error extracting user_id from token: {str(e)}")
            return None
    
    def extract_user_info_from_token(
        self, 
        token: str,
        verify_exp: bool = True,
        verify_signature: bool = False
    ) -> Optional[Dict[str, Any]]:
        """
        Extract complete user information from a JWT token.
        
        Args:
            token: JWT token string
            verify_exp: Whether to verify token expiration
            verify_signature: Whether to verify signature
            
        Returns:
            Dictionary with user information or None if extraction fails
        """
        if not token:
            self.logger.warning("No token provided for extraction")
            return None
        
        try:
            decode_options = {
                "verify_signature": verify_signature,
                "verify_exp": verify_exp,
                "verify_aud": False,
                "verify_iss": False
            }
            
            decoded_token = jwt.decode(
                token,
                options=decode_options,
                algorithms=["HS256", "RS256"]
            )
            
            # Extract standard Keycloak user claims
            user_info = {
                "user_id": decoded_token.get('sub'),
                "email": decoded_token.get('email'),
                "email_verified": decoded_token.get('email_verified', False),
                "name": decoded_token.get('name'),
                "given_name": decoded_token.get('given_name'),
                "family_name": decoded_token.get('family_name'),
                "preferred_username": decoded_token.get('preferred_username'),
                "realm_roles": decoded_token.get('realm_access', {}).get('roles', []),
                "client_roles": decoded_token.get('resource_access', {})
            }
            
            # Remove None values
            user_info = {k: v for k, v in user_info.items() if v is not None}
            
            self.logger.info(f"Successfully extracted user info for user: {user_info.get('user_id', 'unknown')[:8]}...")
            return user_info
            
        except Exception as e:
            self.logger.error(f"Error extracting user info from token: {str(e)}")
            return None
    
    def extract_token_from_header(self, authorization_header: str) -> Optional[str]:
        """
        Extract JWT token from Authorization header.
        
        Args:
            authorization_header: Authorization header value (e.g., "Bearer token...")
            
        Returns:
            Extracted token or None if not found
        """
        if not authorization_header:
            return None
        
        # Check for Bearer token
        if authorization_header.startswith("Bearer "):
            token = authorization_header[7:]  # Remove "Bearer " prefix
            return token.strip()
        
        self.logger.warning(f"Authorization header does not start with 'Bearer ': {authorization_header[:20]}...")
        return None
    
    def extract_user_id_from_request(self, request) -> Optional[str]:
        """
        Extract user_id from a request object.
        
        This is a convenience method that extracts the token from the request's
        Authorization header and then extracts the user_id.
        
        Args:
            request: Request object with headers
            
        Returns:
            User ID or None if not found
        """
        try:
            # Get Authorization header
            auth_header = None
            
            # Try different ways to access headers depending on request type
            if hasattr(request, 'headers'):
                if hasattr(request.headers, 'get'):
                    auth_header = request.headers.get('Authorization')
                elif isinstance(request.headers, dict):
                    auth_header = request.headers.get('Authorization')
            
            if not auth_header:
                self.logger.debug("No Authorization header found in request")
                return None
            
            # Extract token from header
            token = self.extract_token_from_header(auth_header)
            if not token:
                return None
            
            # Extract user_id from token
            return self.extract_user_id_from_token(token)
            
        except Exception as e:
            self.logger.error(f"Error extracting user_id from request: {str(e)}")
            return None


# Singleton instance for convenience
_token_extraction_service = None


def get_token_extraction_service() -> TokenExtractionService:
    """Get or create the singleton TokenExtractionService instance"""
    global _token_extraction_service
    if _token_extraction_service is None:
        _token_extraction_service = TokenExtractionService()
    return _token_extraction_service


# Convenience functions
def extract_user_id_from_token(token: str, **kwargs) -> Optional[str]:
    """Convenience function to extract user_id from token"""
    service = get_token_extraction_service()
    return service.extract_user_id_from_token(token, **kwargs)


def extract_user_id_from_request(request) -> Optional[str]:
    """Convenience function to extract user_id from request"""
    service = get_token_extraction_service()
    return service.extract_user_id_from_request(request)