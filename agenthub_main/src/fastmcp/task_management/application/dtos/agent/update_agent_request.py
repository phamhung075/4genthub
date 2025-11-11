"""
DTO for agent update requests.
"""

from __future__ import annotations

from dataclasses import dataclass


@dataclass
class UpdateAgentRequest:
    """Request DTO for updating agent information."""

    project_id: str
    agent_id: str
    name: str | None = None
    call_agent: str | None = None
    user_id: str | None = None

    def validate(self) -> None:
        """Validate the request data."""
        if not self.project_id:
            raise ValueError("project_id is required")
        if not self.agent_id:
            raise ValueError("agent_id is required")
        if not self.name and not self.call_agent:
            raise ValueError("At least one field to update must be provided")
