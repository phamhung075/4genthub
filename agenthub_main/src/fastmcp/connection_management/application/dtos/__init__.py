"""Application DTOs for Connection Management"""

from .connection_dtos import (
    HealthCheckRequest, HealthCheckResponse,
    ServerCapabilitiesRequest, ServerCapabilitiesResponse,
    ConnectionHealthRequest, ConnectionHealthResponse,
    ServerStatusRequest, ServerStatusResponse,
    RegisterUpdatesRequest, RegisterUpdatesResponse
)

__all__ = [
    "HealthCheckRequest", "HealthCheckResponse",
    "ServerCapabilitiesRequest", "ServerCapabilitiesResponse",
    "ConnectionHealthRequest", "ConnectionHealthResponse", 
    "ServerStatusRequest", "ServerStatusResponse",
    "RegisterUpdatesRequest", "RegisterUpdatesResponse"
] 