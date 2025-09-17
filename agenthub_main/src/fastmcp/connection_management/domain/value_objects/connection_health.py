"""ConnectionHealth Value Object"""

from dataclasses import dataclass
from typing import Dict, Any, List


@dataclass(frozen=True)
class ConnectionHealth:
    """Immutable value object representing connection health status"""
    
    status: str  # "healthy" or "unhealthy"
    connection_id: str
    idle_time_seconds: float
    duration_seconds: float
    client_info: Dict[str, Any]
    issues: List[str]
    recommendations: List[str]
    
    def __post_init__(self):
        """Validate connection health values"""
        if self.status not in ["healthy", "unhealthy"]:
            raise ValueError(f"Invalid status: {self.status}. Must be 'healthy' or 'unhealthy'")
        
        if self.idle_time_seconds < 0:
            raise ValueError("Idle time seconds cannot be negative")
        
        if self.duration_seconds < 0:
            raise ValueError("Duration seconds cannot be negative")
    
    def is_healthy(self) -> bool:
        """Check if connection is healthy"""
        return self.status == "healthy"
    
    def has_issues(self) -> bool:
        """Check if connection has any issues"""
        return len(self.issues) > 0
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary representation"""
        return {
            "success": True,
            "status": self.status,
            "connection_id": self.connection_id,
            "idle_time_seconds": self.idle_time_seconds,
            "duration_seconds": self.duration_seconds,
            "client_info": self.client_info,
            "issues": self.issues,
            "recommendations": self.recommendations
        } 