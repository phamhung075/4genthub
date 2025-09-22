"""
WebSocket Protocol v2.0 Package

This package provides the complete WebSocket protocol v2.0 implementation
for real-time communication with full cascade support. NO backward
compatibility with v1.0 - clean implementation only.
"""

from .models import (
    WSMessage,
    WSPayload,
    WSData,
    WSMetadata,
    CascadeData,
    UserUpdateMessage,
    AIBatchMessage,
    SystemMessage,
    HeartbeatMessage,
    ErrorMessage,
    SyncMessage,
)
from .protocol import (
    validate_message,
    create_user_update,
    create_ai_batch,
    create_heartbeat,
    create_error,
    create_sync,
    get_message_size,
    is_message_size_valid,
    MessageSizeError,
    ProtocolError,
    InvalidVersionError,
)
from .types import MessageType, EntityType, SourceType
from .server import WebSocketServer, initialize_websocket_server
from .connection_manager import ConnectionManager
from .batch_processor import BatchProcessor

__all__ = [
    # Models
    "WSMessage",
    "WSPayload",
    "WSData",
    "WSMetadata",
    "CascadeData",
    "UserUpdateMessage",
    "AIBatchMessage",
    "SystemMessage",
    "HeartbeatMessage",
    "ErrorMessage",
    "SyncMessage",
    # Protocol functions
    "validate_message",
    "create_user_update",
    "create_ai_batch",
    "create_heartbeat",
    "create_error",
    "create_sync",
    "get_message_size",
    "is_message_size_valid",
    # Exceptions
    "MessageSizeError",
    "ProtocolError",
    "InvalidVersionError",
    # Types
    "MessageType",
    "EntityType",
    "SourceType",
    # Server components
    "WebSocketServer",
    "initialize_websocket_server",
    "ConnectionManager",
    "BatchProcessor",
]