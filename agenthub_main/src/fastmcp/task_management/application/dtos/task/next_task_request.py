"""Request DTO for getting the next task"""

from dataclasses import dataclass

@dataclass
class NextTaskRequest:
    """Request DTO for getting the next task"""
    git_branch_id: str  # uuid - Unique git branch identifier - contains all necessary context
    include_context: bool = False