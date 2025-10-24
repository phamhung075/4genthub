"""Context Builder for Test Data Creation"""

from typing import Dict, Any
from datetime import datetime, timezone
import uuid
import json


class ContextBuilder:
    """Builder for creating test context data."""

    def __init__(self):
        """Initialize with default values."""
        self.context_id = str(uuid.uuid4())
        self.level = "task"
        self.metadata: Dict[str, Any] = {"version": 1}
        self.objective: Dict[str, Any] = {}
        self.progress: Dict[str, Any] = {"completion_percentage": 0}
        self.custom_data: Dict[str, Any] = {}

    def with_id(self, context_id: str) -> 'ContextBuilder':
        """Set context ID."""
        self.context_id = context_id
        return self

    def with_level(self, level: str) -> 'ContextBuilder':
        """Set context level (global, project, branch, task)."""
        self.level = level
        return self

    def with_objective(self, title: str, description: str = "") -> 'ContextBuilder':
        """Set objective."""
        self.objective = {"title": title, "description": description}
        return self

    def with_progress(self, percentage: int) -> 'ContextBuilder':
        """Set progress percentage."""
        self.progress["completion_percentage"] = percentage
        return self

    def with_custom_data(self, key: str, value: Any) -> 'ContextBuilder':
        """Add custom data."""
        self.custom_data[key] = value
        return self

    def build(self) -> Dict[str, Any]:
        """Build and return the context data dictionary."""
        data = {
            "metadata": self.metadata,
            "progress": self.progress
        }

        if self.objective:
            data["objective"] = self.objective

        data.update(self.custom_data)

        return {
            "context_id": self.context_id,
            "level": self.level,
            "data": data
        }

    def build_as_json_string(self) -> str:
        """Build and return context data as JSON string."""
        built = self.build()
        return json.dumps(built["data"])
