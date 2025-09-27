"""Unit tests for Connection domain entity"""

import pytest
from datetime import datetime, timedelta
from unittest.mock import patch
from fastmcp.connection_management.domain.entities.connection import Connection
from fastmcp.connection_management.domain.value_objects.connection_health import ConnectionHealth
from fastmcp.connection_management.domain.events.connection_events import ConnectionHealthChecked


class TestConnection:
    """Tests for Connection domain entity"""
    
    def test_create_connection(self):
        """Test creating a Connection with factory method"""
        connection_id = "conn-123"
        client_info = {"client": "test-client", "version": "1.0"}
        
        with patch('fastmcp.connection_management.domain.entities.connection.datetime') as mock_datetime:
            mock_now = datetime(2024, 1, 1, 10, 0, 0)
            mock_datetime.now.return_value = mock_now
            
            connection = Connection.create(connection_id, client_info)
            
            assert connection.connection_id == connection_id
            assert connection.client_info == client_info
            assert connection.established_at == mock_now
            assert connection.last_activity == mock_now
            assert connection.status == "active"
            assert connection.metadata == {}
    
    def test_update_activity(self):
        """Test updating connection activity timestamp"""
        connection = Connection.create("conn-123", {"client": "test"})
        initial_activity = connection.last_activity
        
        with patch('fastmcp.connection_management.domain.entities.connection.datetime') as mock_datetime:
            new_time = datetime(2024, 1, 1, 11, 0, 0)
            mock_datetime.now.return_value = new_time
            
            connection.update_activity()
            
            assert connection.last_activity == new_time
            assert connection.last_activity != initial_activity
    
    def test_get_connection_duration(self):
        """Test calculating connection duration"""
        with patch('fastmcp.connection_management.domain.entities.connection.datetime') as mock_datetime:
            start_time = datetime(2024, 1, 1, 10, 0, 0)
            mock_datetime.now.return_value = start_time
            
            connection = Connection.create("conn-123", {"client": "test"})
            
            # Move time forward by 2 hours
            current_time = datetime(2024, 1, 1, 12, 0, 0)
            mock_datetime.now.return_value = current_time
            
            duration = connection.get_connection_duration()
            assert duration == timedelta(hours=2)
    
    def test_get_idle_time(self):
        """Test calculating idle time since last activity"""
        with patch('fastmcp.connection_management.domain.entities.connection.datetime') as mock_datetime:
            start_time = datetime(2024, 1, 1, 10, 0, 0)
            mock_datetime.now.return_value = start_time
            
            connection = Connection.create("conn-123", {"client": "test"})
            
            # Move time forward by 30 minutes
            current_time = datetime(2024, 1, 1, 10, 30, 0)
            mock_datetime.now.return_value = current_time
            
            idle_time = connection.get_idle_time()
            assert idle_time == timedelta(minutes=30)
    
    def test_is_active_within_threshold(self):
        """Test checking if connection is active within threshold"""
        with patch('fastmcp.connection_management.domain.entities.connection.datetime') as mock_datetime:
            start_time = datetime(2024, 1, 1, 10, 0, 0)
            mock_datetime.now.return_value = start_time
            
            connection = Connection.create("conn-123", {"client": "test"})
            
            # Move time forward by 20 minutes
            current_time = datetime(2024, 1, 1, 10, 20, 0)
            mock_datetime.now.return_value = current_time
            
            # Should be active with default 30 minute threshold
            assert connection.is_active() is True
            
            # Should be active with 25 minute threshold
            assert connection.is_active(activity_threshold_minutes=25) is True
            
            # Should not be active with 15 minute threshold
            assert connection.is_active(activity_threshold_minutes=15) is False
    
    def test_is_active_beyond_threshold(self):
        """Test checking if connection is inactive beyond threshold"""
        with patch('fastmcp.connection_management.domain.entities.connection.datetime') as mock_datetime:
            start_time = datetime(2024, 1, 1, 10, 0, 0)
            mock_datetime.now.return_value = start_time
            
            connection = Connection.create("conn-123", {"client": "test"})
            
            # Move time forward by 45 minutes
            current_time = datetime(2024, 1, 1, 10, 45, 0)
            mock_datetime.now.return_value = current_time
            
            # Should not be active with default 30 minute threshold
            assert connection.is_active() is False
    
    def test_diagnose_health_healthy(self):
        """Test diagnosing a healthy connection"""
        with patch('fastmcp.connection_management.domain.entities.connection.datetime') as mock_datetime:
            start_time = datetime(2024, 1, 1, 10, 0, 0)
            mock_datetime.now.return_value = start_time
            
            connection = Connection.create("conn-123", {"client": "test"})
            
            # Move time forward by 15 minutes (healthy idle time)
            current_time = datetime(2024, 1, 1, 10, 15, 0)
            mock_datetime.now.return_value = current_time
            
            health = connection.diagnose_health()
            
            assert isinstance(health, ConnectionHealth)
            assert health.status == "healthy"
            assert health.connection_id == "conn-123"
            assert len(health.issues) == 0
            assert len(health.recommendations) == 0
            
            # Check that event was raised
            events = connection.get_events()
            assert len(events) == 1
            assert isinstance(events[0], ConnectionHealthChecked)
            assert events[0].status == "healthy"
    
    def test_diagnose_health_idle_too_long(self):
        """Test diagnosing connection with long idle time"""
        with patch('fastmcp.connection_management.domain.entities.connection.datetime') as mock_datetime:
            start_time = datetime(2024, 1, 1, 10, 0, 0)
            mock_datetime.now.return_value = start_time
            
            connection = Connection.create("conn-123", {"client": "test"})
            
            # Move time forward by 2 hours (unhealthy idle time)
            current_time = datetime(2024, 1, 1, 12, 30, 0)
            mock_datetime.now.return_value = current_time
            
            health = connection.diagnose_health()
            
            assert health.status == "unhealthy"
            assert "idle for over 1 hour" in health.issues[0]
            assert "Consider reconnecting" in health.recommendations[0]
    
    def test_diagnose_health_long_duration(self):
        """Test diagnosing connection with very long duration"""
        with patch('fastmcp.connection_management.domain.entities.connection.datetime') as mock_datetime:
            start_time = datetime(2024, 1, 1, 10, 0, 0)
            mock_datetime.now.return_value = start_time
            
            connection = Connection.create("conn-123", {"client": "test"})
            
            # Update activity to keep it "active"
            activity_time = datetime(2024, 1, 2, 9, 45, 0)
            mock_datetime.now.return_value = activity_time
            connection.update_activity()
            
            # Move time forward to over 24 hours duration but still active
            current_time = datetime(2024, 1, 2, 10, 15, 0)
            mock_datetime.now.return_value = current_time
            
            health = connection.diagnose_health()
            
            # Should be healthy (idle time is short) but have a warning
            assert health.status == "healthy"
            assert "active for over 24 hours" in health.issues[0]
            assert "periodic reconnection" in health.recommendations[0]
    
    def test_diagnose_health_disconnected(self):
        """Test diagnosing a disconnected connection"""
        connection = Connection.create("conn-123", {"client": "test"})
        connection.status = "disconnected"
        
        health = connection.diagnose_health()
        
        assert health.status == "unhealthy"
        assert "status is 'disconnected'" in health.issues[0]
        assert "Check client connection" in health.recommendations[0]
    
    def test_disconnect(self):
        """Test disconnecting a connection"""
        with patch('fastmcp.connection_management.domain.entities.connection.datetime') as mock_datetime:
            start_time = datetime(2024, 1, 1, 10, 0, 0)
            mock_datetime.now.return_value = start_time
            
            connection = Connection.create("conn-123", {"client": "test"})
            
            disconnect_time = datetime(2024, 1, 1, 11, 0, 0)
            mock_datetime.now.return_value = disconnect_time
            
            connection.disconnect()
            
            assert connection.status == "disconnected"
            assert connection.last_activity == disconnect_time
    
    def test_domain_events(self):
        """Test domain event management"""
        connection = Connection.create("conn-123", {"client": "test"})
        
        # Initially no events
        assert len(connection.get_events()) == 0
        
        # Diagnose health raises an event
        connection.diagnose_health()
        events = connection.get_events()
        assert len(events) == 1
        
        # Get events returns a copy
        events2 = connection.get_events()
        assert events is not connection._events
        assert events2 is not connection._events
        
        # Clear events
        connection.clear_events()
        assert len(connection.get_events()) == 0
    
    def test_connection_with_metadata(self):
        """Test creating connection with metadata"""
        connection = Connection(
            connection_id="conn-123",
            client_info={"client": "test"},
            established_at=datetime.now(),
            last_activity=datetime.now(),
            status="active",
            metadata={"user_id": "user-456", "session_type": "api"}
        )
        
        assert connection.metadata["user_id"] == "user-456"
        assert connection.metadata["session_type"] == "api"