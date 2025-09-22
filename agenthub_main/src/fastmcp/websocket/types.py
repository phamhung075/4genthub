"""
WebSocket Protocol v2.0 Type Definitions

Defines all the type literals and enums used in the WebSocket protocol.
Clean implementation with NO backward compatibility.
"""

from typing import Literal

# Message Types
MessageType = Literal["update", "bulk", "sync", "heartbeat", "error"]

# Entity Types
EntityType = Literal["task", "branch", "project", "subtask", "context", "multiple"]

# Action Types
ActionType = Literal["create", "update", "delete", "batch"]

# Source Types - identifies who/what sent the message
SourceType = Literal["mcp-ai", "user", "system"]

# Protocol Version - ONLY v2.0 supported
ProtocolVersion = Literal["2.0"]