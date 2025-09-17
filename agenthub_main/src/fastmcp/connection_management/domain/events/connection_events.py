"""Connection Management Domain Events"""

from dataclasses import dataclass
from datetime import datetime
from typing import Any, Dict


@dataclass
class ConnectionEvent:
    """Base class for all connection-related domain events"""
    timestamp: datetime
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert event to dictionary"""
        return {
            "event_type": self.__class__.__name__,
            "timestamp": self.timestamp.isoformat(),
            **self.__dict__
        }


@dataclass
class ServerHealthChecked(ConnectionEvent):
    """Event raised when server health is checked"""
    server_name: str
    status: str
    uptime_seconds: float
    
    def __init__(self, server_name: str, status: str, uptime_seconds: float, timestamp: datetime):
        super().__init__(timestamp)
        self.server_name = server_name
        self.status = status
        self.uptime_seconds = uptime_seconds


@dataclass
class ConnectionHealthChecked(ConnectionEvent):
    """Event raised when connection health is checked"""
    connection_id: str
    status: str
    idle_time_seconds: float
    
    def __init__(self, connection_id: str, status: str, idle_time_seconds: float, timestamp: datetime):
        super().__init__(timestamp)
        self.connection_id = connection_id
        self.status = status
        self.idle_time_seconds = idle_time_seconds


@dataclass
class StatusUpdateRequested(ConnectionEvent):
    """Event raised when a status update is requested"""
    session_id: str
    update_type: str
    
    def __init__(self, session_id: str, update_type: str, timestamp: datetime):
        super().__init__(timestamp)
        self.session_id = session_id
        self.update_type = update_type


@dataclass
class ClientRegisteredForUpdates(ConnectionEvent):
    """Event raised when a client registers for status updates"""
    session_id: str
    client_info: Dict[str, Any]
    
    def __init__(self, session_id: str, client_info: Dict[str, Any], timestamp: datetime):
        super().__init__(timestamp)
        self.session_id = session_id
        self.client_info = client_info


@dataclass
class ServerCapabilitiesRequested(ConnectionEvent):
    """Event raised when server capabilities are requested"""
    requester_session: str
    
    def __init__(self, requester_session: str, timestamp: datetime):
        super().__init__(timestamp)
        self.requester_session = requester_session


@dataclass
class StatusUpdateBroadcasted(ConnectionEvent):
    """Event raised when a status update is broadcasted"""
    event_type: str
    session_id: str
    data: Dict[str, Any]
    
    def __init__(self, event_type: str, session_id: str, data: Dict[str, Any], timestamp: datetime):
        super().__init__(timestamp)
        self.event_type = event_type
        self.session_id = session_id
        self.data = data


@dataclass
class ClientRegistered(ConnectionEvent):
    """Event raised when a client is registered"""
    session_id: str
    client_info: Dict[str, Any]
    
    def __init__(self, session_id: str, client_info: Dict[str, Any], timestamp: datetime):
        super().__init__(timestamp)
        self.session_id = session_id
        self.client_info = client_info


@dataclass
class ClientUnregistered(ConnectionEvent):
    """Event raised when a client is unregistered"""
    session_id: str
    reason: str
    
    def __init__(self, session_id: str, reason: str, timestamp: datetime):
        super().__init__(timestamp)
        self.session_id = session_id
        self.reason = reason 