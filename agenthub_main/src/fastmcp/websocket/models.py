"""
WebSocket Protocol v2.0 Message Models

Complete Pydantic models for WebSocket Protocol v2.0 with full cascade support.
NO backward compatibility - clean v2.0 implementation only.
"""

import uuid
from datetime import datetime
from typing import Any, Dict, List, Optional, Union

from pydantic import BaseModel, Field, ConfigDict

from .types import MessageType, EntityType, ActionType, SourceType, ProtocolVersion


class CascadeData(BaseModel):
    """
    Cascade data containing all affected entities for a change.

    This eliminates the need for secondary API calls by including
    all related entity data in the WebSocket message.
    """

    branches: List[Dict[str, Any]] = Field(
        default_factory=list,
        description="All affected branch entities with full data"
    )

    tasks: List[Dict[str, Any]] = Field(
        default_factory=list,
        description="All affected task entities with full data"
    )

    projects: List[Dict[str, Any]] = Field(
        default_factory=list,
        description="All affected project entities with full data"
    )

    subtasks: List[Dict[str, Any]] = Field(
        default_factory=list,
        description="All affected subtask entities with full data"
    )

    contexts: List[Dict[str, Any]] = Field(
        default_factory=list,
        description="All affected context entities with full data"
    )

    def get_total_entities(self) -> int:
        """Get total count of entities in cascade data"""
        return (
            len(self.branches) +
            len(self.tasks) +
            len(self.projects) +
            len(self.subtasks) +
            len(self.contexts)
        )

    def is_empty(self) -> bool:
        """Check if cascade data contains any entities"""
        return self.get_total_entities() == 0


class WSData(BaseModel):
    """
    WebSocket data payload with cascade and delta support.

    Contains the primary entity data plus all cascade information
    for efficient real-time updates.
    """

    primary: Union[Dict[str, Any], List[Dict[str, Any]]] = Field(
        description="Primary entity or entities being updated"
    )

    cascade: Optional[CascadeData] = Field(
        default=None,
        description="All affected entities (eliminates secondary API calls)"
    )

    delta: Optional[Dict[str, Any]] = Field(
        default=None,
        description="Delta patch for efficient large updates"
    )


class WSPayload(BaseModel):
    """
    WebSocket payload structure defining the operation and data.
    """

    entity: EntityType = Field(
        description="Type of entity being affected"
    )

    action: ActionType = Field(
        description="Action being performed on the entity"
    )

    data: WSData = Field(
        description="The actual data and cascade information"
    )


class WSMetadata(BaseModel):
    """
    WebSocket metadata for dual-track processing.

    Supports both immediate user updates and batched AI updates
    with proper source identification and correlation.
    """

    source: SourceType = Field(
        description="Source of the message (mcp-ai, user, system)"
    )

    user_id: Optional[str] = Field(
        default=None,
        description="User ID for authentication and tracking"
    )

    session_id: Optional[str] = Field(
        default=None,
        description="Session ID for connection management"
    )

    correlation_id: Optional[str] = Field(
        default=None,
        description="Correlation ID for request tracking"
    )

    batch_id: Optional[str] = Field(
        default=None,
        description="Batch ID for AI batched updates (500ms interval)"
    )

    immediate: bool = Field(
        default=True,
        description="True for user actions (immediate), False for AI batches"
    )


class WSMessage(BaseModel):
    """
    Base WebSocket message structure for Protocol v2.0.

    This is the root message type that all WebSocket communications
    must conform to. NO backward compatibility with v1.0.
    """

    id: str = Field(
        default_factory=lambda: str(uuid.uuid4()),
        description="Unique message identifier"
    )

    version: ProtocolVersion = Field(
        default="2.0",
        description="Protocol version - ONLY v2.0 supported"
    )

    type: MessageType = Field(
        description="Message type for routing and processing"
    )

    timestamp: datetime = Field(
        default_factory=datetime.utcnow,
        description="Message creation timestamp (UTC)"
    )

    sequence: int = Field(
        description="Message sequence number for ordering"
    )

    payload: WSPayload = Field(
        description="Message payload with entity data and cascade"
    )

    metadata: WSMetadata = Field(
        description="Metadata for source tracking and correlation"
    )

    model_config = ConfigDict(
        json_encoders={
            datetime: lambda v: v.isoformat(),
            uuid.UUID: str
        }
    )


# Specialized Message Types for Type Safety

class UserUpdateMessage(WSMessage):
    """
    User-initiated update message (immediate processing).

    These messages have immediate=True and source='user'.
    They include full cascade data for single entity updates.
    """

    type: MessageType = Field(default="update", description="Always 'update' for user messages")

    metadata: WSMetadata = Field(
        description="Metadata with source='user' and immediate=True"
    )

    def __init__(self, **data):
        # Ensure user message defaults
        if 'metadata' in data:
            data['metadata']['source'] = 'user'
            data['metadata']['immediate'] = True
        super().__init__(**data)


class AIBatchMessage(WSMessage):
    """
    AI-initiated batch update message (500ms batching).

    These messages have immediate=False and source='mcp-ai'.
    They include combined cascade data for multiple entity updates.
    """

    type: MessageType = Field(default="bulk", description="Always 'bulk' for AI batch messages")

    metadata: WSMetadata = Field(
        description="Metadata with source='mcp-ai' and immediate=False"
    )

    def __init__(self, **data):
        # Ensure AI batch message defaults
        if 'metadata' in data:
            data['metadata']['source'] = 'mcp-ai'
            data['metadata']['immediate'] = False
        super().__init__(**data)


class SystemMessage(WSMessage):
    """Base class for system messages (heartbeat, error, sync)."""

    metadata: WSMetadata = Field(
        description="Metadata with source='system'"
    )

    def __init__(self, **data):
        # Ensure system message defaults
        if 'metadata' in data:
            data['metadata']['source'] = 'system'
        super().__init__(**data)


class HeartbeatMessage(SystemMessage):
    """Heartbeat message for connection management."""

    type: MessageType = Field(default="heartbeat", description="Always 'heartbeat'")


class ErrorMessage(SystemMessage):
    """Error message with detailed context."""

    type: MessageType = Field(default="error", description="Always 'error'")


class SyncMessage(SystemMessage):
    """Sync message for client reconnection."""

    type: MessageType = Field(default="sync", description="Always 'sync'")