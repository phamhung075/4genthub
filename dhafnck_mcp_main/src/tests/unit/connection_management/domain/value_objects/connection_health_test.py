"""Unit tests for ConnectionHealth value object"""

import pytest
from fastmcp.connection_management.domain.value_objects.connection_health import ConnectionHealth


class TestConnectionHealth:
    """Tests for ConnectionHealth value object"""
    
    def test_create_healthy_connection_health(self):
        """Test creating a healthy ConnectionHealth"""
        health = ConnectionHealth(
            status="healthy",
            connection_id="conn-123",
            idle_time_seconds=30.0,
            duration_seconds=300.0,
            client_info={"client": "test-client"},
            issues=[],
            recommendations=[]
        )
        
        assert health.status == "healthy"
        assert health.connection_id == "conn-123"
        assert health.idle_time_seconds == 30.0
        assert health.duration_seconds == 300.0
        assert health.client_info == {"client": "test-client"}
        assert health.issues == []
        assert health.recommendations == []
    
    def test_create_unhealthy_connection_health(self):
        """Test creating an unhealthy ConnectionHealth"""
        health = ConnectionHealth(
            status="unhealthy",
            connection_id="conn-456",
            idle_time_seconds=7200.0,
            duration_seconds=86400.0,
            client_info={"client": "test-client", "version": "1.0"},
            issues=["Connection idle for too long", "High latency detected"],
            recommendations=["Consider reconnecting", "Check network stability"]
        )
        
        assert health.status == "unhealthy"
        assert health.connection_id == "conn-456"
        assert health.idle_time_seconds == 7200.0
        assert health.duration_seconds == 86400.0
        assert len(health.issues) == 2
        assert "Connection idle for too long" in health.issues
        assert len(health.recommendations) == 2
        assert "Consider reconnecting" in health.recommendations
    
    def test_is_healthy(self):
        """Test is_healthy method"""
        healthy = ConnectionHealth(
            status="healthy",
            connection_id="conn-123",
            idle_time_seconds=10.0,
            duration_seconds=100.0,
            client_info={},
            issues=[],
            recommendations=[]
        )
        
        unhealthy = ConnectionHealth(
            status="unhealthy",
            connection_id="conn-456",
            idle_time_seconds=3600.0,
            duration_seconds=7200.0,
            client_info={},
            issues=["Timeout"],
            recommendations=["Reconnect"]
        )
        
        assert healthy.is_healthy() is True
        assert unhealthy.is_healthy() is False
    
    def test_has_issues(self):
        """Test has_issues method"""
        no_issues = ConnectionHealth(
            status="healthy",
            connection_id="conn-123",
            idle_time_seconds=10.0,
            duration_seconds=100.0,
            client_info={},
            issues=[],
            recommendations=[]
        )
        
        with_issues = ConnectionHealth(
            status="unhealthy",
            connection_id="conn-456",
            idle_time_seconds=3600.0,
            duration_seconds=7200.0,
            client_info={},
            issues=["Connection timeout", "High memory usage"],
            recommendations=[]
        )
        
        # Can have issues even when healthy (warnings)
        healthy_with_warnings = ConnectionHealth(
            status="healthy",
            connection_id="conn-789",
            idle_time_seconds=60.0,
            duration_seconds=90000.0,
            client_info={},
            issues=["Connection active for over 24 hours"],
            recommendations=["Consider periodic reconnection"]
        )
        
        assert no_issues.has_issues() is False
        assert with_issues.has_issues() is True
        assert healthy_with_warnings.has_issues() is True
    
    def test_to_dict(self):
        """Test converting ConnectionHealth to dictionary"""
        health = ConnectionHealth(
            status="healthy",
            connection_id="conn-123",
            idle_time_seconds=45.5,
            duration_seconds=1800.0,
            client_info={"client": "test", "ip": "127.0.0.1"},
            issues=[],
            recommendations=[]
        )
        
        result = health.to_dict()
        
        assert result["success"] is True
        assert result["status"] == "healthy"
        assert result["connection_id"] == "conn-123"
        assert result["idle_time_seconds"] == 45.5
        assert result["duration_seconds"] == 1800.0
        assert result["client_info"]["client"] == "test"
        assert result["client_info"]["ip"] == "127.0.0.1"
        assert result["issues"] == []
        assert result["recommendations"] == []
    
    def test_invalid_status(self):
        """Test that invalid status raises ValueError"""
        with pytest.raises(ValueError, match="Invalid status: active"):
            ConnectionHealth(
                status="active",  # Invalid status
                connection_id="conn-123",
                idle_time_seconds=10.0,
                duration_seconds=100.0,
                client_info={},
                issues=[],
                recommendations=[]
            )
        
        with pytest.raises(ValueError, match="Invalid status: disconnected"):
            ConnectionHealth(
                status="disconnected",  # Invalid status
                connection_id="conn-123",
                idle_time_seconds=10.0,
                duration_seconds=100.0,
                client_info={},
                issues=[],
                recommendations=[]
            )
    
    def test_negative_idle_time(self):
        """Test that negative idle time raises ValueError"""
        with pytest.raises(ValueError, match="Idle time seconds cannot be negative"):
            ConnectionHealth(
                status="healthy",
                connection_id="conn-123",
                idle_time_seconds=-10.0,  # Negative idle time
                duration_seconds=100.0,
                client_info={},
                issues=[],
                recommendations=[]
            )
    
    def test_negative_duration(self):
        """Test that negative duration raises ValueError"""
        with pytest.raises(ValueError, match="Duration seconds cannot be negative"):
            ConnectionHealth(
                status="healthy",
                connection_id="conn-123",
                idle_time_seconds=10.0,
                duration_seconds=-100.0,  # Negative duration
                client_info={},
                issues=[],
                recommendations=[]
            )
    
    def test_immutability(self):
        """Test that ConnectionHealth is immutable"""
        health = ConnectionHealth(
            status="healthy",
            connection_id="conn-123",
            idle_time_seconds=10.0,
            duration_seconds=100.0,
            client_info={"client": "test"},
            issues=[],
            recommendations=[]
        )
        
        # Should not be able to modify attributes
        with pytest.raises(AttributeError):
            health.status = "unhealthy"
        
        with pytest.raises(AttributeError):
            health.idle_time_seconds = 20.0
        
        # But can modify mutable internal structures (this is a Python limitation)
        # The dataclass frozen=True only prevents reassignment, not mutation
        original_client_info = health.client_info.copy()
        health.client_info["new_key"] = "new_value"
        assert health.client_info["new_key"] == "new_value"  # Mutation is possible
        
        # Same with lists
        health.issues.append("New issue")
        assert "New issue" in health.issues  # Mutation is possible
    
    def test_complex_client_info(self):
        """Test ConnectionHealth with complex client information"""
        complex_client_info = {
            "client": "test-client",
            "version": "2.0.0",
            "platform": {
                "os": "Linux",
                "arch": "x86_64",
                "python": "3.11"
            },
            "features": ["auth", "rate-limiting", "caching"],
            "metadata": {
                "user_id": "user-123",
                "session_id": "sess-456",
                "region": "us-west-2"
            }
        }
        
        health = ConnectionHealth(
            status="healthy",
            connection_id="conn-complex",
            idle_time_seconds=15.0,
            duration_seconds=3600.0,
            client_info=complex_client_info,
            issues=[],
            recommendations=[]
        )
        
        assert health.client_info["platform"]["os"] == "Linux"
        assert "auth" in health.client_info["features"]
        assert health.client_info["metadata"]["user_id"] == "user-123"
        
        # Check to_dict preserves complex structure
        dict_repr = health.to_dict()
        assert dict_repr["client_info"]["platform"]["python"] == "3.11"
        assert len(dict_repr["client_info"]["features"]) == 3