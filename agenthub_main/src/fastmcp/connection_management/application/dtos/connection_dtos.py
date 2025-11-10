"""Connection Management Application DTOs"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any


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
    authentication: dict[str, Any]
    task_management: dict[str, Any]
    environment: dict[str, Any]
    connections: dict[str, Any]
    timestamp: float
    error: str | None = None


@dataclass
class ServerCapabilitiesRequest:
    """Request DTO for server capabilities operation"""
    include_details: bool = True


@dataclass
class ServerCapabilitiesResponse:
    """Response DTO for server capabilities operation"""
    success: bool
    core_features: list
    available_actions: dict[str, list]
    authentication_enabled: bool
    mvp_mode: bool
    version: str
    total_actions: int
    error: str | None = None


@dataclass
class ConnectionHealthRequest:
    """Request DTO for connection health check operation"""
    connection_id: str | None = None
    include_details: bool = True


@dataclass
class ConnectionHealthResponse:
    """Response DTO for connection health check operation"""
    success: bool
    status: str
    connection_info: dict[str, Any]
    diagnostics: dict[str, Any]
    recommendations: list
    error: str | None = None


@dataclass
class ServerStatusRequest:
    """Request DTO for server status operation"""
    include_details: bool = True


@dataclass
class ServerStatusResponse:
    """Response DTO for server status operation"""
    success: bool
    server_info: dict[str, Any]
    connection_stats: dict[str, Any]
    health_status: dict[str, Any]
    capabilities_summary: dict[str, Any]
    error: str | None = None


@dataclass
class RegisterUpdatesRequest:
    """Request DTO for register status updates operation"""
    session_id: str
    client_info: dict[str, Any] | None = None


@dataclass
class RegisterUpdatesResponse:
    """Response DTO for register status updates operation"""
    success: bool
    session_id: str
    registered: bool
    update_info: dict[str, Any]
    error: str | None = None 