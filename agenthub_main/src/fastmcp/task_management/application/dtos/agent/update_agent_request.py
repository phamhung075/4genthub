"""
DTO for agent update requests.
"""

from dataclasses import dataclass
from typing import Optional


@dataclass
class UpdateAgentRequest:
    """Request DTO for updating agent information."""
    
    project_id: str
    agent_id: str
    name: Optional[str] = None
    call_agent: Optional[str] = None
    user_id: Optional[str] = None
    
    def validate(self) -> None:
        """Validate the request data."""
        if not self.project_id:
            raise ValueError("project_id is required")
        if not self.agent_id:
            raise ValueError("agent_id is required")
        if not self.name and not self.call_agent:
            raise ValueError("At least one field to update must be provided")