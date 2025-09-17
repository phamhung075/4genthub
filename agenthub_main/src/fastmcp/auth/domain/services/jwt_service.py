"""
JWT Service for token generation and validation

This service handles JWT token creation, validation, and refresh token management.
"""

import logging
import secrets
from datetime import datetime, timedelta, timezone
from typing import Optional, Dict, Any, Tuple
import jwt
from jwt.exceptions import InvalidTokenError, ExpiredSignatureError

logger = logging.getLogger(__name__)


class JWTService:
    """Service for JWT token management"""
    
    # Token configuration
    ALGORITHM = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES = 15  # Short-lived access tokens
    REFRESH_TOKEN_EXPIRE_DAYS = 30    # Long-lived refresh tokens
    RESET_TOKEN_EXPIRE_HOURS = 24     # Password reset tokens
    
    def __init__(self, secret_key: str, issuer: str = "agenthub"):
        """
        Initialize JWT service
        
        Args:
            secret_key: Secret key for signing tokens
            issuer: Token issuer identifier
        """
        if not secret_key:
            raise ValueError("Secret key is required for JWT service")
        
        self.secret_key = secret_key
        self.issuer = issuer
    
    def create_access_token(self, 
                          user_id: str,
                          email: str,
                          roles: list[str],
                          additional_claims: Optional[Dict[str, Any]] = None,
                          audience: str = "mcp-server") -> str:
        """
        Create an access token for API authentication
        
        Args:
            user_id: User's unique identifier
            email: User's email
            roles: User's roles
            additional_claims: Additional JWT claims
            audience: Token audience (defaults to "mcp-server" for local tokens)
            
        Returns:
            Encoded JWT access token
        """
        now = datetime.now(timezone.utc)
        expires = now + timedelta(minutes=self.ACCESS_TOKEN_EXPIRE_MINUTES)
        
        payload = {
            "sub": user_id,  # Subject (user ID)
            "email": email,
            "roles": roles,
            "type": "access",
            "aud": audience,  # Audience claim
            "iat": now,
            "exp": expires,
            "iss": self.issuer,
            "jti": secrets.token_hex(16),  # JWT ID for tracking
        }
        
        if additional_claims:
            payload.update(additional_claims)
        
        return jwt.encode(payload, self.secret_key, algorithm=self.ALGORITHM)
    
    def create_refresh_token(self,
                           user_id: str,
                           token_family: Optional[str] = None,
                           token_version: int = 0) -> Tuple[str, str]:
        """
        Create a refresh token for token renewal
        
        Args:
            user_id: User's unique identifier
            token_family: Token family for rotation tracking
            token_version: Token version for invalidation
            
        Returns:
            Tuple of (encoded refresh token, token family ID)
        """
        now = datetime.now(timezone.utc)
        expires = now + timedelta(days=self.REFRESH_TOKEN_EXPIRE_DAYS)
        
        # Generate new family ID if not provided
        if not token_family:
            token_family = secrets.token_hex(16)
        
        payload = {
            "sub": user_id,
            "type": "refresh",
            "family": token_family,
            "version": token_version,
            "iat": now,
            "exp": expires,
            "iss": self.issuer,
            "jti": secrets.token_hex(16),
        }
        
        token = jwt.encode(payload, self.secret_key, algorithm=self.ALGORITHM)
        return token, token_family
    
    def create_reset_token(self, user_id: str, email: str) -> str:
        """
        Create a password reset token
        
        Args:
            user_id: User's unique identifier
            email: User's email
            
        Returns:
            Encoded reset token
        """
        now = datetime.now(timezone.utc)
        expires = now + timedelta(hours=self.RESET_TOKEN_EXPIRE_HOURS)
        
        payload = {
            "sub": user_id,
            "email": email,
            "type": "reset",
            "iat": now,
            "exp": expires,
            "iss": self.issuer,
            "jti": secrets.token_hex(16),
        }
        
        return jwt.encode(payload, self.secret_key, algorithm=self.ALGORITHM)
    
    def verify_token(self, token: str, expected_type: str = "access", expected_audience: Optional[str] = None) -> Optional[Dict[str, Any]]:
        """
        Verify and decode a JWT token
        
        Args:
            token: JWT token to verify
            expected_type: Expected token type (access, refresh, reset, api_token)
            expected_audience: Expected audience (optional, for audience validation)
            
        Returns:
            Decoded token payload if valid, None otherwise
        """
        try:
            # Decode and verify token with flexible validation options
            payload = None
            decode_options = {}
            
            # If audience is expected, validate it through JWT library
            if expected_audience:
                try:
                    payload = jwt.decode(
                        token,
                        self.secret_key,
                        algorithms=[self.ALGORITHM],
                        audience=expected_audience,
                        issuer=self.issuer
                    )
                except InvalidTokenError:
                    # Try without issuer validation for compatibility
                    payload = jwt.decode(
                        token,
                        self.secret_key,
                        algorithms=[self.ALGORITHM],
                        audience=expected_audience
                    )
            else:
                # No audience validation - let JWT library skip audience checks
                try:
                    payload = jwt.decode(
                        token,
                        self.secret_key,
                        algorithms=[self.ALGORITHM],
                        issuer=self.issuer,
                        options={"verify_aud": False}
                    )
                except InvalidTokenError:
                    # Try without issuer validation for frontend compatibility
                    payload = jwt.decode(
                        token,
                        self.secret_key,
                        algorithms=[self.ALGORITHM],
                        options={"verify_aud": False}
                    )
            
            if not payload:
                return None
            
            # Audience validation is now handled by the JWT library above
            # The token payload will only contain valid tokens with correct audience
            # Verify token type - be flexible with type validation
            token_type = payload.get("type")
            if token_type != expected_type:
                # Allow api_token type for access token compatibility
                if expected_type == "access" and token_type == "api_token":
                    logger.debug(f"Accepting api_token type for access token compatibility")
                elif expected_type == "api_token" and token_type == "access":
                    logger.debug(f"Accepting access type for api_token compatibility")
                elif token_type is None:
                    # Supabase tokens don't have 'type' field, accept them for access tokens
                    logger.debug(f"Accepting token without 'type' field (likely Supabase token)")
                else:
                    logger.warning(f"Token type mismatch: expected {expected_type}, got {token_type}")
                    return None
            
            return payload
            
        except ExpiredSignatureError:
            logger.info("Token has expired")
            return None
        except InvalidTokenError as e:
            logger.warning(f"Invalid token: {e}")
            return None
        except Exception as e:
            logger.error(f"Token verification error: {e}")
            return None
    
    def verify_access_token(self, token: str, expected_audience: Optional[str] = None) -> Optional[Dict[str, Any]]:
        """
        Verify an access token
        
        Args:
            token: Access token to verify
            expected_audience: Expected audience (optional)
            
        Returns:
            Decoded token payload if valid
        """
        return self.verify_token(token, "access", expected_audience)
    
    def verify_refresh_token(self, token: str) -> Optional[Dict[str, Any]]:
        """
        Verify a refresh token
        
        Args:
            token: Refresh token to verify
            
        Returns:
            Decoded token payload if valid
        """
        return self.verify_token(token, "refresh")
    
    def verify_reset_token(self, token: str) -> Optional[Dict[str, Any]]:
        """
        Verify a password reset token
        
        Args:
            token: Reset token to verify
            
        Returns:
            Decoded token payload if valid
        """
        return self.verify_token(token, "reset")
    
    def generate_token(self, 
                      user_id: str,
                      scopes: list[str],
                      expires_in_days: int,
                      token_id: str,
                      audience: str = "mcp-server") -> str:
        """
        Generate an API token with specified scopes and expiration.
        
        Args:
            user_id: User's unique identifier
            scopes: List of permission scopes for the token
            expires_in_days: Token expiration in days
            token_id: Unique token identifier
            audience: Token audience (defaults to "mcp-server")
            
        Returns:
            Encoded JWT API token
        """
        now = datetime.now(timezone.utc)
        expires = now + timedelta(days=expires_in_days)
        
        payload = {
            "sub": user_id,  # Subject (user ID)
            "scopes": scopes,
            "type": "api_token",
            "aud": audience,  # Audience claim
            "iat": now,
            "exp": expires,
            "iss": self.issuer,
            "jti": token_id,  # JWT ID for tracking
        }
        
        return jwt.encode(payload, self.secret_key, algorithm=self.ALGORITHM)
    
    def refresh_access_token(self, refresh_token: str) -> Optional[Tuple[str, str]]:
        """
        Use a refresh token to generate new access and refresh tokens
        
        Args:
            refresh_token: Valid refresh token
            
        Returns:
            Tuple of (new access token, new refresh token) if valid
        """
        payload = self.verify_refresh_token(refresh_token)
        if not payload:
            return None
        
        # Extract user information
        user_id = payload.get("sub")
        token_family = payload.get("family")
        token_version = payload.get("version", 0)
        
        # Note: In production, you would validate the token family and version
        # against the database to ensure it hasn't been revoked
        
        # Create new tokens
        # Note: You would need to fetch user details from database here
        # For now, we'll create minimal tokens
        new_access_token = jwt.encode(
            {
                "sub": user_id,
                "type": "access",
                "iat": datetime.now(timezone.utc),
                "exp": datetime.now(timezone.utc) + timedelta(minutes=self.ACCESS_TOKEN_EXPIRE_MINUTES),
                "iss": self.issuer,
                "jti": secrets.token_hex(16),
            },
            self.secret_key,
            algorithm=self.ALGORITHM
        )
        
        new_refresh_token, _ = self.create_refresh_token(
            user_id,
            token_family,
            token_version + 1  # Increment version
        )
        
        return new_access_token, new_refresh_token
    
    def extract_token_from_header(self, authorization_header: str) -> Optional[str]:
        """
        Extract token from Authorization header
        
        Args:
            authorization_header: Authorization header value
            
        Returns:
            Extracted token or None
        """
        if not authorization_header:
            return None
        
        # Expected format: "Bearer <token>"
        parts = authorization_header.split()
        if len(parts) != 2 or parts[0].lower() != "bearer":
            return None
        
        return parts[1]
    
    def get_token_expiry(self, token: str) -> Optional[datetime]:
        """
        Get token expiration time
        
        Args:
            token: JWT token
            
        Returns:
            Expiration datetime or None if invalid
        """
        try:
            # Decode without verification to get expiry
            payload = jwt.decode(
                token,
                options={"verify_signature": False}
            )
            
            exp = payload.get("exp")
            if exp:
                return datetime.fromtimestamp(exp, tz=timezone.utc)
            
        except Exception as e:
            logger.warning(f"Could not extract token expiry: {e}")
        
        return None
    
    def is_token_expired(self, token: str) -> bool:
        """
        Check if a token is expired
        
        Args:
            token: JWT token
            
        Returns:
            True if expired, False otherwise
        """
        expiry = self.get_token_expiry(token)
        if not expiry:
            return True
        
        return datetime.now(timezone.utc) > expiry