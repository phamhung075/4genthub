"""Connection Domain Entity"""

from dataclasses import dataclass, field
from typing import Dict, Any, List, Optional
from datetime import datetime, timedelta

from ..value_objects.connection_health import ConnectionHealth
from ..events.connection_events import ConnectionHealthChecked


@dataclass
class Connection:
    """Connection domain entity representing a client connection"""
    
    connection_id: str
    client_info: Dict[str, Any]
    established_at: datetime
    last_activity: datetime
    status: str = "active"
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    # Domain events
    _events: List[Any] = field(default_factory=list, init=False)
    
    @classmethod
    def create(cls, connection_id: str, client_info: Dict[str, Any]) -> 'Connection':
        """Factory method to create a new connection"""
        now = datetime.now()
        return cls(
            connection_id=connection_id,
            client_info=client_info,
            established_at=now,
            last_activity=now
        )
    
    def update_activity(self) -> None:
        """Update the last activity timestamp"""
        self.last_activity = datetime.now()
    
    def get_connection_duration(self) -> timedelta:
        """Get the duration of this connection"""
        return datetime.now() - self.established_at
    
    def get_idle_time(self) -> timedelta:
        """Get the time since last activity"""
        return datetime.now() - self.last_activity
    
    def is_active(self, activity_threshold_minutes: int = 30) -> bool:
        """Check if connection is considered active based on recent activity"""
        threshold = timedelta(minutes=activity_threshold_minutes)
        return self.get_idle_time() < threshold
    
    def diagnose_health(self) -> ConnectionHealth:
        """Diagnose connection health and provide recommendations"""
        idle_time = self.get_idle_time()
        duration = self.get_connection_duration()
        
        # Business rules for connection health
        is_healthy = True
        issues = []
        recommendations = []
        
        # Check for long idle time
        if idle_time > timedelta(hours=1):
            is_healthy = False
            issues.append("Connection has been idle for over 1 hour")
            recommendations.append("Consider reconnecting to refresh the session")
        
        # Check for very long connection duration
        if duration > timedelta(days=1):
            issues.append("Connection has been active for over 24 hours")
            recommendations.append("Consider periodic reconnection for optimal performance")
        
        # Check connection status
        if self.status != "active":
            is_healthy = False
            issues.append(f"Connection status is '{self.status}' instead of 'active'")
            recommendations.append("Check client connection and network stability")
        
        status = "healthy" if is_healthy else "unhealthy"
        
        # Raise domain event
        self._events.append(ConnectionHealthChecked(
            connection_id=self.connection_id,
            status=status,
            idle_time_seconds=idle_time.total_seconds(),
            timestamp=datetime.now()
        ))
        
        return ConnectionHealth(
            status=status,
            connection_id=self.connection_id,
            idle_time_seconds=idle_time.total_seconds(),
            duration_seconds=duration.total_seconds(),
            client_info=self.client_info,
            issues=issues,
            recommendations=recommendations
        )
    
    def disconnect(self) -> None:
        """Mark connection as disconnected"""
        self.status = "disconnected"
        self.update_activity()
    
    def get_events(self) -> List[Any]:
        """Get domain events"""
        return self._events.copy()
    
    def clear_events(self) -> None:
        """Clear domain events"""
        self._events.clear() 