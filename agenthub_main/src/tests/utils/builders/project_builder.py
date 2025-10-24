"""Project Builder for Test Data Creation"""

from typing import List, Optional, Dict, Any
from datetime import datetime, timezone
import uuid


class ProjectBuilder:
    """Builder for creating test project data."""

    def __init__(self):
        """Initialize with default values."""
        self.project_id = str(uuid.uuid4())
        self.name = "Test Project"
        self.description = "Test project description"
        self.user_id = "test-user"
        self.status = "active"
        self.created_at = datetime.now(timezone.utc)
        self.updated_at = datetime.now(timezone.utc)
        self.metadata: Dict[str, Any] = {}

    def with_id(self, project_id: str) -> 'ProjectBuilder':
        """Set project ID."""
        self.project_id = project_id
        return self

    def with_name(self, name: str) -> 'ProjectBuilder':
        """Set project name."""
        self.name = name
        return self

    def with_description(self, description: str) -> 'ProjectBuilder':
        """Set project description."""
        self.description = description
        return self

    def with_user_id(self, user_id: str) -> 'ProjectBuilder':
        """Set owner user ID."""
        self.user_id = user_id
        return self

    def with_status(self, status: str) -> 'ProjectBuilder':
        """Set project status."""
        self.status = status
        return self

    def with_metadata(self, key: str, value: Any) -> 'ProjectBuilder':
        """Add custom metadata."""
        self.metadata[key] = value
        return self

    def build(self) -> Dict[str, Any]:
        """Build and return the project data dictionary."""
        return {
            "id": self.project_id,
            "name": self.name,
            "description": self.description,
            "user_id": self.user_id,
            "status": self.status,
            "created_at": self.created_at.isoformat(),
            "updated_at": self.updated_at.isoformat(),
            "metadata": self.metadata
        }
