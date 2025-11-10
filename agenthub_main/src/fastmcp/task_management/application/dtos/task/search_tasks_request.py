"""Request DTO for searching tasks with hierarchical storage support"""

from __future__ import annotations

from dataclasses import dataclass


@dataclass
class SearchTasksRequest:
    """Request DTO for searching tasks with hierarchical storage support"""
    query: str
    git_branch_id: str | None = None  # uuid - Unique git branch identifier - may be omitted when searching globally
    limit: int = 10 