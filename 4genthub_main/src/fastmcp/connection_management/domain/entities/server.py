"""Server Domain Entity"""

import time
from dataclasses import dataclass, field
from typing import Dict, Any, List, Optional
from datetime import datetime

from ..value_objects.server_status import ServerStatus
from ..value_objects.server_capabilities import ServerCapabilities
from ..events.connection_events import ServerHealthChecked


@dataclass
class Server:
    """Server domain entity representing the MCP server instance"""
    
    name: str
    version: str
    started_at: datetime
    restart_count: int = 0
    environment: Dict[str, Any] = field(default_factory=dict)
    authentication: Dict[str, Any] = field(default_factory=dict)
    task_management: Dict[str, Any] = field(default_factory=dict)
    
    # Domain events
    _events: List[Any] = field(default_factory=list, init=False)
    
    @classmethod
    def create(cls, name: str, version: str, environment: Dict[str, Any], 
               authentication: Dict[str, Any], task_management: Dict[str, Any]) -> 'Server':
        """Factory method to create a new server instance"""
        server = cls(
            name=name,
            version=version,
            started_at=datetime.now(),
            environment=environment,
            authentication=authentication,
            task_management=task_management
        )
        return server
    
    def get_uptime_seconds(self) -> float:
        """Calculate server uptime in seconds"""
        return (datetime.now() - self.started_at).total_seconds()
    
    def check_health(self) -> ServerStatus:
        """Perform health check and return server status"""
        uptime = self.get_uptime_seconds()
        
        # Business rule: Server is healthy if uptime > 0 and no critical errors
        is_healthy = uptime > 0
        status = "healthy" if is_healthy else "unhealthy"
        
        health_info = {
            "status": status,
            "uptime_seconds": uptime,
            "restart_count": self.restart_count,
            "authentication": self.authentication,
            "task_management": self.task_management,
            "environment": self.environment
        }
        
        # Raise domain event
        self._events.append(ServerHealthChecked(
            server_name=self.name,
            status=status,
            uptime_seconds=uptime,
            timestamp=datetime.now()
        ))
        
        return ServerStatus(
            status=status,
            server_name=self.name,
            version=self.version,
            uptime_seconds=uptime,
            restart_count=self.restart_count,
            details=health_info
        )
    
    def get_capabilities(self) -> ServerCapabilities:
        """Get server capabilities and features"""
        core_features = [
            "Task Management",
            "Project Management", 
            "Agent Orchestration",
            "Cursor Rules Integration",
            "Multi-Agent Coordination",
            "Token-based Authentication",
            "Rate Limiting",
            "Security Logging",
            "Connection Management",
            "Real-time Status Updates"
        ]
        
        available_actions = {
            "connection_management": [
                "health_check", "server_capabilities", "connection_health",
                "status", "register_updates"
            ],
            "authentication": [
                "validate_token", "get_rate_limit_status", "revoke_token",
                "get_auth_status", "generate_token"
            ],
            "project_management": [
                "create", "get", "list", "create_tree", "get_tree_status", 
                "orchestrate", "get_dashboard"
            ],
            "task_management": [
                "create", "update", "complete", "list", "search", "get_next",
                "add_dependency", "remove_dependency", "list_dependencies"
            ],
            "subtask_management": [
                "add", "update", "remove", "list"
            ],
            "agent_management": [
                "register", "assign", "update", "list", "get", "unassign", "unregister"
            ]
        }
        
        return ServerCapabilities(
            core_features=core_features,
            available_actions=available_actions,
            authentication_enabled=self.authentication.get("enabled", False),
            mvp_mode=self.authentication.get("mvp_mode", False),
            version=self.version
        )
    
    def restart(self) -> None:
        """Record a server restart"""
        self.restart_count += 1
        self.started_at = datetime.now()
    
    def get_events(self) -> List[Any]:
        """Get domain events"""
        return self._events.copy()
    
    def clear_events(self) -> None:
        """Clear domain events"""
        self._events.clear() 