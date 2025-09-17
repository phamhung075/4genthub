"""Test suite for Connection Management Domain Exceptions"""

import pytest

from fastmcp.connection_management.domain.exceptions.connection_exceptions import (
    ConnectionError,
    ServerNotFoundError,
    ConnectionNotFoundError,
    InvalidServerStatusError,
    InvalidConnectionStatusError,
    ServerHealthCheckFailedError,
    ConnectionHealthCheckFailedError,
    StatusBroadcastError
)


class TestConnectionError:
    """Test suite for base ConnectionError class"""

    def test_connection_error_init(self):
        """Test ConnectionError initialization"""
        message = "Test connection error"
        error = ConnectionError(message)
        
        assert str(error) == message
        assert isinstance(error, Exception)
        
    def test_connection_error_inheritance(self):
        """Test ConnectionError inheritance"""
        error = ConnectionError("Test error")
        
        assert isinstance(error, Exception)
        assert issubclass(ConnectionError, Exception)


class TestServerNotFoundError:
    """Test suite for ServerNotFoundError"""

    def test_server_not_found_error_init(self):
        """Test ServerNotFoundError initialization"""
        server_name = "test_server"
        error = ServerNotFoundError(server_name)
        
        assert error.server_name == server_name
        assert str(error) == f"Server not found: {server_name}"
        assert isinstance(error, ConnectionError)
        
    def test_server_not_found_error_inheritance(self):
        """Test ServerNotFoundError inheritance"""
        error = ServerNotFoundError("test_server")
        
        assert isinstance(error, ConnectionError)
        assert isinstance(error, Exception)
        assert issubclass(ServerNotFoundError, ConnectionError)
        
    def test_server_not_found_error_with_special_chars(self):
        """Test ServerNotFoundError with special characters in server name"""
        server_name = "test-server_123!@#"
        error = ServerNotFoundError(server_name)
        
        assert error.server_name == server_name
        assert str(error) == f"Server not found: {server_name}"
        
    def test_server_not_found_error_with_empty_name(self):
        """Test ServerNotFoundError with empty server name"""
        server_name = ""
        error = ServerNotFoundError(server_name)
        
        assert error.server_name == server_name
        assert str(error) == "Server not found: "


class TestConnectionNotFoundError:
    """Test suite for ConnectionNotFoundError"""

    def test_connection_not_found_error_init(self):
        """Test ConnectionNotFoundError initialization"""
        connection_id = "conn_123"
        error = ConnectionNotFoundError(connection_id)
        
        assert error.connection_id == connection_id
        assert str(error) == f"Connection not found: {connection_id}"
        assert isinstance(error, ConnectionError)
        
    def test_connection_not_found_error_inheritance(self):
        """Test ConnectionNotFoundError inheritance"""
        error = ConnectionNotFoundError("conn_123")
        
        assert isinstance(error, ConnectionError)
        assert isinstance(error, Exception)
        assert issubclass(ConnectionNotFoundError, ConnectionError)
        
    def test_connection_not_found_error_with_uuid(self):
        """Test ConnectionNotFoundError with UUID-like connection ID"""
        connection_id = "550e8400-e29b-41d4-a716-446655440000"
        error = ConnectionNotFoundError(connection_id)
        
        assert error.connection_id == connection_id
        assert str(error) == f"Connection not found: {connection_id}"


class TestInvalidServerStatusError:
    """Test suite for InvalidServerStatusError"""

    def test_invalid_server_status_error_init(self):
        """Test InvalidServerStatusError initialization"""
        status = "invalid_status"
        error = InvalidServerStatusError(status)
        
        assert error.status == status
        assert str(error) == f"Invalid server status: {status}"
        assert isinstance(error, ConnectionError)
        
    def test_invalid_server_status_error_inheritance(self):
        """Test InvalidServerStatusError inheritance"""
        error = InvalidServerStatusError("invalid_status")
        
        assert isinstance(error, ConnectionError)
        assert isinstance(error, Exception)
        assert issubclass(InvalidServerStatusError, ConnectionError)
        
    def test_invalid_server_status_error_with_common_statuses(self):
        """Test InvalidServerStatusError with various status values"""
        statuses = ["unknown", "error", "404", "timeout", ""]
        
        for status in statuses:
            error = InvalidServerStatusError(status)
            assert error.status == status
            assert str(error) == f"Invalid server status: {status}"


class TestInvalidConnectionStatusError:
    """Test suite for InvalidConnectionStatusError"""

    def test_invalid_connection_status_error_init(self):
        """Test InvalidConnectionStatusError initialization"""
        status = "invalid_status"
        error = InvalidConnectionStatusError(status)
        
        assert error.status == status
        assert str(error) == f"Invalid connection status: {status}"
        assert isinstance(error, ConnectionError)
        
    def test_invalid_connection_status_error_inheritance(self):
        """Test InvalidConnectionStatusError inheritance"""
        error = InvalidConnectionStatusError("invalid_status")
        
        assert isinstance(error, ConnectionError)
        assert isinstance(error, Exception)
        assert issubclass(InvalidConnectionStatusError, ConnectionError)


class TestServerHealthCheckFailedError:
    """Test suite for ServerHealthCheckFailedError"""

    def test_server_health_check_failed_error_init(self):
        """Test ServerHealthCheckFailedError initialization"""
        reason = "Connection timeout"
        error = ServerHealthCheckFailedError(reason)
        
        assert error.reason == reason
        assert str(error) == f"Server health check failed: {reason}"
        assert isinstance(error, ConnectionError)
        
    def test_server_health_check_failed_error_inheritance(self):
        """Test ServerHealthCheckFailedError inheritance"""
        error = ServerHealthCheckFailedError("timeout")
        
        assert isinstance(error, ConnectionError)
        assert isinstance(error, Exception)
        assert issubclass(ServerHealthCheckFailedError, ConnectionError)
        
    def test_server_health_check_failed_error_with_various_reasons(self):
        """Test ServerHealthCheckFailedError with various failure reasons"""
        reasons = [
            "Connection timeout",
            "Server not responding",
            "Invalid response format",
            "Authentication failed",
            "Network error"
        ]
        
        for reason in reasons:
            error = ServerHealthCheckFailedError(reason)
            assert error.reason == reason
            assert str(error) == f"Server health check failed: {reason}"


class TestConnectionHealthCheckFailedError:
    """Test suite for ConnectionHealthCheckFailedError"""

    def test_connection_health_check_failed_error_init(self):
        """Test ConnectionHealthCheckFailedError initialization"""
        connection_id = "conn_123"
        reason = "Connection idle timeout"
        error = ConnectionHealthCheckFailedError(connection_id, reason)
        
        assert error.connection_id == connection_id
        assert error.reason == reason
        expected_message = f"Connection health check failed for {connection_id}: {reason}"
        assert str(error) == expected_message
        assert isinstance(error, ConnectionError)
        
    def test_connection_health_check_failed_error_inheritance(self):
        """Test ConnectionHealthCheckFailedError inheritance"""
        error = ConnectionHealthCheckFailedError("conn_123", "timeout")
        
        assert isinstance(error, ConnectionError)
        assert isinstance(error, Exception)
        assert issubclass(ConnectionHealthCheckFailedError, ConnectionError)
        
    def test_connection_health_check_failed_error_with_various_scenarios(self):
        """Test ConnectionHealthCheckFailedError with various scenarios"""
        test_cases = [
            ("conn_123", "Connection timeout"),
            ("550e8400-e29b-41d4-a716-446655440000", "Idle for too long"),
            ("websocket_conn_456", "Lost heartbeat"),
            ("", "Unknown connection error"),  # Edge case with empty connection_id
        ]
        
        for connection_id, reason in test_cases:
            error = ConnectionHealthCheckFailedError(connection_id, reason)
            assert error.connection_id == connection_id
            assert error.reason == reason
            expected_message = f"Connection health check failed for {connection_id}: {reason}"
            assert str(error) == expected_message


class TestStatusBroadcastError:
    """Test suite for StatusBroadcastError"""

    def test_status_broadcast_error_init(self):
        """Test StatusBroadcastError initialization"""
        reason = "WebSocket connection lost"
        error = StatusBroadcastError(reason)
        
        assert error.reason == reason
        assert str(error) == f"Status broadcast failed: {reason}"
        assert isinstance(error, ConnectionError)
        
    def test_status_broadcast_error_inheritance(self):
        """Test StatusBroadcastError inheritance"""
        error = StatusBroadcastError("broadcast failed")
        
        assert isinstance(error, ConnectionError)
        assert isinstance(error, Exception)
        assert issubclass(StatusBroadcastError, ConnectionError)
        
    def test_status_broadcast_error_with_various_reasons(self):
        """Test StatusBroadcastError with various failure reasons"""
        reasons = [
            "WebSocket connection lost",
            "Client disconnected",
            "Serialization error",
            "Network unreachable",
            "Rate limit exceeded"
        ]
        
        for reason in reasons:
            error = StatusBroadcastError(reason)
            assert error.reason == reason
            assert str(error) == f"Status broadcast failed: {reason}"


class TestExceptionHierarchy:
    """Test suite for verifying exception hierarchy"""

    def test_all_exceptions_inherit_from_connection_error(self):
        """Test that all domain exceptions inherit from ConnectionError"""
        exceptions = [
            ServerNotFoundError("server"),
            ConnectionNotFoundError("conn_123"),
            InvalidServerStatusError("invalid"),
            InvalidConnectionStatusError("invalid"),
            ServerHealthCheckFailedError("reason"),
            ConnectionHealthCheckFailedError("conn_123", "reason"),
            StatusBroadcastError("reason")
        ]
        
        for exception in exceptions:
            assert isinstance(exception, ConnectionError)
            assert isinstance(exception, Exception)
            
    def test_connection_error_inheritance_chain(self):
        """Test the inheritance chain from Exception to ConnectionError"""
        error = ConnectionError("test error")
        
        assert isinstance(error, Exception)
        assert type(error).__bases__ == (Exception,)
        
    def test_derived_exceptions_inheritance_chain(self):
        """Test inheritance chain for derived exceptions"""
        error = ServerNotFoundError("server")
        
        assert isinstance(error, ServerNotFoundError)
        assert isinstance(error, ConnectionError)
        assert isinstance(error, Exception)
        
        # Check class hierarchy
        assert issubclass(ServerNotFoundError, ConnectionError)
        assert issubclass(ConnectionError, Exception)


class TestExceptionAttributes:
    """Test suite for exception attributes and edge cases"""

    def test_exception_attributes_persistence(self):
        """Test that exception attributes persist correctly"""
        server_error = ServerNotFoundError("test_server")
        connection_error = ConnectionNotFoundError("conn_123")
        health_error = ConnectionHealthCheckFailedError("conn_456", "timeout")
        
        # Test that attributes are accessible after creation
        assert hasattr(server_error, "server_name")
        assert hasattr(connection_error, "connection_id")
        assert hasattr(health_error, "connection_id")
        assert hasattr(health_error, "reason")
        
    def test_exception_with_none_values(self):
        """Test exceptions with None values"""
        # Most of these would fail at the constructor level since they expect strings
        # But we can test what happens if we manually set attributes
        error = ConnectionError("test")
        error.custom_attr = None
        
        assert error.custom_attr is None
        
    def test_exception_str_representation_consistency(self):
        """Test that str representation is consistent"""
        server_name = "test_server"
        error = ServerNotFoundError(server_name)
        
        # Test multiple calls return the same string
        str1 = str(error)
        str2 = str(error)
        
        assert str1 == str2
        assert str1 == f"Server not found: {server_name}"