"""
Progress Handler for Subtask MCP Controller

Handles progress tracking and parent task context updates for subtask operations.
"""

import logging
from datetime import datetime, timezone
from typing import Any

logger = logging.getLogger(__name__)


class ProgressHandler:
    """Handles progress tracking and parent task updates for subtasks."""

    def __init__(self, context_facade=None, task_facade=None):
        self._context_facade = context_facade
        self._task_facade = task_facade

    def update_parent_progress(
        self,
        task_id: str,
        subtask_operation: str,
        subtask_data: dict[str, Any],
        progress_notes: str | None = None,
    ) -> dict[str, Any]:
        """Update parent task progress based on subtask operation."""

        if not self._context_facade:
            return {"updated": False, "reason": "No context facade available"}

        try:
            # Create progress content based on operation
            progress_content = self._create_progress_content(
                subtask_operation, subtask_data, progress_notes
            )

            # Add progress to parent task context
            _ = self._context_facade.add_progress(
                task_id=task_id, content=progress_content, agent="subtask_controller"
            )

            # Calculate overall progress
            overall_progress = self._calculate_overall_progress(task_id)

            return {
                "updated": True,
                "progress_content": progress_content,
                "overall_progress": overall_progress,
                "timestamp": datetime.now(timezone.utc).isoformat(),
            }

        except Exception as e:
            logger.error(f"Error updating parent progress: {e}")
            return {"updated": False, "error": str(e)}

    def calculate_task_progress(
        self, task_id: str, subtasks: list[dict[str, Any]]
    ) -> dict[str, Any]:
        """Calculate overall task progress based on subtasks."""

        try:
            total_subtasks = len(subtasks)

            if total_subtasks == 0:
                return {
                    "total_subtasks": 0,
                    "completed_subtasks": 0,
                    "in_progress_subtasks": 0,
                    "pending_subtasks": 0,
                    "progress_percentage": 0,
                    "progress_status": "no_subtasks",
                }

            # Count subtasks by status
            status_counts = {
                "completed": 0,
                "in_progress": 0,
                "pending": 0,
                "blocked": 0,
                "cancelled": 0,
            }

            for subtask in subtasks:
                status = subtask.get("status", "pending").lower()
                if status in status_counts:
                    status_counts[status] += 1
                else:
                    status_counts["pending"] += 1

            # Calculate progress percentage
            completed = status_counts["completed"]
            in_progress = status_counts["in_progress"]

            # Weight in-progress subtasks as 50% complete
            weighted_completed = completed + (in_progress * 0.5)
            progress_percentage = int((weighted_completed / total_subtasks) * 100)

            # Determine overall status
            if completed == total_subtasks:
                progress_status = "completed"
            elif completed > 0 or in_progress > 0:
                progress_status = "in_progress"
            elif status_counts["blocked"] > 0:
                progress_status = "blocked"
            else:
                progress_status = "pending"

            return {
                "total_subtasks": total_subtasks,
                "completed_subtasks": completed,
                "in_progress_subtasks": in_progress,
                "pending_subtasks": status_counts["pending"],
                "blocked_subtasks": status_counts["blocked"],
                "cancelled_subtasks": status_counts["cancelled"],
                "progress_percentage": progress_percentage,
                "progress_status": progress_status,
                "last_calculated": datetime.now(timezone.utc).isoformat(),
            }

        except Exception as e:
            logger.error(f"Error calculating task progress: {e}")
            return {"error": f"Failed to calculate progress: {str(e)}"}

    def get_progress_summary(
        self, task_id: str, subtasks: list[dict[str, Any]]
    ) -> dict[str, Any]:
        """Get comprehensive progress summary for a task."""

        try:
            # Basic progress calculation
            progress = self.calculate_task_progress(task_id, subtasks)

            # Add additional insights
            progress["insights"] = self._generate_progress_insights(progress, subtasks)
            progress["recommendations"] = self._generate_progress_recommendations(
                progress, subtasks
            )
            # OPTIMIZATION: Removed visual_indicators to reduce token overhead
            # Frontend can compute progress bars/emojis from progress_percentage

            return progress

        except Exception as e:
            logger.error(f"Error getting progress summary: {e}")
            return {"error": f"Failed to get progress summary: {str(e)}"}

    def _create_progress_content(
        self, operation: str, subtask_data: dict[str, Any], notes: str | None = None
    ) -> str:
        """Create descriptive progress content based on operation."""

        title = subtask_data.get("title", "Unknown subtask")

        if operation == "create":
            content = f"Created subtask: {title}"
        elif operation == "update":
            status = subtask_data.get("status")
            if status:
                content = f"Updated subtask '{title}' - Status: {status}"
            else:
                content = f"Updated subtask: {title}"
        elif operation == "complete":
            content = f"Completed subtask: {title}"
        elif operation == "delete":
            content = f"Deleted subtask: {title}"
        else:
            content = f"Modified subtask: {title}"

        if notes:
            content += f" - {notes}"

        return content

    def _calculate_overall_progress(self, task_id: str) -> dict[str, Any]:
        """Calculate overall progress for a task (placeholder implementation)."""
        # This would typically query the subtask repository
        # For now, return a placeholder
        return {
            "calculation_needed": True,
            "task_id": task_id,
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }

    def _generate_progress_insights(
        self, progress: dict[str, Any], subtasks: list[dict[str, Any]]
    ) -> list[str]:
        """Generate insights based on progress data."""

        insights = []

        total = progress.get("total_subtasks", 0)
        completed = progress.get("completed_subtasks", 0)
        in_progress = progress.get("in_progress_subtasks", 0)
        blocked = progress.get("blocked_subtasks", 0)

        if total == 0:
            insights.append("No subtasks defined - consider breaking down the work")
        elif completed == total:
            insights.append("All subtasks completed! 🎉")
        elif blocked > 0:
            insights.append(f"{blocked} subtask(s) blocked - may need attention")
        elif in_progress > total * 0.7:
            insights.append("Many subtasks in progress - consider focusing efforts")
        elif completed > total * 0.8:
            insights.append("Nearly complete! Only a few subtasks remaining")

        return insights

    def _generate_progress_recommendations(
        self, progress: dict[str, Any], subtasks: list[dict[str, Any]]
    ) -> list[str]:
        """Generate recommendations based on progress data."""

        recommendations = []

        total = progress.get("total_subtasks", 0)
        completed = progress.get("completed_subtasks", 0)
        in_progress = progress.get("in_progress_subtasks", 0)
        blocked = progress.get("blocked_subtasks", 0)
        pending = progress.get("pending_subtasks", 0)

        if blocked > 0:
            recommendations.append("Address blocked subtasks to maintain momentum")

        if in_progress == 0 and pending > 0:
            recommendations.append("Start working on pending subtasks")

        if in_progress > 3:
            recommendations.append("Consider focusing on fewer subtasks simultaneously")

        if completed > 0 and completed == total:
            recommendations.append("Consider marking the parent task as completed")

        return recommendations

    # DEPRECATED: Removed to reduce token overhead (~40-60 tokens per response)
    # Frontend should compute visual indicators client-side:
    #
    # Progress bar: Math.floor(percentage / 20) filled blocks (🟩/⬜)
    # Status emoji: {"completed": "✅", "in_progress": "🔄", "blocked": "🚫", "pending": "⏳"}
    # Color mapping: percentage or status-based client-side computation
