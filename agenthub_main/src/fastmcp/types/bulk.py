"""
Bulk Operation Models
Handles bulk API operations matching frontend api.types.ts
"""

from __future__ import annotations

from typing import Any

from pydantic import BaseModel, ConfigDict, Field


class BulkSummaryRequest(BaseModel):
    """Bulk summary request matching frontend BulkSummaryRequest interface"""

    projectIds: list[str] | None = Field(None, alias="projectIds")
    userId: str | None = Field(None, alias="userId")
    includeArchived: bool | None = Field(False, alias="includeArchived")

    model_config = ConfigDict(populate_by_name=True)


class BulkSummaryMetadata(BaseModel):
    """Bulk summary metadata matching frontend BulkSummaryMetadata interface"""

    count: int
    queryTimeMs: float = Field(
        alias="queryTimeMs"
    )  # Changed to float to accept decimal milliseconds
    fromCache: bool = Field(alias="fromCache")

    model_config = ConfigDict(populate_by_name=True)


class BulkSummaryResponse(BaseModel):
    """Bulk summary response matching frontend BulkSummaryResponse interface

    Note: summaries and projects use dict[str, Any] instead of strict DTOs
    to allow flexibility in response construction while still serializing correctly.
    """

    success: bool = True
    summaries: dict[str, Any] = {}
    projects: dict[str, Any] = {}
    metadata: BulkSummaryMetadata
    timestamp: str
    message: str | None = None
