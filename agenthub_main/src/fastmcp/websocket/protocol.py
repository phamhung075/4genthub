"""
WebSocket Protocol v2.0 Implementation

Main protocol implementation with validation, message creation, and cascade integration.
NO backward compatibility - clean v2.0 implementation only.
"""

import json
import logging
import uuid
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional, Union

from pydantic import ValidationError

from ..task_management.domain.services.cascade_calculator import (
    CascadeCalculator,
    CascadeResult,
    EntityType as CascadeEntityType
)
from .models import (
    WSMessage,
    WSPayload,
    WSData,
    WSMetadata,
    CascadeData,
    UserUpdateMessage,
    AIBatchMessage,
    HeartbeatMessage,
    ErrorMessage,
    SyncMessage,
)
from .types import MessageType, EntityType, ActionType, SourceType

logger = logging.getLogger(__name__)

# Maximum message size (64KB)
MAX_MESSAGE_SIZE_BYTES = 64 * 1024


class ProtocolError(Exception):
    """Base exception for WebSocket protocol errors."""
    pass


class MessageSizeError(ProtocolError):
    """Exception raised when message exceeds size limit."""
    pass


class InvalidVersionError(ProtocolError):
    """Exception raised when message version is not v2.0."""
    pass


def validate_message(message: Dict[str, Any]) -> WSMessage:
    """
    Validate and parse a WebSocket message according to v2.0 protocol.

    Args:
        message: Raw message dictionary from WebSocket

    Returns:
        Validated WSMessage instance

    Raises:
        InvalidVersionError: If version is not 2.0
        ValidationError: If message structure is invalid
        MessageSizeError: If message exceeds size limit
    """
    # CRITICAL: NO backward compatibility - only v2.0
    if message.get("version") != "2.0":
        raise InvalidVersionError(f"Only protocol v2.0 is supported, got: {message.get('version')}")

    # Check message size
    message_json = json.dumps(message)
    message_size = len(message_json.encode('utf-8'))

    if message_size > MAX_MESSAGE_SIZE_BYTES:
        raise MessageSizeError(
            f"Message size {message_size} bytes exceeds limit of {MAX_MESSAGE_SIZE_BYTES} bytes"
        )

    try:
        return WSMessage(**message)
    except ValidationError as e:
        logger.error(f"Message validation failed: {e}")
        raise ProtocolError(f"Invalid message structure: {e}")


async def create_user_update(
    entity_type: EntityType,
    action: ActionType,
    primary_data: Union[Dict[str, Any], List[Dict[str, Any]]],
    cascade_calculator: Optional[CascadeCalculator] = None,
    entity_id: Optional[str] = None,
    user_id: Optional[str] = None,
    session_id: Optional[str] = None,
    correlation_id: Optional[str] = None,
    sequence: int = 0
) -> UserUpdateMessage:
    """
    Create a user-initiated update message with cascade data.

    Args:
        entity_type: Type of entity being updated
        action: Action being performed
        primary_data: Primary entity data
        cascade_calculator: Optional cascade calculator for affected entities
        entity_id: ID of the entity (for cascade calculation)
        user_id: User ID for authentication
        session_id: Session ID for tracking
        correlation_id: Correlation ID for request tracking
        sequence: Message sequence number

    Returns:
        UserUpdateMessage with full cascade data
    """
    # Calculate cascade data if calculator and entity_id provided
    cascade_data = None
    if cascade_calculator and entity_id:
        try:
            # Map entity types
            cascade_entity_type = _map_entity_type(entity_type)
            cascade_result = await cascade_calculator.calculate_cascade(
                entity_id=entity_id,
                entity_type=cascade_entity_type
            )
            cascade_data = _convert_cascade_result(cascade_result)
        except Exception as e:
            logger.warning(f"Failed to calculate cascade for {entity_id}: {e}")

    # Create WSData with cascade
    ws_data = WSData(
        primary=primary_data,
        cascade=cascade_data
    )

    # Create payload
    payload = WSPayload(
        entity=entity_type,
        action=action,
        data=ws_data
    )

    # Create metadata for user update
    metadata = WSMetadata(
        source="user",
        user_id=user_id,
        session_id=session_id,
        correlation_id=correlation_id,
        immediate=True
    )

    return UserUpdateMessage(
        type="update",
        sequence=sequence,
        payload=payload,
        metadata=metadata
    )


async def create_ai_batch(
    updates: List[Dict[str, Any]],
    batch_id: str,
    cascade_calculator: Optional[CascadeCalculator] = None,
    user_id: Optional[str] = None,
    sequence: int = 0
) -> AIBatchMessage:
    """
    Create an AI-initiated batch update message.

    Args:
        updates: List of update operations
        batch_id: Unique batch ID for 500ms interval batching
        cascade_calculator: Optional cascade calculator
        user_id: User ID for context
        sequence: Message sequence number

    Returns:
        AIBatchMessage with combined cascade data
    """
    # Combine all cascade data from multiple updates
    combined_cascade = CascadeData()

    if cascade_calculator:
        for update in updates:
            entity_id = update.get('entity_id')
            entity_type = update.get('entity_type')

            if entity_id and entity_type:
                try:
                    cascade_entity_type = _map_entity_type(entity_type)
                    cascade_result = await cascade_calculator.calculate_cascade(
                        entity_id=entity_id,
                        entity_type=cascade_entity_type
                    )
                    _merge_cascade_data(combined_cascade, cascade_result)
                except Exception as e:
                    logger.warning(f"Failed to calculate cascade for {entity_id}: {e}")

    # Create WSData with combined updates
    ws_data = WSData(
        primary=updates,
        cascade=combined_cascade if not combined_cascade.is_empty() else None
    )

    # Create payload for multiple entities
    payload = WSPayload(
        entity="multiple",
        action="batch",
        data=ws_data
    )

    # Create metadata for AI batch
    metadata = WSMetadata(
        source="mcp-ai",
        user_id=user_id,
        batch_id=batch_id,
        immediate=False
    )

    return AIBatchMessage(
        type="bulk",
        sequence=sequence,
        payload=payload,
        metadata=metadata
    )


def create_heartbeat(
    session_id: Optional[str] = None,
    sequence: int = 0
) -> HeartbeatMessage:
    """
    Create a heartbeat message for connection management.

    Args:
        session_id: Session ID for tracking
        sequence: Message sequence number

    Returns:
        HeartbeatMessage
    """
    # Heartbeat payload is minimal
    ws_data = WSData(primary={"status": "alive"})

    payload = WSPayload(
        entity="multiple",
        action="update",
        data=ws_data
    )

    metadata = WSMetadata(
        source="system",
        session_id=session_id,
        immediate=True
    )

    return HeartbeatMessage(
        sequence=sequence,
        payload=payload,
        metadata=metadata
    )


def create_error(
    error_message: str,
    error_code: Optional[str] = None,
    error_details: Optional[Dict[str, Any]] = None,
    session_id: Optional[str] = None,
    correlation_id: Optional[str] = None,
    sequence: int = 0
) -> ErrorMessage:
    """
    Create an error message with detailed context.

    Args:
        error_message: Human-readable error message
        error_code: Optional error code for programmatic handling
        error_details: Optional additional error details
        session_id: Session ID for tracking
        correlation_id: Correlation ID for request tracking
        sequence: Message sequence number

    Returns:
        ErrorMessage
    """
    error_data = {
        "message": error_message,
        "timestamp": datetime.now(timezone.utc).isoformat()
    }

    if error_code:
        error_data["code"] = error_code

    if error_details:
        error_data["details"] = error_details

    ws_data = WSData(primary=error_data)

    payload = WSPayload(
        entity="multiple",
        action="update",
        data=ws_data
    )

    metadata = WSMetadata(
        source="system",
        session_id=session_id,
        correlation_id=correlation_id,
        immediate=True
    )

    return ErrorMessage(
        sequence=sequence,
        payload=payload,
        metadata=metadata
    )


def create_sync(
    sync_data: Dict[str, Any],
    session_id: Optional[str] = None,
    user_id: Optional[str] = None,
    sequence: int = 0
) -> SyncMessage:
    """
    Create a sync message for client reconnection.

    Args:
        sync_data: Synchronization data for client state
        session_id: Session ID for tracking
        user_id: User ID for context
        sequence: Message sequence number

    Returns:
        SyncMessage
    """
    ws_data = WSData(primary=sync_data)

    payload = WSPayload(
        entity="multiple",
        action="update",
        data=ws_data
    )

    metadata = WSMetadata(
        source="system",
        session_id=session_id,
        user_id=user_id,
        immediate=True
    )

    return SyncMessage(
        sequence=sequence,
        payload=payload,
        metadata=metadata
    )


# Helper Functions

def _map_entity_type(entity_type: EntityType) -> CascadeEntityType:
    """Map WebSocket entity type to cascade calculator entity type."""
    mapping = {
        "task": CascadeEntityType.TASK,
        "subtask": CascadeEntityType.SUBTASK,
        "branch": CascadeEntityType.BRANCH,
        "project": CascadeEntityType.PROJECT,
        "context": CascadeEntityType.CONTEXT,
    }

    if entity_type not in mapping:
        raise ValueError(f"Unsupported entity type for cascade: {entity_type}")

    return mapping[entity_type]


def _convert_cascade_result(cascade_result: CascadeResult) -> CascadeData:
    """Convert CascadeResult to CascadeData model."""
    return CascadeData(
        branches=[{"id": bid} for bid in cascade_result.affected_branches],
        tasks=[{"id": tid} for tid in cascade_result.affected_tasks],
        projects=[{"id": pid} for pid in cascade_result.affected_projects],
        subtasks=[{"id": sid} for sid in cascade_result.affected_subtasks],
        contexts=[{"id": cid} for cid in cascade_result.affected_contexts],
    )


def _merge_cascade_data(target: CascadeData, cascade_result: CascadeResult) -> None:
    """Merge cascade result into existing cascade data."""
    # Add new entities, avoiding duplicates
    existing_branch_ids = {b.get("id") for b in target.branches}
    existing_task_ids = {t.get("id") for t in target.tasks}
    existing_project_ids = {p.get("id") for p in target.projects}
    existing_subtask_ids = {s.get("id") for s in target.subtasks}
    existing_context_ids = {c.get("id") for c in target.contexts}

    # Add new branches
    for bid in cascade_result.affected_branches:
        if bid not in existing_branch_ids:
            target.branches.append({"id": bid})

    # Add new tasks
    for tid in cascade_result.affected_tasks:
        if tid not in existing_task_ids:
            target.tasks.append({"id": tid})

    # Add new projects
    for pid in cascade_result.affected_projects:
        if pid not in existing_project_ids:
            target.projects.append({"id": pid})

    # Add new subtasks
    for sid in cascade_result.affected_subtasks:
        if sid not in existing_subtask_ids:
            target.subtasks.append({"id": sid})

    # Add new contexts
    for cid in cascade_result.affected_contexts:
        if cid not in existing_context_ids:
            target.contexts.append({"id": cid})


def get_message_size(message: WSMessage) -> int:
    """
    Get the size of a message in bytes when serialized to JSON.

    Args:
        message: WSMessage to measure

    Returns:
        Size in bytes
    """
    message_json = message.model_dump_json()
    return len(message_json.encode('utf-8'))


def is_message_size_valid(message: WSMessage) -> bool:
    """
    Check if message size is within the 64KB limit.

    Args:
        message: WSMessage to check

    Returns:
        True if message is within size limit
    """
    return get_message_size(message) <= MAX_MESSAGE_SIZE_BYTES