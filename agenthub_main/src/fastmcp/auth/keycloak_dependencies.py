"""
Keycloak-aware authentication dependencies for FastAPI.

This module provides authentication dependencies that can handle both
Keycloak JWT tokens (RS256) and local JWT tokens (HS256).
"""

from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from typing import Optional
import jwt
import os
import logging
from datetime import datetime, timezone
import httpx

from fastmcp.auth.domain.entities.user import User

logger = logging.getLogger(__name__)

# Security scheme
security = HTTPBearer()

# Local JWT configuration (for tokens we generate)
JWT_SECRET_KEY = os.getenv("JWT_SECRET_KEY")
JWT_ALGORITHM = os.getenv("JWT_ALGORITHM", "HS256")

# Keycloak configuration
KEYCLOAK_URL = os.getenv("KEYCLOAK_URL")
KEYCLOAK_REALM = os.getenv("KEYCLOAK_REALM", "mcp")
AUTH_PROVIDER = os.getenv("AUTH_PROVIDER", "keycloak")

# Cache for Keycloak public keys
_keycloak_jwks_client = None

def get_keycloak_jwks_client():
    """Get or create JWKS client for Keycloak token validation."""
    global _keycloak_jwks_client

    # Get current value of KEYCLOAK_URL (not the one cached at module import)
    keycloak_url = os.getenv("KEYCLOAK_URL")
    keycloak_realm = os.getenv("KEYCLOAK_REALM", "mcp")

    if not keycloak_url:
        return None

    if _keycloak_jwks_client is None:
        from jwt import PyJWKClient
        import ssl
        import urllib.request

        # Create SSL context that doesn't verify certificates (for self-signed certs)
        ssl_context = ssl.create_default_context()
        ssl_context.check_hostname = False
        ssl_context.verify_mode = ssl.CERT_NONE

        # Create custom URL opener with unverified SSL
        opener = urllib.request.build_opener(urllib.request.HTTPSHandler(context=ssl_context))
        urllib.request.install_opener(opener)

        jwks_url = f"{keycloak_url}/realms/{keycloak_realm}/protocol/openid-connect/certs"
        logger.info(f"Fetching JWKS from: {jwks_url}")
        _keycloak_jwks_client = PyJWKClient(jwks_url, cache_keys=True, lifespan=3600)
    return _keycloak_jwks_client


async def get_current_user_universal(
    credentials: HTTPAuthorizationCredentials = Depends(security)
) -> User:
    """
    Get the current authenticated user from either Keycloak or local JWT token.
    
    This dependency first tries to validate as a Keycloak token (RS256),
    then falls back to local JWT validation (HS256).
    """
    token = credentials.credentials
    
    # First, try to decode as Keycloak token (without verification to check structure)
    try:
        # Decode without verification to check issuer
        unverified_payload = jwt.decode(token, options={"verify_signature": False})
        issuer = unverified_payload.get("iss", "")
        
        # Check if this is a Keycloak token
        if KEYCLOAK_URL and issuer.startswith(KEYCLOAK_URL):
            logger.debug("Detected Keycloak token, validating with Keycloak")
            return await validate_keycloak_token(token)
        else:
            logger.debug("Not a Keycloak token, trying local validation")
            return validate_local_token(token)
            
    except jwt.DecodeError:
        # If we can't even decode it, try local validation
        logger.debug("Failed to decode token structure, trying local validation")
        return validate_local_token(token)


async def validate_keycloak_token(token: str) -> User:
    """Validate a Keycloak JWT token."""
    try:
        # Read current environment values to support testing with patch.dict
        auth_provider = os.getenv("AUTH_PROVIDER", "keycloak")
        keycloak_url = os.getenv("KEYCLOAK_URL")

        if auth_provider != "keycloak" or not keycloak_url:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Keycloak not configured"
            )
        
        # Get JWKS client for key validation
        jwks_client = get_keycloak_jwks_client()
        if not jwks_client:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Keycloak JWKS client not available"
            )
        
        # Get the signing key from Keycloak
        signing_key = jwks_client.get_signing_key_from_jwt(token)
        
        # Decode and validate the token with clock skew tolerance
        payload = jwt.decode(
            token,
            signing_key.key,
            algorithms=["RS256"],
            audience="account",  # Keycloak default audience
            options={
                "verify_aud": False,  # Disable audience verification for now
                "verify_exp": True,
                "verify_iat": True
            },
            leeway=30  # Allow 30 seconds of clock skew
        )
        
        # Extract user information from Keycloak token
        user_id = payload.get("sub")
        email = payload.get("email")
        username = payload.get("preferred_username") or email
        
        if not user_id:
            logger.error("Keycloak token missing 'sub' claim")
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid token: missing user ID"
            )
        
        # Check token expiration
        exp = payload.get("exp")
        if exp and datetime.now(timezone.utc).timestamp() > exp:
            logger.error("Keycloak token expired")
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Token expired"
            )
        
        # Create User object
        user = User(
            id=user_id,
            email=email or f"{username}@keycloak.local",
            username=username or user_id,
            password_hash="keycloak-authenticated"
        )
        
        logger.info(f"Authenticated Keycloak user: {user.id} ({user.email})")
        return user
        
    except jwt.ExpiredSignatureError:
        logger.error("Keycloak token expired")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token expired"
        )
    except jwt.InvalidTokenError as e:
        logger.error(f"Invalid Keycloak token: {e}")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=f"Invalid token: {str(e)}"
        )
    except HTTPException:
        # Re-raise HTTPExceptions (like configuration errors) as-is
        raise
    except Exception as e:
        logger.error(f"Keycloak token validation error: {e}")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token validation failed"
        )


def validate_local_token(token: str) -> User:
    """Validate a locally-generated JWT token."""
    # Read current environment value to support testing with patch.dict
    jwt_secret = os.getenv("JWT_SECRET_KEY")
    if not jwt_secret:
        logger.error("JWT_SECRET_KEY not configured")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Server configuration error: JWT secret not set"
        )
    
    try:
        # Decode the local JWT token with clock skew tolerance
        payload = jwt.decode(
            token,
            jwt_secret,
            algorithms=[JWT_ALGORITHM],
            leeway=30  # Allow 30 seconds of clock skew
        )
        
        # Extract user information
        user_id = payload.get("sub") or payload.get("user_id")
        email = payload.get("email")
        
        if not user_id:
            logger.error("Local token missing user_id/sub claim")
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid token: missing user ID"
            )
        
        # Check token expiration
        exp = payload.get("exp")
        if exp and datetime.now(timezone.utc).timestamp() > exp:
            logger.error("Local token expired")
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Token expired"
            )
        
        # Create User object
        user = User(
            id=user_id,
            email=email or f"{user_id}@local.dev",
            username=payload.get("username") or email or user_id,
            password_hash="local-jwt-authenticated"
        )
        
        logger.info(f"Authenticated local user: {user.id}")
        return user
        
    except jwt.ExpiredSignatureError:
        logger.error("Local token expired")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token expired"
        )
    except jwt.InvalidTokenError as e:
        logger.error(f"Invalid local token: {e}")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid token"
        )


async def get_current_user_from_ws(websocket, token: str) -> dict:
    """
    Validate a JWT token from a WebSocket connection.

    Args:
        websocket: The WebSocket connection
        token: The JWT token to validate

    Returns:
        User information dict

    Raises:
        HTTPException: If the token is invalid
    """
    # Try Keycloak validation first (if configured)
    if AUTH_PROVIDER == "keycloak" and KEYCLOAK_URL:
        user = await validate_keycloak_token(token)
        if user:
            return {
                "sub": user.id,
                "email": user.email,
                "username": user.username
            }

    # Fall back to local JWT validation
    user = await validate_local_jwt(token)
    return {
        "sub": user.id,
        "email": user.email,
        "username": user.username
    }


