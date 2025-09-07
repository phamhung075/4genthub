"""Register Agent Request DTO"""

import uuid
from dataclasses import dataclass
from typing import Optional


@dataclass
class RegisterAgentRequest:
    """Request DTO for registering an agent"""
    
    project_id: str
    agent_id: Optional[str] = None  # Now optional, will auto-generate if not provided
    name: str = None
    call_agent: Optional[str] = None
    
    def __post_init__(self):
        """Validate the request after initialization"""
        if not self.project_id or not self.project_id.strip():
            raise ValueError("Project ID is required")
        
        # Agent ID validation - auto-generate if not provided
        self.agent_id = self._validate_and_normalize_agent_id(self.agent_id)
        
        if not self.name or not self.name.strip():
            raise ValueError("Agent name is required")
        
        
        # Validate project_id is a valid UUID
        self._validate_uuid(self.project_id, "Project ID")
    
    def _validate_and_normalize_agent_id(self, agent_id: Optional[str]) -> str:
        """
        Validate and normalize agent ID to ensure it's a valid UUID.
        If agent_id is empty or not provided, generate a new UUID.
        If agent_id is not a valid UUID, auto-generate one with a helpful error message.
        """
        if not agent_id or agent_id.strip() == "":
            # Auto-generate UUID if not provided
            new_id = str(uuid.uuid4())
            return new_id
        
        # Check if it's already a valid UUID
        try:
            uuid.UUID(agent_id)
            return agent_id
        except ValueError:
            # Not a valid UUID - auto-generate a new one
            new_id = str(uuid.uuid4())
            raise ValueError(
                f"Agent ID '{agent_id}' is not a valid UUID. "
                f"Agent IDs must be valid UUIDs. "
                f"Auto-generated UUID: '{new_id}'. "
                f"Please use this UUID or provide your own valid UUID."
            )
    
    def _validate_uuid(self, value: str, field_name: str) -> None:
        """Validate that a value is a valid UUID"""
        try:
            uuid.UUID(value)
        except ValueError:
            raise ValueError(f"{field_name} '{value}' is not a valid UUID")