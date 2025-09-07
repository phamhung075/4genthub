"""Unit tests for ConnectionDiagnosticsService Interface following DDD patterns"""

import pytest
from unittest.mock import Mock, MagicMock
from typing import Dict, Any, List
from datetime import datetime, timezone

from fastmcp.connection_management.domain.services.connection_diagnostics_service import ConnectionDiagnosticsService
from fastmcp.connection_management.domain.entities.connection import Connection
from fastmcp.connection_management.domain.value_objects.connection_health import ConnectionHealth


class MockConnectionDiagnosticsService(ConnectionDiagnosticsService):
    """Mock implementation of ConnectionDiagnosticsService for testing"""
    
    def __init__(self):
        self.diagnose_connection_health_called = False
        self.get_connection_statistics_called = False
        self.get_reconnection_recommendations_called = False
        self.analyze_connection_patterns_called = False
        self.validate_connection_infrastructure_called = False
    
    def diagnose_connection_health(self, connection: Connection) -> ConnectionHealth:
        """Mock implementation of connection health diagnosis"""
        self.diagnose_connection_health_called = True
        return ConnectionHealth(
            status="healthy",
            connection_id=connection.connection_id,
            idle_time_seconds=10.0,
            duration_seconds=100.0,
            client_info={"client": "test"},
            issues=[],
            recommendations=[]
        )
    
    def get_connection_statistics(self) -> Dict[str, Any]:
        """Mock implementation of connection statistics retrieval"""
        self.get_connection_statistics_called = True
        return {
            "total_connections": 50,
            "active_connections": 35,
            "failed_connections": 5,
            "average_latency_ms": 30,
            "average_uptime_hours": 24,
            "success_rate": 0.95
        }
    
    def get_reconnection_recommendations(self) -> Dict[str, Any]:
        """Mock implementation of reconnection recommendations"""
        self.get_reconnection_recommendations_called = True
        return {
            "recommendations": [
                "Increase connection timeout to 30s",
                "Enable connection pooling",
                "Implement exponential backoff for retries"
            ],
            "priority": "medium",
            "estimated_improvement": "25% reduction in connection failures"
        }
    
    def analyze_connection_patterns(self, connections: List[Connection]) -> Dict[str, Any]:
        """Mock implementation of connection pattern analysis"""
        self.analyze_connection_patterns_called = True
        return {
            "patterns": {
                "peak_hours": ["09:00-11:00", "14:00-16:00"],
                "failure_clusters": ["database_connections"],
                "bottlenecks": ["api_gateway"]
            },
            "insights": [
                "Most failures occur during peak hours",
                "Database connection pool is undersized"
            ],
            "risk_level": "moderate"
        }
    
    def validate_connection_infrastructure(self) -> Dict[str, Any]:
        """Mock implementation of infrastructure validation"""
        self.validate_connection_infrastructure_called = True
        return {
            "infrastructure_health": "good",
            "components": {
                "load_balancer": "healthy",
                "connection_pool": "healthy",
                "network": "degraded",
                "firewall": "healthy"
            },
            "issues": ["Network latency spike detected"],
            "recommendations": ["Consider upgrading network bandwidth"]
        }


class TestConnectionDiagnosticsService:
    """Test suite for ConnectionDiagnosticsService interface following DDD patterns"""
    
    def test_interface_methods_exist(self):
        """Test that all required interface methods exist"""
        required_methods = [
            'diagnose_connection_health',
            'get_connection_statistics',
            'get_reconnection_recommendations',
            'analyze_connection_patterns',
            'validate_connection_infrastructure'
        ]
        
        for method in required_methods:
            assert hasattr(ConnectionDiagnosticsService, method)
    
    def test_diagnose_connection_health_implementation(self):
        """Test diagnose_connection_health method implementation"""
        service = MockConnectionDiagnosticsService()
        connection = Mock(spec=Connection)
        connection.connection_id = "test-conn-1"
        
        result = service.diagnose_connection_health(connection)
        
        assert service.diagnose_connection_health_called is True
        assert isinstance(result, ConnectionHealth)
        assert result.status == "healthy"
        assert result.connection_id == "test-conn-1"
        assert result.idle_time_seconds == 10.0
        assert result.duration_seconds == 100.0
    
    def test_get_connection_statistics_implementation(self):
        """Test get_connection_statistics method implementation"""
        service = MockConnectionDiagnosticsService()
        
        result = service.get_connection_statistics()
        
        assert service.get_connection_statistics_called is True
        assert isinstance(result, dict)
        assert result["total_connections"] == 50
        assert result["active_connections"] == 35
        assert result["failed_connections"] == 5
        assert result["average_latency_ms"] == 30
        assert result["success_rate"] == 0.95
    
    def test_get_reconnection_recommendations_implementation(self):
        """Test get_reconnection_recommendations method implementation"""
        service = MockConnectionDiagnosticsService()
        
        result = service.get_reconnection_recommendations()
        
        assert service.get_reconnection_recommendations_called is True
        assert isinstance(result, dict)
        assert "recommendations" in result
        assert len(result["recommendations"]) == 3
        assert result["priority"] == "medium"
        assert "estimated_improvement" in result
    
    def test_analyze_connection_patterns_implementation(self):
        """Test analyze_connection_patterns method implementation"""
        service = MockConnectionDiagnosticsService()
        connections = [Mock(spec=Connection) for _ in range(5)]
        
        result = service.analyze_connection_patterns(connections)
        
        assert service.analyze_connection_patterns_called is True
        assert isinstance(result, dict)
        assert "patterns" in result
        assert "peak_hours" in result["patterns"]
        assert "failure_clusters" in result["patterns"]
        assert "insights" in result
        assert result["risk_level"] == "moderate"
    
    def test_validate_connection_infrastructure_implementation(self):
        """Test validate_connection_infrastructure method implementation"""
        service = MockConnectionDiagnosticsService()
        
        result = service.validate_connection_infrastructure()
        
        assert service.validate_connection_infrastructure_called is True
        assert isinstance(result, dict)
        assert result["infrastructure_health"] == "good"
        assert "components" in result
        assert result["components"]["load_balancer"] == "healthy"
        assert result["components"]["network"] == "degraded"
        assert len(result["issues"]) == 1
        assert len(result["recommendations"]) == 1
    
    def test_abstract_methods_cannot_be_instantiated(self):
        """Test that abstract ConnectionDiagnosticsService cannot be instantiated directly"""
        with pytest.raises(TypeError):
            # This should fail because ConnectionDiagnosticsService is abstract
            ConnectionDiagnosticsService()
    
    def test_service_integration_workflow(self):
        """Test a complete diagnostic workflow using the service"""
        service = MockConnectionDiagnosticsService()
        connection = Mock(spec=Connection)
        connection.connection_id = "test-conn-1"
        connections = [Mock(spec=Connection) for _ in range(3)]
        
        # Diagnose individual connection
        health = service.diagnose_connection_health(connection)
        assert health.status == "healthy"
        
        # Get overall statistics
        stats = service.get_connection_statistics()
        assert stats["total_connections"] > 0
        
        # Get recommendations
        recommendations = service.get_reconnection_recommendations()
        assert len(recommendations["recommendations"]) > 0
        
        # Analyze patterns
        patterns = service.analyze_connection_patterns(connections)
        assert "patterns" in patterns
        
        # Validate infrastructure
        infrastructure = service.validate_connection_infrastructure()
        assert "infrastructure_health" in infrastructure
        
        # Verify all methods were called
        assert service.diagnose_connection_health_called is True
        assert service.get_connection_statistics_called is True
        assert service.get_reconnection_recommendations_called is True
        assert service.analyze_connection_patterns_called is True
        assert service.validate_connection_infrastructure_called is True
    
    def test_service_with_unhealthy_connections(self):
        """Test service behavior with unhealthy connection scenarios"""
        class UnhealthyConnectionDiagnosticsService(ConnectionDiagnosticsService):
            def diagnose_connection_health(self, connection: Connection) -> ConnectionHealth:
                return ConnectionHealth(
                    status="unhealthy",
                    connection_id=connection.connection_id,
                    idle_time_seconds=300.0,
                    duration_seconds=50.0,
                    client_info={"client": "test", "errors": "multiple"},
                    issues=["High latency", "Packet loss", "Connection timeout"],
                    recommendations=["Check network", "Restart connection"]
                )
            
            def get_connection_statistics(self) -> Dict[str, Any]:
                return {
                    "total_connections": 100,
                    "active_connections": 20,
                    "failed_connections": 45,
                    "average_latency_ms": 250,
                    "average_uptime_hours": 2,
                    "success_rate": 0.55
                }
            
            def get_reconnection_recommendations(self) -> Dict[str, Any]:
                return {
                    "recommendations": [
                        "URGENT: Increase connection pool size immediately",
                        "URGENT: Implement circuit breaker pattern",
                        "CRITICAL: Review network infrastructure"
                    ],
                    "priority": "critical",
                    "estimated_improvement": "60% reduction in failures needed"
                }
            
            def analyze_connection_patterns(self, connections: List[Connection]) -> Dict[str, Any]:
                return {
                    "patterns": {
                        "failure_rate": "45%",
                        "cascade_failures": True,
                        "bottlenecks": ["all_services"]
                    },
                    "insights": [
                        "System experiencing cascade failures",
                        "All services showing degradation"
                    ],
                    "risk_level": "critical"
                }
            
            def validate_connection_infrastructure(self) -> Dict[str, Any]:
                return {
                    "infrastructure_health": "critical",
                    "components": {
                        "load_balancer": "failed",
                        "connection_pool": "exhausted",
                        "network": "critical",
                        "firewall": "overloaded"
                    },
                    "issues": [
                        "Load balancer not responding",
                        "Connection pool exhausted",
                        "Network packet loss exceeding threshold",
                        "Firewall dropping legitimate connections"
                    ],
                    "recommendations": [
                        "IMMEDIATE: Restart load balancer",
                        "IMMEDIATE: Increase connection pool size",
                        "URGENT: Scale infrastructure horizontally"
                    ]
                }
        
        service = UnhealthyConnectionDiagnosticsService()
        connection = Mock(spec=Connection)
        connection.connection_id = "unhealthy-conn-1"
        connections = [Mock(spec=Connection) for _ in range(5)]
        
        # Check unhealthy connection
        health = service.diagnose_connection_health(connection)
        assert health.status == "unhealthy"
        assert health.idle_time_seconds > 100
        assert len(health.issues) > 0
        
        # Check poor statistics
        stats = service.get_connection_statistics()
        assert stats["success_rate"] < 0.6
        assert stats["failed_connections"] > stats["active_connections"]
        
        # Check critical recommendations
        recommendations = service.get_reconnection_recommendations()
        assert recommendations["priority"] == "critical"
        assert any("URGENT" in r or "CRITICAL" in r for r in recommendations["recommendations"])
        
        # Check critical patterns
        patterns = service.analyze_connection_patterns(connections)
        assert patterns["risk_level"] == "critical"
        assert patterns["patterns"]["cascade_failures"] is True
        
        # Check critical infrastructure
        infrastructure = service.validate_connection_infrastructure()
        assert infrastructure["infrastructure_health"] == "critical"
        assert len(infrastructure["issues"]) > 2
        assert infrastructure["components"]["load_balancer"] == "failed"
    
    def test_empty_connections_list_handling(self):
        """Test handling of empty connections list in pattern analysis"""
        class EmptyConnectionsService(ConnectionDiagnosticsService):
            def diagnose_connection_health(self, connection: Connection) -> ConnectionHealth:
                return ConnectionHealth(
                    status="healthy",
                    latency_ms=0,
                    packet_loss=0.0,
                    bandwidth_mbps=0,
                    last_check=datetime.now(timezone.utc)
                )
            
            def get_connection_statistics(self) -> Dict[str, Any]:
                return {
                    "total_connections": 0,
                    "active_connections": 0,
                    "failed_connections": 0,
                    "average_latency_ms": 0,
                    "average_uptime_hours": 0,
                    "success_rate": 0.0
                }
            
            def get_reconnection_recommendations(self) -> Dict[str, Any]:
                return {
                    "recommendations": [],
                    "priority": "none",
                    "estimated_improvement": "N/A"
                }
            
            def analyze_connection_patterns(self, connections: List[Connection]) -> Dict[str, Any]:
                if not connections:
                    return {
                        "patterns": {},
                        "insights": ["No connections to analyze"],
                        "risk_level": "unknown"
                    }
                return {
                    "patterns": {},
                    "insights": [],
                    "risk_level": "low"
                }
            
            def validate_connection_infrastructure(self) -> Dict[str, Any]:
                return {
                    "infrastructure_health": "unknown",
                    "components": {},
                    "issues": [],
                    "recommendations": []
                }
        
        service = EmptyConnectionsService()
        empty_connections = []
        
        result = service.analyze_connection_patterns(empty_connections)
        assert result["risk_level"] == "unknown"
        assert result["insights"] == ["No connections to analyze"]