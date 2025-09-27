"""StatusUpdate Value Object"""

from dataclasses import dataclass
from typing import Dict, Any
from datetime import datetime


@dataclass(frozen=True)
class StatusUpdate:
    """Immutable value object representing a status update event"""
    
    event_type: str
    timestamp: datetime
    data: Dict[str, Any]
    session_id: str
    
    def __post_init__(self):
        """Validate status update values"""
        if not self.event_type:
            raise ValueError("Event type cannot be empty")
        
        if not self.session_id:
            raise ValueError("Session ID cannot be empty")
        
        valid_event_types = [
            "server_health_changed",
            "connection_established",
            "connection_lost",
            "status_broadcast",
            "client_registered",
            "client_unregistered"
        ]
        
        if self.event_type not in valid_event_types:
            raise ValueError(f"Invalid event type: {self.event_type}. Must be one of {valid_event_types}")
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary representation"""
        return {
            "event_type": self.event_type,
            "timestamp": self.timestamp.isoformat(),
            "session_id": self.session_id,
            "data": self.data
        }
    
    @classmethod
    def create_server_health_update(cls, session_id: str, health_status: str, details: Dict[str, Any]) -> 'StatusUpdate':
        """Factory method for server health updates"""
        return cls(
            event_type="server_health_changed",
            timestamp=datetime.now(),
            session_id=session_id,
            data={
                "health_status": health_status,
                **details
            }
        )
    
    @classmethod
    def create_connection_update(cls, session_id: str, connection_id: str, event: str) -> 'StatusUpdate':
        """Factory method for connection updates"""
        return cls(
            event_type=f"connection_{event}",
            timestamp=datetime.now(),
            session_id=session_id,
            data={
                "connection_id": connection_id
            }
        )
    
    @classmethod
    def create_client_registration_update(cls, session_id: str, registered: bool) -> 'StatusUpdate':
        """Factory method for client registration updates"""
        event_type = "client_registered" if registered else "client_unregistered"
        return cls(
            event_type=event_type,
            timestamp=datetime.now(),
            session_id=session_id,
            data={}
        ) 