"""Server Repository Interface"""

from abc import ABC, abstractmethod
from typing import Optional

from ..entities.server import Server


class ServerRepository(ABC):
    """Repository interface for Server aggregate"""
    
    @abstractmethod
    def get_current_server(self) -> Optional[Server]:
        """Get the current server instance"""
        pass
    
    @abstractmethod
    def save_server(self, server: Server) -> None:
        """Save server state"""
        pass
    
    @abstractmethod
    def create_server(self, name: str, version: str, environment: dict, 
                      authentication: dict, task_management: dict) -> Server:
        """Create a new server instance"""
        pass
    
    @abstractmethod
    def update_server_uptime(self, server: Server) -> None:
        """Update server uptime information"""
        pass 