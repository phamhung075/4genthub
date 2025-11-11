"""Utility Service Interface - Domain Layer"""

from __future__ import annotations

from abc import ABC, abstractmethod
from pathlib import Path
from typing import Any


class IPathResolver(ABC):
    """Domain interface for path resolution operations"""

    @abstractmethod
    def resolve_path(self, path: str | Path) -> Path:
        """Resolve a path to absolute path"""
        pass

    @abstractmethod
    def resolve_relative(self, path: str | Path, base: str | Path) -> Path:
        """Resolve a path relative to base"""
        pass

    @abstractmethod
    def normalize_path(self, path: str | Path) -> str:
        """Normalize a path to standard format"""
        pass

    @abstractmethod
    def path_exists(self, path: str | Path) -> bool:
        """Check if path exists"""
        pass

    @abstractmethod
    def is_directory(self, path: str | Path) -> bool:
        """Check if path is a directory"""
        pass

    @abstractmethod
    def is_file(self, path: str | Path) -> bool:
        """Check if path is a file"""
        pass

    @abstractmethod
    def get_parent_directory(self, path: str | Path) -> Path:
        """Get parent directory of path"""
        pass

    @abstractmethod
    def join_paths(self, *paths: str | Path) -> Path:
        """Join multiple paths"""
        pass


class IAgentDocGenerator(ABC):
    """Domain interface for agent documentation generation"""

    @abstractmethod
    def generate_documentation(
        self, agent_id: str, agent_config: dict[str, Any]
    ) -> str:
        """Generate documentation for an agent"""
        pass

    @abstractmethod
    def generate_api_docs(self, agent_id: str) -> dict[str, Any]:
        """Generate API documentation for agent"""
        pass

    @abstractmethod
    def validate_agent_config(self, config: dict[str, Any]) -> bool:
        """Validate agent configuration"""
        pass

    @abstractmethod
    def get_agent_capabilities(self, agent_id: str) -> list[str]:
        """Get capabilities of an agent"""
        pass

    @abstractmethod
    def format_agent_response(self, response: dict[str, Any]) -> str:
        """Format agent response for documentation"""
        pass


class IUtilityService(ABC):
    """Domain interface for utility operations"""

    @abstractmethod
    def generate_uuid(self) -> str:
        """Generate a UUID"""
        pass

    @abstractmethod
    def generate_timestamp(self) -> str:
        """Generate an ISO timestamp"""
        pass

    @abstractmethod
    def hash_string(self, input_string: str) -> str:
        """Hash a string"""
        pass

    @abstractmethod
    def validate_uuid(self, uuid_string: str) -> bool:
        """Validate UUID format"""
        pass

    @abstractmethod
    def serialize_data(self, data: Any) -> str:
        """Serialize data to string"""
        pass

    @abstractmethod
    def deserialize_data(self, data_string: str) -> Any:
        """Deserialize data from string"""
        pass

    @abstractmethod
    def deep_merge(
        self, dict1: dict[str, Any], dict2: dict[str, Any]
    ) -> dict[str, Any]:
        """Deep merge two dictionaries"""
        pass

    @abstractmethod
    def flatten_dict(
        self, nested_dict: dict[str, Any], separator: str = "."
    ) -> dict[str, Any]:
        """Flatten a nested dictionary"""
        pass
