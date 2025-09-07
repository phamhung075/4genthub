"""Server Health Service Interface"""

from abc import ABC, abstractmethod
from typing import Dict, Any

from ..entities.server import Server
from ..value_objects.server_status import ServerStatus


class ServerHealthService(ABC):
    """Domain service interface for server health operations"""
    
    @abstractmethod
    def check_server_health(self, server: Server) -> ServerStatus:
        """Perform comprehensive server health check"""
        pass
    
    @abstractmethod
    def get_environment_info(self) -> Dict[str, Any]:
        """Get server environment information"""
        pass
    
    @abstractmethod
    def get_authentication_status(self) -> Dict[str, Any]:
        """Get authentication configuration and status"""
        pass
    
    @abstractmethod
    def get_task_management_info(self) -> Dict[str, Any]:
        """Get task management system information"""
        pass
    
    @abstractmethod
    def validate_server_configuration(self) -> Dict[str, Any]:
        """Validate server configuration and dependencies"""
        pass 