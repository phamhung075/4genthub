"""Context Repository Interface - Domain Layer"""

from abc import ABC, abstractmethod
from typing import Any

from ..entities.context import ContextInsight, ContextProgressAction, TaskContext


class ContextRepository(ABC):
    """
    Domain repository interface for context operations.
    Defines the contract for context persistence and retrieval.
    """

    @abstractmethod
    def create_context(self, context: TaskContext) -> dict[str, Any]:
        """Create a new context"""
        pass

    @abstractmethod
    def get_context(self, task_id: str) -> TaskContext | None:
        """Get context by task ID"""
        pass

    @abstractmethod
    def update_context(self, context: TaskContext) -> dict[str, Any]:
        """Update existing context"""
        pass

    @abstractmethod
    def delete_context(self, task_id: str) -> dict[str, Any]:
        """Delete context"""
        pass

    @abstractmethod
    def list_contexts(self) -> list[TaskContext]:
        """List all contexts"""
        pass

    @abstractmethod
    def get_property(self, task_id: str, property_path: str) -> Any:
        """Get specific property from context"""
        pass

    @abstractmethod
    def update_property(
        self, task_id: str, property_path: str, value: Any
    ) -> dict[str, Any]:
        """Update specific property in context"""
        pass

    @abstractmethod
    def merge_context_data(self, task_id: str, data: dict[str, Any]) -> dict[str, Any]:
        """Merge data into existing context"""
        pass

    @abstractmethod
    def add_insight(self, task_id: str, insight: ContextInsight) -> dict[str, Any]:
        """Add insight to context"""
        pass

    @abstractmethod
    def add_progress(
        self, task_id: str, progress: ContextProgressAction
    ) -> dict[str, Any]:
        """Add progress entry to context"""
        pass

    @abstractmethod
    def update_next_steps(self, task_id: str, next_steps: list[str]) -> dict[str, Any]:
        """Update next steps in context"""
        pass

    @abstractmethod
    def context_exists(self, task_id: str) -> bool:
        """Check if context exists"""
        pass

    @abstractmethod
    def get_context_metadata(self, task_id: str) -> dict[str, Any]:
        """Get context metadata only"""
        pass

    @abstractmethod
    def search_contexts(self, query: str, limit: int = 10) -> list[TaskContext]:
        """Search contexts by query"""
        pass
