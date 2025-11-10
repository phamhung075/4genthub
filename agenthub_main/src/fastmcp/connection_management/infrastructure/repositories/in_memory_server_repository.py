"""In-Memory Server Repository Implementation"""

from typing import Any

from ...domain.entities.server import Server
from ...domain.repositories.server_repository import ServerRepository


class InMemoryServerRepository(ServerRepository):
    """In-memory implementation of ServerRepository for connection management"""
    
    def __init__(self):
        self._server: Server | None = None
    
    def get_current_server(self) -> Server | None:
        """Get the current server instance"""
        return self._server
    
    def save_server(self, server: Server) -> None:
        """Save server state"""
        self._server = server
    
    def create_server(self, name: str, version: str, environment: dict[str, Any], 
                      authentication: dict[str, Any], task_management: dict[str, Any]) -> Server:
        """Create a new server instance"""
        server = Server.create(
            name=name,
            version=version,
            environment=environment,
            authentication=authentication,
            task_management=task_management
        )
        self._server = server
        return server
    
    def update_server_uptime(self, server: Server) -> None:
        """Update server uptime information"""
        # In memory implementation doesn't need special uptime handling
        # since the server entity calculates uptime dynamically
        self.save_server(server) 