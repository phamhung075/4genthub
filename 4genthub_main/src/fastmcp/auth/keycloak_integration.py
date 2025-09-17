"""
Keycloak Integration for MCP Authentication
Clean implementation with no backward compatibility
"""

import os
import logging
import json
from typing import Optional, Dict, Any, List
from datetime import datetime, timedelta, timezone
from urllib.parse import urljoin
import httpx
import jwt
from jwt import PyJWKClient
from functools import lru_cache

logger = logging.getLogger(__name__)

class KeycloakAuthProvider:
    """
    Clean Keycloak authentication provider for MCP.
    Handles token validation and user authentication via Keycloak.
    """

    def __init__(
        self,
        keycloak_url: Optional[str] = None,
        realm: Optional[str] = None,
        client_id: Optional[str] = None,
        client_secret: Optional[str] = None,
        verify_audience: bool = True,
        ssl_verify: bool = True,
        token_cache_ttl: int = 300,
        public_key_cache_ttl: int = 3600
    ):
        """
        Initialize Keycloak authentication provider.

        Args:
            keycloak_url: Keycloak server URL
            realm: Keycloak realm name
            client_id: Client ID for this application
            client_secret: Client secret for confidential clients
            verify_audience: Whether to verify token audience
            ssl_verify: Whether to verify SSL certificates
            token_cache_ttl: Token cache TTL in seconds
            public_key_cache_ttl: Public key cache TTL in seconds
        """
        self.keycloak_url = keycloak_url or os.getenv("KEYCLOAK_URL")
        self.realm = realm or os.getenv("KEYCLOAK_REALM", "4genthub")
        self.client_id = client_id or os.getenv("KEYCLOAK_CLIENT_ID", "mcp-backend")
        self.client_secret = client_secret or os.getenv("KEYCLOAK_CLIENT_SECRET")

        if not self.keycloak_url:
            raise ValueError("KEYCLOAK_URL is required")

        # Configuration
        self.verify_audience = verify_audience
        self.ssl_verify = ssl_verify
        self.token_cache_ttl = token_cache_ttl
        self.public_key_cache_ttl = public_key_cache_ttl

        # Build URLs
        self.realm_url = f"{self.keycloak_url}/realms/{self.realm}"
        self.well_known_url = f"{self.realm_url}/.well-known/openid-configuration"
        self.token_url = f"{self.realm_url}/protocol/openid-connect/token"
        self.userinfo_url = f"{self.realm_url}/protocol/openid-connect/userinfo"
        self.jwks_url = f"{self.realm_url}/protocol/openid-connect/certs"

        # Initialize JWKS client for token validation
        self._jwks_client = None
        self._oidc_config = None
        self._last_config_fetch = None

        # HTTP client
        self.http_client = httpx.AsyncClient(verify=self.ssl_verify)

        logger.info(f"Keycloak provider initialized for realm: {self.realm}")

    @property
    def jwks_client(self) -> PyJWKClient:
        """Get or create JWKS client for token validation"""
        if self._jwks_client is None:
            self._jwks_client = PyJWKClient(
                self.jwks_url,
                cache_keys=True,
                lifespan=self.public_key_cache_ttl
            )
        return self._jwks_client

    async def get_oidc_configuration(self) -> Dict[str, Any]:
        """
        Get OpenID Connect configuration from Keycloak.
        Cached for performance.
        """
        now = datetime.now(timezone.utc)

        # Check cache
        if self._oidc_config and self._last_config_fetch:
            if (now - self._last_config_fetch).seconds < self.public_key_cache_ttl:
                return self._oidc_config

        # Fetch configuration
        try:
            response = await self.http_client.get(self.well_known_url)
            response.raise_for_status()

            self._oidc_config = response.json()
            self._last_config_fetch = now

            logger.debug("OIDC configuration fetched successfully")
            return self._oidc_config

        except Exception as e:
            logger.error(f"Failed to fetch OIDC configuration: {e}")
            # Return cached config if available
            if self._oidc_config:
                return self._oidc_config
            raise

    async def validate_token(self, token: str) -> Optional[Dict[str, Any]]:
        """
        Validate a Keycloak JWT token.

        Args:
            token: JWT token to validate

        Returns:
            Token payload if valid, None otherwise
        """
        try:
            # Get OIDC configuration
            config = await self.get_oidc_configuration()
            issuer = config.get("issuer")

            # Get signing key
            signing_key = self.jwks_client.get_signing_key_from_jwt(token)

            # Validate token
            options = {
                "verify_signature": True,
                "verify_aud": self.verify_audience,
                "verify_iss": True,
                "verify_exp": True,
                "verify_nbf": True,
                "verify_iat": True,
                "require": ["exp", "iat", "sub"]
            }

            payload = jwt.decode(
                token,
                signing_key.key,
                algorithms=["RS256"],
                audience=self.client_id if self.verify_audience else None,
                issuer=issuer,
                options=options
            )

            # Additional validation
            if not payload.get("sub"):
                logger.warning("Token missing subject claim")
                return None

            # Check if token is active
            now = datetime.now(timezone.utc).timestamp()
            if payload.get("exp", 0) < now:
                logger.warning("Token expired")
                return None

            logger.debug(f"Token validated for user: {payload.get('preferred_username', payload.get('sub'))}")
            return payload

        except jwt.ExpiredSignatureError:
            logger.warning("Token has expired")
            return None
        except jwt.InvalidTokenError as e:
            logger.warning(f"Invalid token: {e}")
            return None
        except Exception as e:
            logger.error(f"Token validation error: {e}")
            return None

    async def get_user_info(self, access_token: str) -> Optional[Dict[str, Any]]:
        """
        Get user information from Keycloak userinfo endpoint.

        Args:
            access_token: Valid access token

        Returns:
            User information if successful, None otherwise
        """
        try:
            headers = {"Authorization": f"Bearer {access_token}"}
            response = await self.http_client.get(self.userinfo_url, headers=headers)
            response.raise_for_status()

            user_info = response.json()
            logger.debug(f"User info fetched for: {user_info.get('preferred_username', user_info.get('sub'))}")
            return user_info

        except Exception as e:
            logger.error(f"Failed to fetch user info: {e}")
            return None

    async def exchange_token(
        self,
        username: Optional[str] = None,
        password: Optional[str] = None,
        refresh_token: Optional[str] = None,
        authorization_code: Optional[str] = None,
        redirect_uri: Optional[str] = None
    ) -> Optional[Dict[str, Any]]:
        """
        Exchange credentials for tokens using Keycloak token endpoint.

        Supports multiple grant types:
        - password: Username/password authentication
        - refresh_token: Refresh an existing token
        - authorization_code: OAuth2 authorization code flow

        Returns:
            Token response with access_token, refresh_token, etc.
        """
        try:
            data = {
                "client_id": self.client_id,
            }

            # Add client secret if configured (confidential client)
            if self.client_secret:
                data["client_secret"] = self.client_secret

            # Determine grant type and add appropriate parameters
            if username and password:
                data.update({
                    "grant_type": "password",
                    "username": username,
                    "password": password,
                    "scope": "openid profile email"
                })
            elif refresh_token:
                data.update({
                    "grant_type": "refresh_token",
                    "refresh_token": refresh_token
                })
            elif authorization_code and redirect_uri:
                data.update({
                    "grant_type": "authorization_code",
                    "code": authorization_code,
                    "redirect_uri": redirect_uri
                })
            else:
                logger.error("No valid credentials provided for token exchange")
                return None

            # Make request
            response = await self.http_client.post(
                self.token_url,
                data=data,
                headers={"Content-Type": "application/x-www-form-urlencoded"}
            )
            response.raise_for_status()

            token_response = response.json()
            logger.info(f"Token exchanged successfully for grant_type: {data.get('grant_type')}")

            return token_response

        except httpx.HTTPStatusError as e:
            logger.error(f"Token exchange failed: {e.response.status_code} - {e.response.text}")
            return None
        except Exception as e:
            logger.error(f"Token exchange error: {e}")
            return None

    async def logout(self, refresh_token: str) -> bool:
        """
        Logout user by revoking refresh token.

        Args:
            refresh_token: Refresh token to revoke

        Returns:
            True if successful, False otherwise
        """
        try:
            logout_url = f"{self.realm_url}/protocol/openid-connect/logout"

            data = {
                "client_id": self.client_id,
                "refresh_token": refresh_token
            }

            if self.client_secret:
                data["client_secret"] = self.client_secret

            response = await self.http_client.post(
                logout_url,
                data=data,
                headers={"Content-Type": "application/x-www-form-urlencoded"}
            )
            response.raise_for_status()

            logger.info("User logged out successfully")
            return True

        except Exception as e:
            logger.error(f"Logout failed: {e}")
            return False

    async def close(self):
        """Close HTTP client connections"""
        await self.http_client.aclose()

class KeycloakMCPAuth:
    """
    MCP-specific Keycloak authentication handler.
    Maps Keycloak tokens to MCP authentication context.
    """

    def __init__(self, keycloak_provider: Optional[KeycloakAuthProvider] = None):
        """
        Initialize MCP Keycloak authentication.

        Args:
            keycloak_provider: Keycloak provider instance (creates default if None)
        """
        self.keycloak = keycloak_provider or KeycloakAuthProvider()

    async def authenticate_mcp_request(
        self,
        authorization_header: Optional[str] = None
    ) -> Optional[Dict[str, Any]]:
        """
        Authenticate an MCP request using Keycloak token.

        Args:
            authorization_header: Authorization header value (e.g., "Bearer token")

        Returns:
            User context if authenticated, None otherwise
        """
        if not authorization_header:
            logger.debug("No authorization header provided")
            return None

        # Extract token from header
        parts = authorization_header.split()
        if len(parts) != 2 or parts[0].lower() != "bearer":
            logger.warning("Invalid authorization header format")
            return None

        token = parts[1]

        # Validate token
        payload = await self.keycloak.validate_token(token)
        if not payload:
            return None

        # Build MCP user context
        user_context = {
            "user_id": payload.get("sub"),
            "username": payload.get("preferred_username", payload.get("email")),
            "email": payload.get("email"),
            "roles": payload.get("realm_access", {}).get("roles", []),
            "scopes": payload.get("scope", "").split(),
            "authenticated": True,
            "auth_provider": "keycloak",
            "token_exp": payload.get("exp"),
            "session_id": payload.get("sid"),
        }

        # Add MCP-specific permissions based on roles
        mcp_permissions = []
        if "admin" in user_context["roles"]:
            mcp_permissions = ["mcp:*"]  # Full access
        elif "developer" in user_context["roles"]:
            mcp_permissions = ["mcp:read", "mcp:write", "mcp:execute"]
        elif "user" in user_context["roles"]:
            mcp_permissions = ["mcp:read", "mcp:execute"]
        else:
            mcp_permissions = ["mcp:read"]  # Minimum access

        user_context["mcp_permissions"] = mcp_permissions

        logger.info(f"MCP request authenticated for user: {user_context['username']}")
        return user_context

    async def create_mcp_token(
        self,
        keycloak_token: str,
        name: str = "MCP Token",
        scopes: Optional[List[str]] = None
    ) -> Optional[Dict[str, Any]]:
        """
        Create an MCP-specific token from a Keycloak token.
        This allows MCP clients to use simplified tokens.

        Args:
            keycloak_token: Valid Keycloak access token
            name: Name for the MCP token
            scopes: MCP-specific scopes

        Returns:
            MCP token information if successful
        """
        # Validate Keycloak token first
        payload = await self.keycloak.validate_token(keycloak_token)
        if not payload:
            logger.warning("Invalid Keycloak token for MCP token creation")
            return None

        # Generate MCP token
        import secrets
        import hashlib
        from datetime import datetime, timedelta, timezone

        mcp_token = f"mcp_{secrets.token_urlsafe(32)}"
        token_hash = hashlib.sha256(mcp_token.encode()).hexdigest()

        # Token metadata
        token_info = {
            "token": mcp_token,
            "token_hash": token_hash,
            "name": name,
            "user_id": payload.get("sub"),
            "username": payload.get("preferred_username"),
            "scopes": scopes or ["mcp:read", "mcp:execute"],
            "created_at": datetime.now(timezone.utc).isoformat(),
            "expires_at": (datetime.now(timezone.utc) + timedelta(days=30)).isoformat(),
            "keycloak_session": payload.get("sid"),
            "active": True
        }

        # TODO: Store token in database for validation
        # This would typically be done via the token management service

        logger.info(f"MCP token created for user: {token_info['username']}")
        return token_info

# Singleton instance for easy import
_default_provider = None

def get_keycloak_provider() -> KeycloakAuthProvider:
    """Get or create default Keycloak provider"""
    global _default_provider
    if _default_provider is None:
        _default_provider = KeycloakAuthProvider()
    return _default_provider

def get_keycloak_mcp_auth() -> KeycloakMCPAuth:
    """Get or create default Keycloak MCP auth handler"""
    return KeycloakMCPAuth(get_keycloak_provider())