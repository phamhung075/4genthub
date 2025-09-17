"""Get Server Status Use Case"""

import logging

from ..dtos.connection_dtos import ServerStatusRequest, ServerStatusResponse
from ...domain.repositories.server_repository import ServerRepository
from ...domain.repositories.connection_repository import ConnectionRepository
from ...domain.services.server_health_service import ServerHealthService
from ...domain.services.connection_diagnostics_service import ConnectionDiagnosticsService

logger = logging.getLogger(__name__)


class GetServerStatusUseCase:
    """Use case for getting comprehensive server status"""
    
    def __init__(self, server_repository: ServerRepository,
                 connection_repository: ConnectionRepository,
                 health_service: ServerHealthService,
                 diagnostics_service: ConnectionDiagnosticsService):
        self._server_repository = server_repository
        self._connection_repository = connection_repository
        self._health_service = health_service
        self._diagnostics_service = diagnostics_service
    
    def execute(self, request: ServerStatusRequest) -> ServerStatusResponse:
        """Execute the get server status use case"""
        try:
            # Get server info
            server = self._server_repository.get_current_server()
            if not server:
                # Create default server if none exists
                environment = self._health_service.get_environment_info()
                authentication = self._health_service.get_authentication_status()
                task_management = self._health_service.get_task_management_info()
                
                server = self._server_repository.create_server(
                    name="agenthub - Task Management & Agent Orchestration",
                    version="2.1.0",
                    environment=environment,
                    authentication=authentication,
                    task_management=task_management
                )
            
            # Get server health status
            health_status = server.check_health().to_dict()
            
            # Get connection statistics
            connection_stats = self._diagnostics_service.get_connection_statistics()
            
            # Get capabilities summary
            capabilities = server.get_capabilities()
            capabilities_summary = {
                "total_features": len(capabilities.core_features),
                "total_actions": capabilities.get_total_actions_count(),
                "authentication_enabled": capabilities.authentication_enabled
            }
            
            # Server info
            server_info = {
                "name": server.name,
                "version": server.version,
                "uptime_seconds": server.get_uptime_seconds(),
                "restart_count": server.restart_count
            }
            
            return ServerStatusResponse(
                success=True,
                server_info=server_info,
                connection_stats=connection_stats,
                health_status=health_status,
                capabilities_summary=capabilities_summary
            )
            
        except Exception as e:
            logger.error(f"Error getting server status: {e}")
            return ServerStatusResponse(
                success=False,
                server_info={},
                connection_stats={},
                health_status={},
                capabilities_summary={},
                error=str(e)
            ) 