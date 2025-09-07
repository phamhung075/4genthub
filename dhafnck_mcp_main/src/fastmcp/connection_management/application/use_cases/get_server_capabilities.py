"""Get Server Capabilities Use Case"""

import logging

from ..dtos.connection_dtos import ServerCapabilitiesRequest, ServerCapabilitiesResponse
from ...domain.repositories.server_repository import ServerRepository
from ...domain.services.server_health_service import ServerHealthService

logger = logging.getLogger(__name__)


class GetServerCapabilitiesUseCase:
    """Use case for getting server capabilities"""
    
    def __init__(self, server_repository: ServerRepository, health_service: ServerHealthService):
        self._server_repository = server_repository
        self._health_service = health_service
    
    def execute(self, request: ServerCapabilitiesRequest) -> ServerCapabilitiesResponse:
        """Execute the get server capabilities use case"""
        try:
            # Get current server instance
            server = self._server_repository.get_current_server()
            
            if not server:
                # Create a default server instance if none exists
                environment = self._health_service.get_environment_info()
                authentication = self._health_service.get_authentication_status()
                task_management = self._health_service.get_task_management_info()
                
                server = self._server_repository.create_server(
                    name="DhafnckMCP - Task Management & Agent Orchestration",
                    version="2.1.0",
                    environment=environment,
                    authentication=authentication,
                    task_management=task_management
                )
                self._server_repository.save_server(server)
            
            # Get server capabilities
            capabilities = server.get_capabilities()
            
            return ServerCapabilitiesResponse(
                success=True,
                core_features=capabilities.core_features,
                available_actions=capabilities.available_actions,
                authentication_enabled=capabilities.authentication_enabled,
                mvp_mode=capabilities.mvp_mode,
                version=capabilities.version,
                total_actions=capabilities.get_total_actions_count()
            )
            
        except Exception as e:
            logger.error(f"Error getting server capabilities: {e}")
            return ServerCapabilitiesResponse(
                success=False,
                core_features=[],
                available_actions={},
                authentication_enabled=False,
                mvp_mode=False,
                version="Unknown",
                total_actions=0,
                error=str(e)
            ) 