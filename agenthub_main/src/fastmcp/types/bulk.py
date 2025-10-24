"""
Bulk Operation Models
Handles bulk API operations matching frontend api.types.ts
"""

from typing import Optional, List, Dict, Any
from pydantic import BaseModel, Field, ConfigDict

from .summaries import BranchSummaryDTO, ProjectSummaryDTO


class BulkSummaryRequest(BaseModel):
    """Bulk summary request matching frontend BulkSummaryRequest interface"""
    projectIds: Optional[List[str]] = Field(None, alias="projectIds")
    userId: Optional[str] = Field(None, alias="userId")
    includeArchived: Optional[bool] = Field(False, alias="includeArchived")

    model_config = ConfigDict(populate_by_name=True)


class BulkSummaryMetadata(BaseModel):
    """Bulk summary metadata matching frontend BulkSummaryMetadata interface"""
    count: int
    queryTimeMs: float = Field(alias="queryTimeMs")  # Changed to float to accept decimal milliseconds
    fromCache: bool = Field(alias="fromCache")

    model_config = ConfigDict(populate_by_name=True)


class BulkSummaryResponse(BaseModel):
    """Bulk summary response matching frontend BulkSummaryResponse interface

    Note: summaries and projects use Dict[str, Any] instead of strict DTOs
    to allow flexibility in response construction while still serializing correctly.
    """
    success: bool = True
    summaries: Dict[str, Any] = {}
    projects: Dict[str, Any] = {}
    metadata: BulkSummaryMetadata
    timestamp: str
    message: Optional[str] = None