"""Task workflow guidance factory."""

from typing import Any

from ..base import WorkflowGuidanceInterface
from .task_workflow_guidance import TaskWorkflowGuidance


class TaskWorkflowFactory:
    """Factory for creating task workflow guidance instances."""

    @staticmethod
    def create() -> WorkflowGuidanceInterface:
        """
        Create a new task workflow guidance instance.

        Returns:
            TaskWorkflowGuidance instance
        """
        return TaskWorkflowGuidance()

    @staticmethod
    def create_with_config(config: dict[str, Any]) -> WorkflowGuidanceInterface:
        """
        Create a task workflow guidance instance with configuration.

        Args:
            config: Configuration dictionary

        Returns:
            Configured TaskWorkflowGuidance instance
        """
        # For now, just return a standard instance
        # In the future, this could use config to customize behavior
        return TaskWorkflowGuidance()
