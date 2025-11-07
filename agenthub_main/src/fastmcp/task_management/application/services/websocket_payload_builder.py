"""WebSocket Payload Builder Service

This service provides a centralized, DRY way to build complete WebSocket payloads
for task events. It eliminates code duplication across use cases and ensures
consistent, complete data is sent to the frontend for real-time updates.

Purpose:
- Build complete WebSocket payloads with all required fields
- Eliminate UI flicker by providing all data needed for immediate rendering
- Reduce unnecessary API refetches by including complete task information
- Follow DRY principles by centralizing payload construction logic

Usage:
    from ..services.websocket_payload_builder import WebSocketPayloadBuilder

    # Build payload from task entity and response DTO
    payload = WebSocketPayloadBuilder.build_task_payload(task, task_response)

    # Send WebSocket notification
    await websocket_manager.broadcast(event="task.created", data=payload)
"""

from typing import Dict, Any, Optional
from datetime import datetime


class WebSocketPayloadBuilder:
    """Centralized service for building WebSocket payloads following DRY principles"""

    @staticmethod
    def build_task_payload(
        task,
        task_response=None,
        include_progress_history: bool = True
    ) -> Dict[str, Any]:
        """Build complete WebSocket payload for task events.

        This method constructs a comprehensive payload that includes all fields
        needed by the frontend to render task cards without additional API calls.

        Args:
            task: Domain task entity (required)
            task_response: Optional TaskResponse DTO for enhanced data (project_id, subtask counts)
            include_progress_history: Whether to include full progress history (default: True)

        Returns:
            Dictionary with complete task data for WebSocket transmission

        Payload Structure:
            {
                # Core identifiers
                "id": str,
                "title": str,
                "status": str,
                "priority": str,

                # Relationship data
                "project_id": str | None,
                "git_branch_id": str | None,

                # Subtask information (eliminates badge flicker)
                "subtask_count": int,
                "completed_subtasks": int,

                # Team & assignment
                "assignees": List[str],

                # Progress tracking
                "progress_percentage": int,
                "progress_history": Dict | None,
                "progress_count": int,

                # Metadata
                "has_dependencies": bool,
                "has_context": bool,
                "labels": List[str],

                # Timestamps
                "created_at": str | None,
                "updated_at": str | None,

                # Optional rich fields
                "description": str | None,
                "details": str
            }
        """
        # Core identifiers from domain task
        # CRITICAL FIX: Ensure enums are serialized to their string values, not enum objects
        payload = {
            "id": str(task.id.value if hasattr(task.id, 'value') else task.id),
            "title": task.title,
            "status": task.status.value if hasattr(task.status, 'value') else str(task.status),
            "priority": task.priority.value if hasattr(task.priority, 'value') else str(task.priority),
        }

        # Relationship data (from task_response if available, else from task)
        if task_response:
            # Enhanced data from response DTO (includes batch-loaded data)
            payload["project_id"] = task_response.project_id
            payload["git_branch_id"] = task_response.git_branch_id
            payload["subtask_count"] = task_response.subtask_count
            payload["completed_subtasks"] = task_response.completed_subtasks
            payload["progress_percentage"] = task_response.progress_percentage
            payload["progress_count"] = task_response.progress_count

            # Progress history (optional, can be large)
            if include_progress_history:
                payload["progress_history"] = task_response.progress_history
                payload["details"] = task_response.details
            else:
                # Omit large progress history to reduce message size
                payload["progress_history"] = {}
                payload["details"] = ""
        else:
            # Fallback to task entity data (less complete but still functional)
            payload["project_id"] = None  # Not available without repository join
            payload["git_branch_id"] = task.git_branch_id if hasattr(task, 'git_branch_id') else None
            payload["subtask_count"] = len(task.subtasks) if hasattr(task, 'subtasks') and task.subtasks else 0
            payload["completed_subtasks"] = 0  # Cannot determine without loading subtask entities
            payload["progress_percentage"] = task.progress_percentage if hasattr(task, 'progress_percentage') else 0
            payload["progress_count"] = task.progress_count if hasattr(task, 'progress_count') else 0

            # Progress history from task entity
            if include_progress_history:
                payload["progress_history"] = task.progress_history if hasattr(task, 'progress_history') else {}
                payload["details"] = task.get_progress_history_text() if hasattr(task, 'get_progress_history_text') else ""
            else:
                payload["progress_history"] = {}
                payload["details"] = ""

        # Team & assignment (from task entity)
        payload["assignees"] = task.assignees if hasattr(task, 'assignees') and task.assignees else []

        # Metadata (from task entity)
        payload["has_dependencies"] = (
            len(task.dependencies) > 0
            if hasattr(task, 'dependencies') and task.dependencies
            else False
        )
        payload["has_context"] = task.context_id is not None if hasattr(task, 'context_id') else False
        payload["labels"] = task.labels if hasattr(task, 'labels') and task.labels else []

        # Timestamps (from task entity)
        payload["created_at"] = (
            task.created_at.isoformat()
            if hasattr(task, 'created_at') and task.created_at
            else None
        )
        payload["updated_at"] = (
            task.updated_at.isoformat()
            if hasattr(task, 'updated_at') and task.updated_at
            else None
        )

        # Optional rich fields (truncated to keep message size reasonable)
        description = task.description if hasattr(task, 'description') else None
        if description and len(description) > 200:
            # Truncate long descriptions to avoid bloating WebSocket messages
            payload["description"] = description[:200] + "..."
        else:
            payload["description"] = description

        return payload

    @staticmethod
    def estimate_payload_size(payload: Dict[str, Any]) -> int:
        """Estimate the size of a WebSocket payload in bytes.

        This is useful for monitoring message sizes and ensuring they stay
        within reasonable limits (< 2KB recommended).

        Args:
            payload: The payload dictionary to measure

        Returns:
            Approximate size in bytes
        """
        import json
        return len(json.dumps(payload).encode('utf-8'))

    @staticmethod
    def build_lightweight_payload(task, task_response=None) -> Dict[str, Any]:
        """Build a lightweight payload for high-frequency updates.

        This variant excludes progress_history to minimize message size
        for scenarios like real-time progress updates where history is not needed.

        Args:
            task: Domain task entity
            task_response: Optional TaskResponse DTO

        Returns:
            Dictionary with essential task data (no progress history)
        """
        return WebSocketPayloadBuilder.build_task_payload(
            task,
            task_response,
            include_progress_history=False
        )
