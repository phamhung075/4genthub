"""Domain Layer for Connection Management

This module contains the core business entities, value objects, and domain services
for connection management functionality.
"""

from .entities.server import Server
from .entities.connection import Connection
from .value_objects.server_status import ServerStatus
from .value_objects.connection_health import ConnectionHealth
from .value_objects.server_capabilities import ServerCapabilities
from .value_objects.status_update import StatusUpdate
from .repositories.server_repository import ServerRepository
from .repositories.connection_repository import ConnectionRepository
from .services.server_health_service import ServerHealthService
from .services.connection_diagnostics_service import ConnectionDiagnosticsService
from .services.status_broadcasting_service import StatusBroadcastingService
from .events.connection_events import ConnectionEvent, ServerHealthChecked, StatusUpdateRequested
from .exceptions.connection_exceptions import ConnectionError, ServerNotFoundError, ConnectionNotFoundError

__all__ = [
    # Entities
    'Server',
    'Connection',
    # Value Objects
    'ServerStatus',
    'ConnectionHealth', 
    'ServerCapabilities',
    'StatusUpdate',
    # Repositories
    'ServerRepository',
    'ConnectionRepository',
    # Domain Services
    'ServerHealthService',
    'ConnectionDiagnosticsService',
    'StatusBroadcastingService',
    # Events
    'ConnectionEvent',
    'ServerHealthChecked',
    'StatusUpdateRequested',
    # Exceptions
    'ConnectionError',
    'ServerNotFoundError',
    'ConnectionNotFoundError'
] 