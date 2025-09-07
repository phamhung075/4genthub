"""Connection Repository Interface"""

from abc import ABC, abstractmethod
from typing import List, Optional, Dict, Any

from ..entities.connection import Connection


class ConnectionRepository(ABC):
    """Repository interface for Connection aggregate"""
    
    @abstractmethod
    def find_by_id(self, connection_id: str) -> Optional[Connection]:
        """Find connection by ID"""
        pass
    
    @abstractmethod
    def find_all_active(self) -> List[Connection]:
        """Find all active connections"""
        pass
    
    @abstractmethod
    def save_connection(self, connection: Connection) -> None:
        """Save connection state"""
        pass
    
    @abstractmethod
    def create_connection(self, connection_id: str, client_info: Dict[str, Any]) -> Connection:
        """Create a new connection"""
        pass
    
    @abstractmethod
    def remove_connection(self, connection_id: str) -> bool:
        """Remove a connection"""
        pass
    
    @abstractmethod
    def get_connection_count(self) -> int:
        """Get total number of active connections"""
        pass
    
    @abstractmethod
    def get_connection_statistics(self) -> Dict[str, Any]:
        """Get connection statistics"""
        pass 