"""Agent Response DTO"""

from dataclasses import dataclass
from typing import Dict, Any, List


@dataclass
class AgentResponse:
    """Response DTO for agent data"""
    
    id: str
    name: str
    call_agent: str
    assignments: List[str]
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "AgentResponse":
        """Create AgentResponse from dictionary"""
        return cls(
            id=data.get("id", ""),
            name=data.get("name", ""),
            call_agent=data.get("call_agent", ""),
            assignments=data.get("assignments", [])
        )