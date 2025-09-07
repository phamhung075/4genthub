"""Connection Management Domain Exceptions"""


class ConnectionError(Exception):
    """Base exception for connection management domain errors"""
    pass


class ServerNotFoundError(ConnectionError):
    """Raised when a server cannot be found"""
    
    def __init__(self, server_name: str):
        self.server_name = server_name
        super().__init__(f"Server not found: {server_name}")


class ConnectionNotFoundError(ConnectionError):
    """Raised when a connection cannot be found"""
    
    def __init__(self, connection_id: str):
        self.connection_id = connection_id
        super().__init__(f"Connection not found: {connection_id}")


class InvalidServerStatusError(ConnectionError):
    """Raised when server status is invalid"""
    
    def __init__(self, status: str):
        self.status = status
        super().__init__(f"Invalid server status: {status}")


class InvalidConnectionStatusError(ConnectionError):
    """Raised when connection status is invalid"""
    
    def __init__(self, status: str):
        self.status = status
        super().__init__(f"Invalid connection status: {status}")


class ServerHealthCheckFailedError(ConnectionError):
    """Raised when server health check fails"""
    
    def __init__(self, reason: str):
        self.reason = reason
        super().__init__(f"Server health check failed: {reason}")


class ConnectionHealthCheckFailedError(ConnectionError):
    """Raised when connection health check fails"""
    
    def __init__(self, connection_id: str, reason: str):
        self.connection_id = connection_id
        self.reason = reason
        super().__init__(f"Connection health check failed for {connection_id}: {reason}")


class StatusBroadcastError(ConnectionError):
    """Raised when status broadcasting fails"""
    
    def __init__(self, reason: str):
        self.reason = reason
        super().__init__(f"Status broadcast failed: {reason}") 