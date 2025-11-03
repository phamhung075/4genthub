"""
Unified Token Validator - Shared Authentication Logic

This module provides a single, reusable token validation function that supports
all token types used in the system:
1. Keycloak JWT tokens (from frontend login)
2. API tokens (JWT signed with JWT_SECRET_KEY, from .mcp.json)
3. MCP tokens (legacy token system via TokenValidator)

Used by both HTTP middleware and WebSocket handlers to ensure consistent
authentication behavior across all connection types.
"""

import os
import logging
from typing import Optional, Dict, Any
from dataclasses import dataclass

logger = logging.getLogger(__name__)


@dataclass
class AuthResult:
    """Unified authentication result."""
    valid: bool
    user_id: Optional[str] = None
    email: Optional[str] = None
    auth_method: Optional[str] = None
    error: Optional[str] = None
    # Additional fields for debugging and context
    token_id: Optional[str] = None
    roles: Optional[list] = None
    scopes: Optional[list] = None
    user_data: Optional[Dict[str, Any]] = None


async def validate_token_universal(
    token: str,
    client_info: Optional[Dict[str, Any]] = None
) -> AuthResult:
    """
    Validate any token type: Keycloak, API token, or MCP token.

    This implements the same fallback chain as DualAuthMiddleware but as a
    reusable function that can be called from HTTP middleware, WebSocket
    handlers, or any other authentication point.

    Validation chain:
    1. Check if JWT token → Try Keycloak validation
    2. Try API token validation (JWT_SECRET_KEY)
    3. Try MCP token validation (TokenValidator)

    Args:
        token: The token to validate
        client_info: Optional client information (user_agent, path, method)

    Returns:
        AuthResult with validation results
    """
    if not token:
        return AuthResult(valid=False, error="No token provided")

    client_info = client_info or {}

    # 1. Check if it's a JWT token and try validation
    if token.startswith('eyJ'):  # JWT tokens start with this
        try:
            logger.debug("🔍 UNIFIED VALIDATOR: Detected JWT token")

            # Decode without verification to check token structure
            import jwt as pyjwt
            try:
                unverified_payload = pyjwt.decode(token, options={"verify_signature": False})

                # Check if it's a Keycloak token (has iss claim pointing to Keycloak)
                auth_provider = os.getenv("AUTH_PROVIDER", "supabase").lower()
                issuer = unverified_payload.get('iss', '')
                keycloak_url = os.getenv("KEYCLOAK_URL", "")

                if auth_provider == "keycloak" and keycloak_url and issuer.startswith(keycloak_url):
                    logger.debug("🔍 UNIFIED VALIDATOR: Token appears to be Keycloak token")
                    result = await _validate_keycloak_token(token)
                    if result.valid:
                        return result
                    logger.debug(f"🔍 UNIFIED VALIDATOR: Keycloak validation failed: {result.error}")

                # Check if it's an API token (has token_id claim)
                elif unverified_payload.get('token_id') or unverified_payload.get('type') == 'api_token':
                    logger.debug("🔍 UNIFIED VALIDATOR: Token appears to be API token")
                    result = await _validate_api_token(token)
                    if result.valid:
                        return result
                    logger.debug(f"🔍 UNIFIED VALIDATOR: API token validation failed: {result.error}")

            except Exception as decode_error:
                logger.debug(f"🔍 UNIFIED VALIDATOR: Could not decode token: {decode_error}")

            # Try general local JWT validation
            logger.debug("🔍 UNIFIED VALIDATOR: Trying general local JWT validation")
            result = await _validate_local_jwt(token)
            if result.valid:
                return result
            logger.debug(f"🔍 UNIFIED VALIDATOR: Local JWT validation failed: {result.error}")

        except Exception as e:
            logger.debug(f"🔍 UNIFIED VALIDATOR: JWT validation failed: {e}")

    # 2. Try MCP token validation (for generated tokens)
    try:
        logger.debug("🔍 UNIFIED VALIDATOR: Trying MCP token validation")
        result = await _validate_mcp_token(token, client_info)
        if result.valid:
            return result
        logger.debug(f"🔍 UNIFIED VALIDATOR: MCP token validation failed: {result.error}")
    except Exception as e:
        logger.debug(f"🔍 UNIFIED VALIDATOR: MCP token validation error: {e}")

    # No valid authentication found
    logger.warning("❌ UNIFIED VALIDATOR: All token validation methods failed")
    return AuthResult(
        valid=False,
        error="Invalid token: no validation method succeeded"
    )


async def _validate_keycloak_token(token: str) -> AuthResult:
    """Validate a Keycloak JWT token."""
    try:
        from .keycloak_dependencies import validate_keycloak_token

        user = await validate_keycloak_token(token)
        logger.info(f"✅ UNIFIED VALIDATOR: Keycloak token validated for user {user.id}")

        return AuthResult(
            valid=True,
            user_id=user.id,
            email=user.email,
            auth_method='keycloak',
            user_data={
                'id': user.id,
                'email': user.email,
                'username': user.username
            }
        )
    except Exception as e:
        logger.debug(f"Keycloak token validation failed: {e}")
        return AuthResult(valid=False, error=f"Keycloak validation failed: {str(e)}")


async def _validate_api_token(token: str) -> AuthResult:
    """Validate an API token generated by token management system."""
    try:
        from .domain.services.jwt_service import JWTService

        # API tokens are signed with JWT_SECRET_KEY
        jwt_secret = os.getenv("JWT_SECRET_KEY")
        if not jwt_secret:
            return AuthResult(valid=False, error="JWT_SECRET_KEY not configured")

        jwt_service = JWTService(secret_key=jwt_secret)

        # API tokens have type 'api_token'
        payload = jwt_service.verify_token(token, expected_type="api_token")
        if payload:
            user_id = payload.get('user_id') or payload.get('sub')
            logger.info(f"✅ UNIFIED VALIDATOR: API token validated for user {user_id}")

            return AuthResult(
                valid=True,
                user_id=user_id,
                email=payload.get('email'),
                auth_method='api_token',
                token_id=payload.get('token_id') or payload.get('jti'),
                scopes=payload.get('scopes', []),
                roles=payload.get('roles', [])
            )

        return AuthResult(valid=False, error="API token validation failed")

    except Exception as e:
        logger.debug(f"API token validation failed: {e}")
        return AuthResult(valid=False, error=f"API token validation failed: {str(e)}")


async def _validate_local_jwt(token: str) -> AuthResult:
    """Validate a local JWT token using available secrets."""
    try:
        from .domain.services.jwt_service import JWTService
        import jwt as pyjwt

        # Get both potential secrets
        jwt_secret = os.getenv("JWT_SECRET_KEY", "default-secret-key-change-in-production")
        supabase_jwt_secret = os.getenv("SUPABASE_JWT_SECRET")

        # List of secrets to try
        secrets_to_try = []
        if supabase_jwt_secret:
            secrets_to_try.append(("SUPABASE_JWT_SECRET", supabase_jwt_secret))
        if jwt_secret and jwt_secret != "default-secret-key-change-in-production":
            secrets_to_try.append(("JWT_SECRET_KEY", jwt_secret))

        # Try each secret until one works
        for secret_name, secret_value in secrets_to_try:
            try:
                jwt_service = JWTService(secret_key=secret_value)

                # Special handling for Supabase tokens
                if secret_name == "SUPABASE_JWT_SECRET":
                    try:
                        payload = pyjwt.decode(
                            token,
                            secret_value,
                            algorithms=["HS256"],
                            audience="authenticated",
                            options={"verify_iss": False}
                        )
                        if payload:
                            user_id = payload.get('user_id') or payload.get('sub')
                            logger.info(f"✅ UNIFIED VALIDATOR: Supabase JWT validated for user {user_id}")
                            return AuthResult(
                                valid=True,
                                user_id=user_id,
                                email=payload.get('email'),
                                auth_method='local_jwt',
                                roles=payload.get('roles', [])
                            )
                    except:
                        pass

                # Try standard validation
                for token_type in ["api_token", "access"]:
                    try:
                        payload = jwt_service.verify_token(token, expected_type=token_type)
                        if payload:
                            user_id = payload.get('user_id') or payload.get('sub')
                            logger.info(f"✅ UNIFIED VALIDATOR: Local JWT validated for user {user_id}")
                            return AuthResult(
                                valid=True,
                                user_id=user_id,
                                email=payload.get('email'),
                                auth_method='local_jwt',
                                token_id=payload.get('token_id') or payload.get('jti'),
                                scopes=payload.get('scopes', []),
                                roles=payload.get('roles', [])
                            )
                    except:
                        continue

            except Exception as e:
                logger.debug(f"JWT validation with {secret_name} failed: {e}")
                continue

        return AuthResult(valid=False, error="Local JWT validation failed with all secrets")

    except Exception as e:
        logger.debug(f"Local JWT validation error: {e}")
        return AuthResult(valid=False, error=f"Local JWT validation error: {str(e)}")


async def _validate_mcp_token(token: str, client_info: Dict[str, Any]) -> AuthResult:
    """Validate an MCP-generated token."""
    try:
        from .token_validator import TokenValidator

        token_validator = TokenValidator()
        token_info = await token_validator.validate_token(token, client_info)

        logger.info(f"✅ UNIFIED VALIDATOR: MCP token validated for user {token_info.user_id}")

        return AuthResult(
            valid=True,
            user_id=token_info.user_id,
            auth_method='mcp_token',
            user_data={
                'created_at': token_info.created_at.isoformat() if token_info.created_at else None,
                'expires_at': token_info.expires_at.isoformat() if token_info.expires_at else None
            }
        )

    except Exception as e:
        logger.debug(f"MCP token validation failed: {e}")
        return AuthResult(valid=False, error=f"MCP token validation failed: {str(e)}")
