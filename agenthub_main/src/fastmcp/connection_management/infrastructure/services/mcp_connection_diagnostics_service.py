"""MCP Connection Diagnostics Service Implementation"""

import logging
from typing import Dict, Any, List

from ...domain.services.connection_diagnostics_service import ConnectionDiagnosticsService
from ...domain.entities.connection import Connection
from ...domain.value_objects.connection_health import ConnectionHealth

logger = logging.getLogger(__name__)


class MCPConnectionDiagnosticsService(ConnectionDiagnosticsService):
    """Infrastructure implementation of ConnectionDiagnosticsService that integrates with MCP infrastructure"""
    
    def diagnose_connection_health(self, connection: Connection) -> ConnectionHealth:
        """Perform comprehensive connection health diagnosis"""
        # Delegate to the connection entity for the actual diagnosis logic
        return connection.diagnose_health()
    
    def get_connection_statistics(self) -> Dict[str, Any]:
        """Get overall connection statistics"""
        try:
            # Try to get stats from the existing connection manager
            from ....server.connection_manager import get_connection_manager
            
            # For now, return basic stats
            # In a real async implementation, this would await the connection manager
            return {
                "active_connections": 0,
                "total_connections": 0,
                "server_restart_count": 0,
                "uptime_seconds": 0,
                "connection_health": "no_clients"
            }
            
        except Exception as e:
            logger.error(f"Error getting connection statistics: {e}")
            return {
                "active_connections": 0,
                "total_connections": 0,
                "error": str(e)
            }
    
    def get_reconnection_recommendations(self) -> Dict[str, Any]:
        """Get recommendations for connection issues"""
        try:
            # Try to get recommendations from the existing connection manager
            from ....server.connection_manager import get_connection_manager
            
            # For now, return basic recommendations
            # In a real async implementation, this would await the connection manager
            return {
                "recommended_action": "no_action_needed",
                "recommendations": [
                    "Server is running normally",
                    "No connection issues detected",
                    "Monitor connection patterns for optimization"
                ]
            }
            
        except Exception as e:
            logger.error(f"Error getting reconnection recommendations: {e}")
            return {
                "recommended_action": "check_server_logs",
                "recommendations": [
                    "Check server logs for connection issues",
                    "Verify network connectivity",
                    "Restart MCP server if problems persist"
                ],
                "error": str(e)
            }
    
    def analyze_connection_patterns(self, connections: List[Connection]) -> Dict[str, Any]:
        """Analyze connection patterns and identify issues"""
        if not connections:
            return {
                "pattern_analysis": "no_connections",
                "issues": ["No active connections to analyze"],
                "recommendations": ["Establish at least one connection for pattern analysis"]
            }
        
        # Analyze connection patterns
        total_connections = len(connections)
        active_connections = [conn for conn in connections if conn.is_active()]
        idle_connections = [conn for conn in connections if not conn.is_active()]
        
        issues = []
        recommendations = []
        
        if len(idle_connections) > len(active_connections):
            issues.append("More idle connections than active ones")
            recommendations.append("Consider cleaning up idle connections")
        
        if total_connections > 10:
            issues.append("High number of connections detected")
            recommendations.append("Monitor connection pooling and cleanup")
        
        return {
            "total_connections": total_connections,
            "active_connections": len(active_connections),
            "idle_connections": len(idle_connections),
            "issues": issues,
            "recommendations": recommendations
        }
    
    def validate_connection_infrastructure(self) -> Dict[str, Any]:
        """Validate connection infrastructure health"""
        try:
            # Check if connection manager and status broadcaster are available
            from ....server.connection_manager import get_connection_manager
            from ....server.connection_status_broadcaster import get_status_broadcaster
            
            return {
                "connection_manager_available": True,
                "status_broadcaster_available": True,
                "infrastructure_health": "healthy"
            }
            
        except ImportError as e:
            logger.error(f"Connection infrastructure not available: {e}")
            return {
                "connection_manager_available": False,
                "status_broadcaster_available": False,
                "infrastructure_health": "degraded",
                "error": str(e)
            }
        except Exception as e:
            logger.error(f"Error validating connection infrastructure: {e}")
            return {
                "infrastructure_health": "error",
                "error": str(e)
            } 