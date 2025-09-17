"""Check Connection Health Use Case"""

import logging

from ..dtos.connection_dtos import ConnectionHealthRequest, ConnectionHealthResponse
from ...domain.repositories.connection_repository import ConnectionRepository
from ...domain.services.connection_diagnostics_service import ConnectionDiagnosticsService

logger = logging.getLogger(__name__)


class CheckConnectionHealthUseCase:
    """Use case for checking connection health"""
    
    def __init__(self, connection_repository: ConnectionRepository, 
                 diagnostics_service: ConnectionDiagnosticsService):
        self._connection_repository = connection_repository
        self._diagnostics_service = diagnostics_service
    
    def execute(self, request: ConnectionHealthRequest) -> ConnectionHealthResponse:
        """Execute the check connection health use case"""
        try:
            # Get connection statistics and diagnostics
            connection_stats = self._diagnostics_service.get_connection_statistics()
            recommendations = self._diagnostics_service.get_reconnection_recommendations()
            
            # If specific connection ID provided, check that connection
            connection_info = {}
            if request.connection_id:
                connection = self._connection_repository.find_by_id(request.connection_id)
                if connection:
                    health = connection.diagnose_health()
                    connection_info = health.to_dict()
                else:
                    connection_info = {
                        "error": f"Connection {request.connection_id} not found"
                    }
            else:
                # General connection health
                active_connections = self._connection_repository.find_all_active()
                connection_info = {
                    "active_connections": len(active_connections),
                    "total_connections": self._connection_repository.get_connection_count()
                }
            
            # Determine overall status
            status = "healthy"
            if connection_stats.get("active_connections", 0) == 0:
                status = "no_clients"
            
            return ConnectionHealthResponse(
                success=True,
                status=status,
                connection_info=connection_info,
                diagnostics=connection_stats,
                recommendations=recommendations.get("recommendations", [])
            )
            
        except Exception as e:
            logger.error(f"Error checking connection health: {e}")
            return ConnectionHealthResponse(
                success=False,
                status="error",
                connection_info={},
                diagnostics={},
                recommendations=[],
                error=str(e)
            ) 