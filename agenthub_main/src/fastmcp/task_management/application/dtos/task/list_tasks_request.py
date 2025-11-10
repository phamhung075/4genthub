"""Request DTO for listing tasks with hierarchical storage support"""

from __future__ import annotations

from dataclasses import dataclass


@dataclass
class ListTasksRequest:
    """Request DTO for listing tasks with hierarchical storage support"""
    git_branch_id: str | None = None  # uuid - Unique git branch identifier - may be omitted to list across branches
    status: str | None = None
    priority: str | None = None
    assignees: list[str] | None = None
    labels: list[str] | None = None
    limit: int | None = None 