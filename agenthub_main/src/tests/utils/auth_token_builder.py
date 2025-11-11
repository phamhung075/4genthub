"""Auth Token Builder for Test Infrastructure

This module provides utilities for generating JWT/Keycloak tokens for authentication testing.
Supports creating valid tokens with various configurations, expired tokens, invalid tokens,
and mock JWKS key pairs for signature validation testing.

Usage Examples:
    # Generate a basic valid token
    >>> token = AuthTokenBuilder().build()

    # Generate an admin token with custom permissions
    >>> admin_token = (AuthTokenBuilder()
    ...     .with_role("admin")
    ...     .with_permissions(["mcp:*", "admin:*"])
    ...     .build())

    # Generate an expired token for testing token refresh
    >>> expired_token = (AuthTokenBuilder()
    ...     .with_expired_token(hours_ago=2)
    ...     .build())

    # Generate an invalid token for security testing
    >>> invalid_token = AuthTokenBuilder.generate_invalid_token(reason="bad_signature")
"""

from __future__ import annotations

import json
import uuid
from datetime import UTC, datetime, timedelta
from typing import Any

import jwt
from cryptography.hazmat.backends import default_backend
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric import rsa


class JWKSKeyPair:
    """Mock JWKS key pair for JWT signature validation testing."""

    def __init__(self):
        """Generate RSA key pair for JWT signing and validation."""
        self.private_key = rsa.generate_private_key(
            public_exponent=65537, key_size=2048, backend=default_backend()
        )
        self.public_key = self.private_key.public_key()
        self.kid = str(uuid.uuid4())  # Key ID for JWKS

    def get_private_pem(self) -> bytes:
        """Get private key in PEM format for signing."""
        return self.private_key.private_bytes(
            encoding=serialization.Encoding.PEM,
            format=serialization.PrivateFormat.PKCS8,
            encryption_algorithm=serialization.NoEncryption(),
        )

    def get_public_pem(self) -> bytes:
        """Get public key in PEM format for validation."""
        return self.public_key.public_bytes(
            encoding=serialization.Encoding.PEM,
            format=serialization.PublicFormat.SubjectPublicKeyInfo,
        )

    def get_jwks(self) -> dict[str, Any]:
        """Get JWKS (JSON Web Key Set) representation."""

        public_numbers = self.public_key.public_numbers()

        # Convert to base64url encoding
        import base64

        def int_to_base64url(num: int) -> str:
            # Convert integer to bytes (big-endian)
            byte_length = (num.bit_length() + 7) // 8
            num_bytes = num.to_bytes(byte_length, byteorder="big")
            # Base64url encode (no padding)
            return base64.urlsafe_b64encode(num_bytes).rstrip(b"=").decode("utf-8")

        return {
            "keys": [
                {
                    "kty": "RSA",
                    "use": "sig",
                    "kid": self.kid,
                    "alg": "RS256",
                    "n": int_to_base64url(public_numbers.n),
                    "e": int_to_base64url(public_numbers.e),
                }
            ]
        }


class AuthTokenBuilder:
    """Builder pattern for creating JWT tokens with configurable properties.

    Supports Keycloak-style token structure with roles, permissions, and claims.
    """

    # Class-level key pair for consistent signing across tests
    _default_key_pair: JWKSKeyPair | None = None

    def __init__(self):
        """Initialize token builder with default values."""
        self.user_id = f"test-user-{uuid.uuid4()}"
        self.email = "test@example.com"
        self.username = "testuser"
        self.roles = ["user"]
        self.permissions = ["mcp:read"]
        self.issuer = "http://localhost:8080/realms/agenthub"
        self.audience = "mcp-client"
        self.subject = self.user_id
        self.issued_at = datetime.now(UTC)
        self.expires_at = self.issued_at + timedelta(hours=1)
        self.not_before = self.issued_at
        self.custom_claims: dict[str, Any] = {}
        self.key_pair = self._get_default_key_pair()

    @classmethod
    def _get_default_key_pair(cls) -> JWKSKeyPair:
        """Get or create the default key pair for token signing."""
        if cls._default_key_pair is None:
            cls._default_key_pair = JWKSKeyPair()
        return cls._default_key_pair

    @classmethod
    def reset_key_pair(cls):
        """Reset the default key pair (useful for testing key rotation)."""
        cls._default_key_pair = None

    def with_user_id(self, user_id: str) -> AuthTokenBuilder:
        """Set the user ID for the token."""
        self.user_id = user_id
        self.subject = user_id
        return self

    def with_email(self, email: str) -> AuthTokenBuilder:
        """Set the email address for the token."""
        self.email = email
        return self

    def with_username(self, username: str) -> AuthTokenBuilder:
        """Set the username for the token."""
        self.username = username
        return self

    def with_role(self, role: str) -> AuthTokenBuilder:
        """Add a role to the token."""
        if role not in self.roles:
            self.roles.append(role)
        return self

    def with_roles(self, roles: list[str]) -> AuthTokenBuilder:
        """Set multiple roles for the token."""
        self.roles = roles
        return self

    def with_admin_role(self) -> AuthTokenBuilder:
        """Convenience method to add admin role and permissions."""
        self.roles.append("admin")
        self.permissions = ["mcp:*", "admin:*"]
        return self

    def with_permission(self, permission: str) -> AuthTokenBuilder:
        """Add a permission to the token."""
        if permission not in self.permissions:
            self.permissions.append(permission)
        return self

    def with_permissions(self, permissions: list[str]) -> AuthTokenBuilder:
        """Set multiple permissions for the token."""
        self.permissions = permissions
        return self

    def with_issuer(self, issuer: str) -> AuthTokenBuilder:
        """Set the token issuer."""
        self.issuer = issuer
        return self

    def with_audience(self, audience: str) -> AuthTokenBuilder:
        """Set the token audience."""
        self.audience = audience
        return self

    def with_expiry(self, expires_at: datetime) -> AuthTokenBuilder:
        """Set the token expiration time."""
        self.expires_at = expires_at
        return self

    def with_expired_token(self, hours_ago: int = 1) -> AuthTokenBuilder:
        """Create an expired token for testing token refresh/validation."""
        now = datetime.now(UTC)
        self.issued_at = now - timedelta(hours=hours_ago + 1)
        self.expires_at = now - timedelta(hours=hours_ago)
        return self

    def with_not_yet_valid_token(self, hours_future: int = 1) -> AuthTokenBuilder:
        """Create a token that's not yet valid (nbf in future)."""
        now = datetime.now(UTC)
        self.issued_at = now
        self.not_before = now + timedelta(hours=hours_future)
        self.expires_at = now + timedelta(hours=hours_future + 1)
        return self

    def with_custom_claim(self, key: str, value: Any) -> AuthTokenBuilder:
        """Add a custom claim to the token."""
        self.custom_claims[key] = value
        return self

    def with_custom_key_pair(self, key_pair: JWKSKeyPair) -> AuthTokenBuilder:
        """Use a custom key pair instead of the default."""
        self.key_pair = key_pair
        return self

    def build(self) -> str:
        """Build and return the signed JWT token string."""
        payload = {
            "sub": self.subject,
            "iss": self.issuer,
            "aud": self.audience,
            "iat": int(self.issued_at.timestamp()),
            "exp": int(self.expires_at.timestamp()),
            "nbf": int(self.not_before.timestamp()),
            "email": self.email,
            "preferred_username": self.username,
            "realm_access": {"roles": self.roles},
            "resource_access": {self.audience: {"roles": self.permissions}},
            **self.custom_claims,
        }

        # Sign the token
        token = jwt.encode(
            payload,
            self.key_pair.get_private_pem(),
            algorithm="RS256",
            headers={"kid": self.key_pair.kid},
        )

        return token

    def build_with_payload(self) -> tuple[str, dict[str, Any]]:
        """Build token and return both the token string and payload.

        Useful for tests that need to inspect the payload.
        """
        token = self.build()
        payload = jwt.decode(
            token,
            self.key_pair.get_public_pem(),
            algorithms=["RS256"],
            audience=self.audience,
            options={"verify_exp": False},  # Don't verify expiry for testing
        )
        return token, payload

    @staticmethod
    def generate_invalid_token(reason: str = "bad_signature") -> str:
        """Generate various types of invalid tokens for security testing.

        Args:
            reason: Type of invalid token to generate:
                - "bad_signature": Valid structure but incorrect signature
                - "malformed": Malformed token structure
                - "missing_claims": Missing required claims
                - "wrong_algorithm": Token signed with wrong algorithm

        Returns:
            Invalid token string
        """
        if reason == "bad_signature":
            # Create a valid token but modify it slightly to break the signature
            valid_token = AuthTokenBuilder().build()
            parts = valid_token.split(".")
            # Modify the payload slightly
            import base64

            payload = base64.urlsafe_b64decode(parts[1] + "==")
            modified_payload = payload.replace(b"test@example.com", b"fake@example.com")
            parts[1] = (
                base64.urlsafe_b64encode(modified_payload).decode("utf-8").rstrip("=")
            )
            return ".".join(parts)

        elif reason == "malformed":
            return "this.is.not.a.valid.jwt.token.structure"

        elif reason == "missing_claims":
            # Token without required claims
            payload = {
                "sub": "test-user",
                # Missing iss, aud, exp, etc.
            }
            key_pair = AuthTokenBuilder._get_default_key_pair()
            return jwt.encode(payload, key_pair.get_private_pem(), algorithm="RS256")

        elif reason == "wrong_algorithm":
            # Token signed with HS256 instead of RS256
            payload = {
                "sub": "test-user",
                "iss": "test-issuer",
                "aud": "test-audience",
                "exp": int((datetime.now(UTC) + timedelta(hours=1)).timestamp()),
            }
            return jwt.encode(payload, "secret-key", algorithm="HS256")

        else:
            raise ValueError(f"Unknown invalid token reason: {reason}")

    @staticmethod
    def decode_token(token: str, verify: bool = False) -> dict[str, Any]:
        """Decode a JWT token without validation (for inspection).

        Args:
            token: JWT token string
            verify: Whether to verify signature (default False for inspection)

        Returns:
            Decoded token payload
        """
        if verify:
            key_pair = AuthTokenBuilder._get_default_key_pair()
            return jwt.decode(
                token,
                key_pair.get_public_pem(),
                algorithms=["RS256"],
                options={"verify_exp": False},
            )
        else:
            return jwt.decode(token, options={"verify_signature": False})


class MockKeycloakJWKS:
    """Mock Keycloak JWKS endpoint for testing token validation.

    Usage:
        >>> jwks = MockKeycloakJWKS()
        >>> jwks_json = jwks.get_jwks()
        >>> # Use this in tests to mock the Keycloak JWKS endpoint
    """

    def __init__(self, key_pair: JWKSKeyPair | None = None):
        """Initialize with a key pair or use the default."""
        self.key_pair = key_pair or AuthTokenBuilder._get_default_key_pair()

    def get_jwks(self) -> dict[str, Any]:
        """Get the JWKS JSON structure."""
        return self.key_pair.get_jwks()

    def get_jwks_json(self) -> str:
        """Get the JWKS as a JSON string."""
        return json.dumps(self.get_jwks(), indent=2)


# Convenience functions for quick token generation


def create_test_token(
    user_id: str | None = None,
    email: str = "test@example.com",
    roles: list[str] | None = None,
    permissions: list[str] | None = None,
    expired: bool = False,
) -> str:
    """Quick helper to create a test token with common parameters.

    Args:
        user_id: User ID (auto-generated if not provided)
        email: User email
        roles: List of roles (defaults to ["user"])
        permissions: List of permissions (defaults to ["mcp:read"])
        expired: Whether to create an expired token

    Returns:
        JWT token string
    """
    builder = AuthTokenBuilder()

    if user_id:
        builder.with_user_id(user_id)
    if email:
        builder.with_email(email)
    if roles:
        builder.with_roles(roles)
    if permissions:
        builder.with_permissions(permissions)
    if expired:
        builder.with_expired_token()

    return builder.build()


def create_admin_token() -> str:
    """Quick helper to create an admin token."""
    return AuthTokenBuilder().with_admin_role().build()


def create_expired_token() -> str:
    """Quick helper to create an expired token."""
    return AuthTokenBuilder().with_expired_token().build()
