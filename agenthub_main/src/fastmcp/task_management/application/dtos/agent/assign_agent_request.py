"""
DTO for agent assignment requests.
"""

from __future__ import annotations

from dataclasses import dataclass


@dataclass
class AssignAgentRequest:
    """Request DTO for assigning an agent to a git branch."""

    project_id: str
    agent_id: str
    git_branch_id: str
    user_id: str | None = None

    def validate(self) -> None:
        """Validate the request data."""
        if not self.project_id:
            raise ValueError("project_id is required")
        if not self.agent_id:
            raise ValueError("agent_id is required")
        if not self.git_branch_id:
            raise ValueError("git_branch_id is required")
