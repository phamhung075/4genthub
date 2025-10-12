"""Base workflow guidance interface."""

from abc import ABC, abstractmethod
from typing import Any


class WorkflowGuidanceInterface(ABC):
    """Interface for workflow guidance providers."""

    @abstractmethod
    def enhance_response(
        self, response: dict[str, Any], action: str, context: dict[str, Any]
    ) -> dict[str, Any]:
        """
        Enhance response with workflow guidance.

        Args:
            response: Original response from operation
            action: The action that was performed
            context: Context information

        Returns:
            Enhanced response with workflow_guidance
        """
        pass

    @abstractmethod
    def analyze_state(
        self, response: dict[str, Any], context: dict[str, Any]
    ) -> dict[str, Any]:
        """Analyze current state for contextual guidance."""
        pass

    @abstractmethod
    def get_rules(self, action: str, response: dict[str, Any]) -> list[str]:
        """Get contextual rules for the current action."""
        pass

    @abstractmethod
    def suggest_next_actions(
        self, action: str, response: dict[str, Any], context: dict[str, Any]
    ) -> list[dict[str, Any]]:
        """Suggest contextual next actions with examples."""
        pass

    @abstractmethod
    def generate_hints(
        self, action: str, response: dict[str, Any], context: dict[str, Any]
    ) -> list[str]:
        """Generate contextual hints."""
        pass

    @abstractmethod
    def check_warnings(
        self, action: str, response: dict[str, Any], context: dict[str, Any]
    ) -> list[str]:
        """Check for potential issues and generate warnings."""
        pass

    @abstractmethod
    def get_examples(self, action: str, context: dict[str, Any]) -> dict[str, Any]:
        """Get relevant examples for the current action."""
        pass

    @abstractmethod
    def get_parameter_guidance(self, action: str) -> dict[str, Any]:
        """Get detailed parameter guidance for the action."""
        pass


class BaseWorkflowGuidance:
    """Base class for workflow guidance implementations."""

    def generate_guidance(
        self, action: str, context: dict[str, Any] = None
    ) -> dict[str, Any]:
        """Generate workflow guidance for an action.

        Args:
            action: The action being performed
            context: Optional context information

        Returns:
            Workflow guidance dictionary
        """
        context = context or {}

        return {
            "current_state": self._determine_state(action, context),
            "rules": self._get_rules(action),
            "next_actions": self._get_next_actions(action, context),
            "hints": self._get_hints(action),
            "warnings": self._get_warnings(action),
            "examples": self._get_examples(action, context),
            "parameter_guidance": self._get_parameter_guidance(action),
        }

    def _determine_state(self, action: str, context: dict[str, Any]) -> dict[str, Any]:
        """Determine current workflow state. Override in subclasses."""
        return {"phase": "operation", "action": action}

    def _get_rules(self, action: str) -> list[str]:
        """Get general rules. Override in subclasses."""
        return []

    def _get_next_actions(
        self, action: str, context: dict[str, Any]
    ) -> list[dict[str, Any]]:
        """Get next action suggestions. Override in subclasses."""
        return []

    def _get_hints(self, action: str) -> list[str]:
        """Get helpful hints. Override in subclasses."""
        return []

    def _get_warnings(self, action: str) -> list[str]:
        """Get warnings. Override in subclasses."""
        return []

    def _get_examples(self, action: str, context: dict[str, Any]) -> dict[str, Any]:
        """Get examples. Override in subclasses."""
        return {}

    def _get_parameter_guidance(self, action: str) -> dict[str, Any]:
        """Get parameter guidance. Override in subclasses."""
        return {"applicable_parameters": [], "parameter_tips": {}}
