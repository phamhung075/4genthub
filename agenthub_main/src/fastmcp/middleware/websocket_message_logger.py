"""
WebSocket Message Logger and Validator

This module provides runtime logging and validation for WebSocket messages.
It intercepts WebSocket broadcasts to validate message structure and content.

Purpose:
- Log all WebSocket messages for debugging
- Validate message structure against expected schemas
- Detect missing or incorrect fields in real-time updates
- Track cascade updates and their completeness

Environment Variables:
- LOG_WEBSOCKET_MESSAGES: Enable/disable logging (default: True in dev)
- WS_LOG_LEVEL: error|warning|info|debug (default: info)
- WS_VALIDATION_ENABLED: Enable schema validation (default: True)
"""

import json
import logging
import os
from typing import Dict, Any, List, Optional
from datetime import datetime, timezone
from enum import Enum

logger = logging.getLogger(__name__)

# Configuration
LOG_WEBSOCKET_MESSAGES = os.getenv("LOG_WEBSOCKET_MESSAGES", "true").lower() in ("true", "1", "yes")
WS_LOG_LEVEL = os.getenv("WS_LOG_LEVEL", "info").lower()
WS_VALIDATION_ENABLED = os.getenv("WS_VALIDATION_ENABLED", "true").lower() in ("true", "1", "yes")


class WebSocketEventType(str, Enum):
    """Known WebSocket event types"""
    TASK_CREATED = "task.created"
    TASK_UPDATED = "task.updated"
    TASK_DELETED = "task.deleted"
    TASK_COMPLETED = "task.completed"
    SUBTASK_CREATED = "subtask.created"
    SUBTASK_UPDATED = "subtask.updated"
    SUBTASK_DELETED = "subtask.deleted"
    SUBTASK_COMPLETED = "subtask.completed"
    BRANCH_UPDATED = "branch.updated"
    PROJECT_UPDATED = "project.updated"
    CONTEXT_UPDATED = "context.updated"


class WebSocketMessageValidator:
    """Validates WebSocket message structure and content"""

    # Base message structure
    BASE_MESSAGE_SCHEMA = {
        "event": {"type": str, "required": True},
        "data": {"type": dict, "required": True},
    }

    # Task event data schema
    TASK_EVENT_DATA_SCHEMA = {
        "id": {"type": str, "required": True},
        "title": {"type": str, "required": True},
        "status": {"type": str, "required": True},
        "priority": {"type": str, "required": True},
        "assignees": {"type": list, "required": True},
        "subtask_count": {"type": int, "required": True},
        "completed_subtasks": {"type": int, "required": True},
        "progress_percentage": {"type": int, "required": True},
        "progress_count": {"type": int, "required": True},
        "created_at": {"type": str, "required": True},
        "updated_at": {"type": str, "required": True},
        # Optional fields
        "project_id": {"type": str, "required": False},
        "git_branch_id": {"type": str, "required": False},
        "description": {"type": str, "required": False},
        "details": {"type": str, "required": False},
        "labels": {"type": list, "required": False},
    }

    # Subtask event data schema
    SUBTASK_EVENT_DATA_SCHEMA = {
        "id": {"type": str, "required": True},
        "title": {"type": str, "required": True},
        "status": {"type": str, "required": True},
        "priority": {"type": str, "required": True},
        "parent_task_id": {"type": str, "required": True},
        "assignees": {"type": list, "required": True},
        "progress_percentage": {"type": int, "required": True},
        "created_at": {"type": str, "required": True},
        "updated_at": {"type": str, "required": True},
    }

    @classmethod
    def validate_message(cls, message: Dict[str, Any]) -> List[str]:
        """
        Validate a WebSocket message structure.

        Args:
            message: The WebSocket message to validate

        Returns:
            List of validation error messages (empty if valid)
        """
        errors = []

        # Validate base structure
        if not isinstance(message, dict):
            errors.append("Message must be a dictionary")
            return errors

        # Check required fields
        if "event" not in message:
            errors.append("Missing required field: 'event'")
        elif not isinstance(message["event"], str):
            errors.append("Field 'event' must be a string")

        if "data" not in message:
            errors.append("Missing required field: 'data'")
        elif not isinstance(message["data"], dict):
            errors.append("Field 'data' must be a dictionary")
            return errors  # Can't validate data if it's not a dict

        # Validate data based on event type
        event = message.get("event", "")
        data = message.get("data", {})

        if event.startswith("task."):
            errors.extend(cls._validate_task_event_data(data, event))
        elif event.startswith("subtask."):
            errors.extend(cls._validate_subtask_event_data(data, event))

        return errors

    @classmethod
    def _validate_task_event_data(cls, data: Dict[str, Any], event: str) -> List[str]:
        """Validate task event data"""
        errors = []

        for field_name, field_spec in cls.TASK_EVENT_DATA_SCHEMA.items():
            is_required = field_spec.get("required", False)
            expected_type = field_spec.get("type")

            if field_name not in data:
                if is_required:
                    errors.append(f"Task event '{event}': Missing required field '{field_name}'")
            elif data[field_name] is None:
                if is_required:
                    errors.append(f"Task event '{event}': Required field '{field_name}' is null")
            elif expected_type and not isinstance(data[field_name], expected_type):
                errors.append(
                    f"Task event '{event}': Field '{field_name}' has wrong type "
                    f"(expected {expected_type.__name__}, got {type(data[field_name]).__name__})"
                )

        # Specific validations for critical fields
        if "subtask_count" in data and "completed_subtasks" in data:
            subtask_count = data.get("subtask_count", 0)
            completed_subtasks = data.get("completed_subtasks", 0)

            if completed_subtasks > subtask_count:
                errors.append(
                    f"Task event '{event}': completed_subtasks ({completed_subtasks}) "
                    f"exceeds subtask_count ({subtask_count})"
                )

        if "assignees" in data:
            assignees = data.get("assignees", [])
            if not isinstance(assignees, list):
                errors.append(f"Task event '{event}': assignees must be a list, got {type(assignees).__name__}")
            elif assignees:  # If not empty, validate format
                for idx, assignee in enumerate(assignees):
                    if not isinstance(assignee, str):
                        errors.append(f"Task event '{event}': assignees[{idx}] must be string")

        return errors

    @classmethod
    def _validate_subtask_event_data(cls, data: Dict[str, Any], event: str) -> List[str]:
        """Validate subtask event data"""
        errors = []

        for field_name, field_spec in cls.SUBTASK_EVENT_DATA_SCHEMA.items():
            is_required = field_spec.get("required", False)
            expected_type = field_spec.get("type")

            if field_name not in data:
                if is_required:
                    errors.append(f"Subtask event '{event}': Missing required field '{field_name}'")
            elif data[field_name] is None:
                if is_required:
                    errors.append(f"Subtask event '{event}': Required field '{field_name}' is null")
            elif expected_type and not isinstance(data[field_name], expected_type):
                errors.append(
                    f"Subtask event '{event}': Field '{field_name}' has wrong type "
                    f"(expected {expected_type.__name__}, got {type(data[field_name]).__name__})"
                )

        return errors


class WebSocketMessageLogger:
    """
    Logger for WebSocket messages with validation.

    This class can be used to wrap WebSocket broadcast calls to add
    logging and validation.
    """

    def __init__(self):
        self.message_count = 0
        self.error_count = 0
        self.validation_errors = []
        logger.info(f"WebSocketMessageLogger initialized (logging={LOG_WEBSOCKET_MESSAGES}, validation={WS_VALIDATION_ENABLED})")

    def log_message(
        self,
        event: str,
        data: Dict[str, Any],
        user_id: Optional[str] = None,
        validate: bool = True
    ) -> List[str]:
        """
        Log and optionally validate a WebSocket message.

        Args:
            event: Event type (e.g., "task.created")
            data: Event data payload
            user_id: Optional user ID receiving the message
            validate: Whether to validate the message

        Returns:
            List of validation errors (empty if valid or validation disabled)
        """
        self.message_count += 1

        message = {
            "event": event,
            "data": data,
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }

        # Log the message
        if LOG_WEBSOCKET_MESSAGES:
            log_msg = f"📡 WS Message #{self.message_count}: {event}"
            if user_id:
                log_msg += f" (user: {user_id})"

            if WS_LOG_LEVEL == "debug":
                # Include full data in debug mode
                log_msg += f"\n  Data: {json.dumps(data, indent=2)}"

            logger.info(log_msg)

        # Validate if enabled
        validation_errors = []
        if validate and WS_VALIDATION_ENABLED:
            validation_errors = WebSocketMessageValidator.validate_message(message)

            if validation_errors:
                self.error_count += 1
                self.validation_errors.extend(validation_errors)

                logger.error(
                    f"🚨 WebSocket Message Validation FAILED for event '{event}':\n" +
                    "\n".join([f"  - {error}" for error in validation_errors])
                )

        return validation_errors

    def get_stats(self) -> Dict[str, Any]:
        """Get logging statistics"""
        return {
            "total_messages": self.message_count,
            "validation_errors": self.error_count,
            "error_rate": f"{(self.error_count / max(self.message_count, 1)) * 100:.1f}%",
            "recent_errors": self.validation_errors[-10:] if self.validation_errors else []
        }


# Global instance for easy access
_global_logger = WebSocketMessageLogger()


def log_websocket_message(
    event: str,
    data: Dict[str, Any],
    user_id: Optional[str] = None,
    validate: bool = True
) -> List[str]:
    """
    Log a WebSocket message using the global logger.

    This is a convenience function for easy integration with existing code.

    Args:
        event: Event type
        data: Event data
        user_id: Optional user ID
        validate: Whether to validate

    Returns:
        List of validation errors
    """
    return _global_logger.log_message(event, data, user_id, validate)


def get_websocket_logger() -> WebSocketMessageLogger:
    """Get the global WebSocket logger instance"""
    return _global_logger


def get_websocket_stats() -> Dict[str, Any]:
    """Get WebSocket logging statistics"""
    return _global_logger.get_stats()
