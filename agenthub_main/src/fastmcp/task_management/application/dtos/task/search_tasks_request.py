"""Request DTO for searching tasks with hierarchical storage support"""

from dataclasses import dataclass
from typing import Optional

@dataclass
class SearchTasksRequest:
    """Request DTO for searching tasks with hierarchical storage support"""
    query: str
    git_branch_id: Optional[str] = None  # uuid - Unique git branch identifier - may be omitted when searching globally
    limit: int = 10 