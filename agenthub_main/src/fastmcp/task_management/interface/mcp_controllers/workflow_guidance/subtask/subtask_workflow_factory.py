"""Subtask workflow guidance factory."""

from typing import Any

from ..base import WorkflowGuidanceInterface
from .subtask_workflow_guidance import SubtaskWorkflowGuidance


class SubtaskWorkflowFactory:
    """Factory for creating subtask workflow guidance instances."""

    @staticmethod
    def create() -> WorkflowGuidanceInterface:
        """
        Create a new subtask workflow guidance instance.

        Returns:
            SubtaskWorkflowGuidance instance
        """
        return SubtaskWorkflowGuidance()

    @staticmethod
    def create_with_config(config: dict[str, Any]) -> WorkflowGuidanceInterface:
        """
        Create a subtask workflow guidance instance with configuration.

        Args:
            config: Configuration dictionary

        Returns:
            Configured SubtaskWorkflowGuidance instance
        """
        # For now, just return a standard instance
        # In the future, this could use config to customize behavior
        return SubtaskWorkflowGuidance()
