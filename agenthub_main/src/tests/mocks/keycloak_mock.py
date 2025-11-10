"""Mock Keycloak Server for Authentication Testing

Provides a mock Keycloak server that simulates authentication flows, token
validation, and JWKS endpoints without requiring a real Keycloak instance.

Usage:
    # Create mock server
    >>> mock_server = MockKeycloakServer()
    >>> mock_server.start()

    # Use in tests
    >>> client = MockKeycloakClient(mock_server)
    >>> token = client.login("user@example.com", "password")
    >>> assert token is not None

    # Cleanup
    >>> mock_server.stop()
"""

from __future__ import annotations

import uuid
from datetime import UTC, datetime, timedelta
from typing import Any


class MockKeycloakServer:
    """Mock Keycloak server for testing authentication flows."""

    def __init__(
        self,
        realm: str = "agenthub",
        base_url: str = "http://localhost:8080"
    ):
        """Initialize mock Keycloak server.

        Args:
            realm: Keycloak realm name
            base_url: Base URL for the mock server
        """
        self.realm = realm
        self.base_url = base_url
        self.users: dict[str, dict[str, Any]] = {}
        self.tokens: dict[str, dict[str, Any]] = {}
        self.refresh_tokens: dict[str, str] = {}
        self._running = False

        # Add default test users
        self._create_default_users()

    def _create_default_users(self):
        """Create default test users."""
        self.add_user(
            email="test@example.com",
            password="password123",
            roles=["user"],
            permissions=["mcp:read"]
        )
        self.add_user(
            email="admin@example.com",
            password="admin123",
            roles=["admin", "user"],
            permissions=["mcp:*", "admin:*"]
        )

    def start(self):
        """Start the mock server."""
        self._running = True
        print(f"Mock Keycloak server started at {self.base_url}/realms/{self.realm}")

    def stop(self):
        """Stop the mock server."""
        self._running = False
        self.tokens.clear()
        self.refresh_tokens.clear()
        print("Mock Keycloak server stopped")

    def add_user(
        self,
        email: str,
        password: str,
        user_id: str | None = None,
        username: str | None = None,
        roles: list[str | None] = None,
        permissions: list[str | None] = None
    ) -> str:
        """Add a user to the mock server.

        Args:
            email: User email
            password: User password
            user_id: Optional user ID (auto-generated if not provided)
            username: Optional username (defaults to email)
            roles: List of roles
            permissions: List of permissions

        Returns:
            User ID
        """
        user_id = user_id or str(uuid.uuid4())
        username = username or email.split('@')[0]

        self.users[email] = {
            "id": user_id,
            "email": email,
            "username": username,
            "password": password,  # In real Keycloak, this would be hashed
            "roles": roles or ["user"],
            "permissions": permissions or ["mcp:read"],
            "enabled": True,
            "created_at": datetime.now(UTC).isoformat()
        }

        return user_id

    def remove_user(self, email: str):
        """Remove a user from the mock server."""
        if email in self.users:
            del self.users[email]

    def authenticate(
        self,
        email: str,
        password: str,
        client_id: str = "mcp-client"
    ) -> dict[str, Any | None]:
        """Authenticate a user and return tokens.

        Args:
            email: User email
            password: User password
            client_id: OAuth client ID

        Returns:
            Token response dictionary or None if authentication fails
        """
        user = self.users.get(email)
        if not user or user["password"] != password or not user["enabled"]:
            return None

        # Generate access token
        access_token = self._generate_access_token(user, client_id)
        refresh_token = self._generate_refresh_token(user)

        # Store tokens
        self.tokens[access_token] = {
            "user_id": user["id"],
            "email": user["email"],
            "expires_at": datetime.now(UTC) + timedelta(hours=1)
        }
        self.refresh_tokens[refresh_token] = access_token

        return {
            "access_token": access_token,
            "token_type": "Bearer",
            "refresh_token": refresh_token,
            "expires_in": 3600,
            "user_id": user["id"],
            "email": user["email"]
        }

    def _generate_access_token(self, user: dict[str, Any], client_id: str) -> str:
        """Generate a mock access token (in reality, this would be a JWT)."""
        from tests.utils.auth_token_builder import AuthTokenBuilder

        return (AuthTokenBuilder()
                .with_user_id(user["id"])
                .with_email(user["email"])
                .with_username(user["username"])
                .with_roles(user["roles"])
                .with_permissions(user["permissions"])
                .with_audience(client_id)
                .build())

    def _generate_refresh_token(self, user: dict[str, Any]) -> str:
        """Generate a mock refresh token."""
        return f"refresh_{user['id']}_{uuid.uuid4()}"

    def validate_token(self, token: str) -> dict[str, Any | None]:
        """Validate an access token.

        Args:
            token: Access token to validate

        Returns:
            User information if valid, None otherwise
        """
        token_info = self.tokens.get(token)
        if not token_info:
            return None

        # Check expiration
        if datetime.now(UTC) > token_info["expires_at"]:
            del self.tokens[token]
            return None

        return token_info

    def refresh_access_token(self, refresh_token: str) -> dict[str, Any | None]:
        """Refresh an access token using a refresh token.

        Args:
            refresh_token: Refresh token

        Returns:
            New token response or None if refresh fails
        """
        old_access_token = self.refresh_tokens.get(refresh_token)
        if not old_access_token:
            return None

        # Get user from old token
        old_token_info = self.tokens.get(old_access_token)
        if not old_token_info:
            return None

        user = self.users.get(old_token_info["email"])
        if not user:
            return None

        # Generate new tokens
        new_access_token = self._generate_access_token(user, "mcp-client")
        new_refresh_token = self._generate_refresh_token(user)

        # Remove old tokens
        if old_access_token in self.tokens:
            del self.tokens[old_access_token]
        if refresh_token in self.refresh_tokens:
            del self.refresh_tokens[refresh_token]

        # Store new tokens
        self.tokens[new_access_token] = {
            "user_id": user["id"],
            "email": user["email"],
            "expires_at": datetime.now(UTC) + timedelta(hours=1)
        }
        self.refresh_tokens[new_refresh_token] = new_access_token

        return {
            "access_token": new_access_token,
            "token_type": "Bearer",
            "refresh_token": new_refresh_token,
            "expires_in": 3600
        }

    def logout(self, token: str):
        """Logout a user by invalidating their token.

        Args:
            token: Access token to invalidate
        """
        if token in self.tokens:
            del self.tokens[token]

        # Also remove associated refresh token
        refresh_to_remove = None
        for refresh_token, access_token in self.refresh_tokens.items():
            if access_token == token:
                refresh_to_remove = refresh_token
                break

        if refresh_to_remove:
            del self.refresh_tokens[refresh_to_remove]

    def get_jwks(self) -> dict[str, Any]:
        """Get the JWKS (JSON Web Key Set) for token validation.

        Returns:
            JWKS dictionary
        """
        from tests.utils.auth_token_builder import MockKeycloakJWKS

        jwks_mock = MockKeycloakJWKS()
        return jwks_mock.get_jwks()

    def get_user_info(self, token: str) -> dict[str, Any | None]:
        """Get user information from an access token.

        Args:
            token: Access token

        Returns:
            User information or None if token is invalid
        """
        token_info = self.validate_token(token)
        if not token_info:
            return None

        user = self.users.get(token_info["email"])
        if not user:
            return None

        return {
            "sub": user["id"],
            "email": user["email"],
            "preferred_username": user["username"],
            "email_verified": True,
            "roles": user["roles"]
        }


class MockKeycloakClient:
    """Client for interacting with the mock Keycloak server."""

    def __init__(self, server: MockKeycloakServer):
        """Initialize client with a mock server.

        Args:
            server: Mock Keycloak server instance
        """
        self.server = server
        self.current_token: str | None = None
        self.current_refresh_token: str | None = None

    def login(self, email: str, password: str) -> str | None:
        """Login and get an access token.

        Args:
            email: User email
            password: User password

        Returns:
            Access token or None if login fails
        """
        response = self.server.authenticate(email, password)
        if response:
            self.current_token = response["access_token"]
            self.current_refresh_token = response["refresh_token"]
            return self.current_token

        return None

    def logout(self):
        """Logout the current user."""
        if self.current_token:
            self.server.logout(self.current_token)
            self.current_token = None
            self.current_refresh_token = None

    def refresh_token(self) -> str | None:
        """Refresh the current access token.

        Returns:
            New access token or None if refresh fails
        """
        if not self.current_refresh_token:
            return None

        response = self.server.refresh_access_token(self.current_refresh_token)
        if response:
            self.current_token = response["access_token"]
            self.current_refresh_token = response["refresh_token"]
            return self.current_token

        return None

    def validate_current_token(self) -> bool:
        """Validate the current access token.

        Returns:
            True if token is valid, False otherwise
        """
        if not self.current_token:
            return False

        return self.server.validate_token(self.current_token) is not None

    def get_user_info(self) -> dict[str, Any | None]:
        """Get information about the current user.

        Returns:
            User information or None if not logged in
        """
        if not self.current_token:
            return None

        return self.server.get_user_info(self.current_token)
