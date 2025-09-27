"""In-Memory Connection Repository Implementation"""

from typing import List, Optional, Dict, Any

from ...domain.repositories.connection_repository import ConnectionRepository
from ...domain.entities.connection import Connection


class InMemoryConnectionRepository(ConnectionRepository):
    """In-memory implementation of ConnectionRepository for connection management"""
    
    def __init__(self):
        self._connections: Dict[str, Connection] = {}
    
    def find_by_id(self, connection_id: str) -> Optional[Connection]:
        """Find connection by ID"""
        return self._connections.get(connection_id)
    
    def find_all_active(self) -> List[Connection]:
        """Find all active connections"""
        return [conn for conn in self._connections.values() if conn.status == "active"]
    
    def save_connection(self, connection: Connection) -> None:
        """Save connection state"""
        self._connections[connection.connection_id] = connection
    
    def create_connection(self, connection_id: str, client_info: Dict[str, Any]) -> Connection:
        """Create a new connection"""
        connection = Connection.create(connection_id, client_info)
        self._connections[connection_id] = connection
        return connection
    
    def remove_connection(self, connection_id: str) -> bool:
        """Remove a connection"""
        if connection_id in self._connections:
            del self._connections[connection_id]
            return True
        return False
    
    def get_connection_count(self) -> int:
        """Get total number of active connections"""
        return len(self.find_all_active())
    
    def get_connection_statistics(self) -> Dict[str, Any]:
        """Get connection statistics"""
        all_connections = list(self._connections.values())
        active_connections = self.find_all_active()
        
        return {
            "total_connections": len(all_connections),
            "active_connections": len(active_connections),
            "inactive_connections": len(all_connections) - len(active_connections),
            "connection_ids": list(self._connections.keys())
        } 