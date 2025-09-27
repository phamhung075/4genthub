"""Register Agent Response DTO"""

from dataclasses import dataclass
from typing import Optional
from .agent_response import AgentResponse


@dataclass
class RegisterAgentResponse:
    """Response DTO for agent registration"""
    
    success: bool
    agent: Optional[AgentResponse] = None
    message: Optional[str] = None
    error: Optional[str] = None
    
    @classmethod
    def success_response(cls, agent: AgentResponse, message: str = "Agent registered successfully") -> "RegisterAgentResponse":
        """Create a success response"""
        return cls(success=True, agent=agent, message=message)
    
    @classmethod
    def error_response(cls, error: str) -> "RegisterAgentResponse":
        """Create an error response"""
        return cls(success=False, error=error)