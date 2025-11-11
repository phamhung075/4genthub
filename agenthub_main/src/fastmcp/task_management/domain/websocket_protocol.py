"""
WebSocket Protocol v2.0 - Type-Safe Communication Models (Python)

SINGLE SOURCE OF TRUTH for WebSocket message structure
- Mirrors TypeScript types in agenthub-frontend/src/types/websocket-protocol.ts
- Provides runtime validation via Pydantic
- Enforces required fields before sending messages
- Prevents payload inconsistency bugs

USAGE:
    from fastmcp.task_management.domain.websocket_protocol import (
        BranchDeletePayload,
        WSMessage,
        create_delete_message
    )

    # Type-safe payload construction
    payload = BranchDeletePayload(
        id=branch_id,
        name=branch_name,
        project_id=project_id
    )

    # Validated WebSocket message
    message = create_delete_message(
        entity='branch',
        payload=payload,
        user_id=user_id
    )
"""

from __future__ import annotations

import uuid
from datetime import datetime
from typing import Any, Literal

from pydantic import BaseModel, Field, field_validator

# =============================================================================
# ENTITY PAYLOAD MODELS - CRUD Operations
# =============================================================================

# -----------------------------------------------------------------------------
# PROJECT PAYLOADS
# -----------------------------------------------------------------------------


class ProjectCreatePayload(BaseModel):
    """Project creation WebSocket payload"""

    id: str
    name: str
    description: str | None = None
    created_at: str | None = None
    updated_at: str | None = None


class ProjectUpdatePayload(BaseModel):
    """Project update WebSocket payload"""

    id: str
    name: str
    description: str | None = None
    updated_at: str | None = None


class ProjectDeletePayload(BaseModel):
    """
    Project deletion WebSocket payload

    REQUIRED FIELDS:
    - id: For frontend cache operations
    - name: For toast notification display
    """

    id: str = Field(..., description="Project UUID - REQUIRED for frontend handler")
    name: str = Field(..., description="Project name - REQUIRED for toast notification")

    @field_validator("id")
    @classmethod
    def validate_id(cls, v: str) -> str:
        if not v or not v.strip():
            raise ValueError("Project ID cannot be empty")
        return v

    @field_validator("name")
    @classmethod
    def validate_name(cls, v: str) -> str:
        if not v or not v.strip():
            raise ValueError("Project name cannot be empty")
        return v


# -----------------------------------------------------------------------------
# BRANCH PAYLOADS
# -----------------------------------------------------------------------------


class BranchCreatePayload(BaseModel):
    """Branch creation WebSocket payload"""

    id: str
    name: str
    git_branch_name: str
    project_id: str
    description: str | None = None
    status: str | None = None
    created_at: str | None = None


class BranchUpdatePayload(BaseModel):
    """Branch update WebSocket payload"""

    id: str
    name: str
    git_branch_name: str
    project_id: str
    description: str | None = None
    status: str | None = None
    updated_at: str | None = None


class BranchDeletePayload(BaseModel):
    """
    Branch deletion WebSocket payload

    REQUIRED FIELDS:
    - id: For frontend cache operations
    - name: For toast notification display
    - project_id: For cache invalidation of parent project
    """

    id: str = Field(..., description="Branch UUID - REQUIRED for frontend handler")
    name: str = Field(..., description="Branch name - REQUIRED for toast notification")
    project_id: str = Field(
        ..., description="Parent project UUID - REQUIRED for cache invalidation"
    )

    @field_validator("id", "project_id")
    @classmethod
    def validate_id(cls, v: str) -> str:
        if not v or not v.strip():
            raise ValueError("ID cannot be empty")
        return v

    @field_validator("name")
    @classmethod
    def validate_name(cls, v: str) -> str:
        if not v or not v.strip():
            raise ValueError("Branch name cannot be empty")
        return v


# -----------------------------------------------------------------------------
# TASK PAYLOADS
# -----------------------------------------------------------------------------


class TaskCreatePayload(BaseModel):
    """Task creation WebSocket payload"""

    id: str
    title: str
    description: str | None = None
    status: str
    priority: str
    git_branch_id: str
    assignees: list[str] | None = None
    labels: list[str] | None = None
    created_at: str | None = None


class TaskUpdatePayload(BaseModel):
    """Task update WebSocket payload"""

    id: str
    title: str
    description: str | None = None
    status: str
    priority: str
    git_branch_id: str
    assignees: list[str] | None = None
    labels: list[str] | None = None
    updated_at: str | None = None


class TaskDeletePayload(BaseModel):
    """
    Task deletion WebSocket payload

    REQUIRED FIELDS:
    - id: For frontend cache operations
    - title: For toast notification display
    - git_branch_id: For cache invalidation of parent branch (optional but recommended)
    """

    id: str = Field(..., description="Task UUID - REQUIRED for frontend handler")
    title: str = Field(..., description="Task title - REQUIRED for toast notification")
    git_branch_id: str | None = Field(
        None, description="Parent branch UUID - for cache invalidation"
    )

    @field_validator("id")
    @classmethod
    def validate_id(cls, v: str) -> str:
        if not v or not v.strip():
            raise ValueError("Task ID cannot be empty")
        return v

    @field_validator("title")
    @classmethod
    def validate_title(cls, v: str) -> str:
        if not v or not v.strip():
            raise ValueError("Task title cannot be empty")
        return v


class TaskCompletePayload(BaseModel):
    """Task completion WebSocket payload"""

    id: str
    title: str
    status: Literal["done"] = "done"
    completion_summary: str | None = None
    testing_notes: str | None = None
    completed_at: str | None = None


# -----------------------------------------------------------------------------
# SUBTASK PAYLOADS
# -----------------------------------------------------------------------------


class SubtaskCreatePayload(BaseModel):
    """Subtask creation WebSocket payload"""

    id: str
    title: str
    description: str | None = None
    status: str
    task_id: str
    progress_percentage: int | None = None
    created_at: str | None = None
    updated_at: str | None = (
        None  # ✅ FIX: Added to match frontend validator requirements
    )


class SubtaskUpdatePayload(BaseModel):
    """Subtask update WebSocket payload"""

    id: str
    title: str
    description: str | None = None
    status: str
    task_id: str
    progress_percentage: int | None = None
    created_at: str | None = (
        None  # ✅ FIX: Added to match frontend validator requirements
    )
    updated_at: str | None = None


class SubtaskDeletePayload(BaseModel):
    """
    Subtask deletion WebSocket payload

    REQUIRED FIELDS:
    - id: For frontend cache operations
    - task_id: For cache invalidation of parent task
    - title: For toast notification (optional but recommended)
    """

    id: str = Field(..., description="Subtask UUID - REQUIRED for frontend handler")
    task_id: str = Field(
        ..., description="Parent task UUID - REQUIRED for cache invalidation"
    )
    title: str | None = Field(
        None, description="Subtask title - for toast notification"
    )

    @field_validator("id", "task_id")
    @classmethod
    def validate_id(cls, v: str) -> str:
        if not v or not v.strip():
            raise ValueError("ID cannot be empty")
        return v


class SubtaskCompletePayload(BaseModel):
    """Subtask completion WebSocket payload"""

    id: str
    title: str
    status: Literal["done"] = "done"
    task_id: str
    completion_summary: str | None = None
    progress_percentage: Literal[100] = 100
    created_at: str | None = (
        None  # ✅ FIX: Added to match frontend validator requirements
    )
    updated_at: str | None = (
        None  # ✅ FIX: Added to match frontend validator requirements
    )
    completed_at: str | None = None


# =============================================================================
# WEBSOCKET MESSAGE STRUCTURE (v2.0)
# =============================================================================


class WSMetadata(BaseModel):
    """WebSocket metadata - contextual information"""

    source: Literal["mcp-ai", "user", "system"]
    userId: str | None = None
    sessionId: str | None = None
    correlationId: str | None = None

    # Entity context
    entity_type: str | None = None
    entity_id: str | None = None
    event_type: str | None = None

    # Entity-specific metadata
    project_id: str | None = None
    git_branch_id: str | None = None
    task_id: str | None = None

    # Display metadata (for toasts)
    project_name: str | None = None
    branch_title: str | None = None
    task_title: str | None = None
    subtask_title: str | None = None

    timestamp: str | None = None

    class Config:
        extra = "allow"  # Allow additional metadata fields


class WSPayloadData(BaseModel):
    """WebSocket payload data structure"""

    primary: dict[str, Any] = Field(
        ..., description="Main entity data - MUST include 'id' field"
    )
    cascade: dict[str, list[Any]] | None = Field(
        None, description="Related entities updated"
    )

    @field_validator("primary")
    @classmethod
    def validate_primary_has_id(cls, v: dict[str, Any]) -> dict[str, Any]:
        if "id" not in v:
            raise ValueError("Payload primary data MUST include 'id' field")
        return v


class WSPayload(BaseModel):
    """WebSocket payload structure"""

    entity: Literal["project", "branch", "task", "subtask", "context", "agent"]
    action: Literal[
        "created", "updated", "deleted", "completed", "assigned", "unassigned"
    ]
    data: WSPayloadData


class WSMessage(BaseModel):
    """Complete WebSocket message (v2.0 protocol)"""

    id: str = Field(default_factory=lambda: f"ws-{uuid.uuid4().hex[:12]}")
    version: Literal["2.0"] = "2.0"
    type: Literal["update", "bulk", "sync", "heartbeat", "error"]
    timestamp: str = Field(default_factory=lambda: datetime.utcnow().isoformat())
    sequence: int = Field(default_factory=lambda: 0)
    payload: WSPayload
    metadata: WSMetadata


# =============================================================================
# MESSAGE FACTORY FUNCTIONS
# =============================================================================


def create_delete_message(
    entity: Literal["project", "branch", "task", "subtask"],
    payload: ProjectDeletePayload
    | BranchDeletePayload
    | TaskDeletePayload
    | SubtaskDeletePayload,
    user_id: str,
    metadata_overrides: dict[str, Any] | None = None,
) -> WSMessage:
    """
    Create type-safe WebSocket message for DELETE operations

    Args:
        entity: Entity type being deleted
        payload: Typed delete payload (validated by Pydantic)
        user_id: User performing the delete
        metadata_overrides: Additional metadata fields

    Returns:
        Validated WSMessage ready to send

    Example:
        >>> payload = BranchDeletePayload(id="uuid", name="test-branch", project_id="project-uuid")
        >>> message = create_delete_message('branch', payload, 'user-123')
        >>> # message is fully validated and type-safe
    """
    # Convert payload to dict (already validated by Pydantic)
    payload_dict = payload.model_dump()

    # Build metadata
    metadata = WSMetadata(
        source="user",
        userId=user_id,
        entity_type=entity,
        entity_id=payload_dict["id"],
        event_type="deleted",
        **(metadata_overrides or {}),
    )

    # Build payload
    ws_payload = WSPayload(
        entity=entity, action="deleted", data=WSPayloadData(primary=payload_dict)
    )

    # Create complete message
    return WSMessage(type="update", payload=ws_payload, metadata=metadata)


def create_update_message(
    entity: Literal["project", "branch", "task", "subtask"],
    payload: ProjectUpdatePayload
    | BranchUpdatePayload
    | TaskUpdatePayload
    | SubtaskUpdatePayload,
    user_id: str,
    metadata_overrides: dict[str, Any] | None = None,
) -> WSMessage:
    """Create type-safe WebSocket message for UPDATE operations"""
    payload_dict = payload.model_dump()

    metadata = WSMetadata(
        source="user",
        userId=user_id,
        entity_type=entity,
        entity_id=payload_dict["id"],
        event_type="updated",
        **(metadata_overrides or {}),
    )

    ws_payload = WSPayload(
        entity=entity, action="updated", data=WSPayloadData(primary=payload_dict)
    )

    return WSMessage(type="update", payload=ws_payload, metadata=metadata)


def create_create_message(
    entity: Literal["project", "branch", "task", "subtask"],
    payload: ProjectCreatePayload
    | BranchCreatePayload
    | TaskCreatePayload
    | SubtaskCreatePayload,
    user_id: str,
    metadata_overrides: dict[str, Any] | None = None,
) -> WSMessage:
    """Create type-safe WebSocket message for CREATE operations"""
    payload_dict = payload.model_dump()

    metadata = WSMetadata(
        source="user",
        userId=user_id,
        entity_type=entity,
        entity_id=payload_dict["id"],
        event_type="created",
        **(metadata_overrides or {}),
    )

    ws_payload = WSPayload(
        entity=entity, action="created", data=WSPayloadData(primary=payload_dict)
    )

    return WSMessage(type="update", payload=ws_payload, metadata=metadata)


# =============================================================================
# VALIDATION HELPERS
# =============================================================================


def validate_delete_payload(data: dict[str, Any]) -> tuple[bool, list[str]]:
    """
    Validate delete payload follows required pattern

    Returns:
        (is_valid, error_messages)
    """
    errors = []

    # Check required: id
    if not data.get("id"):
        errors.append("Missing required field: id (string)")

    # Check required: name OR title
    if not data.get("name") and not data.get("title"):
        errors.append("Missing required field: name or title (string)")

    return (len(errors) == 0, errors)


# =============================================================================
# MIGRATION HELPERS - Convert Legacy to Type-Safe
# =============================================================================


def convert_branch_delete_legacy(
    branch_id: str, branch_name: str, project_id: str
) -> BranchDeletePayload:
    """
    Convert legacy branch delete dict to typed payload

    BEFORE (legacy):
        branch_data = {"name": branch_name}  # Missing ID!

    AFTER (type-safe):
        payload = convert_branch_delete_legacy(branch_id, branch_name, project_id)
        # Pydantic validates all required fields are present
    """
    return BranchDeletePayload(id=branch_id, name=branch_name, project_id=project_id)


def convert_task_delete_legacy(task_snapshot: dict[str, Any]) -> TaskDeletePayload:
    """
    Convert legacy task delete dict to typed payload with fallback handling

    Args:
        task_snapshot: Task data dict from entity.to_dict() or similar source

    Returns:
        Validated TaskDeletePayload with proper fallbacks for missing data

    Raises:
        ValueError: If task_snapshot is invalid or missing required 'id' field
    """
    if not task_snapshot:
        raise TypeError("task_snapshot cannot be None or empty")

    # Check if 'id' key exists
    if "id" not in task_snapshot:
        raise KeyError("task_snapshot must contain 'id' field")

    task_id = task_snapshot["id"]

    # Check if id is empty or whitespace
    if not task_id or (isinstance(task_id, str) and not task_id.strip()):
        raise ValueError("Task ID cannot be empty")

    # Get title with fallback for empty/None values
    title = task_snapshot.get("title")
    if not title or (isinstance(title, str) and not title.strip()):
        title = f"Task {task_id[:8]}"

    return TaskDeletePayload(
        id=task_id, title=title, git_branch_id=task_snapshot.get("git_branch_id")
    )


def convert_subtask_delete_legacy(
    subtask_id: str, task_id: str, title: str | None = None
) -> SubtaskDeletePayload:
    """Convert legacy subtask delete dict to typed payload"""
    return SubtaskDeletePayload(id=subtask_id, task_id=task_id, title=title)
