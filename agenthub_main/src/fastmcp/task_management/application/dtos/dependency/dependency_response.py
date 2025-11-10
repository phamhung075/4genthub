"""Response DTO for dependency operations."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass
class DependencyResponse:
    success: bool
    message: str | None = None
    task_id: str | int | None = None
    depends_on_task_id: str | int | None = None
    dependency_type: str | None = None
    errors: list[str] | None = None 