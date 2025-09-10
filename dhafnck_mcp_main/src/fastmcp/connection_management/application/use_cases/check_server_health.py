"""Check Server Health Use Case"""

import time
import logging
from typing import Optional

from ..dtos.connection_dtos import HealthCheckRequest, HealthCheckResponse
from ...domain.repositories.server_repository import ServerRepository
from ...domain.services.server_health_service import ServerHealthService
from ...domain.exceptions.connection_exceptions import ServerHealthCheckFailedError
from ....config.version import VERSION, VERSION_INFO

logger = logging.getLogger(__name__)


class CheckServerHealthUseCase:
    """Use case for checking server health"""
    
    def __init__(self, server_repository: ServerRepository, health_service: ServerHealthService):
        self._server_repository = server_repository
        self._health_service = health_service
    
    def execute(self, request: HealthCheckRequest) -> HealthCheckResponse:
        """Execute the check server health use case"""
        try:
            # Get current server instance
            server = self._server_repository.get_current_server()
            
            if not server:
                # Create a default server instance if none exists
                environment = self._health_service.get_environment_info()
                authentication = self._health_service.get_authentication_status()
                task_management = self._health_service.get_task_management_info()
                
                server = self._server_repository.create_server(
                    name=VERSION_INFO["name"],
                    version=VERSION,
                    environment=environment,
                    authentication=authentication,
                    task_management=task_management
                )
                self._server_repository.save_server(server)
            
            # Perform health check
            server_status = server.check_health()
            
            # Get additional connection information if requested
            connections_info = {}
            if request.include_details:
                try:
                    # This will be implemented by the infrastructure service
                    connections_info = self._health_service.validate_server_configuration()
                except Exception as e:
                    logger.warning(f"Could not get connection info: {e}")
                    connections_info = {"error": str(e)}
            
            return HealthCheckResponse(
                success=True,
                status=server_status.status,
                server_name=server_status.server_name,
                version=server_status.version,
                uptime_seconds=server_status.uptime_seconds,
                restart_count=server_status.restart_count,
                authentication=server.authentication,
                task_management=server.task_management,
                environment=server.environment,
                connections=connections_info,
                timestamp=time.time()
            )
            
        except ServerHealthCheckFailedError as e:
            logger.error(f"Server health check failed: {e}")
            return HealthCheckResponse(
                success=False,
                status="error",
                server_name="Unknown",
                version="Unknown",
                uptime_seconds=0,
                restart_count=0,
                authentication={},
                task_management={},
                environment={},
                connections={},
                timestamp=time.time(),
                error=str(e)
            )
        except Exception as e:
            logger.error(f"Unexpected error during health check: {e}")
            return HealthCheckResponse(
                success=False,
                status="error",
                server_name="Unknown",
                version="Unknown",
                uptime_seconds=0,
                restart_count=0,
                authentication={},
                task_management={},
                environment={},
                connections={},
                timestamp=time.time(),
                error=f"Unexpected error: {str(e)}"
            ) 