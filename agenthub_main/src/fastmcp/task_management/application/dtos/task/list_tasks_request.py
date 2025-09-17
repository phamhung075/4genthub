"""Request DTO for listing tasks with hierarchical storage support"""

from dataclasses import dataclass
from typing import Optional, List

@dataclass
class ListTasksRequest:
    """Request DTO for listing tasks with hierarchical storage support"""
    git_branch_id: Optional[str] = None  # uuid - Unique git branch identifier - may be omitted to list across branches
    status: Optional[str] = None
    priority: Optional[str] = None
    assignees: Optional[List[str]] = None
    labels: Optional[List[str]] = None
    limit: Optional[int] = None 