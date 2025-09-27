"""Unit tests for ServerStatus value object"""

import pytest
from fastmcp.connection_management.domain.value_objects.server_status import ServerStatus


class TestServerStatus:
    """Tests for ServerStatus value object"""
    
    def test_create_healthy_server_status(self):
        """Test creating a healthy ServerStatus"""
        status = ServerStatus(
            status="healthy",
            server_name="test-server",
            version="1.0.0",
            uptime_seconds=3600.0,
            restart_count=0,
            details={"environment": "test", "load": "low"}
        )
        
        assert status.status == "healthy"
        assert status.server_name == "test-server"
        assert status.version == "1.0.0"
        assert status.uptime_seconds == 3600.0
        assert status.restart_count == 0
        assert status.details["environment"] == "test"
        assert status.details["load"] == "low"
    
    def test_create_unhealthy_server_status(self):
        """Test creating an unhealthy ServerStatus"""
        status = ServerStatus(
            status="unhealthy",
            server_name="prod-server",
            version="2.1.0",
            uptime_seconds=30.0,
            restart_count=5,
            details={
                "environment": "production",
                "error": "Database connection failed",
                "last_error_time": "2024-01-01T10:00:00"
            }
        )
        
        assert status.status == "unhealthy"
        assert status.server_name == "prod-server"
        assert status.version == "2.1.0"
        assert status.uptime_seconds == 30.0
        assert status.restart_count == 5
        assert status.details["error"] == "Database connection failed"
    
    def test_is_healthy(self):
        """Test is_healthy method"""
        healthy = ServerStatus(
            status="healthy",
            server_name="server1",
            version="1.0.0",
            uptime_seconds=1000.0,
            restart_count=0,
            details={}
        )
        
        unhealthy = ServerStatus(
            status="unhealthy",
            server_name="server2",
            version="1.0.0",
            uptime_seconds=10.0,
            restart_count=3,
            details={"error": "High CPU usage"}
        )
        
        assert healthy.is_healthy() is True
        assert unhealthy.is_healthy() is False
    
    def test_to_dict(self):
        """Test converting ServerStatus to dictionary"""
        status = ServerStatus(
            status="healthy",
            server_name="api-server",
            version="3.0.0",
            uptime_seconds=86400.0,
            restart_count=1,
            details={
                "environment": "staging",
                "authentication": {"enabled": True, "mvp_mode": False},
                "connections": 42,
                "memory_usage_mb": 512
            }
        )
        
        result = status.to_dict()
        
        assert result["success"] is True
        assert result["status"] == "healthy"
        assert result["server_name"] == "api-server"
        assert result["version"] == "3.0.0"
        assert result["uptime_seconds"] == 86400.0
        assert result["restart_count"] == 1
        # Details should be merged into the result
        assert result["environment"] == "staging"
        assert result["authentication"]["enabled"] is True
        assert result["connections"] == 42
        assert result["memory_usage_mb"] == 512
    
    def test_invalid_status(self):
        """Test that invalid status raises ValueError"""
        with pytest.raises(ValueError, match="Invalid status: running"):
            ServerStatus(
                status="running",  # Invalid status
                server_name="server",
                version="1.0.0",
                uptime_seconds=100.0,
                restart_count=0,
                details={}
            )
        
        with pytest.raises(ValueError, match="Invalid status: error"):
            ServerStatus(
                status="error",  # Invalid status
                server_name="server",
                version="1.0.0",
                uptime_seconds=100.0,
                restart_count=0,
                details={}
            )
    
    def test_negative_uptime(self):
        """Test that negative uptime raises ValueError"""
        with pytest.raises(ValueError, match="Uptime seconds cannot be negative"):
            ServerStatus(
                status="healthy",
                server_name="server",
                version="1.0.0",
                uptime_seconds=-10.0,  # Negative uptime
                restart_count=0,
                details={}
            )
    
    def test_negative_restart_count(self):
        """Test that negative restart count raises ValueError"""
        with pytest.raises(ValueError, match="Restart count cannot be negative"):
            ServerStatus(
                status="healthy",
                server_name="server",
                version="1.0.0",
                uptime_seconds=100.0,
                restart_count=-1,  # Negative restart count
                details={}
            )
    
    def test_immutability(self):
        """Test that ServerStatus is immutable"""
        status = ServerStatus(
            status="healthy",
            server_name="immutable-server",
            version="1.0.0",
            uptime_seconds=1000.0,
            restart_count=0,
            details={"key": "value"}
        )
        
        # Should not be able to modify attributes
        with pytest.raises(AttributeError):
            status.status = "unhealthy"
        
        with pytest.raises(AttributeError):
            status.uptime_seconds = 2000.0
        
        with pytest.raises(AttributeError):
            status.restart_count = 5
        
        # Note: The details dict can still be mutated (Python limitation)
        status.details["new_key"] = "new_value"
        assert status.details["new_key"] == "new_value"
    
    def test_complex_details(self):
        """Test ServerStatus with complex details"""
        complex_details = {
            "environment": {
                "type": "production",
                "region": "us-west-2",
                "cluster": "primary"
            },
            "authentication": {
                "enabled": True,
                "mvp_mode": False,
                "providers": ["jwt", "oauth2"],
                "rate_limits": {
                    "per_minute": 60,
                    "per_hour": 1000
                }
            },
            "task_management": {
                "active_tasks": 150,
                "completed_tasks": 3420,
                "max_tasks": 10000,
                "features": ["dependencies", "subtasks", "priorities"]
            },
            "monitoring": {
                "metrics_enabled": True,
                "logging_level": "INFO",
                "alerts": []
            }
        }
        
        status = ServerStatus(
            status="healthy",
            server_name="complex-server",
            version="4.2.0",
            uptime_seconds=172800.0,  # 2 days
            restart_count=2,
            details=complex_details
        )
        
        assert status.details["environment"]["region"] == "us-west-2"
        assert "jwt" in status.details["authentication"]["providers"]
        assert status.details["task_management"]["active_tasks"] == 150
        assert status.details["monitoring"]["logging_level"] == "INFO"
        
        # Check to_dict preserves complex structure
        dict_repr = status.to_dict()
        assert dict_repr["authentication"]["rate_limits"]["per_minute"] == 60
        assert "subtasks" in dict_repr["task_management"]["features"]
        assert dict_repr["monitoring"]["metrics_enabled"] is True
    
    def test_zero_values(self):
        """Test ServerStatus with zero values"""
        status = ServerStatus(
            status="healthy",
            server_name="new-server",
            version="0.0.1",
            uptime_seconds=0.0,  # Just started
            restart_count=0,     # Never restarted
            details={}
        )
        
        assert status.uptime_seconds == 0.0
        assert status.restart_count == 0
        assert status.is_healthy() is True
    
    def test_high_restart_count(self):
        """Test ServerStatus with high restart count"""
        status = ServerStatus(
            status="unhealthy",
            server_name="unstable-server",
            version="1.0.0",
            uptime_seconds=60.0,
            restart_count=100,  # Many restarts
            details={
                "stability": "poor",
                "last_restart_reason": "Out of memory",
                "recommendations": ["Increase memory allocation", "Check for memory leaks"]
            }
        )
        
        assert status.restart_count == 100
        assert status.details["stability"] == "poor"
        assert "Increase memory allocation" in status.details["recommendations"]