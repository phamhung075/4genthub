"""Request DTO for updating a task with hierarchical storage support"""

from __future__ import annotations

from typing import Any

from pydantic import BaseModel, Field


class UpdateTaskRequest(BaseModel):
    """Request DTO for updating a task with hierarchical storage support"""

    task_id: Any
    title: str | None = Field(default=None)
    description: str | None = Field(default=None)
    status: str | None = Field(default=None)
    priority: str | None = Field(default=None)
    details: str | None = Field(default=None)
    estimated_effort: str | None = Field(default=None)
    assignees: list[str] | None = Field(default=None)
    labels: list[str] | None = Field(default=None)
    due_date: str | None = Field(default=None)
    context_id: str | None = Field(default=None)
    completion_summary: str | None = Field(default=None)
    testing_notes: str | None = Field(default=None)
    completed_at: str | None = Field(default=None)
    progress_percentage: int | None = Field(default=None)

    class Config:
        # Allow extra fields in case frontend sends additional data
        extra = "allow"
