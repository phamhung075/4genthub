"""
Keycloak Authentication Service for MCP
Clean implementation with no backward compatibility
"""

import os
import logging
import asyncio
from typing import Optional, Dict, Any, List
from dataclasses import dataclass
import httpx
from jose import jwt, JWTError
from datetime import datetime, timedelta

logger = logging.getLogger(__name__)

@dataclass
class AuthResult:
    """Authentication result data class"""
    success: bool
    access_token: Optional[str] = None
    refresh_token: Optional[str] = None
    expires_in: Optional[int] = None
    user: Optional[Dict[str, Any]] = None
    roles: Optional[List[str]] = None
    mcp_permissions: Optional[List[str]] = None
    error: Optional[str] = None

@dataclass
class TokenValidation:
    """Token validation result"""
    valid: bool
    user_id: Optional[str] = None
    email: Optional[str] = None
    roles: Optional[List[str]] = None
    mcp_permissions: Optional[List[str]] = None
    error: Optional[str] = None

class KeycloakAuth:
    """
    Keycloak authentication service for MCP.
    Handles all authentication operations with Keycloak cloud instance.
    """

    def __init__(self):
        """Initialize Keycloak authentication"""
        self.keycloak_url = os.getenv("KEYCLOAK_URL")
        self.realm = os.getenv("KEYCLOAK_REALM")
        self.client_id = os.getenv("KEYCLOAK_CLIENT_ID")
        self.client_secret = os.getenv("KEYCLOAK_CLIENT_SECRET")

        # Validate configuration
        if not all([self.keycloak_url, self.realm, self.client_id, self.client_secret]):
            raise ValueError(
                "Missing Keycloak configuration. "
                "Please set KEYCLOAK_URL, KEYCLOAK_REALM, "
                "KEYCLOAK_CLIENT_ID, and KEYCLOAK_CLIENT_SECRET"
            )

        # Remove trailing slash from URL
        self.keycloak_url = self.keycloak_url.rstrip("/")

        # Build endpoint URLs
        self.token_endpoint = f"{self.keycloak_url}/realms/{self.realm}/protocol/openid-connect/token"
        self.userinfo_endpoint = f"{self.keycloak_url}/realms/{self.realm}/protocol/openid-connect/userinfo"
        self.introspect_endpoint = f"{self.keycloak_url}/realms/{self.realm}/protocol/openid-connect/token/introspect"
        self.logout_endpoint = f"{self.keycloak_url}/realms/{self.realm}/protocol/openid-connect/logout"
        self.jwks_endpoint = f"{self.keycloak_url}/realms/{self.realm}/protocol/openid-connect/certs"

        # HTTP client with timeout
        self.client = httpx.AsyncClient(timeout=30.0)

        # Cache for JWKS (JSON Web Key Set)
        self._jwks_cache = None
        self._jwks_cache_time = None
        self._jwks_cache_ttl = 3600  # 1 hour

        logger.info(f"✅ Keycloak authentication initialized for realm: {self.realm}")

    async def login(self, username: str, password: str) -> AuthResult:
        """
        Authenticate user with Keycloak.

        Args:
            username: User's username
            password: User's password

        Returns:
            AuthResult with tokens and user info
        """
        try:
            data = {
                "grant_type": "password",
                "client_id": self.client_id,
                "client_secret": self.client_secret,
                "username": username,
                "password": password,
                "scope": "openid profile email"
            }

            response = await self.client.post(
                self.token_endpoint,
                data=data,
                headers={"Content-Type": "application/x-www-form-urlencoded"}
            )

            if response.status_code == 200:
                token_data = response.json()

                # Parse user info from ID token
                user_info = self._parse_id_token(token_data.get("id_token"))

                # Extract roles and permissions from access token
                access_token_data = self._parse_access_token(token_data.get("access_token"))

                return AuthResult(
                    success=True,
                    access_token=token_data.get("access_token"),
                    refresh_token=token_data.get("refresh_token"),
                    expires_in=token_data.get("expires_in"),
                    user=user_info,
                    roles=access_token_data.get("roles", []),
                    mcp_permissions=access_token_data.get("mcp_permissions", [])
                )
            else:
                error_data = response.json()
                return AuthResult(
                    success=False,
                    error=error_data.get("error_description", "Authentication failed")
                )

        except Exception as e:
            logger.error(f"Login error: {e}")
            return AuthResult(
                success=False,
                error=str(e)
            )

    async def validate_token(self, token: str) -> TokenValidation:
        """
        Validate an access token with Keycloak.

        Args:
            token: The access token to validate

        Returns:
            TokenValidation result
        """
        try:
            # First try token introspection
            data = {
                "token": token,
                "client_id": self.client_id,
                "client_secret": self.client_secret
            }

            response = await self.client.post(
                self.introspect_endpoint,
                data=data,
                headers={"Content-Type": "application/x-www-form-urlencoded"}
            )

            if response.status_code == 200:
                introspection = response.json()

                if introspection.get("active"):
                    # Parse token data
                    access_token_data = self._parse_access_token(token)

                    return TokenValidation(
                        valid=True,
                        user_id=introspection.get("sub"),
                        email=introspection.get("email"),
                        roles=access_token_data.get("roles", []),
                        mcp_permissions=access_token_data.get("mcp_permissions", [])
                    )
                else:
                    return TokenValidation(
                        valid=False,
                        error="Token is not active"
                    )
            else:
                return TokenValidation(
                    valid=False,
                    error="Failed to introspect token"
                )

        except Exception as e:
            logger.error(f"Token validation error: {e}")
            return TokenValidation(
                valid=False,
                error=str(e)
            )

    async def refresh_token(self, refresh_token: str) -> AuthResult:
        """
        Refresh an access token using a refresh token.

        Args:
            refresh_token: The refresh token

        Returns:
            AuthResult with new tokens
        """
        try:
            data = {
                "grant_type": "refresh_token",
                "refresh_token": refresh_token,
                "client_id": self.client_id,
                "client_secret": self.client_secret
            }

            response = await self.client.post(
                self.token_endpoint,
                data=data,
                headers={"Content-Type": "application/x-www-form-urlencoded"}
            )

            if response.status_code == 200:
                token_data = response.json()

                # Parse user info from ID token
                user_info = self._parse_id_token(token_data.get("id_token"))

                # Extract roles and permissions
                access_token_data = self._parse_access_token(token_data.get("access_token"))

                return AuthResult(
                    success=True,
                    access_token=token_data.get("access_token"),
                    refresh_token=token_data.get("refresh_token"),
                    expires_in=token_data.get("expires_in"),
                    user=user_info,
                    roles=access_token_data.get("roles", []),
                    mcp_permissions=access_token_data.get("mcp_permissions", [])
                )
            else:
                error_data = response.json()
                return AuthResult(
                    success=False,
                    error=error_data.get("error_description", "Token refresh failed")
                )

        except Exception as e:
            logger.error(f"Token refresh error: {e}")
            return AuthResult(
                success=False,
                error=str(e)
            )

    async def logout(self, refresh_token: str) -> bool:
        """
        Logout user from Keycloak.

        Args:
            refresh_token: The refresh token to revoke

        Returns:
            True if logout successful
        """
        try:
            data = {
                "refresh_token": refresh_token,
                "client_id": self.client_id,
                "client_secret": self.client_secret
            }

            response = await self.client.post(
                self.logout_endpoint,
                data=data,
                headers={"Content-Type": "application/x-www-form-urlencoded"}
            )

            return response.status_code in [200, 204]

        except Exception as e:
            logger.error(f"Logout error: {e}")
            return False

    def _parse_id_token(self, id_token: str) -> Dict[str, Any]:
        """Parse user info from ID token"""
        try:
            # Decode without verification for user info (already validated by Keycloak)
            decoded = jwt.get_unverified_claims(id_token)

            return {
                "id": decoded.get("sub"),
                "email": decoded.get("email"),
                "username": decoded.get("preferred_username"),
                "name": decoded.get("name"),
                "given_name": decoded.get("given_name"),
                "family_name": decoded.get("family_name"),
                "email_verified": decoded.get("email_verified", False)
            }
        except Exception as e:
            logger.error(f"Failed to parse ID token: {e}")
            return {}

    def _parse_access_token(self, access_token: str) -> Dict[str, Any]:
        """Parse roles and permissions from access token"""
        try:
            # Decode without verification for parsing
            decoded = jwt.get_unverified_claims(access_token)

            # Extract roles from different possible locations
            roles = []

            # Check realm roles
            if "realm_access" in decoded:
                roles.extend(decoded["realm_access"].get("roles", []))

            # Check resource/client roles
            if "resource_access" in decoded:
                client_access = decoded["resource_access"].get(self.client_id, {})
                roles.extend(client_access.get("roles", []))

            # Extract MCP-specific permissions
            mcp_permissions = []

            # Check for mcp-admin role (full access)
            if "mcp-admin" in roles:
                mcp_permissions = ["*"]
            else:
                # Check for specific MCP permissions in token
                if "mcp_permissions" in decoded:
                    mcp_permissions = decoded["mcp_permissions"]
                elif "permissions" in decoded:
                    # Filter for MCP-related permissions
                    all_permissions = decoded["permissions"]
                    mcp_permissions = [p for p in all_permissions if p.startswith("mcp:")]

            return {
                "roles": roles,
                "mcp_permissions": mcp_permissions,
                "scope": decoded.get("scope", "").split() if decoded.get("scope") else []
            }

        except Exception as e:
            logger.error(f"Failed to parse access token: {e}")
            return {"roles": [], "mcp_permissions": []}

    async def get_user_info(self, access_token: str) -> Optional[Dict[str, Any]]:
        """
        Get user info from Keycloak userinfo endpoint.

        Args:
            access_token: Valid access token

        Returns:
            User info dict or None
        """
        try:
            response = await self.client.get(
                self.userinfo_endpoint,
                headers={"Authorization": f"Bearer {access_token}"}
            )

            if response.status_code == 200:
                return response.json()

            return None

        except Exception as e:
            logger.error(f"Failed to get user info: {e}")
            return None

    async def close(self):
        """Close HTTP client connections"""
        await self.client.aclose()

    def __del__(self):
        """Cleanup on deletion"""
        try:
            asyncio.create_task(self.close())
        except:
            pass