"""Connection Management Application DTOs"""

from dataclasses import dataclass
from typing import Dict, Any, Optional


@dataclass
class HealthCheckRequest:
    """Request DTO for health check operation"""
    include_details: bool = True


@dataclass
class HealthCheckResponse:
    """Response DTO for health check operation"""
    success: bool
    status: str
    server_name: str
    version: str
    uptime_seconds: float
    restart_count: int
    authentication: Dict[str, Any]
    task_management: Dict[str, Any]
    environment: Dict[str, Any]
    connections: Dict[str, Any]
    timestamp: float
    error: Optional[str] = None


@dataclass
class ServerCapabilitiesRequest:
    """Request DTO for server capabilities operation"""
    include_details: bool = True


@dataclass
class ServerCapabilitiesResponse:
    """Response DTO for server capabilities operation"""
    success: bool
    core_features: list
    available_actions: Dict[str, list]
    authentication_enabled: bool
    mvp_mode: bool
    version: str
    total_actions: int
    error: Optional[str] = None


@dataclass
class ConnectionHealthRequest:
    """Request DTO for connection health check operation"""
    connection_id: Optional[str] = None
    include_details: bool = True


@dataclass
class ConnectionHealthResponse:
    """Response DTO for connection health check operation"""
    success: bool
    status: str
    connection_info: Dict[str, Any]
    diagnostics: Dict[str, Any]
    recommendations: list
    error: Optional[str] = None


@dataclass
class ServerStatusRequest:
    """Request DTO for server status operation"""
    include_details: bool = True


@dataclass
class ServerStatusResponse:
    """Response DTO for server status operation"""
    success: bool
    server_info: Dict[str, Any]
    connection_stats: Dict[str, Any]
    health_status: Dict[str, Any]
    capabilities_summary: Dict[str, Any]
    error: Optional[str] = None


@dataclass
class RegisterUpdatesRequest:
    """Request DTO for register status updates operation"""
    session_id: str
    client_info: Optional[Dict[str, Any]] = None


@dataclass
class RegisterUpdatesResponse:
    """Response DTO for register status updates operation"""
    success: bool
    session_id: str
    registered: bool
    update_info: Dict[str, Any]
    error: Optional[str] = None 