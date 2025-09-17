"""Test suite for Connection Repository Interface"""

import pytest
from abc import ABC, abstractmethod
from typing import List, Optional, Dict, Any
from unittest.mock import Mock, MagicMock

from fastmcp.connection_management.domain.repositories.connection_repository import ConnectionRepository
from fastmcp.connection_management.domain.entities.connection import Connection


class TestConnectionRepository:
    """Test suite for ConnectionRepository interface"""

    def test_connection_repository_is_abstract(self):
        """Test that ConnectionRepository is an abstract base class"""
        assert issubclass(ConnectionRepository, ABC)
        
        # Should not be able to instantiate directly
        with pytest.raises(TypeError):
            ConnectionRepository()
    
    def test_connection_repository_has_required_abstract_methods(self):
        """Test that ConnectionRepository defines all required abstract methods"""
        abstract_methods = ConnectionRepository.__abstractmethods__
        
        expected_methods = {
            'find_by_id',
            'find_all_active', 
            'save_connection',
            'create_connection',
            'remove_connection',
            'get_connection_count',
            'get_connection_statistics'
        }
        
        assert abstract_methods == expected_methods
    
    def test_find_by_id_signature(self):
        """Test find_by_id method signature"""
        method = ConnectionRepository.find_by_id
        
        # Check it's an abstract method
        assert hasattr(method, '__isabstractmethod__')
        assert method.__isabstractmethod__ is True
        
    def test_find_all_active_signature(self):
        """Test find_all_active method signature"""
        method = ConnectionRepository.find_all_active
        
        assert hasattr(method, '__isabstractmethod__')
        assert method.__isabstractmethod__ is True
        
    def test_save_connection_signature(self):
        """Test save_connection method signature"""
        method = ConnectionRepository.save_connection
        
        assert hasattr(method, '__isabstractmethod__')
        assert method.__isabstractmethod__ is True
        
    def test_create_connection_signature(self):
        """Test create_connection method signature"""
        method = ConnectionRepository.create_connection
        
        assert hasattr(method, '__isabstractmethod__')
        assert method.__isabstractmethod__ is True
        
    def test_remove_connection_signature(self):
        """Test remove_connection method signature"""
        method = ConnectionRepository.remove_connection
        
        assert hasattr(method, '__isabstractmethod__')
        assert method.__isabstractmethod__ is True
        
    def test_get_connection_count_signature(self):
        """Test get_connection_count method signature"""
        method = ConnectionRepository.get_connection_count
        
        assert hasattr(method, '__isabstractmethod__')
        assert method.__isabstractmethod__ is True
        
    def test_get_connection_statistics_signature(self):
        """Test get_connection_statistics method signature"""
        method = ConnectionRepository.get_connection_statistics
        
        assert hasattr(method, '__isabstractmethod__')
        assert method.__isabstractmethod__ is True


class MockConnectionRepository(ConnectionRepository):
    """Mock implementation of ConnectionRepository for testing"""

    def __init__(self):
        self.connections: Dict[str, Connection] = {}
        self.call_log: List[str] = []

    def find_by_id(self, connection_id: str) -> Optional[Connection]:
        self.call_log.append(f"find_by_id({connection_id})")
        return self.connections.get(connection_id)

    def find_all_active(self) -> List[Connection]:
        self.call_log.append("find_all_active()")
        return [conn for conn in self.connections.values() if conn.is_active()]

    def save_connection(self, connection: Connection) -> None:
        self.call_log.append(f"save_connection({connection.id})")
        self.connections[connection.id] = connection

    def create_connection(self, connection_id: str, client_info: Dict[str, Any]) -> Connection:
        self.call_log.append(f"create_connection({connection_id}, {client_info})")
        connection = Mock(spec=Connection)
        connection.id = connection_id
        connection.client_info = client_info
        connection.is_active.return_value = True
        self.connections[connection_id] = connection
        return connection

    def remove_connection(self, connection_id: str) -> bool:
        self.call_log.append(f"remove_connection({connection_id})")
        if connection_id in self.connections:
            del self.connections[connection_id]
            return True
        return False

    def get_connection_count(self) -> int:
        self.call_log.append("get_connection_count()")
        return len([conn for conn in self.connections.values() if conn.is_active()])

    def get_connection_statistics(self) -> Dict[str, Any]:
        self.call_log.append("get_connection_statistics()")
        active_count = self.get_connection_count()
        total_count = len(self.connections)
        return {
            "total_connections": total_count,
            "active_connections": active_count,
            "inactive_connections": total_count - active_count
        }


class TestMockConnectionRepository:
    """Test suite for the mock implementation to verify contract compliance"""

    def setup_method(self):
        """Set up test fixtures"""
        self.repository = MockConnectionRepository()

    def test_mock_repository_instantiation(self):
        """Test that mock repository can be instantiated"""
        repository = MockConnectionRepository()
        assert isinstance(repository, ConnectionRepository)
        assert repository.connections == {}
        assert repository.call_log == []

    def test_find_by_id_returns_none_for_nonexistent(self):
        """Test find_by_id returns None for non-existent connection"""
        result = self.repository.find_by_id("nonexistent_id")
        
        assert result is None
        assert "find_by_id(nonexistent_id)" in self.repository.call_log

    def test_find_by_id_returns_connection_when_exists(self):
        """Test find_by_id returns connection when it exists"""
        connection_id = "test_conn_123"
        client_info = {"name": "test_client"}
        
        # Create connection first
        created_conn = self.repository.create_connection(connection_id, client_info)
        
        # Find it
        found_conn = self.repository.find_by_id(connection_id)
        
        assert found_conn is not None
        assert found_conn.id == connection_id
        assert found_conn == created_conn

    def test_find_all_active_returns_empty_list_initially(self):
        """Test find_all_active returns empty list when no connections"""
        result = self.repository.find_all_active()
        
        assert result == []
        assert "find_all_active()" in self.repository.call_log

    def test_find_all_active_returns_only_active_connections(self):
        """Test find_all_active returns only active connections"""
        # Create active connection
        active_conn = self.repository.create_connection("active_123", {"type": "active"})
        
        # Create inactive connection
        inactive_conn = Mock(spec=Connection)
        inactive_conn.id = "inactive_456"
        inactive_conn.is_active.return_value = False
        self.repository.connections["inactive_456"] = inactive_conn
        
        result = self.repository.find_all_active()
        
        assert len(result) == 1
        assert result[0] == active_conn
        assert result[0].id == "active_123"

    def test_save_connection_stores_connection(self):
        """Test save_connection stores connection properly"""
        connection = Mock(spec=Connection)
        connection.id = "save_test_123"
        
        self.repository.save_connection(connection)
        
        assert "save_test_123" in self.repository.connections
        assert self.repository.connections["save_test_123"] == connection
        assert "save_connection(save_test_123)" in self.repository.call_log

    def test_create_connection_creates_and_stores_connection(self):
        """Test create_connection creates and stores new connection"""
        connection_id = "new_conn_123"
        client_info = {"name": "test_client", "version": "1.0.0"}
        
        result = self.repository.create_connection(connection_id, client_info)
        
        assert result is not None
        assert result.id == connection_id
        assert result.client_info == client_info
        assert connection_id in self.repository.connections
        assert self.repository.connections[connection_id] == result

    def test_remove_connection_removes_existing_connection(self):
        """Test remove_connection removes existing connection"""
        connection_id = "to_remove_123"
        self.repository.create_connection(connection_id, {})
        
        # Verify it exists
        assert connection_id in self.repository.connections
        
        result = self.repository.remove_connection(connection_id)
        
        assert result is True
        assert connection_id not in self.repository.connections

    def test_remove_connection_returns_false_for_nonexistent(self):
        """Test remove_connection returns False for non-existent connection"""
        result = self.repository.remove_connection("nonexistent_123")
        
        assert result is False

    def test_get_connection_count_returns_active_count(self):
        """Test get_connection_count returns count of active connections"""
        # Initially should be 0
        assert self.repository.get_connection_count() == 0
        
        # Add active connection
        self.repository.create_connection("active_1", {})
        assert self.repository.get_connection_count() == 1
        
        # Add inactive connection
        inactive_conn = Mock(spec=Connection)
        inactive_conn.is_active.return_value = False
        self.repository.connections["inactive_1"] = inactive_conn
        
        # Count should still be 1 (only active)
        assert self.repository.get_connection_count() == 1

    def test_get_connection_statistics_returns_correct_stats(self):
        """Test get_connection_statistics returns correct statistics"""
        # Add active connections
        self.repository.create_connection("active_1", {})
        self.repository.create_connection("active_2", {})
        
        # Add inactive connection
        inactive_conn = Mock(spec=Connection)
        inactive_conn.is_active.return_value = False
        self.repository.connections["inactive_1"] = inactive_conn
        
        stats = self.repository.get_connection_statistics()
        
        assert stats["total_connections"] == 3
        assert stats["active_connections"] == 2
        assert stats["inactive_connections"] == 1

    def test_repository_call_logging(self):
        """Test that all method calls are logged"""
        connection_id = "test_123"
        client_info = {"name": "test"}
        
        # Clear log
        self.repository.call_log.clear()
        
        # Call methods
        self.repository.find_by_id(connection_id)
        self.repository.find_all_active()
        self.repository.create_connection(connection_id, client_info)
        self.repository.get_connection_count()
        self.repository.get_connection_statistics()
        self.repository.remove_connection(connection_id)
        
        expected_calls = [
            f"find_by_id({connection_id})",
            "find_all_active()",
            f"create_connection({connection_id}, {client_info})",
            "get_connection_count()",
            "get_connection_statistics()",
            f"remove_connection({connection_id})"
        ]
        
        for expected_call in expected_calls:
            assert expected_call in self.repository.call_log


class TestRepositoryContractCompliance:
    """Test suite to verify repository contract compliance"""

    def test_concrete_implementation_must_implement_all_methods(self):
        """Test that concrete implementations must implement all abstract methods"""
        
        # This should work - all methods implemented
        class CompleteRepository(ConnectionRepository):
            def find_by_id(self, connection_id: str) -> Optional[Connection]:
                return None
            def find_all_active(self) -> List[Connection]:
                return []
            def save_connection(self, connection: Connection) -> None:
                pass
            def create_connection(self, connection_id: str, client_info: Dict[str, Any]) -> Connection:
                return Mock(spec=Connection)
            def remove_connection(self, connection_id: str) -> bool:
                return False
            def get_connection_count(self) -> int:
                return 0
            def get_connection_statistics(self) -> Dict[str, Any]:
                return {}
        
        repo = CompleteRepository()
        assert isinstance(repo, ConnectionRepository)
        
    def test_incomplete_implementation_fails(self):
        """Test that incomplete implementations cannot be instantiated"""
        
        # This should fail - missing methods
        class IncompleteRepository(ConnectionRepository):
            def find_by_id(self, connection_id: str) -> Optional[Connection]:
                return None
            # Missing other required methods
        
        with pytest.raises(TypeError):
            IncompleteRepository()

    def test_method_signature_compliance(self):
        """Test that implementations must match method signatures"""
        repository = MockConnectionRepository()
        
        # Test return types and parameters
        assert repository.find_by_id("test") is None or isinstance(repository.find_by_id("test"), Connection)
        assert isinstance(repository.find_all_active(), list)
        assert isinstance(repository.remove_connection("test"), bool)
        assert isinstance(repository.get_connection_count(), int)
        assert isinstance(repository.get_connection_statistics(), dict)