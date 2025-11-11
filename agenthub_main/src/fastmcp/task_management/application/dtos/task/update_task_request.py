"""Request DTO for updating a task with hierarchical storage support"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any


@dataclass
class UpdateTaskRequest:
    """Request DTO for updating a task with hierarchical storage support"""

    task_id: Any
    title: str | None = None
    description: str | None = None
    status: str | None = None
    priority: str | None = None
    details: str | None = None
    estimated_effort: str | None = None
    assignees: list[str] | None = None
    labels: list[str] | None = None
    due_date: str | None = None
    context_id: str | None = None
    completion_summary: str | None = None
    testing_notes: str | None = None
    completed_at: str | None = None
    progress_percentage: int | None = None
