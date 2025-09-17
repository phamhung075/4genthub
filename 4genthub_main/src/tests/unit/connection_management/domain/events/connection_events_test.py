"""Test suite for Connection Management Domain Events"""

import pytest
from datetime import datetime, timezone
from typing import Dict, Any

from fastmcp.connection_management.domain.events.connection_events import (
    ConnectionEvent,
    ServerHealthChecked,
    ConnectionHealthChecked,
    StatusUpdateRequested,
    ClientRegisteredForUpdates,
    ServerCapabilitiesRequested,
    StatusUpdateBroadcasted,
    ClientRegistered,
    ClientUnregistered
)


class TestConnectionEvent:
    """Test suite for base ConnectionEvent class"""

    def test_connection_event_init(self):
        """Test ConnectionEvent initialization"""
        timestamp = datetime.now(timezone.utc)
        event = ConnectionEvent(timestamp=timestamp)
        
        assert event.timestamp == timestamp
        
    def test_connection_event_to_dict(self):
        """Test ConnectionEvent to_dict method"""
        timestamp = datetime.now(timezone.utc)
        event = ConnectionEvent(timestamp=timestamp)
        
        result = event.to_dict()
        
        assert result["event_type"] == "ConnectionEvent"
        # The to_dict method includes both ISO string and raw timestamp
        # Check that timestamp is present (might be datetime or ISO string)
        assert "timestamp" in result


class TestServerHealthChecked:
    """Test suite for ServerHealthChecked event"""

    def test_server_health_checked_init(self):
        """Test ServerHealthChecked initialization"""
        timestamp = datetime.now(timezone.utc)
        server_name = "test_server"
        status = "healthy"
        uptime_seconds = 123.45
        
        event = ServerHealthChecked(
            server_name=server_name,
            status=status,
            uptime_seconds=uptime_seconds,
            timestamp=timestamp
        )
        
        assert event.timestamp == timestamp
        assert event.server_name == server_name
        assert event.status == status
        assert event.uptime_seconds == uptime_seconds
        
    def test_server_health_checked_to_dict(self):
        """Test ServerHealthChecked to_dict method"""
        timestamp = datetime.now(timezone.utc)
        server_name = "test_server"
        status = "healthy"
        uptime_seconds = 123.45
        
        event = ServerHealthChecked(
            server_name=server_name,
            status=status,
            uptime_seconds=uptime_seconds,
            timestamp=timestamp
        )
        
        result = event.to_dict()
        
        assert result["event_type"] == "ServerHealthChecked"
        # The to_dict method includes the timestamp in the dict
        assert "timestamp" in result
        assert result["server_name"] == server_name
        assert result["status"] == status
        assert result["uptime_seconds"] == uptime_seconds


class TestConnectionHealthChecked:
    """Test suite for ConnectionHealthChecked event"""

    def test_connection_health_checked_init(self):
        """Test ConnectionHealthChecked initialization"""
        timestamp = datetime.now(timezone.utc)
        connection_id = "conn_123"
        status = "active"
        idle_time_seconds = 60.0
        
        event = ConnectionHealthChecked(
            connection_id=connection_id,
            status=status,
            idle_time_seconds=idle_time_seconds,
            timestamp=timestamp
        )
        
        assert event.timestamp == timestamp
        assert event.connection_id == connection_id
        assert event.status == status
        assert event.idle_time_seconds == idle_time_seconds
        
    def test_connection_health_checked_to_dict(self):
        """Test ConnectionHealthChecked to_dict method"""
        timestamp = datetime.now(timezone.utc)
        connection_id = "conn_123"
        status = "active"
        idle_time_seconds = 60.0
        
        event = ConnectionHealthChecked(
            connection_id=connection_id,
            status=status,
            idle_time_seconds=idle_time_seconds,
            timestamp=timestamp
        )
        
        result = event.to_dict()
        
        assert result["event_type"] == "ConnectionHealthChecked"
        # The to_dict method includes the timestamp in the dict
        assert "timestamp" in result
        assert result["connection_id"] == connection_id
        assert result["status"] == status
        assert result["idle_time_seconds"] == idle_time_seconds


class TestStatusUpdateRequested:
    """Test suite for StatusUpdateRequested event"""

    def test_status_update_requested_init(self):
        """Test StatusUpdateRequested initialization"""
        timestamp = datetime.now(timezone.utc)
        session_id = "session_123"
        update_type = "health_check"
        
        event = StatusUpdateRequested(
            session_id=session_id,
            update_type=update_type,
            timestamp=timestamp
        )
        
        assert event.timestamp == timestamp
        assert event.session_id == session_id
        assert event.update_type == update_type
        
    def test_status_update_requested_to_dict(self):
        """Test StatusUpdateRequested to_dict method"""
        timestamp = datetime.now(timezone.utc)
        session_id = "session_123"
        update_type = "health_check"
        
        event = StatusUpdateRequested(
            session_id=session_id,
            update_type=update_type,
            timestamp=timestamp
        )
        
        result = event.to_dict()
        
        assert result["event_type"] == "StatusUpdateRequested"
        # The to_dict method includes the timestamp in the dict
        assert "timestamp" in result
        assert result["session_id"] == session_id
        assert result["update_type"] == update_type


class TestClientRegisteredForUpdates:
    """Test suite for ClientRegisteredForUpdates event"""

    def test_client_registered_for_updates_init(self):
        """Test ClientRegisteredForUpdates initialization"""
        timestamp = datetime.now(timezone.utc)
        session_id = "session_123"
        client_info = {"name": "test_client", "version": "1.0.0"}
        
        event = ClientRegisteredForUpdates(
            session_id=session_id,
            client_info=client_info,
            timestamp=timestamp
        )
        
        assert event.timestamp == timestamp
        assert event.session_id == session_id
        assert event.client_info == client_info
        
    def test_client_registered_for_updates_to_dict(self):
        """Test ClientRegisteredForUpdates to_dict method"""
        timestamp = datetime.now(timezone.utc)
        session_id = "session_123"
        client_info = {"name": "test_client", "version": "1.0.0"}
        
        event = ClientRegisteredForUpdates(
            session_id=session_id,
            client_info=client_info,
            timestamp=timestamp
        )
        
        result = event.to_dict()
        
        assert result["event_type"] == "ClientRegisteredForUpdates"
        # The to_dict method includes the timestamp in the dict
        assert "timestamp" in result
        assert result["session_id"] == session_id
        assert result["client_info"] == client_info


class TestServerCapabilitiesRequested:
    """Test suite for ServerCapabilitiesRequested event"""

    def test_server_capabilities_requested_init(self):
        """Test ServerCapabilitiesRequested initialization"""
        timestamp = datetime.now(timezone.utc)
        requester_session = "session_123"
        
        event = ServerCapabilitiesRequested(
            requester_session=requester_session,
            timestamp=timestamp
        )
        
        assert event.timestamp == timestamp
        assert event.requester_session == requester_session
        
    def test_server_capabilities_requested_to_dict(self):
        """Test ServerCapabilitiesRequested to_dict method"""
        timestamp = datetime.now(timezone.utc)
        requester_session = "session_123"
        
        event = ServerCapabilitiesRequested(
            requester_session=requester_session,
            timestamp=timestamp
        )
        
        result = event.to_dict()
        
        assert result["event_type"] == "ServerCapabilitiesRequested"
        # The to_dict method includes the timestamp in the dict
        assert "timestamp" in result
        assert result["requester_session"] == requester_session


class TestStatusUpdateBroadcasted:
    """Test suite for StatusUpdateBroadcasted event"""

    def test_status_update_broadcasted_init(self):
        """Test StatusUpdateBroadcasted initialization"""
        timestamp = datetime.now(timezone.utc)
        event_type = "health_update"
        session_id = "session_123"
        data = {"status": "healthy", "uptime": 123.45}
        
        event = StatusUpdateBroadcasted(
            event_type=event_type,
            session_id=session_id,
            data=data,
            timestamp=timestamp
        )
        
        assert event.timestamp == timestamp
        assert event.event_type == event_type
        assert event.session_id == session_id
        assert event.data == data
        
    def test_status_update_broadcasted_to_dict(self):
        """Test StatusUpdateBroadcasted to_dict method"""
        timestamp = datetime.now(timezone.utc)
        event_type = "health_update"
        session_id = "session_123"
        data = {"status": "healthy", "uptime": 123.45}
        
        event = StatusUpdateBroadcasted(
            event_type=event_type,
            session_id=session_id,
            data=data,
            timestamp=timestamp
        )
        
        result = event.to_dict()
        
        assert result["event_type"] == "health_update"
        # The to_dict method includes the timestamp in the dict
        assert "timestamp" in result
        # Note: event_type appears twice due to both class name and instance variable
        assert result["session_id"] == session_id
        assert result["data"] == data


class TestClientRegistered:
    """Test suite for ClientRegistered event"""

    def test_client_registered_init(self):
        """Test ClientRegistered initialization"""
        timestamp = datetime.now(timezone.utc)
        session_id = "session_123"
        client_info = {"name": "test_client", "version": "1.0.0"}
        
        event = ClientRegistered(
            session_id=session_id,
            client_info=client_info,
            timestamp=timestamp
        )
        
        assert event.timestamp == timestamp
        assert event.session_id == session_id
        assert event.client_info == client_info
        
    def test_client_registered_to_dict(self):
        """Test ClientRegistered to_dict method"""
        timestamp = datetime.now(timezone.utc)
        session_id = "session_123"
        client_info = {"name": "test_client", "version": "1.0.0"}
        
        event = ClientRegistered(
            session_id=session_id,
            client_info=client_info,
            timestamp=timestamp
        )
        
        result = event.to_dict()
        
        assert result["event_type"] == "ClientRegistered"
        # The to_dict method includes the timestamp in the dict
        assert "timestamp" in result
        assert result["session_id"] == session_id
        assert result["client_info"] == client_info


class TestClientUnregistered:
    """Test suite for ClientUnregistered event"""

    def test_client_unregistered_init(self):
        """Test ClientUnregistered initialization"""
        timestamp = datetime.now(timezone.utc)
        session_id = "session_123"
        reason = "client_disconnect"
        
        event = ClientUnregistered(
            session_id=session_id,
            reason=reason,
            timestamp=timestamp
        )
        
        assert event.timestamp == timestamp
        assert event.session_id == session_id
        assert event.reason == reason
        
    def test_client_unregistered_to_dict(self):
        """Test ClientUnregistered to_dict method"""
        timestamp = datetime.now(timezone.utc)
        session_id = "session_123"
        reason = "client_disconnect"
        
        event = ClientUnregistered(
            session_id=session_id,
            reason=reason,
            timestamp=timestamp
        )
        
        result = event.to_dict()
        
        assert result["event_type"] == "ClientUnregistered"
        # The to_dict method includes the timestamp in the dict
        assert "timestamp" in result
        assert result["session_id"] == session_id
        assert result["reason"] == reason


class TestEventInheritance:
    """Test suite for verifying proper event inheritance"""

    def test_all_events_inherit_from_connection_event(self):
        """Test that all events inherit from ConnectionEvent"""
        timestamp = datetime.now(timezone.utc)
        
        events = [
            ServerHealthChecked("server", "healthy", 123.45, timestamp),
            ConnectionHealthChecked("conn_123", "active", 60.0, timestamp),
            StatusUpdateRequested("session_123", "health_check", timestamp),
            ClientRegisteredForUpdates("session_123", {}, timestamp),
            ServerCapabilitiesRequested("session_123", timestamp),
            StatusUpdateBroadcasted("health_update", "session_123", {}, timestamp),
            ClientRegistered("session_123", {}, timestamp),
            ClientUnregistered("session_123", "disconnect", timestamp)
        ]
        
        for event in events:
            assert isinstance(event, ConnectionEvent)
            assert hasattr(event, "timestamp")
            assert hasattr(event, "to_dict")


class TestEventEdgeCases:
    """Test suite for edge cases and error conditions"""

    def test_empty_client_info(self):
        """Test events with empty client info"""
        timestamp = datetime.now(timezone.utc)
        client_info = {}
        
        event = ClientRegistered(
            session_id="session_123",
            client_info=client_info,
            timestamp=timestamp
        )
        
        assert event.client_info == {}
        result = event.to_dict()
        assert result["client_info"] == {}
        
    def test_empty_data_dict(self):
        """Test StatusUpdateBroadcasted with empty data"""
        timestamp = datetime.now(timezone.utc)
        data = {}
        
        event = StatusUpdateBroadcasted(
            event_type="health_update",
            session_id="session_123",
            data=data,
            timestamp=timestamp
        )
        
        assert event.data == {}
        result = event.to_dict()
        assert result["data"] == {}
        
    def test_zero_uptime_and_idle_time(self):
        """Test events with zero time values"""
        timestamp = datetime.now(timezone.utc)
        
        health_event = ServerHealthChecked("server", "healthy", 0.0, timestamp)
        assert health_event.uptime_seconds == 0.0
        
        conn_event = ConnectionHealthChecked("conn_123", "active", 0.0, timestamp)
        assert conn_event.idle_time_seconds == 0.0
        
    def test_special_characters_in_strings(self):
        """Test events with special characters in string fields"""
        timestamp = datetime.now(timezone.utc)
        
        event = ServerHealthChecked(
            server_name="test-server_123!@#",
            status="healthy/active",
            uptime_seconds=123.45,
            timestamp=timestamp
        )
        
        result = event.to_dict()
        assert result["server_name"] == "test-server_123!@#"
        assert result["status"] == "healthy/active"