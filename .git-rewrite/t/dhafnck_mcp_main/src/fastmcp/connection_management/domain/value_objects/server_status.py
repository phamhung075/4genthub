"""ServerStatus Value Object"""

from dataclasses import dataclass
from typing import Dict, Any


@dataclass(frozen=True)
class ServerStatus:
    """Immutable value object representing server status"""
    
    status: str  # "healthy" or "unhealthy"
    server_name: str
    version: str
    uptime_seconds: float
    restart_count: int
    details: Dict[str, Any]
    
    def __post_init__(self):
        """Validate server status values"""
        if self.status not in ["healthy", "unhealthy"]:
            raise ValueError(f"Invalid status: {self.status}. Must be 'healthy' or 'unhealthy'")
        
        if self.uptime_seconds < 0:
            raise ValueError("Uptime seconds cannot be negative")
        
        if self.restart_count < 0:
            raise ValueError("Restart count cannot be negative")
    
    def is_healthy(self) -> bool:
        """Check if server is healthy"""
        return self.status == "healthy"
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary representation"""
        return {
            "success": True,
            "status": self.status,
            "server_name": self.server_name,
            "version": self.version,
            "uptime_seconds": self.uptime_seconds,
            "restart_count": self.restart_count,
            **self.details
        } 