"""
Workflow Handler for Task MCP Controller

Handles workflow-related operations like context management and enrichment.
"""

import logging
from typing import Any

from ....utils.response_formatter import StandardResponseFormatter

logger = logging.getLogger(__name__)


class WorkflowHandler:
    """Handles workflow and context operations for tasks."""

    def __init__(
        self, response_formatter: StandardResponseFormatter, context_facade_factory=None
    ):
        self._response_formatter = response_formatter
        self._context_facade_factory = context_facade_factory

    def create_task_context(
        self, task_id: str, task_data: dict[str, Any], git_branch_id: str
    ) -> dict[str, Any]:
        """Create context for a newly created task."""
        if not self._context_facade_factory:
            logger.warning("Context facade factory not available")
            return {"success": False, "error": "Context creation not available"}

        try:
            # Create context facade
            context_facade = self._context_facade_factory.create_facade(
                git_branch_id=git_branch_id
            )

            # Create the context
            context_result = context_facade.create_context(
                level="task",
                context_id=task_id,
                data={
                    "title": task_data.get("title"),
                    "description": task_data.get("description"),
                    "status": task_data.get("status"),
                    "priority": task_data.get("priority"),
                    "assignees": task_data.get("assignees", []),
                    "labels": task_data.get("labels", []),
                    "estimated_effort": task_data.get("estimated_effort"),
                    "due_date": task_data.get("due_date"),
                },
            )

            logger.info(f"Context creation result: {context_result}")
            return context_result

        except Exception as e:
            logger.error(f"Error creating task context: {str(e)}")
            return {
                "success": False,
                "error": f"Failed to create task context: {str(e)}",
            }

    def enrich_task_response(
        self,
        response: dict[str, Any],
        action: str,
        task_data: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        """
        Enrich task response with context intelligence and visual indicators.

        Args:
            response: The response from the facade
            action: The action that was performed
            task_data: Optional task data from the response

        Returns:
            Enriched response with visual indicators and contextual guidance
        """
        if not response.get("success") or not task_data:
            return response

        try:
            # Add workflow guidance based on task status
            status = task_data.get("status", "pending")
            priority = task_data.get("priority", "medium")

            # Generate status-based guidance
            workflow_guidance = self._generate_workflow_guidance(
                status, priority, action
            )
            if workflow_guidance:
                response["workflow_guidance"] = workflow_guidance

            # OPTIMIZATION: Removed visual_indicators and context_status
            # Frontend can compute these from task data:
            # - visual_indicators: Map status/priority to emojis client-side
            # - context_status: Check task.context_id !== null

            return response

        except Exception as e:
            logger.error(f"Error enriching task response: {str(e)}")
            return response  # Return original response if enrichment fails

    def _generate_workflow_guidance(
        self, status: str, priority: str, action: str
    ) -> dict[str, Any] | None:
        """Generate workflow guidance based on task state."""
        guidance = {
            "status_guidance": self._get_status_guidance(status),
            "priority_guidance": self._get_priority_guidance(priority),
            "next_actions": self._get_next_actions(status, action),
        }

        return guidance if any(guidance.values()) else None

    def _get_status_guidance(self, status: str) -> str | None:
        """Get guidance based on task status."""
        status_guidance = {
            "pending": "Task is ready to be worked on. Consider updating to 'in_progress' when starting work.",
            "in_progress": "Task is actively being worked on. Update progress regularly.",
            "completed": "Task has been completed. Consider reviewing and archiving.",
            "blocked": "Task is blocked. Identify and resolve blocking issues.",
            "cancelled": "Task has been cancelled. Review if it should be reactivated.",
        }
        return status_guidance.get(status.lower())

    def _get_priority_guidance(self, priority: str) -> str | None:
        """Get guidance based on task priority."""
        priority_guidance = {
            "high": "High priority task - consider working on this soon.",
            "critical": "Critical priority task - immediate attention required.",
            "medium": "Medium priority task - normal workflow applies.",
            "low": "Low priority task - can be deferred if higher priority work exists.",
        }
        return priority_guidance.get(priority.lower())

    def _get_next_actions(self, status: str, action: str) -> list[str]:
        """Get suggested next actions based on status and current action."""
        next_actions = []

        if action == "create" and status == "pending":
            next_actions.extend(
                [
                    "Update task status to 'in_progress' when starting work",
                    "Add more details or subtasks if needed",
                    "Set assignees if working in a team",
                ]
            )
        elif status == "in_progress":
            next_actions.extend(
                [
                    "Update task progress regularly",
                    "Add completion notes when finishing",
                    "Mark as 'completed' when done",
                ]
            )
        elif status == "completed":
            next_actions.extend(
                [
                    "Review task completion",
                    "Add testing notes if applicable",
                    "Consider archiving the task",
                ]
            )

        return next_actions

    # DEPRECATED: Removed to reduce token overhead in responses
    # Frontend should compute visual indicators client-side:
    #
    # STATUS_EMOJI_MAP = {
    #     "pending": "🟡", "in_progress": "🔵", "completed": "🟢",
    #     "blocked": "🔴", "cancelled": "⚫"
    # }
    #
    # PRIORITY_EMOJI_MAP = {
    #     "critical": "🚨", "high": "⚡", "medium": "📋", "low": "📝"
    # }
    #
    # Context availability: Check task.context_id !== null instead
