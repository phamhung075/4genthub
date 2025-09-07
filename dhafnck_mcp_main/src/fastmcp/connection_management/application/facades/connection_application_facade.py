"""Connection Management Application Facade"""

import logging
from typing import Dict, Any

from ..use_cases.check_server_health import CheckServerHealthUseCase
from ..use_cases.get_server_capabilities import GetServerCapabilitiesUseCase
from ..use_cases.check_connection_health import CheckConnectionHealthUseCase
from ..use_cases.get_server_status import GetServerStatusUseCase
from ..use_cases.register_status_updates import RegisterStatusUpdatesUseCase

from ..dtos.connection_dtos import (
    HealthCheckRequest, HealthCheckResponse,
    ServerCapabilitiesRequest, ServerCapabilitiesResponse,
    ConnectionHealthRequest, ConnectionHealthResponse,
    ServerStatusRequest, ServerStatusResponse,
    RegisterUpdatesRequest, RegisterUpdatesResponse
)

from ...domain.repositories.server_repository import ServerRepository
from ...domain.repositories.connection_repository import ConnectionRepository
from ...domain.services.server_health_service import ServerHealthService
from ...domain.services.connection_diagnostics_service import ConnectionDiagnosticsService
from ...domain.services.status_broadcasting_service import StatusBroadcastingService

logger = logging.getLogger(__name__)


class ConnectionApplicationFacade:
    """
    Application Facade that orchestrates connection-related use cases.
    Provides a unified interface for the Interface layer while maintaining
    proper DDD boundaries.
    
    This facade coordinates multiple use cases and handles cross-cutting concerns
    like validation, error handling, and response formatting at the application boundary.
    """
    
    def __init__(self, 
                 server_repository: ServerRepository,
                 connection_repository: ConnectionRepository,
                 health_service: ServerHealthService,
                 diagnostics_service: ConnectionDiagnosticsService,
                 broadcasting_service: StatusBroadcastingService):
        """Initialize facade with required dependencies"""
        self._server_repository = server_repository
        self._connection_repository = connection_repository
        self._health_service = health_service
        self._diagnostics_service = diagnostics_service
        self._broadcasting_service = broadcasting_service
        
        # Initialize use cases
        self._check_health_use_case = CheckServerHealthUseCase(server_repository, health_service)
        self._get_capabilities_use_case = GetServerCapabilitiesUseCase(server_repository, health_service)
        self._check_connection_health_use_case = CheckConnectionHealthUseCase(connection_repository, diagnostics_service)
        self._get_status_use_case = GetServerStatusUseCase(
            server_repository, connection_repository, health_service, diagnostics_service
        )
        self._register_updates_use_case = RegisterStatusUpdatesUseCase(broadcasting_service)
        
        logger.info("ConnectionApplicationFacade initialized")
    
    def check_server_health(self, include_details: bool = True, user_id: str = None) -> HealthCheckResponse:
        """Check server health status"""
        try:
            request = HealthCheckRequest(include_details=include_details)
            return self._check_health_use_case.execute(request)
        except Exception as e:
            logger.error(f"Error in check_server_health: {e}")
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
                timestamp=0,
                error=str(e)
            )
    
    def get_server_capabilities(self, include_details: bool = True, user_id: str = None) -> ServerCapabilitiesResponse:
        """Get server capabilities and features"""
        try:
            request = ServerCapabilitiesRequest(include_details=include_details)
            return self._get_capabilities_use_case.execute(request)
        except Exception as e:
            logger.error(f"Error in get_server_capabilities: {e}")
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
    
    def check_connection_health(self, connection_id: str = None, include_details: bool = True, user_id: str = None) -> ConnectionHealthResponse:
        """Check connection health and diagnostics"""
        try:
            request = ConnectionHealthRequest(connection_id=connection_id, include_details=include_details)
            return self._check_connection_health_use_case.execute(request)
        except Exception as e:
            logger.error(f"Error in check_connection_health: {e}")
            return ConnectionHealthResponse(
                success=False,
                status="error",
                connection_info={},
                diagnostics={},
                recommendations=[],
                error=str(e)
            )
    
    def get_server_status(self, include_details: bool = True, user_id: str = None) -> ServerStatusResponse:
        """Get comprehensive server status"""
        try:
            request = ServerStatusRequest(include_details=include_details)
            return self._get_status_use_case.execute(request)
        except Exception as e:
            logger.error(f"Error in get_server_status: {e}")
            return ServerStatusResponse(
                success=False,
                server_info={},
                connection_stats={},
                health_status={},
                capabilities_summary={},
                error=str(e)
            )
    
    def register_for_status_updates(self, session_id: str, client_info: Dict[str, Any] = None, user_id: str = None) -> RegisterUpdatesResponse:
        """Register client for real-time status updates"""
        try:
            request = RegisterUpdatesRequest(session_id=session_id, client_info=client_info)
            return self._register_updates_use_case.execute(request)
        except Exception as e:
            logger.error(f"Error in register_for_status_updates: {e}")
            return RegisterUpdatesResponse(
                success=False,
                session_id=session_id,
                registered=False,
                update_info={},
                error=str(e)
            ) 