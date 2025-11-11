"""User Builder for Test Data Creation"""

import uuid
from datetime import UTC, datetime
from typing import Any


class UserBuilder:
    """Builder for creating test user data with configurable properties."""

    def __init__(self):
        """Initialize with default values."""
        self.user_id = str(uuid.uuid4())
        self.email = "test@example.com"
        self.username = "testuser"
        self.password = "TestPassword123!"
        self.roles = ["user"]
        self.permissions = ["mcp:read"]
        self.enabled = True
        self.email_verified = False
        self.created_at = datetime.now(UTC)
        self.metadata: dict[str, Any] = {}

    def with_user_id(self, user_id: str) -> "UserBuilder":
        """Set user ID."""
        self.user_id = user_id
        return self

    def with_email(self, email: str) -> "UserBuilder":
        """Set email address."""
        self.email = email
        self.username = email.split("@")[0]
        return self

    def with_username(self, username: str) -> "UserBuilder":
        """Set username."""
        self.username = username
        return self

    def with_password(self, password: str) -> "UserBuilder":
        """Set password."""
        self.password = password
        return self

    def with_role(self, role: str) -> "UserBuilder":
        """Add a role."""
        if role not in self.roles:
            self.roles.append(role)
        return self

    def with_roles(self, roles: list[str]) -> "UserBuilder":
        """Set multiple roles."""
        self.roles = roles
        return self

    def with_admin_role(self) -> "UserBuilder":
        """Add admin role and permissions."""
        self.roles.append("admin")
        self.permissions = ["mcp:*", "admin:*"]
        return self

    def with_permission(self, permission: str) -> "UserBuilder":
        """Add a permission."""
        if permission not in self.permissions:
            self.permissions.append(permission)
        return self

    def with_permissions(self, permissions: list[str]) -> "UserBuilder":
        """Set multiple permissions."""
        self.permissions = permissions
        return self

    def with_enabled(self, enabled: bool) -> "UserBuilder":
        """Set enabled status."""
        self.enabled = enabled
        return self

    def with_email_verified(self, verified: bool) -> "UserBuilder":
        """Set email verification status."""
        self.email_verified = verified
        return self

    def with_metadata(self, key: str, value: Any) -> "UserBuilder":
        """Add custom metadata."""
        self.metadata[key] = value
        return self

    def build(self) -> dict[str, Any]:
        """Build and return the user data dictionary."""
        return {
            "id": self.user_id,
            "email": self.email,
            "username": self.username,
            "password": self.password,
            "roles": self.roles,
            "permissions": self.permissions,
            "enabled": self.enabled,
            "email_verified": self.email_verified,
            "created_at": self.created_at.isoformat(),
            "metadata": self.metadata,
        }
