"""Unit tests for StatusUpdate Value Object following DDD patterns"""

import pytest
from datetime import datetime, timezone
from typing import Dict, Any

from fastmcp.connection_management.domain.value_objects.status_update import StatusUpdate


class TestStatusUpdate:
    """Test suite for StatusUpdate value object following DDD patterns"""
    
    def test_status_update_creation_success(self):
        """Test successful creation of StatusUpdate with valid data"""
        now = datetime.now(timezone.utc)
        status_update = StatusUpdate(
            event_type="server_health_changed",
            timestamp=now,
            data={"health_status": "healthy", "uptime": 3600},
            session_id="session123"
        )
        
        assert status_update.event_type == "server_health_changed"
        assert status_update.timestamp == now
        assert status_update.data == {"health_status": "healthy", "uptime": 3600}
        assert status_update.session_id == "session123"
    
    def test_status_update_immutability(self):
        """Test that StatusUpdate is immutable (frozen dataclass)"""
        now = datetime.now(timezone.utc)
        status_update = StatusUpdate(
            event_type="connection_established",
            timestamp=now,
            data={"connection_id": "conn123"},
            session_id="session456"
        )
        
        # Attempt to modify should raise error
        with pytest.raises(AttributeError):
            status_update.event_type = "connection_lost"
        
        with pytest.raises(AttributeError):
            status_update.session_id = "new_session"
    
    def test_empty_event_type_raises_error(self):
        """Test that empty event type raises ValueError"""
        with pytest.raises(ValueError, match="Event type cannot be empty"):
            StatusUpdate(
                event_type="",
                timestamp=datetime.now(),
                data={},
                session_id="session123"
            )
    
    def test_empty_session_id_raises_error(self):
        """Test that empty session ID raises ValueError"""
        with pytest.raises(ValueError, match="Session ID cannot be empty"):
            StatusUpdate(
                event_type="server_health_changed",
                timestamp=datetime.now(),
                data={},
                session_id=""
            )
    
    def test_invalid_event_type_raises_error(self):
        """Test that invalid event type raises ValueError"""
        with pytest.raises(ValueError, match="Invalid event type: invalid_event"):
            StatusUpdate(
                event_type="invalid_event",
                timestamp=datetime.now(),
                data={},
                session_id="session123"
            )
    
    def test_all_valid_event_types(self):
        """Test creation with all valid event types"""
        valid_event_types = [
            "server_health_changed",
            "connection_established",
            "connection_lost",
            "status_broadcast",
            "client_registered",
            "client_unregistered"
        ]
        
        now = datetime.now(timezone.utc)
        for event_type in valid_event_types:
            status_update = StatusUpdate(
                event_type=event_type,
                timestamp=now,
                data={"test": "data"},
                session_id="session123"
            )
            assert status_update.event_type == event_type
    
    def test_to_dict_conversion(self):
        """Test conversion to dictionary representation"""
        now = datetime.now(timezone.utc)
        status_update = StatusUpdate(
            event_type="server_health_changed",
            timestamp=now,
            data={"health_status": "healthy", "cpu_usage": 45.5},
            session_id="session789"
        )
        
        result = status_update.to_dict()
        
        assert result["event_type"] == "server_health_changed"
        assert result["timestamp"] == now.isoformat()
        assert result["session_id"] == "session789"
        assert result["data"] == {"health_status": "healthy", "cpu_usage": 45.5}
    
    def test_create_server_health_update_factory(self):
        """Test factory method for server health updates"""
        update = StatusUpdate.create_server_health_update(
            session_id="session123",
            health_status="degraded",
            details={"memory_usage": 85, "disk_space": 20}
        )
        
        assert update.event_type == "server_health_changed"
        assert update.session_id == "session123"
        assert update.data["health_status"] == "degraded"
        assert update.data["memory_usage"] == 85
        assert update.data["disk_space"] == 20
        assert isinstance(update.timestamp, datetime)
    
    def test_create_connection_update_factory_established(self):
        """Test factory method for connection established updates"""
        update = StatusUpdate.create_connection_update(
            session_id="session456",
            connection_id="conn789",
            event="established"
        )
        
        assert update.event_type == "connection_established"
        assert update.session_id == "session456"
        assert update.data["connection_id"] == "conn789"
        assert isinstance(update.timestamp, datetime)
    
    def test_create_connection_update_factory_lost(self):
        """Test factory method for connection lost updates"""
        update = StatusUpdate.create_connection_update(
            session_id="session111",
            connection_id="conn222",
            event="lost"
        )
        
        assert update.event_type == "connection_lost"
        assert update.session_id == "session111"
        assert update.data["connection_id"] == "conn222"
        assert isinstance(update.timestamp, datetime)
    
    def test_create_client_registration_update_registered(self):
        """Test factory method for client registration (registered)"""
        update = StatusUpdate.create_client_registration_update(
            session_id="session333",
            registered=True
        )
        
        assert update.event_type == "client_registered"
        assert update.session_id == "session333"
        assert update.data == {}
        assert isinstance(update.timestamp, datetime)
    
    def test_create_client_registration_update_unregistered(self):
        """Test factory method for client registration (unregistered)"""
        update = StatusUpdate.create_client_registration_update(
            session_id="session444",
            registered=False
        )
        
        assert update.event_type == "client_unregistered"
        assert update.session_id == "session444"
        assert update.data == {}
        assert isinstance(update.timestamp, datetime)
    
    def test_complex_data_structure(self):
        """Test StatusUpdate with complex nested data structure"""
        now = datetime.now(timezone.utc)
        complex_data = {
            "health_metrics": {
                "cpu": {"usage": 45.5, "cores": 8},
                "memory": {"used": 4096, "total": 8192},
                "disk": [
                    {"path": "/", "used": 50, "total": 100},
                    {"path": "/data", "used": 20, "total": 50}
                ]
            },
            "services": {
                "database": "running",
                "cache": "running",
                "queue": "stopped"
            },
            "timestamp": now.isoformat()
        }
        
        status_update = StatusUpdate(
            event_type="server_health_changed",
            timestamp=now,
            data=complex_data,
            session_id="complex_session"
        )
        
        assert status_update.data == complex_data
        result = status_update.to_dict()
        assert result["data"] == complex_data
    
    def test_empty_data_allowed(self):
        """Test that empty data dictionary is allowed"""
        now = datetime.now(timezone.utc)
        status_update = StatusUpdate(
            event_type="status_broadcast",
            timestamp=now,
            data={},
            session_id="session_empty"
        )
        
        assert status_update.data == {}
        result = status_update.to_dict()
        assert result["data"] == {}
    
    def test_timestamp_handling(self):
        """Test proper timestamp handling in to_dict"""
        # Test with timezone-aware datetime
        tz_aware = datetime.now(timezone.utc)
        update1 = StatusUpdate(
            event_type="status_broadcast",
            timestamp=tz_aware,
            data={},
            session_id="session1"
        )
        result1 = update1.to_dict()
        assert result1["timestamp"] == tz_aware.isoformat()
        
        # Test with naive datetime
        naive = datetime.now()
        update2 = StatusUpdate(
            event_type="status_broadcast",
            timestamp=naive,
            data={},
            session_id="session2"
        )
        result2 = update2.to_dict()
        assert result2["timestamp"] == naive.isoformat()
    
    def test_factory_methods_generate_unique_timestamps(self):
        """Test that factory methods generate unique timestamps for different calls"""
        import time
        
        update1 = StatusUpdate.create_server_health_update(
            session_id="session1",
            health_status="healthy",
            details={}
        )
        
        # Small delay to ensure different timestamps
        time.sleep(0.001)
        
        update2 = StatusUpdate.create_server_health_update(
            session_id="session2",
            health_status="healthy",
            details={}
        )
        
        # Timestamps should be different
        assert update1.timestamp != update2.timestamp
        assert update1.timestamp < update2.timestamp