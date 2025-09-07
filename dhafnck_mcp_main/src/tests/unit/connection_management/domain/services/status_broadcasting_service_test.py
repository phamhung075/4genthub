"""Test suite for Status Broadcasting Service Interface"""

import pytest
from abc import ABC, abstractmethod
from typing import Dict, Any
from unittest.mock import Mock
from datetime import datetime

from fastmcp.connection_management.domain.services.status_broadcasting_service import StatusBroadcastingService
from fastmcp.connection_management.domain.value_objects.status_update import StatusUpdate


class TestStatusBroadcastingService:
    """Test suite for StatusBroadcastingService interface"""

    def test_status_broadcasting_service_is_abstract(self):
        """Test that StatusBroadcastingService is an abstract base class"""
        assert issubclass(StatusBroadcastingService, ABC)
        
        # Should not be able to instantiate directly
        with pytest.raises(TypeError):
            StatusBroadcastingService()
    
    def test_status_broadcasting_service_has_required_abstract_methods(self):
        """Test that StatusBroadcastingService defines all required abstract methods"""
        abstract_methods = StatusBroadcastingService.__abstractmethods__
        
        expected_methods = {
            'register_client_for_updates',
            'unregister_client',
            'broadcast_status_update',
            'get_registered_clients_count',
            'get_last_broadcast_info',
            'validate_broadcasting_infrastructure'
        }
        
        assert abstract_methods == expected_methods
    
    def test_register_client_for_updates_signature(self):
        """Test register_client_for_updates method signature"""
        method = StatusBroadcastingService.register_client_for_updates
        
        assert hasattr(method, '__isabstractmethod__')
        assert method.__isabstractmethod__ is True
        
    def test_unregister_client_signature(self):
        """Test unregister_client method signature"""
        method = StatusBroadcastingService.unregister_client
        
        assert hasattr(method, '__isabstractmethod__')
        assert method.__isabstractmethod__ is True
        
    def test_broadcast_status_update_signature(self):
        """Test broadcast_status_update method signature"""
        method = StatusBroadcastingService.broadcast_status_update
        
        assert hasattr(method, '__isabstractmethod__')
        assert method.__isabstractmethod__ is True
        
    def test_get_registered_clients_count_signature(self):
        """Test get_registered_clients_count method signature"""
        method = StatusBroadcastingService.get_registered_clients_count
        
        assert hasattr(method, '__isabstractmethod__')
        assert method.__isabstractmethod__ is True
        
    def test_get_last_broadcast_info_signature(self):
        """Test get_last_broadcast_info method signature"""
        method = StatusBroadcastingService.get_last_broadcast_info
        
        assert hasattr(method, '__isabstractmethod__')
        assert method.__isabstractmethod__ is True
        
    def test_validate_broadcasting_infrastructure_signature(self):
        """Test validate_broadcasting_infrastructure method signature"""
        method = StatusBroadcastingService.validate_broadcasting_infrastructure
        
        assert hasattr(method, '__isabstractmethod__')
        assert method.__isabstractmethod__ is True


class MockStatusBroadcastingService(StatusBroadcastingService):
    """Mock implementation of StatusBroadcastingService for testing"""

    def __init__(self):
        self.registered_clients: Dict[str, Dict[str, Any]] = {}
        self.last_broadcast: Dict[str, Any] = {}
        self.call_log: list = []
        self.broadcast_failures: Dict[str, str] = {}  # session_id -> failure_reason

    def register_client_for_updates(self, session_id: str, client_info: Dict[str, Any]) -> StatusUpdate:
        self.call_log.append(f"register_client_for_updates({session_id}, {client_info})")
        self.registered_clients[session_id] = client_info
        
        # Create a mock StatusUpdate
        status_update = Mock(spec=StatusUpdate)
        status_update.session_id = session_id
        status_update.update_type = "registration_confirmed"
        status_update.timestamp = datetime.now()
        status_update.data = {"status": "registered", "client_info": client_info}
        
        return status_update

    def unregister_client(self, session_id: str) -> bool:
        self.call_log.append(f"unregister_client({session_id})")
        if session_id in self.registered_clients:
            del self.registered_clients[session_id]
            return True
        return False

    def broadcast_status_update(self, update: StatusUpdate) -> bool:
        self.call_log.append(f"broadcast_status_update({update.update_type})")
        
        # Record last broadcast info
        self.last_broadcast = {
            "timestamp": datetime.now(),
            "update_type": update.update_type,
            "session_id": getattr(update, 'session_id', None),
            "clients_notified": len(self.registered_clients),
            "data": getattr(update, 'data', {})
        }
        
        # Simulate broadcast success/failure
        if hasattr(update, 'session_id') and update.session_id in self.broadcast_failures:
            return False
        
        return len(self.registered_clients) > 0

    def get_registered_clients_count(self) -> int:
        self.call_log.append("get_registered_clients_count()")
        return len(self.registered_clients)

    def get_last_broadcast_info(self) -> Dict[str, Any]:
        self.call_log.append("get_last_broadcast_info()")
        return self.last_broadcast.copy()

    def validate_broadcasting_infrastructure(self) -> Dict[str, Any]:
        self.call_log.append("validate_broadcasting_infrastructure()")
        return {
            "infrastructure_status": "healthy",
            "registered_clients": len(self.registered_clients),
            "last_broadcast_timestamp": self.last_broadcast.get("timestamp"),
            "websocket_connections": len(self.registered_clients),
            "failed_broadcasts": len(self.broadcast_failures)
        }

    # Helper method for testing
    def simulate_broadcast_failure(self, session_id: str, reason: str):
        """Simulate a broadcast failure for testing"""
        self.broadcast_failures[session_id] = reason


class TestMockStatusBroadcastingService:
    """Test suite for the mock implementation to verify contract compliance"""

    def setup_method(self):
        """Set up test fixtures"""
        self.service = MockStatusBroadcastingService()

    def test_mock_service_instantiation(self):
        """Test that mock service can be instantiated"""
        service = MockStatusBroadcastingService()
        assert isinstance(service, StatusBroadcastingService)
        assert service.registered_clients == {}
        assert service.last_broadcast == {}
        assert service.call_log == []

    def test_register_client_for_updates_creates_registration(self):
        """Test register_client_for_updates creates client registration"""
        session_id = "session_123"
        client_info = {"name": "test_client", "version": "1.0.0", "type": "web"}
        
        result = self.service.register_client_for_updates(session_id, client_info)
        
        assert result is not None
        assert hasattr(result, 'session_id')
        assert result.session_id == session_id
        assert result.update_type == "registration_confirmed"
        assert session_id in self.service.registered_clients
        assert self.service.registered_clients[session_id] == client_info

    def test_register_multiple_clients(self):
        """Test registering multiple clients"""
        clients = [
            ("session_1", {"name": "client1", "type": "web"}),
            ("session_2", {"name": "client2", "type": "mobile"}),
            ("session_3", {"name": "client3", "type": "desktop"})
        ]
        
        for session_id, client_info in clients:
            result = self.service.register_client_for_updates(session_id, client_info)
            assert result.session_id == session_id
        
        assert len(self.service.registered_clients) == 3
        assert self.service.get_registered_clients_count() == 3

    def test_unregister_client_removes_existing_client(self):
        """Test unregister_client removes existing client"""
        session_id = "session_to_remove"
        client_info = {"name": "temp_client"}
        
        # Register first
        self.service.register_client_for_updates(session_id, client_info)
        assert session_id in self.service.registered_clients
        
        # Unregister
        result = self.service.unregister_client(session_id)
        
        assert result is True
        assert session_id not in self.service.registered_clients
        assert self.service.get_registered_clients_count() == 0

    def test_unregister_client_returns_false_for_nonexistent(self):
        """Test unregister_client returns False for non-existent client"""
        result = self.service.unregister_client("nonexistent_session")
        assert result is False

    def test_broadcast_status_update_with_clients(self):
        """Test broadcast_status_update when clients are registered"""
        # Register a client first
        self.service.register_client_for_updates("session_1", {"name": "client1"})
        
        # Create status update
        update = Mock(spec=StatusUpdate)
        update.update_type = "health_check"
        update.session_id = "session_1"
        update.data = {"status": "healthy"}
        
        result = self.service.broadcast_status_update(update)
        
        assert result is True
        assert self.service.last_broadcast["update_type"] == "health_check"
        assert self.service.last_broadcast["clients_notified"] == 1

    def test_broadcast_status_update_without_clients(self):
        """Test broadcast_status_update when no clients are registered"""
        update = Mock(spec=StatusUpdate)
        update.update_type = "health_check"
        update.data = {"status": "healthy"}
        
        result = self.service.broadcast_status_update(update)
        
        assert result is False  # No clients to notify
        assert self.service.last_broadcast["clients_notified"] == 0

    def test_broadcast_status_update_with_simulated_failure(self):
        """Test broadcast_status_update with simulated failure"""
        session_id = "failing_session"
        self.service.register_client_for_updates(session_id, {"name": "failing_client"})
        self.service.simulate_broadcast_failure(session_id, "connection_lost")
        
        update = Mock(spec=StatusUpdate)
        update.update_type = "health_check"
        update.session_id = session_id
        update.data = {"status": "healthy"}
        
        result = self.service.broadcast_status_update(update)
        
        assert result is False  # Simulated failure

    def test_get_registered_clients_count(self):
        """Test get_registered_clients_count returns correct count"""
        assert self.service.get_registered_clients_count() == 0
        
        # Register clients
        for i in range(3):
            self.service.register_client_for_updates(f"session_{i}", {"name": f"client_{i}"})
        
        assert self.service.get_registered_clients_count() == 3
        
        # Unregister one
        self.service.unregister_client("session_1")
        assert self.service.get_registered_clients_count() == 2

    def test_get_last_broadcast_info_initially_empty(self):
        """Test get_last_broadcast_info returns empty dict initially"""
        result = self.service.get_last_broadcast_info()
        assert result == {}

    def test_get_last_broadcast_info_after_broadcast(self):
        """Test get_last_broadcast_info returns correct info after broadcast"""
        # Register client
        self.service.register_client_for_updates("session_1", {"name": "client1"})
        
        # Broadcast update
        update = Mock(spec=StatusUpdate)
        update.update_type = "server_status"
        update.session_id = "session_1"
        update.data = {"uptime": 3600}
        
        self.service.broadcast_status_update(update)
        
        result = self.service.get_last_broadcast_info()
        
        assert result["update_type"] == "server_status"
        assert result["session_id"] == "session_1"
        assert result["clients_notified"] == 1
        assert result["data"] == {"uptime": 3600}
        assert "timestamp" in result

    def test_validate_broadcasting_infrastructure(self):
        """Test validate_broadcasting_infrastructure returns correct status"""
        result = self.service.validate_broadcasting_infrastructure()
        
        expected_keys = {
            "infrastructure_status",
            "registered_clients",
            "last_broadcast_timestamp",
            "websocket_connections",
            "failed_broadcasts"
        }
        
        assert set(result.keys()) == expected_keys
        assert result["infrastructure_status"] == "healthy"
        assert result["registered_clients"] == 0
        assert result["websocket_connections"] == 0
        assert result["failed_broadcasts"] == 0

    def test_validate_broadcasting_infrastructure_with_activity(self):
        """Test validate_broadcasting_infrastructure with clients and broadcasts"""
        # Register clients
        self.service.register_client_for_updates("session_1", {"name": "client1"})
        self.service.register_client_for_updates("session_2", {"name": "client2"})
        
        # Simulate a failure
        self.service.simulate_broadcast_failure("session_1", "connection_lost")
        
        # Broadcast update
        update = Mock(spec=StatusUpdate)
        update.update_type = "test_update"
        self.service.broadcast_status_update(update)
        
        result = self.service.validate_broadcasting_infrastructure()
        
        assert result["registered_clients"] == 2
        assert result["websocket_connections"] == 2
        assert result["failed_broadcasts"] == 1
        assert result["last_broadcast_timestamp"] is not None

    def test_service_call_logging(self):
        """Test that all method calls are logged"""
        session_id = "log_test_session"
        client_info = {"name": "log_test_client"}
        
        # Clear log
        self.service.call_log.clear()
        
        # Call methods
        update_result = self.service.register_client_for_updates(session_id, client_info)
        self.service.get_registered_clients_count()
        self.service.broadcast_status_update(update_result)
        self.service.get_last_broadcast_info()
        self.service.validate_broadcasting_infrastructure()
        self.service.unregister_client(session_id)
        
        expected_calls = [
            f"register_client_for_updates({session_id}, {client_info})",
            "get_registered_clients_count()",
            "broadcast_status_update(registration_confirmed)",
            "get_last_broadcast_info()",
            "validate_broadcasting_infrastructure()",
            f"unregister_client({session_id})"
        ]
        
        for expected_call in expected_calls:
            assert expected_call in self.service.call_log


class TestServiceContractCompliance:
    """Test suite to verify service contract compliance"""

    def test_concrete_implementation_must_implement_all_methods(self):
        """Test that concrete implementations must implement all abstract methods"""
        
        # This should work - all methods implemented
        class CompleteStatusBroadcastingService(StatusBroadcastingService):
            def register_client_for_updates(self, session_id: str, client_info: Dict[str, Any]) -> StatusUpdate:
                return Mock(spec=StatusUpdate)
            def unregister_client(self, session_id: str) -> bool:
                return False
            def broadcast_status_update(self, update: StatusUpdate) -> bool:
                return True
            def get_registered_clients_count(self) -> int:
                return 0
            def get_last_broadcast_info(self) -> Dict[str, Any]:
                return {}
            def validate_broadcasting_infrastructure(self) -> Dict[str, Any]:
                return {"status": "ok"}
        
        service = CompleteStatusBroadcastingService()
        assert isinstance(service, StatusBroadcastingService)
        
    def test_incomplete_implementation_fails(self):
        """Test that incomplete implementations cannot be instantiated"""
        
        # This should fail - missing methods
        class IncompleteStatusBroadcastingService(StatusBroadcastingService):
            def register_client_for_updates(self, session_id: str, client_info: Dict[str, Any]) -> StatusUpdate:
                return Mock(spec=StatusUpdate)
            # Missing other required methods
        
        with pytest.raises(TypeError):
            IncompleteStatusBroadcastingService()

    def test_method_signature_compliance(self):
        """Test that implementations must match method signatures"""
        service = MockStatusBroadcastingService()
        
        # Test return types
        update = service.register_client_for_updates("test", {})
        assert hasattr(update, 'update_type')  # StatusUpdate-like object
        
        assert isinstance(service.unregister_client("test"), bool)
        assert isinstance(service.get_registered_clients_count(), int)
        assert isinstance(service.get_last_broadcast_info(), dict)
        assert isinstance(service.validate_broadcasting_infrastructure(), dict)
        
        # Test broadcast_status_update
        mock_update = Mock(spec=StatusUpdate)
        mock_update.update_type = "test"
        assert isinstance(service.broadcast_status_update(mock_update), bool)


class TestEdgeCasesAndErrorHandling:
    """Test suite for edge cases and error handling"""

    def setup_method(self):
        """Set up test fixtures"""
        self.service = MockStatusBroadcastingService()

    def test_register_client_with_empty_client_info(self):
        """Test registering client with empty client info"""
        session_id = "empty_info_session"
        client_info = {}
        
        result = self.service.register_client_for_updates(session_id, client_info)
        
        assert result is not None
        assert result.session_id == session_id
        assert self.service.registered_clients[session_id] == {}

    def test_register_client_overwrites_existing(self):
        """Test that registering a client overwrites existing registration"""
        session_id = "overwrite_session"
        client_info1 = {"name": "client1", "version": "1.0.0"}
        client_info2 = {"name": "client2", "version": "2.0.0"}
        
        # Register first time
        self.service.register_client_for_updates(session_id, client_info1)
        assert self.service.registered_clients[session_id] == client_info1
        
        # Register again with different info
        self.service.register_client_for_updates(session_id, client_info2)
        assert self.service.registered_clients[session_id] == client_info2
        
        # Still only one client registered
        assert self.service.get_registered_clients_count() == 1

    def test_broadcast_with_status_update_without_session_id(self):
        """Test broadcasting with StatusUpdate that doesn't have session_id"""
        self.service.register_client_for_updates("session_1", {"name": "client1"})
        
        update = Mock(spec=StatusUpdate)
        update.update_type = "global_announcement"
        # No session_id attribute
        
        result = self.service.broadcast_status_update(update)
        
        assert result is True
        info = self.service.get_last_broadcast_info()
        assert info["session_id"] is None
        assert info["update_type"] == "global_announcement"

    def test_multiple_unregistrations(self):
        """Test multiple unregistration calls for same client"""
        session_id = "multi_unregister_session"
        
        # Register client
        self.service.register_client_for_updates(session_id, {"name": "client"})
        assert self.service.get_registered_clients_count() == 1
        
        # First unregister should succeed
        result1 = self.service.unregister_client(session_id)
        assert result1 is True
        assert self.service.get_registered_clients_count() == 0
        
        # Second unregister should fail
        result2 = self.service.unregister_client(session_id)
        assert result2 is False

    def test_broadcast_info_isolation(self):
        """Test that get_last_broadcast_info returns isolated copy"""
        self.service.register_client_for_updates("session_1", {"name": "client1"})
        
        update = Mock(spec=StatusUpdate)
        update.update_type = "test_isolation"
        update.data = {"mutable": ["list"]}
        
        self.service.broadcast_status_update(update)
        
        info1 = self.service.get_last_broadcast_info()
        info2 = self.service.get_last_broadcast_info()
        
        # Should be separate objects
        assert info1 is not info2
        
        # Modifying one shouldn't affect the other
        info1["new_key"] = "new_value"
        assert "new_key" not in info2