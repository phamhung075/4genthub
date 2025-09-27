"""Test suite for Server Repository Interface"""

import pytest
from abc import ABC, abstractmethod
from typing import Optional
from unittest.mock import Mock

from fastmcp.connection_management.domain.repositories.server_repository import ServerRepository
from fastmcp.connection_management.domain.entities.server import Server


class TestServerRepository:
    """Test suite for ServerRepository interface"""

    def test_server_repository_is_abstract(self):
        """Test that ServerRepository is an abstract base class"""
        assert issubclass(ServerRepository, ABC)
        
        # Should not be able to instantiate directly
        with pytest.raises(TypeError):
            ServerRepository()
    
    def test_server_repository_has_required_abstract_methods(self):
        """Test that ServerRepository defines all required abstract methods"""
        abstract_methods = ServerRepository.__abstractmethods__
        
        expected_methods = {
            'get_current_server',
            'save_server',
            'create_server',
            'update_server_uptime'
        }
        
        assert abstract_methods == expected_methods
    
    def test_get_current_server_signature(self):
        """Test get_current_server method signature"""
        method = ServerRepository.get_current_server
        
        # Check it's an abstract method
        assert hasattr(method, '__isabstractmethod__')
        assert method.__isabstractmethod__ is True
        
    def test_save_server_signature(self):
        """Test save_server method signature"""
        method = ServerRepository.save_server
        
        assert hasattr(method, '__isabstractmethod__')
        assert method.__isabstractmethod__ is True
        
    def test_create_server_signature(self):
        """Test create_server method signature"""
        method = ServerRepository.create_server
        
        assert hasattr(method, '__isabstractmethod__')
        assert method.__isabstractmethod__ is True
        
    def test_update_server_uptime_signature(self):
        """Test update_server_uptime method signature"""
        method = ServerRepository.update_server_uptime
        
        assert hasattr(method, '__isabstractmethod__')
        assert method.__isabstractmethod__ is True


class MockServerRepository(ServerRepository):
    """Mock implementation of ServerRepository for testing"""

    def __init__(self):
        self.current_server: Optional[Server] = None
        self.call_log: list = []

    def get_current_server(self) -> Optional[Server]:
        self.call_log.append("get_current_server()")
        return self.current_server

    def save_server(self, server: Server) -> None:
        self.call_log.append(f"save_server({server.name})")
        self.current_server = server

    def create_server(self, name: str, version: str, environment: dict, 
                      authentication: dict, task_management: dict) -> Server:
        self.call_log.append(f"create_server({name}, {version}, {environment}, {authentication}, {task_management})")
        server = Mock(spec=Server)
        server.name = name
        server.version = version
        server.environment = environment
        server.authentication = authentication
        server.task_management = task_management
        self.current_server = server
        return server

    def update_server_uptime(self, server: Server) -> None:
        self.call_log.append(f"update_server_uptime({server.name})")
        # Mock behavior - could update server.uptime_seconds if it exists
        if hasattr(server, 'uptime_seconds'):
            server.uptime_seconds += 1.0


class TestMockServerRepository:
    """Test suite for the mock implementation to verify contract compliance"""

    def setup_method(self):
        """Set up test fixtures"""
        self.repository = MockServerRepository()

    def test_mock_repository_instantiation(self):
        """Test that mock repository can be instantiated"""
        repository = MockServerRepository()
        assert isinstance(repository, ServerRepository)
        assert repository.current_server is None
        assert repository.call_log == []

    def test_get_current_server_returns_none_initially(self):
        """Test get_current_server returns None when no server exists"""
        result = self.repository.get_current_server()
        
        assert result is None
        assert "get_current_server()" in self.repository.call_log

    def test_get_current_server_returns_server_when_exists(self):
        """Test get_current_server returns server when one exists"""
        # Create a server first
        name = "test_server"
        version = "1.0.0"
        environment = {"env": "test"}
        authentication = {"auth": "enabled"}
        task_management = {"tasks": "enabled"}
        
        created_server = self.repository.create_server(
            name, version, environment, authentication, task_management
        )
        
        # Get the current server
        result = self.repository.get_current_server()
        
        assert result is not None
        assert result == created_server
        assert result.name == name
        assert result.version == version

    def test_save_server_stores_server(self):
        """Test save_server stores server properly"""
        server = Mock(spec=Server)
        server.name = "saved_server"
        
        self.repository.save_server(server)
        
        assert self.repository.current_server == server
        assert f"save_server({server.name})" in self.repository.call_log

    def test_create_server_creates_and_stores_server(self):
        """Test create_server creates and stores new server"""
        name = "new_server"
        version = "2.0.0"
        environment = {"env": "production"}
        authentication = {"method": "jwt"}
        task_management = {"enabled": True}
        
        result = self.repository.create_server(
            name, version, environment, authentication, task_management
        )
        
        assert result is not None
        assert result.name == name
        assert result.version == version
        assert result.environment == environment
        assert result.authentication == authentication
        assert result.task_management == task_management
        assert self.repository.current_server == result

    def test_create_server_with_empty_dicts(self):
        """Test create_server with empty dictionary parameters"""
        name = "minimal_server"
        version = "0.1.0"
        environment = {}
        authentication = {}
        task_management = {}
        
        result = self.repository.create_server(
            name, version, environment, authentication, task_management
        )
        
        assert result is not None
        assert result.name == name
        assert result.version == version
        assert result.environment == {}
        assert result.authentication == {}
        assert result.task_management == {}

    def test_update_server_uptime_calls_correctly(self):
        """Test update_server_uptime is called correctly"""
        server = Mock(spec=Server)
        server.name = "uptime_server"
        server.uptime_seconds = 100.0
        
        self.repository.update_server_uptime(server)
        
        assert f"update_server_uptime({server.name})" in self.repository.call_log
        assert server.uptime_seconds == 101.0  # Mock increments by 1

    def test_update_server_uptime_without_uptime_attribute(self):
        """Test update_server_uptime with server lacking uptime_seconds"""
        server = Mock(spec=Server)
        server.name = "no_uptime_server"
        # No uptime_seconds attribute
        
        # Should not raise an exception
        self.repository.update_server_uptime(server)
        
        assert f"update_server_uptime({server.name})" in self.repository.call_log

    def test_repository_call_logging(self):
        """Test that all method calls are logged"""
        name = "log_test_server"
        version = "1.0.0"
        environment = {"env": "test"}
        authentication = {"auth": "test"}
        task_management = {"task": "test"}
        
        # Clear log
        self.repository.call_log.clear()
        
        # Call methods
        self.repository.get_current_server()
        created_server = self.repository.create_server(
            name, version, environment, authentication, task_management
        )
        self.repository.save_server(created_server)
        self.repository.update_server_uptime(created_server)
        self.repository.get_current_server()
        
        expected_calls = [
            "get_current_server()",
            f"create_server({name}, {version}, {environment}, {authentication}, {task_management})",
            f"save_server({name})",
            f"update_server_uptime({name})",
            "get_current_server()"
        ]
        
        for expected_call in expected_calls:
            assert expected_call in self.repository.call_log

    def test_save_server_overwrites_current_server(self):
        """Test that save_server overwrites the current server"""
        # Create first server
        server1 = self.repository.create_server(
            "server1", "1.0.0", {}, {}, {}
        )
        
        assert self.repository.current_server == server1
        
        # Create and save second server
        server2 = Mock(spec=Server)
        server2.name = "server2"
        
        self.repository.save_server(server2)
        
        assert self.repository.current_server == server2
        assert self.repository.current_server != server1


class TestRepositoryContractCompliance:
    """Test suite to verify repository contract compliance"""

    def test_concrete_implementation_must_implement_all_methods(self):
        """Test that concrete implementations must implement all abstract methods"""
        
        # This should work - all methods implemented
        class CompleteServerRepository(ServerRepository):
            def get_current_server(self) -> Optional[Server]:
                return None
            def save_server(self, server: Server) -> None:
                pass
            def create_server(self, name: str, version: str, environment: dict, 
                            authentication: dict, task_management: dict) -> Server:
                return Mock(spec=Server)
            def update_server_uptime(self, server: Server) -> None:
                pass
        
        repo = CompleteServerRepository()
        assert isinstance(repo, ServerRepository)
        
    def test_incomplete_implementation_fails(self):
        """Test that incomplete implementations cannot be instantiated"""
        
        # This should fail - missing methods
        class IncompleteServerRepository(ServerRepository):
            def get_current_server(self) -> Optional[Server]:
                return None
            # Missing other required methods
        
        with pytest.raises(TypeError):
            IncompleteServerRepository()

    def test_method_signature_compliance(self):
        """Test that implementations must match method signatures"""
        repository = MockServerRepository()
        
        # Test return types and parameters
        result = repository.get_current_server()
        assert result is None or isinstance(result, Server)
        
        # Test create_server returns Server
        server = repository.create_server("test", "1.0", {}, {}, {})
        assert hasattr(server, 'name')  # Server-like object
        
        # Test method calls don't raise exceptions
        repository.save_server(server)
        repository.update_server_uptime(server)


class TestEdgeCasesAndErrorHandling:
    """Test suite for edge cases and error handling"""

    def setup_method(self):
        """Set up test fixtures"""
        self.repository = MockServerRepository()

    def test_create_server_with_special_characters(self):
        """Test create_server with special characters in parameters"""
        name = "test-server_123!@#"
        version = "1.0.0-alpha+build.123"
        environment = {"path": "/usr/local/bin", "special": "value!@#$%"}
        authentication = {"token": "eyJ0eXAiOiJKV1QiLCJhbGciOiJIUzI1NiJ9"}
        task_management = {"endpoint": "https://api.example.com/tasks?filter=active"}
        
        result = self.repository.create_server(
            name, version, environment, authentication, task_management
        )
        
        assert result.name == name
        assert result.version == version
        assert result.environment == environment
        assert result.authentication == authentication
        assert result.task_management == task_management

    def test_create_server_with_nested_dicts(self):
        """Test create_server with deeply nested dictionary structures"""
        name = "nested_server"
        version = "1.0.0"
        environment = {
            "database": {
                "host": "localhost",
                "port": 5432,
                "credentials": {
                    "user": "admin",
                    "encrypted": True
                }
            }
        }
        authentication = {
            "methods": ["jwt", "oauth2"],
            "config": {
                "jwt": {"expiry": 3600},
                "oauth2": {"provider": "github"}
            }
        }
        task_management = {
            "features": {
                "scheduling": True,
                "monitoring": {
                    "enabled": True,
                    "interval": 30
                }
            }
        }
        
        result = self.repository.create_server(
            name, version, environment, authentication, task_management
        )
        
        assert result.environment == environment
        assert result.authentication == authentication
        assert result.task_management == task_management

    def test_save_server_with_none(self):
        """Test behavior when saving None (should be handled by type system)"""
        # In a real implementation, this might raise a TypeError
        # In our mock, we'll just test the behavior
        server = Mock(spec=Server)
        server.name = None  # Edge case
        
        self.repository.save_server(server)
        
        assert self.repository.current_server == server
        assert "save_server(None)" in self.repository.call_log

    def test_repository_state_consistency(self):
        """Test that repository maintains consistent state"""
        # Create server
        server1 = self.repository.create_server(
            "server1", "1.0.0", {"env": "test"}, {}, {}
        )
        
        # Verify state
        assert self.repository.get_current_server() == server1
        
        # Create another server (should replace current)
        server2 = self.repository.create_server(
            "server2", "2.0.0", {"env": "prod"}, {}, {}
        )
        
        assert self.repository.get_current_server() == server2
        assert self.repository.get_current_server() != server1
        
        # Save the first server back (should replace current)
        self.repository.save_server(server1)
        
        assert self.repository.get_current_server() == server1
        assert self.repository.get_current_server() != server2